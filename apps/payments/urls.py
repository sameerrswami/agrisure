from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='list'),
    path('<uuid:pk>/', views.payment_detail, name='detail'),
    path('<uuid:pk>/receipt/', views.download_receipt, name='download_receipt'),
    path('<uuid:pk>/refund/', views.admin_refund_payment, name='refund'),
    path('initiate/<uuid:contract_id>/', views.initiate_payment, name='initiate'),
    path('verify/', views.verify_payment, name='verify'),
    path('webhook/', views.razorpay_webhook, name='webhook'),
]
