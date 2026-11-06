import uuid
from django.db import models
from django.conf import settings

class Notification(models.Model):
    class Type(models.TextChoices):
        CONTRACT = 'CONTRACT', 'Contract'
        NEGOTIATION = 'NEGOTIATION', 'Negotiation'
        PAYMENT = 'PAYMENT', 'Payment'
        DELIVERY = 'DELIVERY', 'Delivery'
        MESSAGE = 'MESSAGE', 'Message'
        DISPUTE = 'DISPUTE', 'Dispute'
        SYSTEM = 'SYSTEM', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} -> {self.recipient.email}"
