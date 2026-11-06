from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone
from .models import Contract, ContractHistory, ContractAcceptance
from .forms import ContractRequestForm, ContractAmendmentForm
from .services import ContractService
from apps.crops.models import CropListing
from apps.notifications.services import NotificationService

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required
def contract_list(request):
    if request.user.is_farmer:
        contracts = Contract.objects.filter(farmer=request.user)
    elif request.user.is_buyer:
        contracts = Contract.objects.filter(buyer=request.user)
    else:
        contracts = Contract.objects.all()
    
    tab = request.GET.get('tab', 'all')
    status_filter = request.GET.get('status')
    
    if status_filter:
        contracts = contracts.filter(status=status_filter)
    elif tab == 'requests' or tab == 'awaiting_approval':
        contracts = contracts.filter(status=Contract.Status.PENDING_FARMER)
    elif tab == 'awaiting_buyer':
        contracts = contracts.filter(status=Contract.Status.PENDING_BUYER)
    elif tab == 'active':
        contracts = contracts.filter(status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS])
    elif tab == 'production':
        contracts = contracts.filter(status=Contract.Status.PRODUCTION_IN_PROGRESS)
    elif tab == 'deliveries':
        contracts = contracts.filter(status__in=[Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED, Contract.Status.DELIVERED])
    elif tab == 'completed':
        contracts = contracts.filter(status=Contract.Status.COMPLETED)
    elif tab == 'cancelled':
        contracts = contracts.filter(status=Contract.Status.CANCELLED)

    # Tab counts for UI badges
    base_qs = Contract.objects.filter(farmer=request.user) if request.user.is_farmer else Contract.objects.filter(buyer=request.user)
    counts = {
        'all': base_qs.count(),
        'awaiting_approval': base_qs.filter(status=Contract.Status.PENDING_FARMER if request.user.is_farmer else Contract.Status.PENDING_BUYER).count(),
        'active': base_qs.filter(status__in=[Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]).count(),
        'deliveries': base_qs.filter(status__in=[Contract.Status.READY_FOR_DELIVERY, Contract.Status.PARTIALLY_DELIVERED, Contract.Status.DELIVERED]).count(),
        'completed': base_qs.filter(status=Contract.Status.COMPLETED).count(),
        'cancelled': base_qs.filter(status=Contract.Status.CANCELLED).count(),
    }

    context = {
        'contracts': contracts.select_related('crop_listing', 'farmer', 'buyer').order_by('-created_at'),
        'current_tab': tab,
        'current_status': status_filter,
        'counts': counts,
    }
    return render(request, 'contracts/list.html', context)

@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(
        Contract.objects.select_related('crop_listing', 'farmer', 'farmer__farmer_profile', 'buyer', 'buyer__buyer_profile'),
        pk=pk
    )
    if request.user != contract.farmer and request.user != contract.buyer and not request.user.is_admin_user:
        messages.error(request, "Unauthorized access to this contract.")
        return redirect('core:home')
    
    history = contract.history.all().order_by('-created_at')
    acceptances = contract.acceptances.select_related('user').order_by('-accepted_at')
    amendment_form = ContractAmendmentForm(instance=contract)
    
    # Check if current user has accepted the latest version
    user_accepted_current = False
    if request.user == contract.farmer:
        user_accepted_current = contract.farmer_accepted and (contract.farmer_accepted_version == contract.version)
    elif request.user == contract.buyer:
        user_accepted_current = contract.buyer_accepted and (contract.buyer_accepted_version == contract.version)

    context = {
        'contract': contract,
        'history': history,
        'acceptances': acceptances,
        'amendment_form': amendment_form,
        'is_farmer': request.user == contract.farmer,
        'is_buyer': request.user == contract.buyer,
        'user_accepted_current': user_accepted_current,
    }
    return render(request, 'contracts/detail.html', context)

