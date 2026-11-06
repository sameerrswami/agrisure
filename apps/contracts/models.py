import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
import random
from apps.crops.models import CropListing

class Contract(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_FARMER = 'PENDING_FARMER', 'Pending Farmer Approval'
        PENDING_BUYER = 'PENDING_BUYER', 'Pending Buyer Approval'
        ACTIVE = 'ACTIVE', 'Active & Legally Bound'
        PRODUCTION_IN_PROGRESS = 'PRODUCTION_IN_PROGRESS', 'Production In Progress'
        READY_FOR_DELIVERY = 'READY_FOR_DELIVERY', 'Ready for Delivery'
        PARTIALLY_DELIVERED = 'PARTIALLY_DELIVERED', 'Partially Delivered'
        DELIVERED = 'DELIVERED', 'Delivered'
        COMPLETED = 'COMPLETED', 'Completed & Settled'
        CANCELLED = 'CANCELLED', 'Cancelled'
        DISPUTED = 'DISPUTED', 'Under Dispute'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_number = models.CharField(max_length=30, unique=True, db_index=True)
    crop_listing = models.ForeignKey('crops.CropListing', on_delete=models.PROTECT, related_name='contracts')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='farmer_contracts')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='buyer_contracts')
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, default='quintal')
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    advance_payment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    advance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    payment_terms = models.TextField(blank=True, default='20% advance upon contract signing into secured escrow, 80% final settlement upon verified delivery inspection.')
    
    delivery_date = models.DateField()
    delivery_address = models.TextField()
    required_quality_grade = models.CharField(max_length=20, choices=CropListing.QualityGrade.choices, default=CropListing.QualityGrade.GRADE_A)
    quality_specifications = models.TextField(blank=True)
    harvest_schedule = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    additional_conditions = models.TextField(blank=True)
    penalty_clause = models.TextField(blank=True)
    buyer_message = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_FARMER, db_index=True)
    
    farmer_accepted = models.BooleanField(default=False)
    farmer_accepted_at = models.DateTimeField(null=True, blank=True)
    farmer_accepted_version = models.PositiveIntegerField(null=True, blank=True)
    
    buyer_accepted = models.BooleanField(default=False)
    buyer_accepted_at = models.DateTimeField(null=True, blank=True)
    buyer_accepted_version = models.PositiveIntegerField(null=True, blank=True)
    
    contract_pdf = models.FileField(upload_to='contracts/pdfs/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['farmer', 'status']),
            models.Index(fields=['buyer', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.contract_number:
            now_str = timezone.now().strftime('%Y%m')
            rnd = random.randint(10000, 99999)
            self.contract_number = f"AGR-{now_str}-{rnd}"
        
        # Calculate totals
        if self.quantity and self.price_per_unit:
            self.total_amount = self.quantity * self.price_per_unit
            if self.advance_payment_percentage is not None:
                self.advance_amount = (self.total_amount * Decimal(str(self.advance_payment_percentage))) / Decimal('100')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Contract {self.contract_number} ({self.crop_listing.title})"

    @property
    def is_fully_accepted(self):
        return (
            self.farmer_accepted and
            self.buyer_accepted and
            self.farmer_accepted_version == self.version and
            self.buyer_accepted_version == self.version
        )

    @property
    def total_paid_amount(self):
        from apps.payments.models import Payment
        successful = self.payments.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
        return sum([p.amount for p in successful], Decimal('0.00'))

    @property
    def remaining_payment_amount(self):
        rem = self.total_amount - self.total_paid_amount
        return max(Decimal('0.00'), rem)

    @property
    def is_advance_paid(self):
        from apps.payments.models import Payment
        return self.payments.filter(
            payment_type=Payment.PaymentType.ADVANCE,
            status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED]
        ).exists()

    @property
    def is_fully_paid(self):
        return self.total_paid_amount >= self.total_amount

    @property
    def total_delivered_quantity(self):
        from apps.deliveries.models import Delivery
        delvs = self.deliveries.filter(status__in=[Delivery.Status.DELIVERED, Delivery.Status.PARTIALLY_DELIVERED, Delivery.Status.CONFIRMED])
        total = Decimal('0.00')
        for d in delvs:
            if d.quantity_delivered is not None:
                total += d.quantity_delivered
            elif d.status in [Delivery.Status.DELIVERED, Delivery.Status.CONFIRMED]:
                total += d.quantity_scheduled
        return total

    @property
    def delivery_progress_pct(self):
        if not self.quantity or self.quantity <= 0:
            return 0
        pct = (self.total_delivered_quantity / self.quantity) * 100
        return min(100, int(round(pct)))


class ContractAcceptance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='acceptances')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    accepted_at = models.DateTimeField(auto_now_add=True)
    disclaimer_acknowledged = models.BooleanField(default=True, help_text="Acknowledged platform-recorded acceptance")

    class Meta:
        db_table = 'contract_acceptances'
        ordering = ['-accepted_at']

    def __str__(self):
        return f"Acceptance v{self.version} by {self.user.get_full_name()} for #{self.contract.contract_number}"


class ContractHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='history')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contract_history'
        ordering = ['created_at']
