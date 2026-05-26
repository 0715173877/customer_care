from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('widget/', views.widget, name='widget'),
    path('api/message/', views.chat_api, name='chat_message'),
    path('api/reset/', views.reset_conversation, name='reset_chat'),
    path('api/history/<str:session_id>/', views.conversation_history, name='conversation_history'),
    path('api/knowledge-base/', views.knowledge_base_api, name='knowledge_base_search'),
    path('api/conversations/', views.conversations_api, name='conversations_api'),
]
