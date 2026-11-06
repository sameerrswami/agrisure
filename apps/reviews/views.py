from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg

from .models import Review
from .forms import ReviewForm
from apps.contracts.models import Contract
from apps.notifications.services import NotificationService
from apps.accounts.models import User

@login_required
def review_list(request):
    user = request.user
    if user.is_admin_user:
        reviews = Review.objects.all().select_related('contract', 'reviewer', 'reviewee').order_by('-created_at')
    else:
        reviews = Review.objects.filter(reviewee=user).select_related('contract', 'reviewer').order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0
    total_reviews = reviews.count()

    context = {
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': total_reviews,
    }
    return render(request, 'reviews/list.html', context)


@login_required
def create_review(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)

    # 1. Eligibility: Contract MUST be in COMPLETED status
    if contract.status != Contract.Status.COMPLETED:
        messages.error(request, "Reviews can only be submitted for officially completed contracts.")
        return redirect('contracts:detail', pk=contract.pk)

    # 2. Authority: User must be either the farmer or buyer on this contract
    if request.user != contract.farmer and request.user != contract.buyer:
        messages.error(request, "Only direct participants of this completed contract can submit a review.")
        return redirect('contracts:detail', pk=contract.pk)

    target_user = contract.buyer if request.user == contract.farmer else contract.farmer

    # 3. Duplicate Prevention: Cannot review the same completed contract twice
    if Review.objects.filter(contract=contract, reviewer=request.user).exists():
        messages.info(request, "You have already submitted a verified review for this completed contract.")
        return redirect('contracts:detail', pk=contract.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.contract = contract
            rev.reviewer = request.user
            rev.reviewee = target_user
            rev.is_verified_transaction = True
            rev.save()

            # Update reviewee's average rating in their profile
            all_received = Review.objects.filter(reviewee=target_user)
            avg = all_received.aggregate(Avg('rating'))['rating__avg']
            if avg:
                if target_user.is_farmer and hasattr(target_user, 'farmer_profile'):
                    target_user.farmer_profile.rating = round(avg, 2)
                    target_user.farmer_profile.save()
                elif target_user.is_buyer and hasattr(target_user, 'buyer_profile'):
                    if hasattr(target_user.buyer_profile, 'rating'):
                        target_user.buyer_profile.rating = round(avg, 2)
                        target_user.buyer_profile.save()

            # Notification
            NotificationService.send(
                recipient=target_user,
                notification_type='GENERAL',
                title=f'New {rev.rating}★ Review Received!',
                message=f'{request.user.get_full_name()} posted a review for Contract #{contract.contract_number}.',
                link=f'/reviews/'
            )

            messages.success(request, f"Thank you! Your verified {rev.rating}★ rating has been published.")
            return redirect('contracts:detail', pk=contract.pk)
    else:
        form = ReviewForm()

    context = {
        'form': form,
        'contract': contract,
        'target_user': target_user,
    }
    return render(request, 'reviews/create.html', context)
