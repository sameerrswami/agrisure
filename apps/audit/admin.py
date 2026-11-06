from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'user', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('entity_type', 'entity_id', 'description')
    readonly_fields = ('id', 'user', 'action', 'entity_type', 'entity_id', 'description', 'ip_address', 'user_agent', 'metadata', 'created_at')
