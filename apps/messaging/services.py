from django.utils import timezone
from .models import Conversation, Message
from apps.notifications.services import NotificationService

class MessagingService:
    @staticmethod
    def get_or_create_conversation(user1, user2, contract=None, subject=''):
        conv = Conversation.objects.filter(participants=user1).filter(participants=user2)
        if contract:
            conv = conv.filter(related_contract=contract)
        
        c = conv.first()
        if not c:
            c = Conversation.objects.create(
                subject=subject or (f"Contract #{contract.contract_number}" if contract else f"Chat with {user2.get_full_name()}"),
                related_contract=contract
            )
            c.participants.add(user1, user2)
        return c

    @staticmethod
    def send_message(conversation, sender, content, attachment=None):
        msg = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            attachment=attachment
        )
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Notify recipient
        for p in conversation.participants.exclude(id=sender.id):
            NotificationService.send(
                recipient=p,
                notification_type='MESSAGE',
                title=f'New Message from {sender.get_full_name()}',
                message=content[:100] + ('...' if len(content) > 100 else ''),
                link=f'/messages/{conversation.id}/'
            )
        return msg
