from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    path('', views.call_dashboard, name='dashboard'),
    path('inbound-webhook/', views.inbound_call_webhook, name='inbound_webhook'),
    path('ivr-handler/', views.ivr_handler, name='ivr_handler'),
    path('status-callback/', views.call_status_callback, name='status_callback'),
    path('outbound/', views.outbound_call, name='outbound_call'),
    path('outbound-twiml/', views.outbound_twiml, name='outbound_twiml'),
    path('api/logs/', views.call_logs_api, name='call_logs_api'),
]
