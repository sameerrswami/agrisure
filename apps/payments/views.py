import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.conf import settings
from django.db.models import Sum, Q

from .models import Payment, PaymentRefund, PayoutRecord
from .services import RazorpayService
from apps.contracts.models import Contract
from apps.accounts.decorators import admin_required

@login_required
def payment_list(request):
    user = request.user
    payments = Payment.objects.none()
    
    if user.is_farmer:
        payments = Payment.objects.filter(payee=user).select_related('contract', 'payer', 'payee')
        captured = payments.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
        total_earnings = sum([p.amount for p in captured], Decimal('0.00'))
        
        # Pending payments on active contracts
        farmer_contracts = Contract.objects.filter(farmer=user, status__in=[
            Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS,
            Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED,
            Contract.Status.DELIVERED
        ])
        pending_amount = sum([c.remaining_payment_amount for c in farmer_contracts], Decimal('0.00'))
        
        context = {
            'payments': payments,
            'role': 'FARMER',
            'total_earnings': total_earnings,
            'received_count': captured.count(),
            'pending_amount': pending_amount,
            'active_contracts_count': farmer_contracts.count(),
        }
    elif user.is_buyer:
        payments = Payment.objects.filter(payer=user).select_related('contract', 'payer', 'payee')
        captured = payments.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
        total_expenditure = sum([p.amount for p in captured], Decimal('0.00'))
        
        buyer_contracts = Contract.objects.filter(buyer=user, status__in=[
            Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS,
            Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED,
            Contract.Status.DELIVERED
        ])
        pending_amount = sum([c.remaining_payment_amount for c in buyer_contracts], Decimal('0.00'))
        
        context = {
            'payments': payments,
            'role': 'BUYER',
            'total_expenditure': total_expenditure,
            'completed_count': captured.count(),
            'pending_amount': pending_amount,
            'active_contracts_count': buyer_contracts.count(),
        }
    else:  # Admin
        payments = Payment.objects.all().select_related('contract', 'payer', 'payee')
        captured = payments.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
        total_volume = sum([p.amount for p in captured], Decimal('0.00'))
        failed_count = payments.filter(status=Payment.Status.FAILED).count()
        refunded_count = payments.filter(status__in=[Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED]).count()
        
        context = {
            'payments': payments,
            'role': 'ADMIN',
            'total_volume': total_volume,
            'captured_count': captured.count(),
            'failed_count': failed_count,
            'refunded_count': refunded_count,
        }

    return render(request, 'payments/list.html', context)


@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('contract', 'payer', 'payee'), pk=pk)
    if request.user != payment.payer and request.user != payment.payee and not request.user.is_admin_user:
        messages.error(request, "Unauthorized access.")
        return redirect('payments:list')
    
    refunds = payment.refunds.all()
    return render(request, 'payments/detail.html', {'payment': payment, 'refunds': refunds})


