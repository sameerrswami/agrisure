from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('', views.review_list, name='list'),
    path('contract/<uuid:contract_id>/', views.create_review, name='create'),
]
