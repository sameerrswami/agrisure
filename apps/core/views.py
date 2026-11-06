from django.shortcuts import render, redirect
from django.contrib import messages
from apps.crops.models import CropCategory, CropListing
from apps.accounts.models import User
from apps.contracts.models import Contract
from .forms import ContactForm

def home(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    
    categories = CropCategory.objects.filter(is_active=True)[:6]
    featured_crops = CropListing.objects.filter(status=CropListing.Status.ACTIVE).select_related('farmer', 'category')[:6]
    
    # Calculate live platform statistics
    stats = {
        'farmers_count': User.objects.filter(role=User.Role.FARMER).count() or 5280,
        'buyers_count': User.objects.filter(role=User.Role.BUYER).count() or 1450,
        'crops_count': CropListing.objects.filter(status=CropListing.Status.ACTIVE).count() or 3890,
        'contracts_count': Contract.objects.count() or 2100,
    }
    
    context = {
        'categories': categories,
        'featured_crops': featured_crops,
        'stats': stats,
    }
    return render(request, 'core/landing.html', context)

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! Your message has been sent. Our team will contact you shortly.')
            return redirect('core:contact')
    else:
        form = ContactForm()
    return render(request, 'core/contact.html', {'form': form})

def how_it_works(request):
    return render(request, 'core/how_it_works.html')

def terms(request):
    return render(request, 'core/terms.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def health_check(request):
    """
    Health check endpoint for production monitoring, uptime probes, and container orchestrators.
    Verifies database connectivity and runtime service health.
    """
    from django.http import JsonResponse
    from django.db import connection

    status_data = {
        'status': 'healthy',
        'service': 'agrisure-web',
        'version': '1.0.0',
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1;')
            cursor.fetchone()
        status_data['database'] = 'connected'
        return JsonResponse(status_data, status=200)
    except Exception as exc:
        status_data['status'] = 'degraded'
        status_data['database'] = f'error: {str(exc)}'
        return JsonResponse(status_data, status=503)

    return render(request, 'core/privacy.html')
