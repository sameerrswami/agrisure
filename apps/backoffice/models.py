import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings

class PlatformSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform_name = models.CharField(max_length=100, default='AgriSure')
    support_email = models.EmailField(default='support@agrisure.in')
    support_phone = models.CharField(max_length=30, default='+91 1800 247 4787')
    office_address = models.TextField(default='AgriSure Agritech Park, Sector 44, Gurugram, Haryana - 122003')
    working_hours = models.CharField(max_length=100, default='Monday to Saturday, 8:00 AM - 8:00 PM IST')
    emergency_helpline = models.CharField(max_length=50, default='1800-AGRI-SURE')
    
    max_upload_size_mb = models.PositiveIntegerField(default=10, help_text="Maximum allowed file size in MB")
    platform_commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.50'), help_text="Platform facilitation commission (%)")
    min_contract_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('5000.00'), help_text="Minimum contract value in INR")
    dispute_sla_days = models.PositiveIntegerField(default=7, help_text="Resolution SLA target in business days")
    
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_settings'
        verbose_name = 'Platform Settings'
        verbose_name_plural = 'Platform Settings'

    def __str__(self):
        return f"{self.platform_name} Configuration"

    @classmethod
    def get_settings(cls):
        setting, _ = cls.objects.get_or_create(id='00000000-0000-0000-0000-000000000001')
        return setting


class ReportedListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop_listing = models.ForeignKey('crops.CropListing', on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=150)
    details = models.TextField()
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reported_listings'
        ordering = ['-created_at']

    def __str__(self):
        return f"Report on {self.crop_listing.title} by {self.reported_by.get_full_name()}"


class AdminAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='admin_audit_logs')
    action = models.CharField(max_length=60)
    target_model = models.CharField(max_length=60)
    target_id = models.CharField(max_length=100)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} | {self.admin_user.email} | {self.action} on {self.target_model}"
