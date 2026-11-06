from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.accounts.decorators import farmer_required
from .models import CropListing, CropImage
from .forms import CropListingForm, CropImageForm
from apps.contracts.models import Contract
from apps.negotiations.models import Negotiation

@login_required
@farmer_required
def crop_list(request):
    listings = CropListing.objects.filter(farmer=request.user).select_related('category').order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        listings = listings.filter(status=status_filter)
    
    context = {
        'listings': listings,
        'current_status': status_filter,
    }
    return render(request, 'crops/list.html', context)

@login_required
@farmer_required
def crop_create(request):
    if request.method == 'POST':
        form = CropListingForm(request.POST, request.FILES)
        if form.is_valid():
            crop = form.save(commit=False)
            crop.farmer = request.user
            crop.quantity_remaining = crop.quantity_available
            crop.save()
            
            # Handle additional gallery images
            images = request.FILES.getlist('additional_images')
            for img in images:
                CropImage.objects.create(listing=crop, image=img)
                
            messages.success(request, f'Crop listing "{crop.title}" published successfully!')
            return redirect('crops:detail', pk=crop.pk)
    else:
        initial = {}
        if hasattr(request.user, 'farmer_profile'):
            fp = request.user.farmer_profile
            initial = {
                'state': fp.state,
                'district': fp.district,
                'village': fp.village,
                'pincode': fp.pincode,
                'latitude': fp.latitude,
                'longitude': fp.longitude,
            }
        form = CropListingForm(initial=initial)
    return render(request, 'crops/create.html', {'form': form})

@login_required
def crop_detail(request, pk):
    crop = get_object_or_404(CropListing.objects.select_related('farmer', 'category'), pk=pk)
    if crop.status == CropListing.Status.DRAFT and crop.farmer != request.user and not request.user.is_admin_user:
        messages.error(request, 'This crop listing is not available.')
        return redirect('marketplace:index')
    
    # Increment views
    crop.views_count += 1
    crop.save(update_fields=['views_count'])
    
    gallery = crop.gallery_images.all()
    
    # Performance metrics for the farmer
    related_contracts = Contract.objects.filter(crop_listing=crop)
    related_negotiations = Negotiation.objects.filter(crop_listing=crop)
    
    context = {
        'crop': crop,
        'gallery': gallery,
        'is_owner': crop.farmer == request.user,
        'related_contracts_count': related_contracts.count(),
        'active_contracts_count': related_contracts.filter(status=Contract.Status.ACTIVE).count(),
        'inquiries_count': related_negotiations.count(),
    }
    return render(request, 'crops/detail.html', context)

@login_required
@farmer_required
def crop_edit(request, pk):
    crop = get_object_or_404(CropListing, pk=pk, farmer=request.user)
    if request.method == 'POST':
        form = CropListingForm(request.POST, request.FILES, instance=crop)
        if form.is_valid():
            crop = form.save()
            
            # Handle additional images uploaded during edit
            images = request.FILES.getlist('additional_images')
            for img in images:
                CropImage.objects.create(listing=crop, image=img)
                
            messages.success(request, 'Crop listing updated successfully!')
            return redirect('crops:detail', pk=crop.pk)
    else:
        form = CropListingForm(instance=crop)
    return render(request, 'crops/edit.html', {'form': form, 'crop': crop})

@login_required
@farmer_required
def crop_update_quantity(request, pk):
    crop = get_object_or_404(CropListing, pk=pk, farmer=request.user)
    if request.method == 'POST':
        new_qty_str = request.POST.get('quantity_remaining')
        try:
            new_qty = Decimal(new_qty_str)
            if new_qty < 0:
                messages.error(request, 'Quantity remaining cannot be negative.')
            elif new_qty > crop.quantity_available:
                messages.error(request, f'Remaining quantity cannot exceed total available quantity ({crop.quantity_available} {crop.unit}).')
            else:
                crop.quantity_remaining = new_qty
                if crop.quantity_remaining == 0:
                    crop.status = CropListing.Status.SOLD
                elif crop.status == CropListing.Status.SOLD and crop.quantity_remaining > 0:
                    crop.status = CropListing.Status.ACTIVE
                crop.save(update_fields=['quantity_remaining', 'status'])
                messages.success(request, f'Remaining quantity updated to {crop.quantity_remaining} {crop.unit}.')
        except (ValueError, TypeError):
            messages.error(request, 'Please provide a valid numeric quantity.')
    return redirect('crops:detail', pk=crop.pk)

@login_required
@farmer_required
def crop_delete(request, pk):
    crop = get_object_or_404(CropListing, pk=pk, farmer=request.user)
    if request.method == 'POST':
        title = crop.title
        crop.delete()
        messages.success(request, f'Crop listing "{title}" deleted successfully.')
        return redirect('crops:list')
    return render(request, 'crops/confirm_delete.html', {'crop': crop})

@login_required
@farmer_required
def crop_toggle_status(request, pk):
    crop = get_object_or_404(CropListing, pk=pk, farmer=request.user)
    if request.method == 'POST':
        if crop.status == CropListing.Status.ACTIVE:
            crop.status = CropListing.Status.UNAVAILABLE
            messages.info(request, f'"{crop.title}" is now marked as Unavailable.')
        elif crop.status == CropListing.Status.UNAVAILABLE:
            crop.status = CropListing.Status.ACTIVE
            messages.success(request, f'"{crop.title}" is now Active.')
        crop.save(update_fields=['status'])
    return redirect('crops:list')
