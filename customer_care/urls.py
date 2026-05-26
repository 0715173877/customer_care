"""
URL configuration for customer_care project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('payments:dashboard'), name='home'),
    path('payments/', include('payments.urls')),
]
