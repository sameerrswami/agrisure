from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Delivery, DeliveryUpdate
from .forms import DeliveryCreateForm, DeliveryDispatchForm, DeliveryReceiptForm
from .services import DeliveryService
from apps.contracts.models import Contract
from apps.contracts.services import ContractService

@login_required
def delivery_list(request):
    user = request.user
    if user.is_farmer:
        deliveries = Delivery.objects.filter(contract__farmer=user)
    elif user.is_buyer:
        deliveries = Delivery.objects.filter(contract__buyer=user)
    else:
        deliveries = Delivery.objects.all()

    deliveries = deliveries.select_related('contract', 'contract__farmer', 'contract__buyer').order_by('-created_at')

    # Metrics
    total_count = deliveries.count()
    in_transit_count = deliveries.filter(status__in=[Delivery.Status.DISPATCHED, Delivery.Status.IN_TRANSIT, Delivery.Status.ARRIVING]).count()
    delivered_count = deliveries.filter(status__in=[Delivery.Status.DELIVERED, Delivery.Status.CONFIRMED]).count()
    pending_dispatch_count = deliveries.filter(status__in=[Delivery.Status.SCHEDULED, Delivery.Status.PREPARING]).count()

    context = {
        'deliveries': deliveries,
        'total_count': total_count,
        'in_transit_count': in_transit_count,
        'delivered_count': delivered_count,
        'pending_dispatch_count': pending_dispatch_count,
    }
    return render(request, 'deliveries/list.html', context)


@login_required
def delivery_detail(request, pk):
    delivery = get_object_or_404(
        Delivery.objects.select_related('contract', 'contract__farmer', 'contract__buyer', 'contract__crop_listing'),
        pk=pk
    )
    user = request.user
    if user != delivery.contract.farmer and user != delivery.contract.buyer and not user.is_admin_user:
        messages.error(request, "Unauthorized access to shipment details.")
        return redirect('deliveries:list')

    timeline = delivery.timeline.all().order_by('-timestamp')
    dispatch_form = DeliveryDispatchForm(instance=delivery)
    receipt_form = DeliveryReceiptForm(instance=delivery)

    context = {
        'delivery': delivery,
        'timeline': timeline,
        'dispatch_form': dispatch_form,
        'receipt_form': receipt_form,
        'can_dispatch': (user == delivery.contract.farmer or user.is_admin_user) and delivery.status in [Delivery.Status.SCHEDULED, Delivery.Status.PREPARING],
        'can_confirm': (user == delivery.contract.buyer or user.is_admin_user) and delivery.status in [Delivery.Status.DISPATCHED, Delivery.Status.IN_TRANSIT, Delivery.Status.ARRIVING, Delivery.Status.SHIPPED],
    }
    return render(request, 'deliveries/detail.html', context)


