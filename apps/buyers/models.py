import uuid
from django.db import models
from django.conf import settings

class BuyerProfile(models.Model):
    class BusinessType(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', 'Individual / Retailer'
        COMPANY = 'COMPANY', 'Private Limited / Corporate'
        COOPERATIVE = 'COOPERATIVE', 'Cooperative Society'
        PROCESSOR = 'PROCESSOR', 'Food Processing Industry'
        EXPORTER = 'EXPORTER', 'Agri Exporter'
        WHOLESALER = 'WHOLESALER', 'Wholesaler / Mandi Trader'
        GOVERNMENT = 'GOVERNMENT', 'Government Agency'

    class VerificationStatus(models.TextChoices):
        NOT_SUBMITTED = 'NOT_SUBMITTED', 'Not Submitted'
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_profile',
    )
    company_name = models.CharField(max_length=200, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        default=BusinessType.COMPANY,
    )
    gstin = models.CharField(max_length=20, blank=True, help_text='GST Identification Number')
    pan_number = models.CharField(max_length=10, blank=True)
    business_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_address = models.TextField(blank=True, help_text='Default delivery warehouse address')
    website = models.URLField(blank=True)
    bio = models.TextField(blank=True, help_text='About company procurement and requirements')
    company_logo = models.ImageField(upload_to='buyers/logos/', blank=True, null=True)
    annual_procurement_budget = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Annual budget in INR'
    )
    preferred_crops = models.CharField(max_length=255, blank=True, help_text='Comma-separated crop names')
    preferred_locations = models.CharField(max_length=255, blank=True, help_text='Comma-separated states/regions')
    required_quantities = models.CharField(max_length=255, blank=True, help_text='e.g. 500 Quintals / month')
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_SUBMITTED,
        db_index=True
    )
    verification_document = models.FileField(upload_to='buyers/documents/', blank=True, null=True)
    verification_notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'buyer_profiles'
        verbose_name = 'Buyer Profile'
        verbose_name_plural = 'Buyer Profiles'

    def __str__(self):
        return f"{self.company_name or self.user.get_full_name()}"

    @property
    def logo_url(self):
        if self.company_logo:
            try:
                return self.company_logo.url
            except Exception:
                pass
        name = self.company_name or self.user.get_full_name() or "AgriCorp"
        return f"https://api.dicebear.com/7.x/identicon/svg?seed={name}&backgroundColor=f0fdfa"



class SavedCrop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_crops')
    crop_listing = models.ForeignKey('crops.CropListing', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_crops'
        unique_together = ['buyer', 'crop_listing']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.buyer} saved {self.crop_listing}"
