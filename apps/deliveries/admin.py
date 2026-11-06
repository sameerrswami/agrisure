from django.contrib import admin
from .models import Delivery

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'contract', 'quantity_shipped', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_number', 'carrier_name', 'contract__contract_number')
