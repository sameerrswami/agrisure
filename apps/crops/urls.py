from django.urls import path
from . import views

app_name = 'crops'

urlpatterns = [
    path('', views.crop_list, name='list'),
    path('create/', views.crop_create, name='create'),
    path('<uuid:pk>/', views.crop_detail, name='detail'),
    path('<uuid:pk>/edit/', views.crop_edit, name='edit'),
    path('<uuid:pk>/update-quantity/', views.crop_update_quantity, name='update_quantity'),
    path('<uuid:pk>/delete/', views.crop_delete, name='delete'),
    path('<uuid:pk>/toggle-status/', views.crop_toggle_status, name='toggle_status'),
]
