from django.urls import path
from . import views

app_name = 'dashboard_rt'
urlpatterns = [
    # ── Dashboard utama ──────────────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),

    # ── Jadwal Ronda ─────────────────────────────────────────────────────────
    path('jadwal/',              views.jadwal_ronda,  name='jadwal_ronda'),
    path('jadwal/buat/',         views.jadwal_buat,   name='jadwal_buat'),
    path('jadwal/<int:pk>/',     views.jadwal_detail, name='jadwal_detail'),
    path('jadwal/<int:pk>/edit/',views.jadwal_edit,   name='jadwal_edit'),
    path('jadwal/<int:pk>/hapus/',views.jadwal_hapus, name='jadwal_hapus'),

    # ── Verifikasi Warga ──────────────────────────────────────────────────────
    path('verifikasi-warga/',               views.verifikasi_warga, name='verifikasi_warga'),
    path('verifikasi-warga/<int:pk>/aksi/', views.verifikasi_aksi,  name='verifikasi_aksi'),

    # ── Upload NIK CSV (baru) ─────────────────────────────────────────────────
    path('upload-nik-csv/', views.upload_nik_csv, name='upload_nik_csv'),
]