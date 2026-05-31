from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, NIKWhitelist

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'nama_lengkap', 'nik', 'role', 'rt', 'rw', 'submission_status', 'is_verified', 'preview_ktp', 'preview_kk']
    list_filter   = ['role', 'is_verified', 'submission_status']
    search_fields = ['user__username', 'nama_lengkap', 'nik']
    readonly_fields = ['preview_ktp_besar', 'preview_kk_besar', 'preview_foto_profil']
    fields        = [
        'user', 'nik', 'nama_lengkap', 'no_hp', 'rt', 'rw',
        'alamat', 'tanggal_lahir', 'pekerjaan', 'jenis_kelamin',
        'role', 'submission_status', 'is_verified',
        'preview_foto_profil', 'foto_profil',
        'preview_ktp_besar', 'foto_ktp',
        'preview_kk_besar', 'foto_kk',
    ]

    def preview_ktp(self, obj):
        if obj.foto_ktp:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;">', obj.foto_ktp.url)
        return '-'
    preview_ktp.short_description = 'KTP'

    def preview_kk(self, obj):
        if obj.foto_kk:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;">', obj.foto_kk.url)
        return '-'
    preview_kk.short_description = 'KK'

    def preview_ktp_besar(self, obj):
        if obj.foto_ktp:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:400px;border-radius:8px;"></a>', obj.foto_ktp.url, obj.foto_ktp.url)
        return 'Belum diupload'
    preview_ktp_besar.short_description = 'Preview KTP'

    def preview_kk_besar(self, obj):
        if obj.foto_kk:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-width:400px;border-radius:8px;"></a>', obj.foto_kk.url, obj.foto_kk.url)
        return 'Belum diupload'
    preview_kk_besar.short_description = 'Preview KK'

    def preview_foto_profil(self, obj):
        if obj.foto_profil:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;"></a>', obj.foto_profil.url, obj.foto_profil.url)
        return 'Belum diupload'
    preview_foto_profil.short_description = 'Preview Foto Profil'

@admin.register(NIKWhitelist)
class NIKWhitelistAdmin(admin.ModelAdmin):
    list_display  = ['nik', 'nama_sesuai', 'is_used', 'created_at']
    search_fields = ['nik', 'nama_sesuai']