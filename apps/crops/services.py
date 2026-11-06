from django.db import transaction
from .models import CropListing

class CropService:
    @staticmethod
    def create_listing(farmer, data, files=None):
        with transaction.atomic():
            listing = CropListing(farmer=farmer)
            for k, v in data.items():
                if hasattr(listing, k):
                    setattr(listing, k, v)
            if files and 'featured_image' in files:
                listing.featured_image = files['featured_image']
            listing.quantity_remaining = listing.quantity_available
            listing.save()
            return listing

    @staticmethod
    def update_quantity(listing, quantity_deducted):
        with transaction.atomic():
            listing.refresh_from_db()
            listing.quantity_remaining -= quantity_deducted
            if listing.quantity_remaining <= 0:
                listing.quantity_remaining = 0
                listing.status = CropListing.Status.SOLD
            listing.save()
