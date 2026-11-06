from django.urls import path
from . import views

app_name = 'buyers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/verify/', views.upload_verification, name='submit_verification'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<uuid:crop_id>/', views.toggle_wishlist, name='toggle_wishlist'),
]
