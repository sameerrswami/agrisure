from django.contrib import admin
from .models import CropCategory, CropListing, CropImage

class CropImageInline(admin.TabularInline):
    model = CropImage
    extra = 1

@admin.register(CropCategory)
class CropCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CropListing)
class CropListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'farmer', 'category', 'price_per_unit', 'quantity_available', 'unit', 'status', 'created_at')
    list_filter = ('status', 'quality_grade', 'farming_type', 'category', 'state')
    search_fields = ('title', 'variety', 'district', 'state', 'farmer__email', 'farmer__first_name', 'farmer__last_name')
    inlines = [CropImageInline]
