from django.urls import path
from . import views

app_name = 'sms_app'

urlpatterns = [
    path('', views.sms_dashboard, name='dashboard'),
    path('inbound-webhook/', views.inbound_sms_webhook, name='inbound_webhook'),
    path('send/', views.send_sms, name='send_sms'),
    path('status-callback/', views.sms_status_callback, name='status_callback'),
    path('api/logs/', views.sms_logs_api, name='sms_logs_api'),
]