@login_required
def request_contract(request, crop_id):
    if not request.user.is_buyer:
        messages.error(request, "Only registered institutional buyers can initiate a farming contract request.")
        return redirect('marketplace:crop_detail', pk=crop_id)
        
    crop = get_object_or_404(CropListing, pk=crop_id, status=CropListing.Status.ACTIVE)
    
    if request.method == 'POST':
        form = ContractRequestForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.crop_listing = crop
            contract.farmer = crop.farmer
            contract.buyer = request.user
            contract.title = f"Contract for {crop.title}"
            contract.unit = crop.unit
            contract.status = Contract.Status.PENDING_FARMER
            contract.version = 1
            
            # Buyer automatically accepts version 1 upon initiating
            contract.buyer_accepted = True
            contract.buyer_accepted_at = timezone.now()
            contract.buyer_accepted_version = 1
            contract.save()
            
            # Record explicit digital acceptance
            ip = get_client_ip(request)
            ContractAcceptance.objects.create(
                contract=contract,
                user=request.user,
                version=1,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                disclaimer_acknowledged=True
            )

            # Log history
            ContractHistory.objects.create(
                contract=contract,
                performed_by=request.user,
                from_status='DRAFT',
                to_status=Contract.Status.PENDING_FARMER,
                comment=f"Contract request initiated by buyer. Message: {form.cleaned_data.get('buyer_message', '')}"
            )
            
            # Generate initial PDF
            ContractService.generate_pdf(contract)
            
            # Notify farmer
            NotificationService.send(
                recipient=crop.farmer,
                notification_type='CONTRACT',
                title='New Contract Request Received',
                message=f'{request.user.get_full_name()} sent a contract request for {crop.title} ({contract.quantity} {contract.unit} at ₹{contract.price_per_unit}/unit).',
                link=f'/contracts/{contract.id}/'
            )
            
            messages.success(request, f'Contract request #{contract.contract_number} generated successfully and sent to farmer {crop.farmer.get_full_name()}!')
            return redirect('contracts:detail', pk=contract.pk)
    else:
        initial = {
            'quantity': crop.quantity_remaining,
            'price_per_unit': crop.price_per_unit,
            'advance_payment_percentage': 20,
            'delivery_date': crop.expected_harvest_date or timezone.now().date(),
            'required_quality_grade': crop.quality_grade,
            'quality_specifications': f"Grade: {crop.get_quality_grade_display()}, Variety: {crop.variety or 'Standard'}",
            'payment_terms': "20% advance upon contract signing in secured escrow, 80% balance disbursed upon delivery quality inspection.",
        }
        if hasattr(request.user, 'buyer_profile') and request.user.buyer_profile.delivery_address:
            initial['delivery_address'] = request.user.buyer_profile.delivery_address
        form = ContractRequestForm(initial=initial)
        
    return render(request, 'contracts/request.html', {'form': form, 'crop': crop})

@login_required
def accept_contract(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.user != contract.farmer and request.user != contract.buyer:
        messages.error(request, "Unauthorized access.")
        return redirect('contracts:list')

    if request.method in ['POST', 'GET']:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        try:
            ContractService.accept_contract(contract.id, request.user, ip_address=ip, user_agent=ua)
            contract.refresh_from_db()
            if contract.status == Contract.Status.ACTIVE:
                messages.success(request, f'Contract #{contract.contract_number} has been mutually accepted and is now ACTIVE!')
            else:
                messages.success(request, f'You accepted Contract #{contract.contract_number} (v{contract.version}). Awaiting counterpart acceptance.')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('contracts:detail', pk=contract.pk)

@login_required
def reject_contract(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.user != contract.farmer and request.user != contract.buyer:
        messages.error(request, "Unauthorized.")
        return redirect('contracts:list')

    if request.method in ['POST', 'GET']:
        reason = request.POST.get('cancellation_reason', '') or request.GET.get('cancellation_reason', 'Declined by participant')
        try:
            ContractService.transition_status(contract.id, request.user, Contract.Status.CANCELLED, reason=reason)
            messages.info(request, f'Contract #{contract.contract_number} has been cancelled.')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('contracts:detail', pk=contract.pk)

@login_required
def propose_amendment(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.user != contract.farmer and request.user != contract.buyer:
        messages.error(request, "Unauthorized.")
        return redirect('contracts:list')

    if request.method == 'POST':
        form = ContractAmendmentForm(request.POST)
        if form.is_valid():
            try:
                amended_contract = ContractService.propose_amendment(
                    contract_id=contract.id,
                    user=request.user,
                    form_data=form.cleaned_data,
                    amendment_reason=form.cleaned_data.get('amendment_reason', '')
                )
                messages.success(request, f'Amendment proposed! Contract updated to version v{amended_contract.version}. Counterpart has been notified.')
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, f'Amendment validation error: {form.errors}')
    return redirect('contracts:detail', pk=contract.pk)

@login_required
def update_status(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        reason = request.POST.get('reason', '')
        try:
            ContractService.transition_status(contract.id, request.user, new_status, reason=reason)
            messages.success(request, f'Contract status updated to {dict(Contract.Status.choices).get(new_status)}')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('contracts:detail', pk=contract.pk)

@login_required
def download_pdf(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.user != contract.farmer and request.user != contract.buyer and not request.user.is_admin_user:
        raise Http404("Unauthorized")
        
    if not contract.contract_pdf:
        ContractService.generate_pdf(contract)
        
    try:
        response = HttpResponse(contract.contract_pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="AgriSure_Contract_{contract.contract_number}_v{contract.version}.pdf"'
        return response
    except Exception:
        ContractService.generate_pdf(contract)
        response = HttpResponse(contract.contract_pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="AgriSure_Contract_{contract.contract_number}_v{contract.version}.pdf"'
        return response
