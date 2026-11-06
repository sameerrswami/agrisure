from django.urls import path
from . import views

app_name = 'farmers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/verify/', views.submit_verification, name='submit_verification'),
]
