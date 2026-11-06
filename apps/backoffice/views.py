import json
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db import transaction

from apps.accounts.decorators import admin_required
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.contracts.models import Contract
from apps.crops.models import CropListing, CropCategory
from apps.payments.models import Payment, PaymentRefund, PayoutRecord
from apps.disputes.models import Dispute
from apps.notifications.services import NotificationService

from .models import PlatformSetting, ReportedListing, AdminAuditLog
from .forms import PlatformSettingForm, CropCategoryForm, KYCRejectForm, UserSuspendForm

def log_admin_action(admin_user, action, target_model, target_id, details, request=None):
    ip = request.META.get('REMOTE_ADDR') if request else None
    AdminAuditLog.objects.create(
        admin_user=admin_user,
        action=action,
        target_model=target_model,
        target_id=str(target_id),
        details=details,
        ip_address=ip
    )

@login_required
@admin_required
def dashboard(request):
    # 1. Platform-wide DB Statistics
    total_users = User.objects.count()
    total_farmers = User.objects.filter(role=User.Role.FARMER).count()
    total_buyers = User.objects.filter(role=User.Role.BUYER).count()

    verified_farmers = FarmerProfile.objects.filter(verification_status=FarmerProfile.VerificationStatus.VERIFIED).count()
    verified_buyers = BuyerProfile.objects.filter(verification_status=BuyerProfile.VerificationStatus.VERIFIED).count()

    active_crop_listings = CropListing.objects.filter(status=CropListing.Status.ACTIVE).count()
    total_contracts = Contract.objects.count()
    completed_contracts = Contract.objects.filter(status=Contract.Status.COMPLETED).count()
    cancelled_contracts = Contract.objects.filter(status=Contract.Status.CANCELLED).count()

    # Financial Volumes
    captured_payments = Payment.objects.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
    total_transaction_value = sum([p.amount for p in captured_payments], Decimal('0.00'))

    active_contracts_qs = Contract.objects.filter(status__in=[
        Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS,
        Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED,
        Contract.Status.DELIVERED
    ])
    pending_payment_amount = sum([c.remaining_payment_amount for c in active_contracts_qs], Decimal('0.00'))

    open_disputes = Dispute.objects.filter(status__in=[
        Dispute.Status.OPEN, Dispute.Status.UNDER_REVIEW, Dispute.Status.AWAITING_INFO
    ]).count()

    # 2. Six Chart.js Datasets (Database backed)
    now = timezone.now()
    month_labels = []
    farmer_reg_data = []
    buyer_reg_data = []
    monthly_contracts_data = []
    monthly_volume_data = []

    for i in range(5, -1, -1):
        m_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        label = m_start.strftime('%b %Y')
        month_labels.append(label)

        f_count = User.objects.filter(role=User.Role.FARMER, date_joined__gte=m_start, date_joined__lt=m_end).count()
        b_count = User.objects.filter(role=User.Role.BUYER, date_joined__gte=m_start, date_joined__lt=m_end).count()
        farmer_reg_data.append(f_count)
        buyer_reg_data.append(b_count)

        c_count = Contract.objects.filter(created_at__gte=m_start, created_at__lt=m_end).count()
        monthly_contracts_data.append(c_count)

        vol = Payment.objects.filter(
            status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED],
            paid_at__gte=m_start, paid_at__lt=m_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        monthly_volume_data.append(float(vol))

    # Crop category distribution
    cats = CropCategory.objects.annotate(listing_count=Count('listings'))
    cat_labels = [c.name for c in cats]
    cat_counts = [c.listing_count for c in cats]
    if not cat_labels:
        cat_labels = ["Grains & Cereals", "Pulses", "Oilseeds", "Cash Crops"]
        cat_counts = [5, 4, 3, 2]

    # Contract status breakdown
    in_prog_contracts = Contract.objects.filter(status__in=[
        Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS,
        Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED
    ]).count()
    disputed_contracts = Contract.objects.filter(status=Contract.Status.DISPUTED).count()
    contract_status_labels = ["Completed", "In Progress", "Disputed", "Cancelled"]
    contract_status_counts = [completed_contracts, in_prog_contracts, disputed_contracts, cancelled_contracts]

    # Payment success rate
    failed_pmts = Payment.objects.filter(status=Payment.Status.FAILED).count()
    refund_pmts = Payment.objects.filter(status__in=[Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED]).count()
    pending_pmts = Payment.objects.filter(status__in=[Payment.Status.PENDING, Payment.Status.CREATED]).count()
    captured_count = captured_payments.count()
    payment_status_labels = ["Captured", "Pending", "Failed", "Refunded"]
    payment_status_counts = [captured_count, pending_pmts, failed_pmts, refund_pmts]

    # Recent Records
    recent_users = User.objects.order_by('-date_joined')[:6]
    recent_contracts = Contract.objects.order_by('-created_at')[:6]
    recent_disputes = Dispute.objects.order_by('-created_at')[:5]
    audit_logs = AdminAuditLog.objects.order_by('-created_at')[:6]

    context = {
        # KPI Stats
        'total_users': total_users,
        'total_farmers': total_farmers,
        'total_buyers': total_buyers,
        'verified_farmers': verified_farmers,
        'verified_buyers': verified_buyers,
        'active_crop_listings': active_crop_listings,
        'total_contracts': total_contracts,
        'completed_contracts': completed_contracts,
        'cancelled_contracts': cancelled_contracts,
        'total_transaction_value': total_transaction_value,
        'pending_payment_amount': pending_payment_amount,
        'open_disputes': open_disputes,

        # Chart JSON Data
        'month_labels_json': json.dumps(month_labels),
        'farmer_reg_json': json.dumps(farmer_reg_data),
        'buyer_reg_json': json.dumps(buyer_reg_data),
        'monthly_contracts_json': json.dumps(monthly_contracts_data),
        'monthly_volume_json': json.dumps(monthly_volume_data),
        'cat_labels_json': json.dumps(cat_labels),
        'cat_counts_json': json.dumps(cat_counts),
        'contract_status_labels_json': json.dumps(contract_status_labels),
        'contract_status_counts_json': json.dumps(contract_status_counts),
        'payment_status_labels_json': json.dumps(payment_status_labels),
        'payment_status_counts_json': json.dumps(payment_status_counts),

        # Feed
        'recent_users': recent_users,
        'recent_contracts': recent_contracts,
        'recent_disputes': recent_disputes,
        'audit_logs': audit_logs,
    }
    return render(request, 'backoffice/dashboard.html', context)


