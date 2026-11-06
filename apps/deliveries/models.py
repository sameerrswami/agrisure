import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone

class Delivery(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        PREPARING = 'PREPARING', 'Preparing & Harvesting'
        DISPATCHED = 'DISPATCHED', 'Dispatched / In Transit'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        ARRIVING = 'ARRIVING', 'Arriving'
        DELIVERED = 'DELIVERED', 'Delivered'
        PARTIALLY_DELIVERED = 'PARTIALLY_DELIVERED', 'Partially Delivered'
        FAILED = 'FAILED', 'Failed'
        
        # Compatibility choices
        PENDING = 'PENDING', 'Pending Dispatch'
        SHIPPED = 'SHIPPED', 'Dispatched'
        CONFIRMED = 'CONFIRMED', 'Inspection Verified by Buyer'
        REJECTED = 'REJECTED', 'Rejected on Quality / Damage'

    class InspectionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Inspection'
        VERIFIED = 'VERIFIED', 'Verified & Accepted'
        SHORTAGE = 'SHORTAGE', 'Quantity Shortage'
        DAMAGED = 'DAMAGED', 'Damaged / Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.PROTECT, related_name='deliveries')
    tracking_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    
    quantity_scheduled = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    quantity_shipped = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    quantity_delivered = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, default='quintal')
    
    pickup_location = models.CharField(max_length=255, default='Farm Gate')
    destination_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)  # Compatibility field
    
    transporter_name = models.CharField(max_length=150, blank=True, help_text='Transport Agency / Logistics Carrier')
    carrier_name = models.CharField(max_length=150, blank=True)  # Compatibility field
    vehicle_number = models.CharField(max_length=50, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    proof_of_delivery = models.FileField(upload_to='deliveries/proofs/', blank=True, null=True)
    delivery_notes = models.TextField(blank=True)
    inspection_notes = models.TextField(blank=True)
    inspection_status = models.CharField(max_length=20, choices=InspectionStatus.choices, default=InspectionStatus.PENDING)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'deliveries'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = f"DEL-{secrets.token_hex(5).upper()}"
        if not self.quantity_shipped and self.quantity_scheduled:
            self.quantity_shipped = self.quantity_scheduled
        elif not self.quantity_scheduled and self.quantity_shipped:
            self.quantity_scheduled = self.quantity_shipped
        if not self.destination_address and self.shipping_address:
            self.destination_address = self.shipping_address
        elif not self.shipping_address and self.destination_address:
            self.shipping_address = self.destination_address
        if not self.transporter_name and self.carrier_name:
            self.transporter_name = self.carrier_name
        elif not self.carrier_name and self.transporter_name:
            self.carrier_name = self.transporter_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_number} - {self.quantity_scheduled} {self.unit} ({self.get_status_display()})"


class DeliveryUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=30)
    location = models.CharField(max_length=200, blank=True)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'delivery_updates'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.delivery.tracking_number} - {self.status} at {self.timestamp}"
