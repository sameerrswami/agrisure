import uuid
from django.db import models
from django.conf import settings

class Negotiation(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Negotiation Active'
        ACCEPTED = 'ACCEPTED', 'Agreement Reached'
        REJECTED = 'REJECTED', 'Rejected'
        COUNTER = 'COUNTER', 'Counter Offer Pending'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop_listing = models.ForeignKey('crops.CropListing', on_delete=models.CASCADE, related_name='negotiations')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_negotiations')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer_negotiations')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    
    final_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_agreed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'negotiations'
        ordering = ['-updated_at']
        unique_together = ['crop_listing', 'buyer']

    def __str__(self):
        return f"Negotiation: {self.buyer.get_full_name()} <-> {self.crop_listing.title}"

    @property
    def latest_offer(self):
        return self.offers.order_by('-created_at').first()


class Offer(models.Model):
    class OfferType(models.TextChoices):
        INITIAL = 'INITIAL', 'Initial Offer'
        COUNTER = 'COUNTER', 'Counter Offer'
        FINAL = 'FINAL', 'Final Offer'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Consideration'
        COUNTERED = 'COUNTERED', 'Countered'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        EXPIRED = 'EXPIRED', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    negotiation = models.ForeignKey(Negotiation, on_delete=models.CASCADE, related_name='offers')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    offer_type = models.CharField(max_length=20, choices=OfferType.choices, default=OfferType.INITIAL)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    proposed_delivery_date = models.DateField(null=True, blank=True)
    conditions = models.TextField(blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'negotiation_offers'
        ordering = ['created_at']

    def __str__(self):
        return f"₹{self.price_per_unit}/unit by {self.submitted_by.get_full_name()} ({self.status})"

    @property
    def total_value(self):
        return self.price_per_unit * self.quantity