@login_required
@admin_required
def users_list(request):
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')

    users = User.objects.all().select_related('farmer_profile', 'buyer_profile').order_by('-date_joined')

    if q:
        users = users.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone__icontains=q)
        )

    if role:
        users = users.filter(role=role)

    if status:
        if status == 'VERIFIED':
            users = users.filter(
                Q(farmer_profile__verification_status=FarmerProfile.VerificationStatus.VERIFIED) |
                Q(buyer_profile__verification_status=BuyerProfile.VerificationStatus.VERIFIED)
            )
        elif status == 'PENDING':
            users = users.filter(
                Q(farmer_profile__verification_status=FarmerProfile.VerificationStatus.PENDING) |
                Q(buyer_profile__verification_status=BuyerProfile.VerificationStatus.PENDING)
            )
        elif status == 'REJECTED':
            users = users.filter(
                Q(farmer_profile__verification_status=FarmerProfile.VerificationStatus.REJECTED) |
                Q(buyer_profile__verification_status=BuyerProfile.VerificationStatus.REJECTED)
            )

    context = {
        'users': users,
        'search_query': q,
        'current_role': role,
        'current_status': status,
    }
    return render(request, 'backoffice/users.html', context)


@login_required
@admin_required
def user_detail(request, user_id):
    target_user = get_object_or_404(User.objects.select_related('farmer_profile', 'buyer_profile'), id=user_id)
    reject_form = KYCRejectForm()
    suspend_form = UserSuspendForm()

    user_contracts = Contract.objects.filter(Q(farmer=target_user) | Q(buyer=target_user)).order_by('-created_at')[:8]
    audit_trail = AdminAuditLog.objects.filter(target_id=str(target_user.id)).order_by('-created_at')

    context = {
        'target_user': target_user,
        'reject_form': reject_form,
        'suspend_form': suspend_form,
        'contracts': user_contracts,
        'audit_trail': audit_trail,
    }
    return render(request, 'backoffice/user_detail.html', context)


