from django.urls import path
from . import views

app_name = 'emergency'
urlpatterns = [
    path('kirim/',              views.kirim_laporan,      name='kirim'),
    path('cek-pending/',        views.cek_pending,        name='cek_pending'),
    path('update/<int:laporan_id>/', views.update_status, name='update_status'),
    path('riwayat/',            views.riwayat_laporan,    name='riwayat'),
    path('alert/',              views.alert_petugas,      name='alert_petugas'),   # ← halaman
    path('api/alert/',          views.api_alert_petugas,  name='api_alert'),       # ← AJAX
]