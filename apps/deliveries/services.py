from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Delivery, DeliveryUpdate
from apps.contracts.models import Contract
from apps.notifications.services import NotificationService

class DeliveryService:
    @staticmethod
    def create_shipment(contract, scheduled_quantity, pickup_location, destination_address,
                        estimated_delivery_date, transporter_name="", vehicle_number="",
                        driver_name="", driver_phone="", delivery_notes=""):
        """
        Creates a new scheduled shipment for an active contract with concurrency protection.
        """
        with transaction.atomic():
            scheduled_quantity = Decimal(str(scheduled_quantity))
            if scheduled_quantity <= 0:
                raise ValidationError("Scheduled delivery quantity must be greater than zero.")

            delivery = Delivery.objects.create(
                contract=contract,
                quantity_scheduled=scheduled_quantity,
                quantity_shipped=scheduled_quantity,
                unit=contract.unit,
                pickup_location=pickup_location or "Farm Gate",
                destination_address=destination_address or contract.delivery_address,
                shipping_address=destination_address or contract.delivery_address,
                estimated_delivery_date=estimated_delivery_date or contract.delivery_date,
                transporter_name=transporter_name,
                carrier_name=transporter_name,
                vehicle_number=vehicle_number,
                driver_name=driver_name,
                driver_phone=driver_phone,
                delivery_notes=delivery_notes,
                status=Delivery.Status.SCHEDULED
            )

            DeliveryUpdate.objects.create(
                delivery=delivery,
                status="Shipment Scheduled",
                location=pickup_location or "Farm Gate",
                note=f"Scheduled delivery of {scheduled_quantity} {contract.unit} under Contract #{contract.contract_number}."
            )

            # If vehicle details provided upfront, mark as dispatched directly
            if vehicle_number or transporter_name:
                delivery.status = Delivery.Status.DISPATCHED
                delivery.dispatched_at = timezone.now()
                delivery.save()
                
                DeliveryUpdate.objects.create(
                    delivery=delivery,
                    status="Dispatched & In Transit",
                    location=pickup_location or "Farm Gate",
                    note=f"Vehicle {vehicle_number} departed. Driver: {driver_name} ({driver_phone})."
                )

                if contract.status in [Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]:
                    contract.status = Contract.Status.READY_FOR_DELIVERY
                    contract.save()

            NotificationService.send(
                recipient=contract.buyer,
                notification_type='DELIVERY',
                title='Shipment Scheduled',
                message=f'Shipment #{delivery.tracking_number} ({scheduled_quantity} {contract.unit}) has been scheduled by farmer.',
                link=f'/deliveries/{delivery.id}/'
            )
            return delivery

    @staticmethod
    def confirm_dispatch(delivery, transporter_name, vehicle_number, driver_name="", driver_phone="", notes=""):
        """
        Farmer confirms shipment dispatch with vehicle and transporter details.
        """
        with transaction.atomic():
            locked = Delivery.objects.select_for_update().get(id=delivery.id)
            locked.status = Delivery.Status.DISPATCHED
            locked.transporter_name = transporter_name or locked.transporter_name
            locked.carrier_name = locked.transporter_name
            locked.vehicle_number = vehicle_number or locked.vehicle_number
            locked.driver_name = driver_name or locked.driver_name
            locked.driver_phone = driver_phone or locked.driver_phone
            locked.dispatched_at = timezone.now()
            if notes:
                locked.delivery_notes += f"\nDispatch note: {notes}"
            locked.save()

            DeliveryUpdate.objects.create(
                delivery=locked,
                status="Dispatched from Farm",
                location=locked.pickup_location,
                note=f"Goods dispatched via {locked.transporter_name} ({locked.vehicle_number}). Driver: {locked.driver_name} ({locked.driver_phone})."
            )

            contract = locked.contract
            if contract.status in [Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]:
                contract.status = Contract.Status.READY_FOR_DELIVERY
                contract.save()

            NotificationService.send(
                recipient=contract.buyer,
                notification_type='DELIVERY',
                title='Shipment Dispatched!',
                message=f'Shipment #{locked.tracking_number} is on its way with vehicle {locked.vehicle_number}.',
                link=f'/deliveries/{locked.id}/'
            )
            return locked

    @staticmethod
    def confirm_receipt(delivery, quantity_delivered, proof_file=None, inspection_status='VERIFIED', inspection_notes="", buyer_user=None):
        """
        Buyer verifies shipment arrival, inspects goods, uploads proof of delivery,
        and records verified received quantity.
        """
        with transaction.atomic():
            locked = Delivery.objects.select_for_update().get(id=delivery.id)
            qty = Decimal(str(quantity_delivered))

            locked.quantity_delivered = qty
            if proof_file:
                locked.proof_of_delivery = proof_file
            locked.inspection_status = inspection_status
            locked.inspection_notes = inspection_notes
            locked.actual_delivery_date = timezone.now().date()
            locked.delivered_at = timezone.now()

            # Determine shipment status based on delivered quantity vs scheduled
            if qty < locked.quantity_scheduled or inspection_status == Delivery.InspectionStatus.SHORTAGE:
                locked.status = Delivery.Status.PARTIALLY_DELIVERED
            elif inspection_status == Delivery.InspectionStatus.DAMAGED:
                locked.status = Delivery.Status.FAILED
            else:
                locked.status = Delivery.Status.DELIVERED
            locked.save()

            DeliveryUpdate.objects.create(
                delivery=locked,
                status=f"Received & Inspected ({locked.get_status_display()})",
                location=locked.destination_address,
                note=f"Buyer verified {qty} {locked.unit} received. Inspection verdict: {locked.get_inspection_status_display()}."
            )

            # Contract-wide progress calculation
            contract = locked.contract
            delivered_shipments = contract.deliveries.filter(
                status__in=[Delivery.Status.DELIVERED, Delivery.Status.PARTIALLY_DELIVERED, Delivery.Status.CONFIRMED]
            )
            total_delivered = sum([d.quantity_delivered or d.quantity_scheduled for d in delivered_shipments], Decimal('0.00'))

            if total_delivered >= contract.quantity:
                contract.status = Contract.Status.DELIVERED
            elif total_delivered > 0:
                contract.status = Contract.Status.PARTIALLY_DELIVERED
            contract.save()

            # Notify farmer
            NotificationService.send(
                recipient=contract.farmer,
                notification_type='DELIVERY',
                title='Delivery Arrival Confirmed',
                message=f'Shipment #{locked.tracking_number} verified: {qty} {locked.unit} accepted by buyer.',
                link=f'/deliveries/{locked.id}/'
            )

            return locked

    # Backward compatibility alias
    @staticmethod
    def update_delivery_status(delivery, new_status, proof_file=None):
        delivery.status = new_status
        if proof_file:
            delivery.proof_of_delivery = proof_file
        if new_status in [Delivery.Status.DELIVERED, Delivery.Status.CONFIRMED]:
            delivery.actual_delivery_date = timezone.now().date()
            delivery.delivered_at = timezone.now()
            if new_status == Delivery.Status.CONFIRMED:
                delivery.inspection_status = Delivery.InspectionStatus.VERIFIED
                if delivery.quantity_delivered is None:
                    delivery.quantity_delivered = delivery.quantity_scheduled
        delivery.save()
