from django.contrib import admin
from django.utils.html import format_html
from .models import LaporanDarurat


@admin.register(LaporanDarurat)
class LaporanDaruratAdmin(admin.ModelAdmin):
    list_display  = ('get_nama_lengkap', 'get_no_hp', 'kategori', 'status', 'ditangani_oleh', 'dibuat')
    list_filter   = ('status', 'kategori')
    search_fields = ('user__username', 'user__profile__nama_lengkap', 'deskripsi')
    readonly_fields = ('dibuat', 'lokasi_maps')

    fields = (
        'user', 'kategori', 'deskripsi', 'alamat',
        'latitude', 'longitude', 'lokasi_maps',
        'status', 'ditangani_oleh', 'dibuat',
    )

    def get_nama_lengkap(self, obj):
        return obj.user.profile.nama_lengkap if hasattr(obj.user, 'profile') else obj.user.username
    get_nama_lengkap.short_description = 'Nama Pelapor'

    def get_no_hp(self, obj):
        return obj.user.profile.no_hp if hasattr(obj.user, 'profile') else '-'
    get_no_hp.short_description = 'No HP'

    def lokasi_maps(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
            return format_html('<a href="{}" target="_blank">📍 Buka di Google Maps</a>', url)
        return '⚠️ Lokasi tidak tersedia'
    lokasi_maps.short_description = 'Lokasi'