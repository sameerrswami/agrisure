import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import User, EmailVerificationToken, PasswordResetToken


class AuthService:
    """Service layer for authentication operations."""

    @staticmethod
    def create_verification_token(user):
        """Create email verification token."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        return EmailVerificationToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )

    @staticmethod
    def verify_email(token_str):
        """Verify email with token."""
        try:
            token = EmailVerificationToken.objects.get(token=token_str, used=False)
        except EmailVerificationToken.DoesNotExist:
            return None, 'Invalid verification token.'

        if token.is_expired:
            return None, 'Verification token has expired.'

        token.used = True
        token.save()
        token.user.email_verified = True
        token.user.save()
        return token.user, None

    @staticmethod
    def create_password_reset_token(email):
        """Create password reset token."""
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return None  # Don't reveal if email exists

        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=1)
        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )
        return token

    @staticmethod
    def reset_password(token_str, new_password):
        """Reset password with token."""
        try:
            token = PasswordResetToken.objects.get(token=token_str, used=False)
        except PasswordResetToken.DoesNotExist:
            return None, 'Invalid reset token.'

        if token.is_expired:
            return None, 'Reset token has expired.'

        token.used = True
        token.save()
        token.user.set_password(new_password)
        token.user.save()
        return token.user, None

    @staticmethod
    def send_verification_email(user, token, request=None):
        """Send verification email."""
        if request:
            scheme = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            verify_url = f"{scheme}://{host}/accounts/verify-email/{token.token}/"
        else:
            verify_url = f"http://localhost:8000/accounts/verify-email/{token.token}/"

        subject = 'Verify your AgriSure account'
        message = f"""
Hello {user.first_name},

Thank you for registering with AgriSure!

Please verify your email address by clicking the link below:
{verify_url}

This link will expire in 24 hours.

Best regards,
The AgriSure Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )

    @staticmethod
    def send_password_reset_email(email, token, request=None):
        """Send password reset email."""
        if request:
            scheme = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            reset_url = f"{scheme}://{host}/accounts/reset-password/{token}/"
        else:
            reset_url = f"http://localhost:8000/accounts/reset-password/{token}/"

        subject = 'Reset your AgriSure password'
        message = f"""
Hello,

You requested a password reset for your AgriSure account.

Click the link below to set a new password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The AgriSure Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
