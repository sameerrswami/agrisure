from django.contrib import admin
from .models import Contract, ContractHistory

class ContractHistoryInline(admin.TabularInline):
    model = ContractHistory
    extra = 0
    readonly_fields = ('performed_by', 'from_status', 'to_status', 'comment', 'created_at')

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'title', 'farmer', 'buyer', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'farmer_accepted', 'buyer_accepted', 'created_at')
    search_fields = ('contract_number', 'farmer__email', 'buyer__email', 'title')
    inlines = [ContractHistoryInline]
