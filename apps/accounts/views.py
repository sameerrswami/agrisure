from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import (
    FarmerRegistrationForm,
    BuyerRegistrationForm,
    LoginForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    ProfileEditForm,
    CustomPasswordChangeForm,
)
from .services import AuthService


def register_farmer(request):
    """Farmer registration view."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == 'POST':
        form = FarmerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create and send verification token
            token = AuthService.create_verification_token(user)
            AuthService.send_verification_email(user, token, request)
            messages.success(request, 'Account created! Please check your email to verify your account.')
            return redirect('accounts:login')
    else:
        form = FarmerRegistrationForm()

    return render(request, 'accounts/register_farmer.html', {'form': form})


def register_buyer(request):
    """Buyer registration view."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Store company name for later profile setup
            # The BuyerProfile will be created separately
            request.session['pending_company_name'] = form.cleaned_data.get('company_name', '')
            # Create and send verification token
            token = AuthService.create_verification_token(user)
            AuthService.send_verification_email(user, token, request)
            messages.success(request, 'Account created! Please check your email to verify your account.')
            return redirect('accounts:login')
    else:
        form = BuyerRegistrationForm()

    return render(request, 'accounts/register_buyer.html', {'form': form})


def login_view(request):
    """Custom login view."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            # Redirect to the appropriate dashboard
            next_url = request.GET.get('next', user.get_dashboard_url())
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


def role_redirect(request):
    """Redirect authenticated users to their role-specific dashboard."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect(request.user.get_dashboard_url())


def verify_email(request, token):
    """Verify email with token."""
    user, error = AuthService.verify_email(token)
    if error:
        messages.error(request, error)
    else:
        messages.success(request, 'Email verified successfully! You can now log in.')
    return redirect('accounts:login')


def forgot_password(request):
    """Forgot password view."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            token = AuthService.create_password_reset_token(email)
            if token:
                AuthService.send_password_reset_email(email, token, request)
            # Always show success message (don't reveal if email exists)
            messages.success(request, 'If an account exists with this email, you will receive a password reset link.')
            return redirect('accounts:login')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


def reset_password(request, token):
    """Reset password with token."""
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user, error = AuthService.reset_password(token, form.cleaned_data['password'])
            if error:
                messages.error(request, error)
            else:
                messages.success(request, 'Password reset successfully! You can now log in.')
                return redirect('accounts:login')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form, 'token': token})


@login_required
def profile(request):
    """View user profile."""
    return render(request, 'accounts/profile.html')


@login_required
def edit_profile(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def change_password(request):
    """Change password view."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})
