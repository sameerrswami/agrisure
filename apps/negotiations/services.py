from django.db import transaction
from django.utils import timezone
from .models import Negotiation, Offer
from apps.contracts.models import Contract
from apps.contracts.services import ContractService
from apps.notifications.services import NotificationService

class NegotiationService:
    @staticmethod
    def accept_offer(negotiation_id, offer_id, user):
        with transaction.atomic():
            negotiation = Negotiation.objects.select_for_update().get(id=negotiation_id)
            offer = Offer.objects.select_for_update().get(id=offer_id, negotiation=negotiation)
            
            if offer.status != Offer.Status.PENDING:
                raise ValueError("This offer is no longer open for acceptance.")
            
            # The party accepting MUST NOT be the one who made the offer
            if offer.submitted_by == user:
                raise ValueError("You cannot accept your own offer.")
            
            # Update offer & negotiation status
            offer.status = Offer.Status.ACCEPTED
            offer.save()
            
            negotiation.status = Negotiation.Status.ACCEPTED
            negotiation.final_price_per_unit = offer.price_per_unit
            negotiation.final_quantity = offer.quantity
            negotiation.final_agreed_at = timezone.now()
            negotiation.save()
            
            # Mark all other pending offers in this negotiation as countered/closed
            negotiation.offers.filter(status=Offer.Status.PENDING).exclude(id=offer.id).update(
                status=Offer.Status.COUNTERED
            )
            
            # Automatically generate formal contract from agreed negotiation terms
            crop = negotiation.crop_listing
            contract = Contract.objects.create(
                crop_listing=crop,
                farmer=negotiation.farmer,
                buyer=negotiation.buyer,
                title=f"Contract for {crop.title} (Via Negotiation)",
                quantity=offer.quantity,
                unit=crop.unit,
                price_per_unit=offer.price_per_unit,
                delivery_date=offer.proposed_delivery_date or crop.expected_harvest_date or timezone.now().date(),
                delivery_address="As per agreed negotiation terms",
                quality_specifications=offer.conditions or f"Standard {crop.get_quality_grade_display()}",
                status=Contract.Status.PENDING_FARMER if user == negotiation.buyer else Contract.Status.PENDING_BUYER,
                advance_payment_percentage=20.00
            )
            
            # Generate initial contract PDF
            ContractService.generate_pdf(contract)
            
            # Notify the offer creator
            NotificationService.send(
                recipient=offer.submitted_by,
                notification_type='NEGOTIATION',
                title='Negotiation Offer Accepted!',
                message=f'{user.get_full_name()} accepted your offer of ₹{offer.price_per_unit}/unit for {crop.title}. Formal contract #{contract.contract_number} has been generated.',
                link=f'/contracts/{contract.id}/'
            )
            return contract