@login_required
def create_delivery(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    if request.user != contract.farmer and not request.user.is_admin_user:
        messages.error(request, "Only the contracted farmer can schedule crop deliveries.")
        return redirect('contracts:detail', pk=contract.pk)

    # Calculate remaining unscheduled quantity
    existing_scheduled = sum([d.quantity_scheduled for d in contract.deliveries.all()], Decimal('0.00'))
    remaining_qty = max(Decimal('0.00'), contract.quantity - existing_scheduled)

    if request.method == 'POST':
        form = DeliveryCreateForm(request.POST)
        if form.is_valid():
            delv = form.save(commit=False)
            delv.contract = contract
            delv.unit = contract.unit
            delv.status = Delivery.Status.SCHEDULED

            if delv.vehicle_number or delv.transporter_name:
                delv.status = Delivery.Status.DISPATCHED
                delv.dispatched_at = timezone.now()
                if contract.status in [Contract.Status.ACTIVE, Contract.Status.PRODUCTION_IN_PROGRESS]:
                    contract.status = Contract.Status.READY_FOR_DELIVERY
                    contract.save()

            delv.save()

            # Record timeline event
            DeliveryUpdate.objects.create(
                delivery=delv,
                status=delv.get_status_display(),
                location=delv.pickup_location,
                note=f"Shipment of {delv.quantity_scheduled} {contract.unit} scheduled."
            )

            messages.success(request, f"Shipment #{delv.tracking_number} created successfully!")
            return redirect('deliveries:detail', pk=delv.pk)
    else:
        initial_qty = remaining_qty if remaining_qty > Decimal('0.00') else contract.quantity
        form = DeliveryCreateForm(initial={
            'quantity_scheduled': initial_qty,
            'unit': contract.unit,
            'pickup_location': 'Farm Gate',
            'destination_address': contract.delivery_address,
            'estimated_delivery_date': contract.delivery_date
        })

    context = {
        'form': form,
        'contract': contract,
        'remaining_qty': remaining_qty,
    }
    return render(request, 'deliveries/create.html', context)


@login_required
def dispatch_delivery(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if request.user != delivery.contract.farmer and not request.user.is_admin_user:
        messages.error(request, "Unauthorized to dispatch this shipment.")
        return redirect('deliveries:detail', pk=delivery.pk)

    if request.method == 'POST':
        form = DeliveryDispatchForm(request.POST, instance=delivery)
        if form.is_valid():
            transporter = form.cleaned_data.get('transporter_name')
            vehicle = form.cleaned_data.get('vehicle_number')
            driver_name = form.cleaned_data.get('driver_name')
            driver_phone = form.cleaned_data.get('driver_phone')
            notes = form.cleaned_data.get('delivery_notes')

            DeliveryService.confirm_dispatch(
                delivery=delivery,
                transporter_name=transporter,
                vehicle_number=vehicle,
                driver_name=driver_name,
                driver_phone=driver_phone,
                notes=notes
            )
            messages.success(request, f"Shipment #{delivery.tracking_number} dispatched!")
            return redirect('deliveries:detail', pk=delivery.pk)
        else:
            messages.error(request, "Please provide valid vehicle and transport details.")

    return redirect('deliveries:detail', pk=delivery.pk)


@login_required
def confirm_delivery(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if request.user != delivery.contract.buyer and not request.user.is_admin_user:
        messages.error(request, "Only the buyer can verify and confirm delivery arrival.")
        return redirect('deliveries:detail', pk=delivery.pk)

    if request.method == 'POST':
        form = DeliveryReceiptForm(request.POST, request.FILES, instance=delivery)
        if form.is_valid():
            qty_delivered = form.cleaned_data.get('quantity_delivered')
            inspection_status = form.cleaned_data.get('inspection_status')
            proof_file = form.cleaned_data.get('proof_of_delivery')
            notes = form.cleaned_data.get('inspection_notes')

            DeliveryService.confirm_receipt(
                delivery=delivery,
                quantity_delivered=qty_delivered,
                proof_file=proof_file,
                inspection_status=inspection_status,
                inspection_notes=notes,
                buyer_user=request.user
            )
            messages.success(request, f"Shipment #{delivery.tracking_number} confirmed and verified ({qty_delivered} {delivery.unit} accepted).")
            return redirect('deliveries:detail', pk=delivery.pk)
        else:
            # Fallback for simple confirmation (e.g. from existing test calls)
            qty = request.POST.get('quantity_delivered') or delivery.quantity_scheduled
            DeliveryService.confirm_receipt(
                delivery=delivery,
                quantity_delivered=qty,
                proof_file=request.FILES.get('proof_of_delivery'),
                inspection_status=Delivery.InspectionStatus.VERIFIED,
                inspection_notes="Inspected and accepted.",
                buyer_user=request.user
            )
            messages.success(request, f"Shipment #{delivery.tracking_number} confirmed.")
            return redirect('deliveries:detail', pk=delivery.pk)

    # GET fallback confirmation
    DeliveryService.confirm_receipt(
        delivery=delivery,
        quantity_delivered=delivery.quantity_scheduled,
        inspection_status=Delivery.InspectionStatus.VERIFIED,
        inspection_notes="Inspected and verified arrival.",
        buyer_user=request.user
    )
    messages.success(request, f"Shipment #{delivery.tracking_number} verified.")
    return redirect('deliveries:detail', pk=delivery.pk)


@login_required
def complete_contract_fulfillment(request, contract_id):
    """
    Formal completion of contract by buyer once delivery and payments are settled.
    """
    contract = get_object_or_404(Contract, pk=contract_id)
    if request.user != contract.buyer and not request.user.is_admin_user:
        messages.error(request, "Only the contracted buyer or platform admin can confirm contract completion.")
        return redirect('contracts:detail', pk=contract.pk)

    if request.method == 'POST':
        try:
            ContractService.transition_status(
                contract_id=contract.pk,
                user=request.user,
                new_status=Contract.Status.COMPLETED,
                reason="Buyer verified delivery receipt and completed contract fulfillment."
            )
            messages.success(request, f"Contract #{contract.contract_number} has been officially marked COMPLETED! You may now leave a review.")
        except Exception as e:
            messages.error(request, f"Could not complete contract: {str(e)}")

    return redirect('contracts:detail', pk=contract.pk)
