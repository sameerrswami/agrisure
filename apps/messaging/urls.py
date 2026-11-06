from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('<uuid:pk>/', views.conversation_detail, name='conversation'),
    path('<uuid:pk>/messages/', views.message_stream, name='message_stream'),
    path('start/<uuid:user_id>/', views.start_conversation, name='start'),
]