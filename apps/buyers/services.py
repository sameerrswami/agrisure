from django.db.models import Sum, Q
from apps.contracts.models import Contract
from apps.crops.models import CropListing
from apps.buyers.models import SavedCrop, BuyerProfile
from apps.payments.models import Payment
from apps.negotiations.models import Negotiation
from apps.notifications.models import Notification

class BuyerDashboardService:
    @staticmethod
    def get_dashboard_metrics(buyer, recently_viewed_ids=None):
        contracts = Contract.objects.filter(buyer=buyer)
        payments = Payment.objects.filter(payer=buyer, status=Payment.Status.COMPLETED)
        pending_payments = Payment.objects.filter(payer=buyer, status=Payment.Status.PENDING)

        # 6 Buyer Core Statistics
        total_purchases = contracts.filter(status=Contract.Status.COMPLETED).count()
        active_contracts = contracts.filter(status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]).count()
        pending_requests = contracts.filter(status=Contract.Status.PENDING_FARMER).count()
        completed_contracts = contracts.filter(status=Contract.Status.COMPLETED).count()
        
        # Total Purchase Value
        total_purchase_val = contracts.filter(
            status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS, Contract.Status.COMPLETED]
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        # Outstanding / Pending Escrow payments
        outstanding_payments = pending_payments.aggregate(total=Sum('amount'))['total'] or 0

        # Section: Available crops
        available_crops = CropListing.objects.filter(
            status=CropListing.Status.ACTIVE,
            quantity_remaining__gt=0
        ).select_related('farmer', 'farmer__farmer_profile', 'category').order_by('-created_at')[:6]

        # Section: Recently Viewed Crops
        recently_viewed = []
        if recently_viewed_ids:
            recently_viewed = list(CropListing.objects.filter(
                id__in=recently_viewed_ids,
                status=CropListing.Status.ACTIVE
            ).select_related('farmer', 'category')[:6])

        # Section: Saved Crops (Wishlist)
        saved_crops = SavedCrop.objects.filter(
            buyer=buyer
        ).select_related('crop_listing', 'crop_listing__farmer', 'crop_listing__category')[:6]

        # Section: Farmer Recommendations (based on buyer profile preferred crops and locations)
        recommended_crops = []
        if hasattr(buyer, 'buyer_profile'):
            bp = buyer.buyer_profile
            rec_q = Q(status=CropListing.Status.ACTIVE)
            if bp.preferred_crops:
                crop_keywords = [c.strip() for c in bp.preferred_crops.split(',') if c.strip()]
                crop_q = Q()
                for kw in crop_keywords:
                    crop_q |= Q(title__icontains=kw) | Q(variety__icontains=kw) | Q(category__name__icontains=kw)
                rec_q &= crop_q
            
            if bp.preferred_locations:
                loc_keywords = [l.strip() for l in bp.preferred_locations.split(',') if l.strip()]
                loc_q = Q()
                for loc in loc_keywords:
                    loc_q |= Q(state__icontains=loc) | Q(district__icontains=loc)
                rec_q &= loc_q

            recommended_crops = CropListing.objects.filter(rec_q).select_related('farmer', 'category')[:6]

        if not recommended_crops:
            # Fallback to premium and organic verified crops
            recommended_crops = CropListing.objects.filter(
                status=CropListing.Status.ACTIVE,
                farmer__farmer_profile__is_verified=True
            ).select_related('farmer', 'category').order_by('-created_at')[:6]

        # Section: Pending negotiations
        pending_negotiations = Negotiation.objects.filter(
            buyer=buyer, status=Negotiation.Status.OPEN
        ).select_related('crop_listing', 'farmer').order_by('-updated_at')[:5]

        # Section: Upcoming deliveries
        upcoming_deliveries = contracts.filter(
            status__in=[Contract.Status.ACTIVE, Contract.Status.READY_FOR_DELIVERY, Contract.Status.PRODUCTION_IN_PROGRESS]
        ).select_related('farmer', 'crop_listing').order_by('delivery_date')[:5]

        # Section: Recent purchases
        recent_purchases = contracts.filter(
            status__in=[Contract.Status.ACTIVE, Contract.Status.COMPLETED]
        ).select_related('farmer', 'crop_listing').order_by('-created_at')[:5]

        # Section: Notifications
        recent_notifications = Notification.objects.filter(
            recipient=buyer
        ).order_by('-created_at')[:6]

        return {
            'total_purchases': total_purchases,
            'active_contracts': active_contracts,
            'pending_requests': pending_requests,
            'completed_contracts': completed_contracts,
            'total_purchase_value': total_purchase_val,
            'outstanding_payments': outstanding_payments,
            
            'available_crops': available_crops,
            'recently_viewed': recently_viewed,
            'saved_crops': saved_crops,
            'recommended_crops': recommended_crops,
            'pending_negotiations': pending_negotiations,
            'upcoming_deliveries': upcoming_deliveries,
            'recent_purchases': recent_purchases,
            'recent_notifications': recent_notifications,
        }
