from django.contrib import admin
from .models import BuyerProfile, SavedCrop

@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'business_type', 'city', 'state', 'verification_status', 'is_verified')
    list_filter = ('verification_status', 'business_type', 'state')
    search_fields = ('company_name', 'user__email', 'user__first_name', 'gstin')

@admin.register(SavedCrop)
class SavedCropAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'crop_listing', 'created_at')
