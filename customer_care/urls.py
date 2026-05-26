"""
URL configuration for customer_care project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', lambda request: redirect('payments:dashboard'), name='home'),
    path('payments/', include('payments.urls')),
    path('calls/', include('calls.urls')),
    path('sms/', include('sms_app.urls')),
    path('chatbot/', include('chatbot.urls')),
]
