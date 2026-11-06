from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.index, name='index'),
    path('crop/<uuid:pk>/', views.crop_detail, name='crop_detail'),
]
