from django.contrib import admin
from .models import FarmerProfile

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'farm_name', 'state', 'district', 'verification_status', 'is_verified', 'created_at')
    list_filter = ('verification_status', 'is_verified', 'state', 'organic_certified')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'farm_name', 'district', 'state')
    actions = ['mark_as_verified']

    def mark_as_verified(self, request, queryset):
        queryset.update(verification_status=FarmerProfile.VerificationStatus.VERIFIED, is_verified=True)
    mark_as_verified.short_description = "Mark selected farmers as Verified"
