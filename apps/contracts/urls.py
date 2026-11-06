from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('', views.contract_list, name='list'),
    path('request/<uuid:crop_id>/', views.request_contract, name='request'),
    path('<uuid:pk>/', views.contract_detail, name='detail'),
    path('<uuid:pk>/accept/', views.accept_contract, name='accept'),
    path('<uuid:pk>/reject/', views.reject_contract, name='reject'),
    path('<uuid:pk>/amend/', views.propose_amendment, name='amend'),
    path('<uuid:pk>/pdf/', views.download_pdf, name='pdf'),
    path('<uuid:pk>/update-status/', views.update_status, name='update_status'),
]