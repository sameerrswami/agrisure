"""
URL configuration for AgriSure project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('farmer/', include('apps.farmers.urls')),
    path('buyer/', include('apps.buyers.urls')),
    path('crops/', include('apps.crops.urls')),
    path('marketplace/', include('apps.marketplace.urls')),
    path('contracts/', include('apps.contracts.urls')),
    path('negotiations/', include('apps.negotiations.urls')),
    path('messages/', include('apps.messaging.urls')),
    path('payments/', include('apps.payments.urls')),
    path('deliveries/', include('apps.deliveries.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('disputes/', include('apps.disputes.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('backoffice/', include('apps.backoffice.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
