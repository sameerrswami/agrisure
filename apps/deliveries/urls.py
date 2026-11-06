from django.urls import path
from . import views

app_name = 'deliveries'

urlpatterns = [
    path('', views.delivery_list, name='list'),
    path('<uuid:pk>/', views.delivery_detail, name='detail'),
    path('create/<uuid:contract_id>/', views.create_delivery, name='create'),
    path('<uuid:pk>/dispatch/', views.dispatch_delivery, name='dispatch'),
    path('<uuid:pk>/confirm/', views.confirm_delivery, name='confirm'),
    path('contract/<uuid:contract_id>/complete/', views.complete_contract_fulfillment, name='complete_contract'),
]
