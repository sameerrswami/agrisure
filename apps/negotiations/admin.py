from django.contrib import admin
from .models import Negotiation, Offer

class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0

@admin.register(Negotiation)
class NegotiationAdmin(admin.ModelAdmin):
    list_display = ('crop_listing', 'farmer', 'buyer', 'status', 'final_price_per_unit', 'updated_at')
    list_filter = ('status', 'updated_at')
    inlines = [OfferInline]
