from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def role_required(role):
    """Decorator to restrict views to specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role != role:
                raise PermissionDenied("You don't have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def farmer_required(view_func):
    """Decorator to restrict views to farmers only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_farmer:
            raise PermissionDenied("This page is only accessible to farmers.")
        return view_func(request, *args, **kwargs)
    return wrapper


def buyer_required(view_func):
    """Decorator to restrict views to buyers only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_buyer:
            raise PermissionDenied("This page is only accessible to buyers.")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator to restrict views to admins only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_admin_user:
            raise PermissionDenied("This page is only accessible to administrators.")
        return view_func(request, *args, **kwargs)
    return wrapper
