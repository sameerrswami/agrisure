from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

class NotificationService:
    @staticmethod
    def send(recipient, notification_type, title, message, link='', send_email_alert=True):
        notif = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
        
        # Email notification for important contract, negotiation, and delivery events (Prompt 3 Section 8)
        if send_email_alert and recipient.email:
            try:
                subject = f"[AgriSure] {title}"
                body = (
                    f"Namaste {recipient.get_full_name()},\n\n"
                    f"{message}\n\n"
                    f"View details: {link or '/dashboard/'}\n\n"
                    f"Best regards,\n"
                    f"AgriSure Contract Farming Platform"
                )
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'notifications@agrisure.in')
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[recipient.email],
                    fail_silently=True
                )
            except Exception:
                pass
                
        return notif