@login_required
@admin_required
def verify_user(request, user_id):
    u = get_object_or_404(User, id=user_id)
    with transaction.atomic():
        if u.is_farmer and hasattr(u, 'farmer_profile'):
            u.farmer_profile.verification_status = FarmerProfile.VerificationStatus.VERIFIED
            u.farmer_profile.is_verified = True
            u.farmer_profile.save()
        elif u.is_buyer and hasattr(u, 'buyer_profile'):
            u.buyer_profile.verification_status = BuyerProfile.VerificationStatus.VERIFIED
            u.buyer_profile.is_verified = True
            u.buyer_profile.save()

        log_admin_action(
            admin_user=request.user,
            action="KYC_VERIFIED",
            target_model="User",
            target_id=u.id,
            details=f"Admin approved identity and KYC documents for {u.get_full_name()} ({u.email}).",
            request=request
        )

        NotificationService.send(
            recipient=u,
            notification_type='ACCOUNT',
            title='KYC Verification Approved!',
            message='Congratulations! Your AgriSure identity credentials have been verified. You now enjoy full marketplace access.',
            link='/accounts/profile/'
        )

        messages.success(request, f"User {u.get_full_name()} verified successfully.")
    return redirect(request.META.get('HTTP_REFERER') or 'backoffice:users')


@login_required
@admin_required
def reject_user(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = KYCRejectForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get('rejection_reason')
            with transaction.atomic():
                if u.is_farmer and hasattr(u, 'farmer_profile'):
                    u.farmer_profile.verification_status = FarmerProfile.VerificationStatus.REJECTED
                    u.farmer_profile.is_verified = False
                    u.farmer_profile.save()
                elif u.is_buyer and hasattr(u, 'buyer_profile'):
                    u.buyer_profile.verification_status = BuyerProfile.VerificationStatus.REJECTED
                    u.buyer_profile.is_verified = False
                    u.buyer_profile.save()

                log_admin_action(
                    admin_user=request.user,
                    action="KYC_REJECTED",
                    target_model="User",
                    target_id=u.id,
                    details=f"Admin rejected KYC documents for {u.get_full_name()}. Reason: {reason}",
                    request=request
                )

                NotificationService.send(
                    recipient=u,
                    notification_type='ACCOUNT',
                    title='KYC Verification Rejected',
                    message=f'Verification notice: {reason}. Please re-upload updated documents.',
                    link='/accounts/profile/'
                )

                messages.warning(request, f"User {u.get_full_name()}'s verification rejected with reason recorded.")
    return redirect(request.META.get('HTTP_REFERER') or 'backoffice:users')


@login_required
@admin_required
def toggle_user_status(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if u.is_admin_user:
        messages.error(request, "Cannot alter superuser / administrator status.")
        return redirect('backoffice:users')

    with transaction.atomic():
        u.is_active = not u.is_active
        u.save()

        action = "ACCOUNT_REACTIVATED" if u.is_active else "ACCOUNT_SUSPENDED"
        details = f"Account {u.email} {'reactivated' if u.is_active else 'suspended'} by admin."
        log_admin_action(request.user, action, "User", u.id, details, request)

        NotificationService.send(
            recipient=u,
            notification_type='ACCOUNT',
            title=f'Account {"Reactivated" if u.is_active else "Suspended"}',
            message=f'Your platform account has been {"reactivated" if u.is_active else "suspended"} by administration.',
            link='/core/contact/'
        )

        messages.success(request, f"User {u.get_full_name()} is now {'Active' if u.is_active else 'Suspended'}.")
    return redirect(request.META.get('HTTP_REFERER') or 'backoffice:users')


@login_required
@admin_required
def contracts_list(request):
    status_filter = request.GET.get('status')
    contracts = Contract.objects.all().select_related('farmer', 'buyer', 'crop_listing').order_by('-created_at')
    if status_filter:
        contracts = contracts.filter(status=status_filter)

    return render(request, 'backoffice/contracts.html', {
        'contracts': contracts,
        'current_status': status_filter
    })


@login_required
@admin_required
def payments_admin(request):
    payments = Payment.objects.all().select_related('contract', 'payer', 'payee').order_by('-created_at')
    payouts = PayoutRecord.objects.all().select_related('contract', 'farmer').order_by('-created_at')[:10]
    refunds = PaymentRefund.objects.all().select_related('payment').order_by('-created_at')[:10]

    captured = payments.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.COMPLETED])
    total_volume = sum([p.amount for p in captured], Decimal('0.00'))
    failed_count = payments.filter(status=Payment.Status.FAILED).count()
    refund_count = payments.filter(status__in=[Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED]).count()

    context = {
        'payments': payments,
        'payouts': payouts,
        'refunds': refunds,
        'total_volume': total_volume,
        'captured_count': captured.count(),
        'failed_count': failed_count,
        'refund_count': refund_count,
    }
    return render(request, 'backoffice/payments.html', context)


@login_required
@admin_required
def disputes_list(request):
    disputes = Dispute.objects.all().select_related('contract', 'raised_by', 'against_party', 'resolved_by').order_by('-created_at')
    return render(request, 'backoffice/disputes.html', {'disputes': disputes})


