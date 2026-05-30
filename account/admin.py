from django.contrib import admin
from .models import UserProfile, NIKWhitelist

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'nama_lengkap', 'role', 'rt', 'is_verified']
    list_filter   = ['role', 'is_verified']
    search_fields = ['user__username', 'nama_lengkap', 'nik']
    fields        = ['user', 'nik', 'nama_lengkap', 'no_hp', 'rt', 'role', 'is_verified']

@admin.register(NIKWhitelist)
class NIKWhitelistAdmin(admin.ModelAdmin):
    list_display  = ['nik', 'nama_sesuai', 'is_used', 'created_at']
    search_fields = ['nik', 'nama_sesuai']