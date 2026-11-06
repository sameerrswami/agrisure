from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'contract', 'payer', 'payee', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = ('transaction_id', 'razorpay_payment_id', 'contract__contract_number')
