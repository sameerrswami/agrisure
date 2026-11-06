import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone

class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        PENDING = 'PENDING', 'Pending Payment'
        AUTHORIZED = 'AUTHORIZED', 'Authorized'
        CAPTURED = 'CAPTURED', 'Captured & Settled'
        COMPLETED = 'COMPLETED', 'Completed & Credited'  # Backward compatibility
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially Refunded'
        PROCESSING = 'PROCESSING', 'Processing'  # Backward compatibility
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentType(models.TextChoices):
        ADVANCE = 'ADVANCE', 'Advance Payment'
        PARTIAL = 'PARTIAL', 'Partial / Milestone Payment'
        MILESTONE = 'MILESTONE', 'Milestone Settlement'  # Backward compatibility
        REMAINING = 'REMAINING', 'Remaining Balance Payment'
        FINAL = 'FINAL', 'Final Settlement'  # Backward compatibility
        FULL = 'FULL', 'Full Payment'
        REFUND = 'REFUND', 'Dispute Refund'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.PROTECT, related_name='payments')
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments_made')
    payee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments_received')
    
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.ADVANCE)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.CREATED, db_index=True)
    
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True, help_text='UPI, NetBanking, Card, etc.')
    
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    receipt_number = models.CharField(max_length=100, blank=True, db_index=True)
    
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{secrets.token_hex(6).upper()}"
        if not self.receipt_number:
            now_str = timezone.now().strftime('%Y%m%d')
            self.receipt_number = f"RCP-{now_str}-{secrets.token_hex(4).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount} ({self.get_status_display()})"

    @property
    def is_successful(self):
        return self.status in [self.Status.CAPTURED, self.Status.COMPLETED]


class PaymentRefund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=100, unique=True, db_index=True)
    gateway_refund_id = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_refunds'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = f"RFND-{secrets.token_hex(6).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Refund {self.refund_id} - ₹{self.amount} ({self.status})"


class PayoutRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Settlement'
        PROCESSING = 'PROCESSING', 'Processing with Bank'
        TRANSFERRED = 'TRANSFERRED', 'Settled / Transferred'
        FAILED = 'FAILED', 'Transfer Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.PROTECT, related_name='payouts')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference_id = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50, default='Razorpay Route / Bank NEFT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payout_records'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = f"PAYOUT-{secrets.token_hex(6).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payout {self.reference_id} - ₹{self.amount} to {self.farmer.get_full_name()} ({self.status})"
