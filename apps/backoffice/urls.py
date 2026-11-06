from django.urls import path
from . import views

app_name = 'backoffice'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users_list, name='users'),
    path('users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/verify/', views.verify_user, name='verify_user'),
    path('users/<uuid:user_id>/reject/', views.reject_user, name='reject_user'),
    path('users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('contracts/', views.contracts_list, name='contracts'),
    path('payments/', views.payments_admin, name='payments'),
    path('disputes/', views.disputes_list, name='disputes'),
    path('disputes/<uuid:pk>/resolve/', views.resolve_dispute, name='resolve_dispute'),
    path('marketplace/', views.marketplace_management, name='marketplace'),
    path('marketplace/crop/<uuid:crop_id>/toggle/', views.toggle_listing_status, name='toggle_listing'),
    path('marketplace/report/<uuid:report_id>/resolve/', views.resolve_reported_listing, name='resolve_report'),
    path('settings/', views.settings_view, name='settings'),
]
