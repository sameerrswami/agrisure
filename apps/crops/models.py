import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.text import slugify

class CropCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='sprout', help_text='Lucide icon name')
    image = models.ImageField(upload_to='crops/categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crop_categories'
        verbose_name_plural = 'Crop Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CropListing(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        UNDER_CONTRACT = 'UNDER_CONTRACT', 'Under Contract'
        SOLD = 'SOLD', 'Sold'
        UNAVAILABLE = 'UNAVAILABLE', 'Temporarily Unavailable'
        EXPIRED = 'EXPIRED', 'Expired'

    class QualityGrade(models.TextChoices):
        PREMIUM = 'PREMIUM', 'Premium Grade'
        GRADE_A = 'GRADE_A', 'Grade A'
        GRADE_B = 'GRADE_B', 'Grade B'
        STANDARD = 'STANDARD', 'Standard'

    class Unit(models.TextChoices):
        KG = 'kg', 'Kilogram (kg)'
        QUINTAL = 'quintal', 'Quintal (100 kg)'
        TONNE = 'tonne', 'Tonne (1000 kg)'

    class FarmingType(models.TextChoices):
        ORGANIC = 'ORGANIC', 'Certified Organic'
        NATURAL = 'NATURAL', 'Natural / ZBNF'
        CONVENTIONAL = 'CONVENTIONAL', 'Conventional'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='crop_listings',
    )
    category = models.ForeignKey(CropCategory, on_delete=models.PROTECT, related_name='listings')
    title = models.CharField(max_length=200)
    variety = models.CharField(max_length=100, blank=True, help_text='e.g., Basmati 1121, Sharbati')
    description = models.TextField()
    quantity_available = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Total quantity available'
    )
    quantity_remaining = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text='Quantity currently available for contract'
    )
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.QUINTAL)
    price_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Expected price per unit in INR'
    )
    minimum_acceptable_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0.01)],
        help_text='Lowest negotiable price (private to farmer)'
    )
    minimum_order_quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01)]
    )
    quality_grade = models.CharField(max_length=20, choices=QualityGrade.choices, default=QualityGrade.GRADE_A)
    farming_type = models.CharField(max_length=20, choices=FarmingType.choices, default=FarmingType.CONVENTIONAL)
    is_organic = models.BooleanField(default=False)
    expected_harvest_date = models.DateField(null=True, blank=True)
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    village = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_location_availability = models.CharField(
        max_length=255, blank=True,
        help_text='e.g., Farm Gate pickup, Pan-India delivery, Within State'
    )
    delivery_conditions = models.TextField(blank=True, help_text='Packaging, loading, or transport terms')
    featured_image = models.ImageField(upload_to='crops/images/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crop_listings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['state', 'district']),
            models.Index(fields=['price_per_unit']),
        ]

    def save(self, *args, **kwargs):
        if self.quantity_remaining is None:
            self.quantity_remaining = self.quantity_available
        if self.farming_type == self.FarmingType.ORGANIC:
            self.is_organic = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.farmer.get_full_name()} ({self.get_status_display()})"

    @property
    def is_available(self):
        return self.status == self.Status.ACTIVE and self.quantity_remaining > 0

    @property
    def total_estimated_value(self):
        return self.quantity_available * self.price_per_unit


class CropImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(CropListing, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='crops/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crop_images'
        ordering = ['uploaded_at']
