import uuid
from django.db import models
from django.conf import settings

class FarmerProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        NOT_SUBMITTED = 'NOT_SUBMITTED', 'Not Submitted'
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_profile',
    )
    farm_name = models.CharField(max_length=200, blank=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Farm size in acres')
    village = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    farm_address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    farming_experience_years = models.PositiveIntegerField(default=0)
    farming_methods = models.CharField(max_length=150, blank=True, help_text='e.g. Organic, Natural Farming, Conventional')
    irrigation_facilities = models.CharField(max_length=150, blank=True, help_text='e.g. Drip Irrigation, Canal, Borewell')
    organic_certified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    aadhar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_SUBMITTED,
        db_index=True
    )
    verification_document = models.FileField(upload_to='farmers/documents/', blank=True, null=True)
    verification_notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='farmers/profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'farmer_profiles'
        verbose_name = 'Farmer Profile'
        verbose_name_plural = 'Farmer Profiles'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.farm_name or 'Farm'})"

    @property
    def completion_percentage(self):
        fields = [
            self.farm_name, self.farm_size, self.farm_address, self.state,
            self.district, self.village, self.bio, self.farming_experience_years,
            self.farming_methods, self.irrigation_facilities, self.bank_account_number
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)

    @property
    def average_rating(self):
        from apps.reviews.models import Review
        from django.db.models import Avg
        avg = Review.objects.filter(reviewee=self.user).aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 5.0