@login_required
def initiate_payment(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    if request.user != contract.buyer:
        messages.error(request, "Only the contracted buyer can make payments.")
        return redirect('contracts:detail', pk=contract.pk)

    # Determine default type & amount
    payment_type = request.GET.get('type') or request.POST.get('payment_type')
    amount = Decimal('0.00')

    if not payment_type:
        if not contract.is_advance_paid:
            payment_type = Payment.PaymentType.ADVANCE
            amount = contract.advance_amount
        elif contract.remaining_payment_amount > Decimal('0.00'):
            payment_type = Payment.PaymentType.REMAINING
            amount = contract.remaining_payment_amount
        else:
            messages.info(request, "This contract has already been fully paid.")
            return redirect('contracts:detail', pk=contract.pk)
    else:
        if payment_type == Payment.PaymentType.ADVANCE:
            amount = contract.advance_amount
        elif payment_type in [Payment.PaymentType.REMAINING, Payment.PaymentType.FINAL]:
            amount = contract.remaining_payment_amount
        elif payment_type == Payment.PaymentType.FULL:
            amount = contract.total_amount
        elif payment_type in [Payment.PaymentType.PARTIAL, Payment.PaymentType.MILESTONE]:
            custom_amt = request.POST.get('custom_amount') or request.GET.get('custom_amount')
            if custom_amt:
                try:
                    amount = Decimal(custom_amt)
                except Exception:
                    amount = contract.advance_amount
            else:
                amount = min(contract.remaining_payment_amount, contract.advance_amount)

    if amount <= Decimal('0.00'):
        messages.error(request, "Invalid payment amount calculated.")
        return redirect('contracts:detail', pk=contract.pk)

    # Create server-side Razorpay order
    payment = RazorpayService.create_order(
        contract=contract,
        amount=amount,
        payment_type=payment_type,
        notes=f"{dict(Payment.PaymentType.choices).get(payment_type, payment_type)} for Contract #{contract.contract_number}"
    )

    # Prepare checkout context
    razorpay_key_id = RazorpayService.get_key_id()
    amount_paise = int(payment.amount * 100)

    # Pre-generate sandbox test signature so test simulation completes verified
    test_signature = RazorpayService.generate_test_signature(
        order_id=payment.razorpay_order_id,
        payment_id=f"pay_sim_{payment.transaction_id}"
    )

    context = {
        'contract': contract,
        'payment': payment,
        'razorpay_key_id': razorpay_key_id,
        'amount_paise': amount_paise,
        'test_payment_id': f"pay_sim_{payment.transaction_id}",
        'test_signature': test_signature,
    }
    return render(request, 'payments/checkout.html', context)


@login_required
def verify_payment(request):
    """
    POST view called when Razorpay checkout succeeds or test sandbox payment is submitted.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    order_id = request.POST.get('razorpay_order_id', '').strip()
    payment_id = request.POST.get('razorpay_payment_id', '').strip()
    signature = request.POST.get('razorpay_signature', '').strip()
    payment_pk = request.POST.get('payment_id', '').strip()

    payment = None
    if payment_pk:
        payment = Payment.objects.filter(id=payment_pk).first()
    elif order_id:
        payment = Payment.objects.filter(razorpay_order_id=order_id).first()

    if not payment:
        messages.error(request, "Payment record not found.")
        return redirect('payments:list')

    # Security check: User must be the payer or admin
    if request.user != payment.payer and not request.user.is_admin_user:
        messages.error(request, "Unauthorized.")
        return redirect('payments:list')

    # Verify signature
    is_valid = RazorpayService.verify_signature(order_id, payment_id, signature)
    if not is_valid:
        payment.status = Payment.Status.FAILED
        payment.notes += "\nSignature verification failed on server."
        payment.save()
        messages.error(request, "Security verification failed! The payment signature could not be verified.")
        return redirect('payments:detail', pk=payment.pk)

    # Signature is cryptographically verified -> Capture payment
    payment_method = request.POST.get('payment_method', 'Razorpay Checkout')
    captured_payment = RazorpayService.capture_payment(
        payment=payment,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
        payment_method=payment_method
    )

    messages.success(request, f"Payment of ₹{captured_payment.amount:,.2f} verified and processed successfully!")
    return redirect('payments:detail', pk=captured_payment.pk)


@csrf_exempt
def razorpay_webhook(request):
    """
    Idempotent Webhook endpoint for Razorpay real-time callbacks.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    signature = request.headers.get('X-Razorpay-Signature', '')
    payload_body = request.body

    # In production, verify signature if secret configured
    if getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', ''):
        if not RazorpayService.verify_webhook(payload_body, signature):
            return HttpResponse(status=400)

    try:
        data = json.loads(payload_body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    success = RazorpayService.handle_webhook_event(data)
    return HttpResponse(status=200 if success else 400)


@login_required
def download_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('contract', 'payer', 'payee'), pk=pk)
    if request.user != payment.payer and request.user != payment.payee and not request.user.is_admin_user:
        messages.error(request, "Unauthorized access.")
        return redirect('payments:list')

    pdf_bytes = RazorpayService.generate_receipt_pdf(payment)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="AgriSure_Receipt_{payment.receipt_number}.pdf"'
    return response


@login_required
@admin_required
def admin_refund_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        reason = request.POST.get('reason', 'Admin dispute resolution')
        try:
            refund = RazorpayService.process_refund(payment, amount=amount, reason=reason)
            messages.success(request, f"Refund #{refund.refund_id} for ₹{refund.amount:,.2f} processed successfully.")
        except Exception as e:
            messages.error(request, f"Refund failed: {str(e)}")
    return redirect('payments:detail', pk=payment.pk)
