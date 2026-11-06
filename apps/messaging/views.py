from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from .models import Conversation, Message
from .forms import MessageForm
from .services import MessagingService
from apps.accounts.models import User
from apps.contracts.models import Contract

@login_required
def inbox(request):
    conversations = request.user.conversations.all().prefetch_related('participants', 'messages').order_by('-updated_at')
    
    # Search conversations
    q = request.GET.get('q', '').strip()
    if q:
        conversations = conversations.filter(
            Q(subject__icontains=q) |
            Q(participants__first_name__icontains=q) |
            Q(participants__last_name__icontains=q) |
            Q(messages__content__icontains=q)
        ).distinct()

    # Calculate unread counts per conversation
    conv_data = []
    for conv in conversations:
        other_participant = conv.participants.exclude(id=request.user.id).first()
        unread_count = conv.messages.filter(is_read=False).exclude(sender=request.user).count()
        conv_data.append({
            'conversation': conv,
            'other_participant': other_participant,
            'unread_count': unread_count,
            'latest_message': conv.latest_message,
        })

    return render(request, 'messaging/inbox.html', {
        'conversations_data': conv_data,
        'search_query': q,
        'total_conversations': len(conv_data),
    })

@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    
    # Enforce strict participant-only access (Prompt 3 Section 7)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise PermissionDenied("Unauthorized: Access to private conversations is restricted to participants.")
        
    # Mark messages as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(
        is_read=True, read_at=timezone.now()
    )
    
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    messages_list = conversation.messages.select_related('sender').order_by('created_at')
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            MessagingService.send_message(
                conversation=conversation,
                sender=request.user,
                content=form.cleaned_data['content'],
                attachment=form.cleaned_data.get('attachment')
            )
            return redirect('messaging:conversation', pk=conversation.pk)
        else:
            messages.error(request, f"Message error: {form.errors}")
    else:
        form = MessageForm()
        
    context = {
        'conversation': conversation,
        'other_participant': other_participant,
        'messages_list': messages_list,
        'form': form,
    }
    return render(request, 'messaging/conversation.html', context)

@login_required
def message_stream(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise PermissionDenied("Unauthorized.")
        
    # Mark as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(
        is_read=True, read_at=timezone.now()
    )
    messages_list = conversation.messages.select_related('sender').order_by('created_at')
    return render(request, 'messaging/partials/message_list.html', {
        'conversation': conversation,
        'messages_list': messages_list,
        'user': request.user
    })

@login_required
def start_conversation(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect('messaging:inbox')
        
    contract_id = request.GET.get('contract_id')
    contract = Contract.objects.filter(id=contract_id).first() if contract_id else None
    
    conv = MessagingService.get_or_create_conversation(request.user, target_user, contract)
    return redirect('messaging:conversation', pk=conv.pk)
