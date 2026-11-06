from django.urls import path
from . import views

app_name = 'negotiations'

urlpatterns = [
    path('', views.negotiation_list, name='list'),
    path('start/<uuid:crop_id>/', views.start_negotiation, name='start'),
    path('<uuid:pk>/', views.negotiation_detail, name='detail'),
    path('<uuid:pk>/counter/', views.make_counter_offer, name='counter'),
    path('offer/<uuid:offer_id>/accept/', views.accept_offer, name='accept_offer'),
    path('offer/<uuid:offer_id>/reject/', views.reject_offer, name='reject_offer'),
    path('offer/<uuid:offer_id>/withdraw/', views.withdraw_offer, name='withdraw_offer'),
]
