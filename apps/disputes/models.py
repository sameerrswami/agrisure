import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone

class Dispute(models.Model):
    class Category(models.TextChoices):
        QUALITY = 'QUALITY', 'Crop Quality Below Specifications'
        QUANTITY = 'QUANTITY', 'Incorrect Quantity / Shortage'
        DELAY = 'DELAY', 'Late Delivery'
        DAMAGE = 'DAMAGE', 'Damaged Goods in Transit'
        PAYMENT = 'PAYMENT', 'Payment Default / Issue'
        BREACH = 'BREACH', 'Contract Terms Violation'
        OTHER = 'OTHER', 'Other Discrepancy'
        
        # Compatibility choices
        DELIVERY_DELAY = 'DELIVERY_DELAY', 'Delayed Delivery'
        PAYMENT_ISSUE = 'PAYMENT_ISSUE', 'Payment Default / Delay'
        BREACH_OF_TERMS = 'BREACH_OF_TERMS', 'Contract Breach'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        AWAITING_INFO = 'AWAITING_INFO', 'Awaiting Information'
        RESOLVED = 'RESOLVED', 'Resolved'
        REJECTED = 'REJECTED', 'Rejected'
        CLOSED = 'CLOSED', 'Closed'
        
        # Compatibility choices
        IN_INVESTIGATION = 'IN_INVESTIGATION', 'Investigating'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute_number = models.CharField(max_length=50, blank=True, db_index=True)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.CASCADE, related_name='disputes')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='disputes_raised')
    against_party = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='disputes_against')
    
    category = models.CharField(max_length=30, choices=Category.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    evidence_document = models.FileField(upload_to='disputes/evidence/', blank=True, null=True)
    evidence_file = models.FileField(upload_to='disputes/evidence/', blank=True, null=True)
    
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPEN, db_index=True)
    admin_response = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    resolution_details = models.TextField(blank=True)
    
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'disputes'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.dispute_number:
            year = timezone.now().strftime('%Y')
            self.dispute_number = f"DSP-{year}-{secrets.token_hex(4).upper()}"
        if not self.evidence_file and self.evidence_document:
            self.evidence_file = self.evidence_document
        elif not self.evidence_document and self.evidence_file:
            self.evidence_document = self.evidence_file
        if not self.admin_response and self.resolution:
            self.admin_response = self.resolution
        elif not self.resolution and self.admin_response:
            self.resolution = self.admin_response
        super().save(*args, **kwargs)

    @property
    def submitted_by(self):
        return self.raised_by

    def __str__(self):
        return f"{self.dispute_number} on Contract #{self.contract.contract_number} ({self.get_status_display()})"


class DisputeMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to='disputes/messages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender.get_full_name()} on {self.dispute.dispute_number}"
