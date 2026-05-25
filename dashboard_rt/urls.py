from django.urls import path
from . import views

app_name = 'dashboard_rt'
urlpatterns = [
    path('dashboard/', views.dashboard_utama, name='dashboard'),
]