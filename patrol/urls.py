from django.urls import path
from . import views

app_name = 'patrol'

urlpatterns = [
    # Menu 1: Dashboard Petugas
    path('dashboard/',                      views.petugas_dashboard,    name='petugas_home'),

    # Menu 2: CCTV
    path('cctv/',                           views.petugas_cctv,         name='petugas_cctv'),

    # Menu 3: Alert
    path('alert/',                          views.petugas_alert,        name='petugas_alert'),

    # Menu 4: Shift & Absensi
    path('shift/',                          views.petugas_shift,        name='petugas_shift'),
    path('shift/simpan/',                   views.simpan_absensi,       name='simpan_absensi'),

    # Menu 5: Update item checklist patroli (AJAX)
    path('item/<int:log_id>/update/',       views.update_item_patroli,  name='update_item_patroli'),
]