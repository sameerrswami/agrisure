from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import buyer_required
from apps.crops.models import CropListing
from .models import BuyerProfile, SavedCrop
from .forms import BuyerProfileForm, BuyerVerificationForm
from .services import BuyerDashboardService

@login_required
@buyer_required
def dashboard(request):
    profile, _ = BuyerProfile.objects.get_or_create(user=request.user)
    recently_viewed_ids = request.session.get('recently_viewed_crops', [])
    metrics = BuyerDashboardService.get_dashboard_metrics(request.user, recently_viewed_ids)
    context = {
        'profile': profile,
        'metrics': metrics,
    }
    return render(request, 'buyers/dashboard.html', context)

@login_required
@buyer_required
def profile_view(request):
    profile, _ = BuyerProfile.objects.get_or_create(user=request.user)
    return render(request, 'buyers/profile.html', {'profile': profile})

@login_required
@buyer_required
def profile_edit(request):
    profile, _ = BuyerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = BuyerProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.phone = form.cleaned_data['phone']
            request.user.save()
            bp = form.save(commit=False)
            if 'verification_document' in request.FILES:
                bp.verification_status = BuyerProfile.VerificationStatus.PENDING
            bp.save()
            messages.success(request, 'Corporate profile updated successfully!')
            return redirect('buyers:profile')
    else:
        form = BuyerProfileForm(instance=profile, user=request.user)
    return render(request, 'buyers/profile_edit.html', {'form': form, 'profile': profile})

@login_required
@buyer_required
def upload_verification(request):
    profile, _ = BuyerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = BuyerVerificationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            bp = form.save(commit=False)
            bp.verification_status = BuyerProfile.VerificationStatus.PENDING
            bp.save()
            messages.success(request, 'Verification document submitted! Under review by AgriSure Compliance.')
    return redirect('buyers:profile')

@login_required
@buyer_required
def wishlist(request):
    saved = SavedCrop.objects.filter(buyer=request.user).select_related('crop_listing', 'crop_listing__farmer', 'crop_listing__category')
    return render(request, 'buyers/wishlist.html', {'saved_crops': saved})

@login_required
def toggle_wishlist(request, crop_id):
    crop = get_object_or_404(CropListing, pk=crop_id)
    saved, created = SavedCrop.objects.get_or_create(buyer=request.user, crop_listing=crop)
    if not created:
        saved.delete()
        is_saved = False
        msg = f'"{crop.title}" removed from your wishlist.'
    else:
        is_saved = True
        msg = f'"{crop.title}" added to your wishlist.'
    
    if request.headers.get('HX-Request'):
        return render(request, 'buyers/partials/wishlist_button.html', {'crop': crop, 'is_saved': is_saved})
    
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'marketplace:index'))
