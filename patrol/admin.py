from django.contrib import admin
from .models import JadwalRonda, AbsensiShift

# Register your models here.
@admin.register(JadwalRonda)
class JadwalRondaAdmin(admin.ModelAdmin):
    list_display   = ['petugas', 'tanggal', 'jam_mulai', 'jam_selesai']
    list_filter    = ['tanggal']
    search_fields  = ['petugas__profile__nama_lengkap']
    date_hierarchy = 'tanggal'

    readonly_fields = ['nama_shift']

@admin.register(AbsensiShift)
class AbsensiShiftAdmin(admin.ModelAdmin):
    list_display    = ['jadwal', 'waktu_absen', 'status_absen', 'jarak_dari_pos']
    list_filter     = ['status_absen']
    readonly_fields = ['jadwal', 'waktu_absen', 'foto_absen',
                       'latitude', 'longitude', 'akurasi_gps',
                       'jarak_dari_pos', 'status_absen']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # RT tidak bisa edit apapun

    def has_delete_permission(self, request, obj=None):
        # Hanya superuser/admin yang bisa hapus
        return request.user.is_superuser