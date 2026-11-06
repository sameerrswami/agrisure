from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.decorators import farmer_required
from .models import FarmerProfile
from .forms import FarmerProfileForm, FarmerVerificationForm
from .services import FarmerDashboardService

@login_required
@farmer_required
def dashboard(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    metrics = FarmerDashboardService.get_dashboard_metrics(request.user)
    context = {
        'profile': profile,
        'metrics': metrics,
    }
    return render(request, 'farmers/dashboard.html', context)

@login_required
@farmer_required
def profile_view(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    return render(request, 'farmers/profile.html', {'profile': profile})

@login_required
@farmer_required
def profile_edit(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = FarmerProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            # Update user fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.phone = form.cleaned_data['phone']
            request.user.save()
            
            p = form.save(commit=False)
            if p.completion_percentage >= 70:
                request.user.profile_completed = True
                request.user.save()
            p.save()
            
            messages.success(request, 'Farm profile updated successfully!')
            return redirect('farmers:profile')
    else:
        form = FarmerProfileForm(instance=profile, user=request.user)
    return render(request, 'farmers/profile_edit.html', {'form': form, 'profile': profile})

@login_required
@farmer_required
def submit_verification(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = FarmerVerificationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.verification_status = FarmerProfile.VerificationStatus.PENDING
            p.save()
            messages.success(request, 'Documents uploaded! Verification is under review.')
            return redirect('farmers:profile')
    return redirect('farmers:profile')
