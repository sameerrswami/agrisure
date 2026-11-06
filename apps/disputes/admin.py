from django.contrib import admin
from .models import Dispute

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('title', 'contract', 'category', 'status', 'raised_by', 'created_at')
    list_filter = ('status', 'category')
