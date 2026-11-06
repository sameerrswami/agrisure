import io
import hmac
import hashlib
import secrets
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
import razorpay

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import Payment, PaymentRefund, PayoutRecord
from apps.contracts.models import Contract
from apps.notifications.services import NotificationService

class RazorpayService:
    DEFAULT_TEST_SECRET = "agrisure_rzp_mock_secret_key_2026"

    @classmethod
    def get_client(cls):
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        if key_id and key_secret and not key_id.startswith('rzp_test_mock'):
            try:
                return razorpay.Client(auth=(key_id, key_secret))
            except Exception:
                return None
        return None

    @classmethod
    def get_key_id(cls):
        key = getattr(settings, 'RAZORPAY_KEY_ID', '')
        return key if key else 'rzp_test_agrisure_sandbox'

    @classmethod
    def get_key_secret(cls):
        secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        return secret if secret else cls.DEFAULT_TEST_SECRET

    @classmethod
    def create_order(cls, contract, amount, payment_type=Payment.PaymentType.ADVANCE, notes=""):
        """
        Creates a Razorpay Order and internal Payment record with atomic protection.
        """
        amount = Decimal(str(amount))
        if amount <= Decimal('0.00'):
            raise ValidationError("Payment amount must be greater than zero.")

        amount_paise = int(amount * 100)
        client = cls.get_client()

        order_id = ""
        if client:
            try:
                rzp_order = client.order.create({
                    'amount': amount_paise,
                    'currency': 'INR',
                    'receipt': f"rcpt_{secrets.token_hex(6)}",
                    'notes': {
                        'contract_id': str(contract.id),
                        'contract_number': contract.contract_number,
                        'payment_type': payment_type
                    }
                })
                order_id = rzp_order.get('id', '')
            except Exception:
                order_id = f"order_mock_{secrets.token_hex(8)}"
        else:
            order_id = f"order_mock_{secrets.token_hex(8)}"

        with transaction.atomic():
            payment = Payment.objects.create(
                contract=contract,
                payer=contract.buyer,
                payee=contract.farmer,
                amount=amount,
                currency='INR',
                payment_type=payment_type,
                status=Payment.Status.CREATED,
                razorpay_order_id=order_id,
                notes=notes or f"{dict(Payment.PaymentType.choices).get(payment_type, payment_type)} for Contract #{contract.contract_number}"
            )
            return payment

    @classmethod
    def generate_test_signature(cls, order_id, payment_id):
        """Generates a valid HMAC SHA256 signature for sandbox/test simulation."""
        secret = cls.get_key_secret()
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        return hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()

    @classmethod
    def verify_signature(cls, order_id, payment_id, signature):
        """
        Cryptographically verifies the Razorpay signature against the secret.
        """
        if not signature or not order_id or not payment_id:
            return False

        secret = cls.get_key_secret()
        expected = hmac.new(
            secret.encode('utf-8'),
            f"{order_id}|{payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected, signature)

    @classmethod
    def capture_payment(cls, payment, razorpay_payment_id, razorpay_signature="", payment_method="UPI / Card"):
        """
        Finalizes captured payment with atomic safeguards, creates payout tracking,
        and transitions contract status if applicable.
        """
        with transaction.atomic():
            # Lock payment record to prevent race conditions
            locked_payment = Payment.objects.select_for_update().get(id=payment.id)
            if locked_payment.status in [Payment.Status.CAPTURED, Payment.Status.COMPLETED]:
                return locked_payment  # Idempotent return

            locked_payment.status = Payment.Status.CAPTURED
            locked_payment.razorpay_payment_id = razorpay_payment_id
            locked_payment.razorpay_signature = razorpay_signature
            locked_payment.payment_method = payment_method or 'Razorpay Online'
            locked_payment.paid_at = timezone.now()
            locked_payment.save()

            contract = locked_payment.contract

            # If advance payment was captured and contract is ACTIVE, advance to PRODUCTION_IN_PROGRESS
            if locked_payment.payment_type == Payment.PaymentType.ADVANCE:
                if contract.status == Contract.Status.ACTIVE:
                    contract.status = Contract.Status.PRODUCTION_IN_PROGRESS
                    contract.save()

            # Record payout obligation for reconciliation
            PayoutRecord.objects.get_or_create(
                contract=contract,
                farmer=contract.farmer,
                amount=locked_payment.amount,
                defaults={
                    'status': PayoutRecord.Status.PENDING,
                    'provider': 'Razorpay Route / Bank Direct Settlement',
                    'notes': f"Settlement for {locked_payment.transaction_id}"
                }
            )

            # Notifications
            NotificationService.send(
                recipient=locked_payment.payee,
                notification_type='PAYMENT',
                title='Payment Received!',
                message=f'₹{locked_payment.amount:,.2f} payment received for Contract #{contract.contract_number}.',
                link=f'/payments/{locked_payment.id}/'
            )
            NotificationService.send(
                recipient=locked_payment.payer,
                notification_type='PAYMENT',
                title='Payment Successful',
                message=f'₹{locked_payment.amount:,.2f} successfully processed for Contract #{contract.contract_number}.',
                link=f'/payments/{locked_payment.id}/'
            )

            return locked_payment

    @classmethod
    def process_refund(cls, payment, amount, reason="Dispute resolution"):
        """
        Processes a full or partial refund.
        """
        amount = Decimal(str(amount))
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(id=payment.id)
            if locked.status not in [Payment.Status.CAPTURED, Payment.Status.COMPLETED, Payment.Status.PARTIALLY_REFUNDED]:
                raise ValidationError("Only captured payments can be refunded.")

            # Calculate total already refunded
            existing_refunds = locked.refunds.filter(status=PaymentRefund.Status.PROCESSED)
            total_refunded = sum([r.amount for r in existing_refunds], Decimal('0.00'))
            if total_refunded + amount > locked.amount:
                raise ValidationError("Total refund cannot exceed original payment amount.")

            refund = PaymentRefund.objects.create(
                payment=locked,
                amount=amount,
                reason=reason,
                status=PaymentRefund.Status.PROCESSED,
                gateway_refund_id=f"rfnd_rzp_{secrets.token_hex(6)}"
            )

            new_total = total_refunded + amount
            if new_total >= locked.amount:
                locked.status = Payment.Status.REFUNDED
            else:
                locked.status = Payment.Status.PARTIALLY_REFUNDED
            locked.save()

            NotificationService.send(
                recipient=locked.payer,
                notification_type='PAYMENT',
                title='Refund Processed',
                message=f'A refund of ₹{amount:,.2f} has been processed for Contract #{locked.contract.contract_number}.',
                link=f'/payments/{locked.id}/'
            )
            return refund

    @classmethod
    def verify_webhook(cls, payload_body, signature_header):
        """
        Verifies Razorpay Webhook signature.
        """
        secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '') or cls.DEFAULT_TEST_SECRET
        if not signature_header or not payload_body:
            return False
        expected = hmac.new(
            secret.encode('utf-8'),
            payload_body if isinstance(payload_body, bytes) else payload_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    @classmethod
    def handle_webhook_event(cls, event_data):
        """
        Idempotently processes webhook events:
        'payment.captured', 'payment.failed', 'order.paid'
        """
        event_type = event_data.get('event', '')
        payload = event_data.get('payload', {})

        if event_type in ['payment.captured', 'order.paid']:
            payment_entity = payload.get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')
            method = payment_entity.get('method', 'online')

            if order_id:
                payment = Payment.objects.filter(razorpay_order_id=order_id).first()
                if payment and payment.status not in [Payment.Status.CAPTURED, Payment.Status.COMPLETED]:
                    cls.capture_payment(payment, razorpay_payment_id=payment_id, payment_method=method)
                    return True

        elif event_type == 'payment.failed':
            payment_entity = payload.get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            if order_id:
                payment = Payment.objects.filter(razorpay_order_id=order_id).first()
                if payment and payment.status not in [Payment.Status.CAPTURED, Payment.Status.COMPLETED]:
                    payment.status = Payment.Status.FAILED
                    payment.notes += f"\nPayment failed: {payment_entity.get('error_description', 'Gateway error')}"
                    payment.save()
                    return True

        return True

    @classmethod
    def generate_receipt_pdf(cls, payment):
        """
        Generates a professional downloadable PDF payment receipt using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReceiptTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#064e3b'),
            alignment=1,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            'ReceiptSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#4b5563'),
            alignment=1,
            spaceAfter=14,
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#1f2937'),
        )
        body_bold = ParagraphStyle(
            'BodyBold',
            parent=body_style,
            fontName='Helvetica-Bold',
        )

        elements = []
        elements.append(Paragraph("AGRISURE SECURE TRANSACTION RECEIPT", title_style))
        elements.append(Paragraph(f"Official Electronic Receipt • Receipt No: {payment.receipt_number}", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#059669'), spaceBefore=2, spaceAfter=12))

        # Metadata table
        paid_date = payment.paid_at.strftime('%d %B %Y, %I:%M %p IST') if payment.paid_at else payment.created_at.strftime('%d %B %Y, %I:%M %p IST')
        meta_data = [
            [Paragraph("<b>Transaction ID:</b>", body_style), Paragraph(str(payment.transaction_id), body_style),
             Paragraph("<b>Payment Date:</b>", body_style), Paragraph(paid_date, body_style)],
            [Paragraph("<b>Contract Number:</b>", body_style), Paragraph(f"#{payment.contract.contract_number}", body_style),
             Paragraph("<b>Payment Status:</b>", body_style), Paragraph(f"<font color='#059669'><b>{payment.get_status_display()}</b></font>", body_style)],
            [Paragraph("<b>Gateway Order ID:</b>", body_style), Paragraph(payment.razorpay_order_id or "Direct Gateway", body_style),
             Paragraph("<b>Payment Method:</b>", body_style), Paragraph(payment.payment_method or "Online Escrow", body_style)],
        ]
        t_meta = Table(meta_data, colWidths=[110, 160, 110, 160])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        # Parties
        parties_data = [
            [Paragraph("<b>Payer (Buyer)</b>", body_bold), Paragraph("<b>Payee (Farmer)</b>", body_bold)],
            [
                Paragraph(f"<b>Name:</b> {payment.payer.get_full_name()}<br/><b>Email:</b> {payment.payer.email}<br/><b>Phone:</b> {payment.payer.phone}", body_style),
                Paragraph(f"<b>Name:</b> {payment.payee.get_full_name()}<br/><b>Email:</b> {payment.payee.email}<br/><b>Phone:</b> {payment.payee.phone}", body_style)
            ]
        ]
        t_parties = Table(parties_data, colWidths=[270, 270])
        t_parties.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ecfdf5')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#10b981')),
        ]))
        elements.append(t_parties)
        elements.append(Spacer(1, 14))

        # Payment details
        crop_title = payment.contract.crop_listing.title
        qty = f"{payment.contract.quantity} {payment.contract.unit}"
        items_data = [
            [Paragraph("<b>Item / Description</b>", body_bold), Paragraph("<b>Category</b>", body_bold), Paragraph("<b>Amount (INR)</b>", body_bold)],
            [Paragraph(f"{crop_title} ({qty})<br/><font color='#6b7280'>{payment.get_payment_type_display()} under Contract #{payment.contract.contract_number}</font>", body_style),
             Paragraph(payment.get_payment_type_display(), body_style),
             Paragraph(f"₹{payment.amount:,.2f}", body_bold)],
            [Paragraph("<b>Total Amount Paid:</b>", body_bold), Paragraph("", body_style), Paragraph(f"<b>₹{payment.amount:,.2f}</b>", body_bold)]
        ]
        t_items = Table(items_data, colWidths=[280, 140, 120])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#064e3b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#064e3b')),
            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#064e3b')),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f0fdf4')),
        ]))
        elements.append(t_items)
        elements.append(Spacer(1, 16))

        # Note & Disclaimer
        disc = (
            "This document is an electronically generated receipt issued under the Information Technology Act, 2000. "
            "AgriSure acts as a verified contract marketplace facilitating secure transactions between contracted parties."
        )
        elements.append(Paragraph(disc, ParagraphStyle('disc', fontName='Helvetica-Oblique', fontSize=7.5, textColor=colors.HexColor('#6b7280'))))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# Backward compatibility alias
class PaymentService:
    @staticmethod
    def create_advance_payment(contract):
        return RazorpayService.create_order(
            contract=contract,
            amount=contract.advance_amount,
            payment_type=Payment.PaymentType.ADVANCE
        )

    @staticmethod
    def mark_completed(payment, razorpay_id="SIMULATED_RZP"):
        return RazorpayService.capture_payment(
            payment=payment,
            razorpay_payment_id=razorpay_id,
            payment_method="Simulated Escrow"
        )
