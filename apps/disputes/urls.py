from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    path('', views.dispute_list, name='list'),
    path('<uuid:pk>/', views.dispute_detail, name='detail'),
    path('file/<uuid:contract_id>/', views.file_dispute, name='file'),
    path('<uuid:pk>/resolve/', views.resolve_dispute, name='resolve'),
]
