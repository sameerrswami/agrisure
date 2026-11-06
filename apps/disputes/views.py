from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import Dispute, DisputeMessage
from .forms import DisputeFileForm, DisputeMessageForm, DisputeResolutionForm
from apps.contracts.models import Contract
from apps.contracts.services import ContractService
from apps.notifications.services import NotificationService
from apps.accounts.decorators import admin_required

@login_required
def dispute_list(request):
    user = request.user
    if user.is_admin_user:
        disputes = Dispute.objects.all().select_related('contract', 'raised_by', 'against_party')
    else:
        disputes = Dispute.objects.filter(raised_by=user) | Dispute.objects.filter(against_party=user)
        disputes = disputes.select_related('contract', 'raised_by', 'against_party')

    status_filter = request.GET.get('status')
    if status_filter:
        disputes = disputes.filter(status=status_filter)

    open_count = disputes.filter(status__in=[Dispute.Status.OPEN, Dispute.Status.UNDER_REVIEW, Dispute.Status.AWAITING_INFO]).count()
    resolved_count = disputes.filter(status__in=[Dispute.Status.RESOLVED, Dispute.Status.CLOSED]).count()

    context = {
        'disputes': disputes.order_by('-created_at'),
        'open_count': open_count,
        'resolved_count': resolved_count,
        'current_status': status_filter,
    }
    return render(request, 'disputes/list.html', context)


@login_required
def dispute_detail(request, pk):
    dispute = get_object_or_404(
        Dispute.objects.select_related('contract', 'raised_by', 'against_party', 'resolved_by'),
        pk=pk
    )
    user = request.user
    if user != dispute.raised_by and user != dispute.against_party and not user.is_admin_user:
        messages.error(request, "Unauthorized to access this dispute file.")
        return redirect('disputes:list')

    # Handle posting a new message/evidence into the dispute thread
    if request.method == 'POST' and 'post_message' in request.POST:
        msg_form = DisputeMessageForm(request.POST, request.FILES)
        if msg_form.is_valid():
            msg = msg_form.save(commit=False)
            msg.dispute = dispute
            msg.sender = user
            msg.save()

            # Notify the opposite party
            recipient = dispute.against_party if user == dispute.raised_by else dispute.raised_by
            NotificationService.send(
                recipient=recipient,
                notification_type='DISPUTE',
                title=f'New Message on Dispute {dispute.dispute_number}',
                message=f'{user.get_full_name()} submitted a message regarding Dispute {dispute.dispute_number}.',
                link=f'/disputes/{dispute.id}/'
            )
            messages.success(request, "Mediation response posted.")
            return redirect('disputes:detail', pk=dispute.pk)
    else:
        msg_form = DisputeMessageForm()

    resolution_form = DisputeResolutionForm(instance=dispute)
    messages_thread = dispute.messages.all().select_related('sender').order_by('created_at')

    context = {
        'dispute': dispute,
        'messages_thread': messages_thread,
        'msg_form': msg_form,
        'resolution_form': resolution_form,
        'is_admin': user.is_admin_user,
    }
    return render(request, 'disputes/detail.html', context)


@login_required
def file_dispute(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    if request.user != contract.farmer and request.user != contract.buyer and not request.user.is_admin_user:
        messages.error(request, "You are not an authorized party to this contract.")
        return redirect('contracts:detail', pk=contract.pk)

    against_party = contract.buyer if request.user == contract.farmer else contract.farmer

    if request.method == 'POST':
        form = DisputeFileForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                disp = form.save(commit=False)
                disp.contract = contract
                disp.raised_by = request.user
                disp.against_party = against_party
                disp.status = Dispute.Status.OPEN
                
                # Check file upload
                if 'evidence_file' in request.FILES:
                    disp.evidence_document = request.FILES['evidence_file']
                disp.save()

                # Transition contract to DISPUTED status
                contract.status = Contract.Status.DISPUTED
                contract.save()

                # Notifications
                NotificationService.send(
                    recipient=against_party,
                    notification_type='DISPUTE',
                    title='Dispute Lodged on Contract',
                    message=f'A formal dispute ({disp.get_category_display()}) was raised by {request.user.get_full_name()} on Contract #{contract.contract_number}.',
                    link=f'/disputes/{disp.id}/'
                )

                messages.warning(request, f"Dispute #{disp.dispute_number} successfully registered. AgriSure Mediation Board will review your claim.")
                return redirect('disputes:detail', pk=disp.pk)
    else:
        form = DisputeFileForm()

    context = {
        'form': form,
        'contract': contract,
        'against_party': against_party,
    }
    return render(request, 'disputes/file.html', context)


@login_required
@admin_required
def resolve_dispute(request, pk):
    dispute = get_object_or_404(Dispute, pk=pk)
    if request.method == 'POST':
        form = DisputeResolutionForm(request.POST, instance=dispute)
        if form.is_valid():
            with transaction.atomic():
                disp = form.save(commit=False)
                disp.resolved_by = request.user
                disp.resolved_at = timezone.now()
                disp.save()

                # Contract state action
                contract_action = form.cleaned_data.get('contract_action')
                contract = disp.contract
                if contract_action == 'RESET_ACTIVE':
                    contract.status = Contract.Status.ACTIVE
                    contract.save()
                elif contract_action == 'CANCEL_CONTRACT':
                    contract.status = Contract.Status.CANCELLED
                    contract.save()
                elif contract_action == 'COMPLETE_CONTRACT':
                    contract.status = Contract.Status.COMPLETED
                    contract.save()

                # Notify both parties
                for party in [disp.raised_by, disp.against_party]:
                    NotificationService.send(
                        recipient=party,
                        notification_type='DISPUTE',
                        title=f'Dispute #{disp.dispute_number} {disp.get_status_display()}',
                        message=f'Admin resolution recorded: {disp.admin_response[:100]}...',
                        link=f'/disputes/{disp.id}/'
                    )

                messages.success(request, f"Dispute #{disp.dispute_number} updated to {disp.get_status_display()}.")
    return redirect('disputes:detail', pk=dispute.pk)
