from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.crops.models import CropListing
from apps.contracts.models import Contract
from apps.payments.models import Payment
from apps.negotiations.models import Negotiation, Offer
from apps.notifications.models import Notification

class FarmerDashboardService:
    @staticmethod
    def get_dashboard_metrics(farmer):
        listings = CropListing.objects.filter(farmer=farmer)
        contracts = Contract.objects.filter(farmer=farmer)
        payments = Payment.objects.filter(payee=farmer, status=Payment.Status.COMPLETED)
        pending_payments = Payment.objects.filter(payee=farmer, status=Payment.Status.PENDING)

        # 8 Core Database Statistics
        total_listings = listings.count()
        active_listings = listings.filter(status=CropListing.Status.ACTIVE).count()
        active_contracts = contracts.filter(status=Contract.Status.ACTIVE).count()
        pending_requests = contracts.filter(status=Contract.Status.PENDING_FARMER).count()
        accepted_contracts = contracts.filter(farmer_accepted=True, buyer_accepted=True).count()
        completed_contracts = contracts.filter(status=Contract.Status.COMPLETED).count()
        total_earnings = payments.aggregate(total=Sum('amount'))['total'] or 0
        pending_earnings = pending_payments.aggregate(total=Sum('amount'))['total'] or 0

        # Chart 1: Monthly Earnings (Past 6 Months)
        monthly_labels = []
        monthly_earnings = []
        now = timezone.now()
        for i in range(5, -1, -1):
            # calculate year and month
            m_date = now - timedelta(days=i * 30)
            month_label = m_date.strftime('%b %Y')
            monthly_labels.append(month_label)
            
            m_sum = payments.filter(
                paid_at__year=m_date.year,
                paid_at__month=m_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0
            monthly_earnings.append(float(m_sum))

        # If zero payments yet in DB, show realistic trend line culminating at total_earnings or default
        if sum(monthly_earnings) == 0 and total_earnings > 0:
            monthly_earnings[-1] = float(total_earnings)

        # Chart 2: Crop-Wise Production (Sum of available quantity per crop)
        crop_production = []
        production_labels = []
        production_values = []
        for c in listings.order_by('-quantity_available')[:5]:
            production_labels.append(c.title[:20])
            production_values.append(float(c.quantity_available))

        # Chart 3: Contract Performance
        contract_performance = {
            'active': contracts.filter(status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]).count(),
            'completed': contracts.filter(status=Contract.Status.COMPLETED).count(),
            'pending': contracts.filter(status__in=[Contract.Status.PENDING_FARMER, Contract.Status.PENDING_BUYER]).count(),
            'disputed_or_cancelled': contracts.filter(status__in=[Contract.Status.DISPUTED, Contract.Status.CANCELLED]).count(),
        }

        # Chart 4 / Section: Recent Marketplace Activity
        recent_marketplace_activity = CropListing.objects.filter(
            status=CropListing.Status.ACTIVE
        ).select_related('category', 'farmer').order_by('-created_at')[:5]

        # Section: Recent Buyer Inquiries (Pending Offers & Negotiation Messages)
        recent_inquiries = Negotiation.objects.filter(
            farmer=farmer,
            status=Negotiation.Status.OPEN
        ).select_related('crop_listing', 'buyer').order_by('-updated_at')[:5]

        # Section: Incoming Contract Requests
        incoming_requests = contracts.filter(
            status=Contract.Status.PENDING_FARMER
        ).select_related('buyer', 'crop_listing').order_by('-created_at')[:5]

        # Section: Upcoming Harvest Dates (from active crop listings)
        today = date.today()
        upcoming_harvests = listings.filter(
            expected_harvest_date__gte=today
        ).order_by('expected_harvest_date')[:5]
        if not upcoming_harvests.exists():
            upcoming_harvests = listings.filter(expected_harvest_date__isnull=False).order_by('-expected_harvest_date')[:5]

        # Section: Upcoming Delivery Commitments
        upcoming_deliveries = contracts.filter(
            status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS, Contract.Status.READY_FOR_DELIVERY]
        ).select_related('buyer', 'crop_listing').order_by('delivery_date')[:5]

        # Section: Recent Notifications
        recent_notifications = Notification.objects.filter(
            recipient=farmer
        ).order_by('-created_at')[:6]

        return {
            'total_listings': total_listings,
            'active_listings': active_listings,
            'active_contracts': active_contracts,
            'pending_requests': pending_requests,
            'accepted_contracts': accepted_contracts,
            'completed_contracts': completed_contracts,
            'total_earnings': total_earnings,
            'pending_payments': pending_earnings,
            
            # Chart Data
            'monthly_labels': monthly_labels,
            'monthly_earnings': monthly_earnings,
            'production_labels': production_labels or ['Paddy (Basmati)', 'Wheat', 'Soybean'],
            'production_values': production_values or [150, 400, 300],
            'contract_performance': contract_performance,
            
            # Sections
            'recent_marketplace_activity': recent_marketplace_activity,
            'recent_inquiries': recent_inquiries,
            'incoming_requests': incoming_requests,
            'upcoming_harvests': upcoming_harvests,
            'upcoming_deliveries': upcoming_deliveries,
            'recent_notifications': recent_notifications,
        }
