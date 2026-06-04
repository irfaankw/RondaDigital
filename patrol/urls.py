from django.urls import path
from . import views

app_name = 'patrol'

urlpatterns = [
    # Menu 1: Dashboard Petugas
    path('dashboard/', views.petugas_dashboard, name='petugas_home'),
    
    # Menu 2: Halaman Pantau CCTV
    path('cctv/', views.petugas_cctv, name='petugas_cctv'),
    
    # Menu 3: Riwayat Alert / Laporan Masuk
    path('alert/', views.petugas_alert, name='petugas_alert'),
    
    # Menu 4: Halaman Absensi & Shift (Kode yang kita buat sebelumnya)
    path('shift/', views.petugas_shift, name='petugas_shift'),

    #Menu 5: Halaman untuk menyimpan absensi petugas
    path('shift/simpan/', views.simpan_absensi,   name='simpan_absensi'),
]