@login_required
@admin_required
def resolve_dispute(request, pk):
    disp = get_object_or_404(Dispute, pk=pk)
    if request.method == 'POST':
        disp.status = request.POST.get('status', Dispute.Status.RESOLVED)
        disp.admin_response = request.POST.get('admin_response') or request.POST.get('resolution', 'Resolved via administrative arbitration.')
        disp.resolution = disp.admin_response
        disp.resolution_details = request.POST.get('resolution_details', '')
        disp.resolved_by = request.user
        disp.resolved_at = timezone.now()
        disp.save()

        # Contract action
        action = request.POST.get('contract_action')
        if action == 'RESET_ACTIVE':
            disp.contract.status = Contract.Status.ACTIVE
            disp.contract.save()
        elif action == 'CANCEL_CONTRACT':
            disp.contract.status = Contract.Status.CANCELLED
            disp.contract.save()
        elif action == 'COMPLETE_CONTRACT':
            disp.contract.status = Contract.Status.COMPLETED
            disp.contract.save()

        log_admin_action(
            request.user,
            "DISPUTE_RESOLVED",
            "Dispute",
            disp.id,
            f"Admin resolved dispute #{disp.dispute_number} with status {disp.status}.",
            request
        )

        for p in [disp.raised_by, disp.against_party]:
            NotificationService.send(
                recipient=p,
                notification_type='DISPUTE',
                title=f'Dispute #{disp.dispute_number} Arbitrated',
                message=f'Admin mediation update: {disp.admin_response[:100]}...',
                link=f'/disputes/{disp.id}/'
            )

        messages.success(request, f"Dispute #{disp.dispute_number} resolved.")
    return redirect('backoffice:disputes')


@login_required
@admin_required
def marketplace_management(request):
    categories = CropCategory.objects.annotate(listing_count=Count('listings')).order_by('name')
    reported = ReportedListing.objects.all().select_related('crop_listing', 'reported_by').order_by('-created_at')
    all_listings = CropListing.objects.all().select_related('farmer', 'category').order_by('-created_at')[:20]

    category_form = CropCategoryForm()
    if request.method == 'POST' and 'create_category' in request.POST:
        category_form = CropCategoryForm(request.POST)
        if category_form.is_valid():
            cat = category_form.save()
            log_admin_action(request.user, "CATEGORY_CREATED", "CropCategory", cat.id, f"Added category {cat.name}", request)
            messages.success(request, f"Crop category '{cat.name}' created.")
            return redirect('backoffice:marketplace')

    context = {
        'categories': categories,
        'reported_listings': reported,
        'all_listings': all_listings,
        'category_form': category_form,
    }
    return render(request, 'backoffice/marketplace.html', context)


@login_required
@admin_required
def toggle_listing_status(request, crop_id):
    listing = get_object_or_404(CropListing, pk=crop_id)
    with transaction.atomic():
        if listing.status == CropListing.Status.ACTIVE:
            listing.status = CropListing.Status.UNAVAILABLE
            msg = "Listing disabled and hidden from marketplace."
        else:
            listing.status = CropListing.Status.ACTIVE
            msg = "Listing reinstated to active marketplace status."
        listing.save()

        log_admin_action(
            request.user,
            "LISTING_TOGGLED",
            "CropListing",
            listing.id,
            f"Listing status changed to {listing.status}",
            request
        )
        messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER') or 'backoffice:marketplace')


@login_required
@admin_required
def resolve_reported_listing(request, report_id):
    report = get_object_or_404(ReportedListing, pk=report_id)
    report.is_resolved = True
    report.admin_notes = request.POST.get('admin_notes', 'Resolved by administrative moderation.')
    report.save()

    log_admin_action(request.user, "REPORT_RESOLVED", "ReportedListing", report.id, "Report closed by admin.", request)
    messages.success(request, "Listing report marked as resolved.")
    return redirect('backoffice:marketplace')


@login_required
@admin_required
def settings_view(request):
    settings_obj = PlatformSetting.get_settings()
    if request.method == 'POST':
        form = PlatformSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            log_admin_action(request.user, "SETTINGS_UPDATED", "PlatformSetting", settings_obj.id, "Updated platform configuration.", request)
            messages.success(request, "Platform settings successfully updated.")
            return redirect('backoffice:settings')
    else:
        form = PlatformSettingForm(instance=settings_obj)

    return render(request, 'backoffice/settings.html', {'form': form, 'settings': settings_obj})
