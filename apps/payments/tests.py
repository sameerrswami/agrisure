from decimal import Decimal
import json
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract
from apps.payments.models import Payment, PaymentRefund, PayoutRecord
from apps.payments.services import RazorpayService

class PaymentManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CropCategory.objects.create(name='Oilseeds', slug='oilseeds')

        self.farmer = User.objects.create_user(
            email='farmer.pay@agrisure.in', password='Password123!',
            first_name='Kisan', last_name='Ram', role=User.Role.FARMER,
            phone='9811122233', email_verified=True
        )
        FarmerProfile.objects.create(user=self.farmer, farm_name='Ram Oil Farm', is_verified=True)

        self.buyer = User.objects.create_user(
            email='buyer.pay@agrisure.in', password='Password123!',
            first_name='Adani', last_name='Wilmar', role=User.Role.BUYER,
            phone='9822233344', email_verified=True
        )
        BuyerProfile.objects.create(user=self.buyer, company_name='Adani Wilmar', is_verified=True)

        self.admin = User.objects.create_user(
            email='admin.pay@agrisure.in', password='Password123!',
            first_name='Admin', last_name='User', role=User.Role.ADMIN,
            is_staff=True, is_superuser=True
        )

        self.crop = CropListing.objects.create(
            farmer=self.farmer, category=self.category, title='Mustard Seed High Oil',
            quantity_available=Decimal('200.00'), quantity_remaining=Decimal('200.00'),
            price_per_unit=Decimal('5500.00'), unit=CropListing.Unit.QUINTAL,
            state='Rajasthan', district='Alwar', status=CropListing.Status.ACTIVE
        )

        self.contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            quantity=Decimal('100.00'),
            unit='quintal',
            price_per_unit=Decimal('5500.00'),
            total_amount=Decimal('550000.00'),
            advance_payment_percentage=Decimal('20.00'),
            advance_amount=Decimal('110000.00'),
            delivery_date=date.today() + timedelta(days=30),
            delivery_address='Adani Warehouse, Alwar',
            status=Contract.Status.ACTIVE
        )

    def test_successful_razorpay_order_and_signature_verification(self):
        """Test complete workflow: create order, verify signature, capture payment."""
        self.client.login(email='buyer.pay@agrisure.in', password='Password123!')

        # 1. Initiate checkout view creates server order
        resp = self.client.get(reverse('payments:initiate', kwargs={'contract_id': self.contract.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'AgriSure Secure Payment')

        payment = Payment.objects.filter(contract=self.contract).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('110000.00'))
        self.assertEqual(payment.currency, 'INR')
        self.assertTrue(payment.razorpay_order_id.startswith('order_'))

        # 2. Simulate valid Razorpay client callback
        valid_payment_id = f"pay_test_{payment.transaction_id}"
        valid_signature = RazorpayService.generate_test_signature(
            order_id=payment.razorpay_order_id,
            payment_id=valid_payment_id
        )

        # 3. Post verification
        verify_resp = self.client.post(reverse('payments:verify'), {
            'payment_id': str(payment.id),
            'razorpay_order_id': payment.razorpay_order_id,
            'razorpay_payment_id': valid_payment_id,
            'razorpay_signature': valid_signature,
            'payment_method': 'UPI / NetBanking'
        }, follow=True)

        self.assertEqual(verify_resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(payment.razorpay_payment_id, valid_payment_id)
        self.assertIsNotNone(payment.paid_at)

        # Contract transitioned from ACTIVE to PRODUCTION_IN_PROGRESS upon advance
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.PRODUCTION_IN_PROGRESS)

        # Farmer payout tracking record created
        payout = PayoutRecord.objects.filter(contract=self.contract, farmer=self.farmer).first()
        self.assertIsNotNone(payout)
        self.assertEqual(payout.amount, payment.amount)
        self.assertEqual(payout.status, PayoutRecord.Status.PENDING)

    def test_invalid_signature_rejected(self):
        """Test security: tampered or invalid signature is rejected and marks payment FAILED."""
        self.client.login(email='buyer.pay@agrisure.in', password='Password123!')

        payment = RazorpayService.create_order(
            contract=self.contract,
            amount=Decimal('50000.00'),
            payment_type=Payment.PaymentType.PARTIAL
        )

        resp = self.client.post(reverse('payments:verify'), {
            'payment_id': str(payment.id),
            'razorpay_order_id': payment.razorpay_order_id,
            'razorpay_payment_id': 'pay_fake_9999',
            'razorpay_signature': 'invalid_tampered_signature_hex_12345'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIn("Signature verification failed", payment.notes)

    def test_idempotent_webhook_handling(self):
        """Test webhook idempotency: duplicate webhooks do not duplicate captures or throw errors."""
        payment = RazorpayService.create_order(
            contract=self.contract,
            amount=Decimal('110000.00'),
            payment_type=Payment.PaymentType.ADVANCE
        )

        webhook_payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': f"pay_hook_{payment.transaction_id}",
                        'order_id': payment.razorpay_order_id,
                        'amount': 11000000,
                        'currency': 'INR',
                        'method': 'upi'
                    }
                }
            }
        }

        # First webhook delivery
        resp1 = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps(webhook_payload),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)

        # Second duplicate webhook delivery
        resp2 = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps(webhook_payload),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)

    def test_failed_payment_webhook(self):
        """Test webhook handling for payment.failed event."""
        payment = RazorpayService.create_order(
            contract=self.contract,
            amount=Decimal('110000.00')
        )
        webhook_payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': f"pay_failed_{payment.transaction_id}",
                        'order_id': payment.razorpay_order_id,
                        'error_description': 'Customer cancelled transaction at bank page'
                    }
                }
            }
        }
        resp = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps(webhook_payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_refund_recording_and_validation(self):
        """Test issuing partial and full refunds with constraint checking."""
        payment = RazorpayService.create_order(contract=self.contract, amount=Decimal('100000.00'))
        RazorpayService.capture_payment(payment, razorpay_payment_id='pay_capture_for_refund')

        # Partial refund
        rfnd1 = RazorpayService.process_refund(payment, amount=Decimal('40000.00'), reason='Damaged bags return')
        self.assertIsInstance(rfnd1, PaymentRefund)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PARTIALLY_REFUNDED)

        # Remaining refund to complete full refund
        rfnd2 = RazorpayService.process_refund(payment, amount=Decimal('60000.00'), reason='Complete resolution')
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)

        # Exceeding refund raises error
        with self.assertRaises(Exception):
            RazorpayService.process_refund(payment, amount=Decimal('5000.00'), reason='Excess refund should fail')

    def test_download_receipt_pdf(self):
        """Test ReportLab PDF receipt generation endpoint."""
        self.client.login(email='buyer.pay@agrisure.in', password='Password123!')
        payment = RazorpayService.create_order(contract=self.contract, amount=Decimal('110000.00'))
        RazorpayService.capture_payment(payment, razorpay_payment_id='pay_receipt_test')

        resp = self.client.get(reverse('payments:download_receipt', kwargs={'pk': payment.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
