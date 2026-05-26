"""
URL configuration for customer_care project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('chatbot:dashboard'), name='home'),
    path('calls/', include('calls.urls')),
    path('sms/', include('sms_app.urls')),
    path('chat/', include('chatbot.urls')),
    path('payments/', include('payments.urls')),
]
