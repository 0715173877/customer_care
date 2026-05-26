from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('intake/', views.intake_sms, name='intake'),
    path('review/<uuid:pk>/', views.review_detail, name='review'),
    path('authorize/<uuid:pk>/', views.authorize_detail, name='authorize'),
    path('history/', views.history, name='history'),
]
