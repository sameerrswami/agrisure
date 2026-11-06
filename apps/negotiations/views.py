from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Negotiation, Offer
from .forms import OfferForm
from .services import NegotiationService
from apps.crops.models import CropListing
from apps.notifications.services import NotificationService

@login_required
def negotiation_list(request):
    if request.user.is_farmer:
        negotiations = Negotiation.objects.filter(farmer=request.user)
    elif request.user.is_buyer:
        negotiations = Negotiation.objects.filter(buyer=request.user)
    else:
        negotiations = Negotiation.objects.all()
    
    return render(request, 'negotiations/list.html', {
        'negotiations': negotiations.select_related('crop_listing', 'farmer', 'buyer')
    })

@login_required
def start_negotiation(request, crop_id):
    crop = get_object_or_404(CropListing, pk=crop_id, status=CropListing.Status.ACTIVE)
    if request.user == crop.farmer:
        messages.error(request, "You cannot negotiate on your own listing.")
        return redirect('crops:detail', pk=crop_id)
        
    negotiation, created = Negotiation.objects.get_or_create(
        crop_listing=crop,
        buyer=request.user,
        defaults={'farmer': crop.farmer, 'status': Negotiation.Status.OPEN}
    )
    
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.negotiation = negotiation
            offer.submitted_by = request.user
            offer.offer_type = Offer.OfferType.INITIAL if created else Offer.OfferType.COUNTER
            offer.save()
            
            negotiation.status = Negotiation.Status.OPEN
            negotiation.save()
            
            NotificationService.send(
                recipient=crop.farmer,
                notification_type='NEGOTIATION',
                title='New Price Offer on Crop Listing',
                message=f'{request.user.get_full_name()} offered ₹{offer.price_per_unit}/unit for {crop.title}.',
                link=f'/negotiations/{negotiation.id}/'
            )
            messages.success(request, 'Your offer has been submitted to the farmer!')
            return redirect('negotiations:detail', pk=negotiation.pk)
    else:
        initial = {
            'price_per_unit': crop.price_per_unit,
            'quantity': crop.quantity_remaining,
            'proposed_delivery_date': crop.expected_harvest_date,
        }
        form = OfferForm(initial=initial)
        
    return render(request, 'negotiations/start.html', {'form': form, 'crop': crop, 'negotiation': negotiation})

@login_required
def negotiation_detail(request, pk):
    negotiation = get_object_or_404(
        Negotiation.objects.select_related('crop_listing', 'farmer', 'buyer'),
        pk=pk
    )
    if request.user != negotiation.farmer and request.user != negotiation.buyer and not request.user.is_admin_user:
        messages.error(request, "Unauthorized access.")
        return redirect('core:home')
        
    offers = negotiation.offers.select_related('submitted_by').order_by('created_at')
    form = OfferForm()
    
    context = {
        'negotiation': negotiation,
        'offers': offers,
        'form': form,
        'is_farmer': request.user == negotiation.farmer,
        'is_buyer': request.user == negotiation.buyer,
        'latest_offer': negotiation.latest_offer,
    }
    return render(request, 'negotiations/detail.html', context)

@login_required
def make_counter_offer(request, pk):
    negotiation = get_object_or_404(Negotiation, pk=pk)
    if request.user != negotiation.farmer and request.user != negotiation.buyer:
        messages.error(request, "Unauthorized.")
        return redirect('negotiations:list')
        
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.negotiation = negotiation
            offer.submitted_by = request.user
            offer.offer_type = Offer.OfferType.COUNTER
            offer.save()
            
            # Mark previous offers as countered
            negotiation.offers.filter(status=Offer.Status.PENDING).exclude(id=offer.id).update(
                status=Offer.Status.COUNTERED
            )
            negotiation.status = Negotiation.Status.OPEN
            negotiation.save()
            
            other_party = negotiation.farmer if request.user == negotiation.buyer else negotiation.buyer
            NotificationService.send(
                recipient=other_party,
                notification_type='NEGOTIATION',
                title='Counter Offer Received',
                message=f'{request.user.get_full_name()} submitted a counter-offer of ₹{offer.price_per_unit}/unit.',
                link=f'/negotiations/{negotiation.id}/'
            )
            messages.success(request, 'Counter-offer sent!')
    return redirect('negotiations:detail', pk=negotiation.pk)

@login_required
def accept_offer(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)
    negotiation = offer.negotiation
    try:
        contract = NegotiationService.accept_offer(negotiation.id, offer.id, request.user)
        messages.success(request, f'Offer accepted! A formal contract #{contract.contract_number} has been created.')
        return redirect('contracts:detail', pk=contract.pk)
    except Exception as e:
        messages.error(request, str(e))
        return redirect('negotiations:detail', pk=negotiation.pk)

@login_required
def reject_offer(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)
    if request.user == offer.submitted_by:
        messages.error(request, "You cannot reject your own offer. You may withdraw it instead.")
        return redirect('negotiations:detail', pk=offer.negotiation.pk)
        
    offer.status = Offer.Status.REJECTED
    offer.save()
    offer.negotiation.status = Negotiation.Status.REJECTED
    offer.negotiation.save()
    
    NotificationService.send(
        recipient=offer.submitted_by,
        notification_type='NEGOTIATION',
        title='Offer Rejected',
        message=f'Your offer of ₹{offer.price_per_unit}/unit was rejected by {request.user.get_full_name()}.',
        link=f'/negotiations/{offer.negotiation.id}/'
    )
    messages.info(request, 'Offer rejected.')
    return redirect('negotiations:detail', pk=offer.negotiation.pk)

@login_required
def withdraw_offer(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id, submitted_by=request.user)
    offer.status = Offer.Status.WITHDRAWN
    offer.save()
    messages.info(request, 'Your offer has been withdrawn.')
    return redirect('negotiations:detail', pk=offer.negotiation.pk)
