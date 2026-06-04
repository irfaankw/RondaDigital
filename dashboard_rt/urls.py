from django.urls import path
from . import views

app_name = 'dashboard_rt'

urlpatterns = [
    path('',                        views.dashboard,      name='dashboard'),
    path('jadwal-ronda/',           views.jadwal_ronda,   name='jadwal_ronda'),
    path('jadwal-ronda/buat/',      views.jadwal_buat,    name='jadwal_buat'),
    path('jadwal-ronda/<int:pk>/',  views.jadwal_detail,  name='jadwal_detail'),
    path('jadwal-ronda/<int:pk>/edit/',  views.jadwal_edit,   name='jadwal_edit'),
    path('jadwal-ronda/<int:pk>/hapus/', views.jadwal_hapus,  name='jadwal_hapus'),
]