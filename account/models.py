from django.contrib.auth.models import User
from django.db import models

class NIKWhitelist(models.Model):
    nik         = models.CharField(max_length=16, unique=True)
    nama_sesuai = models.CharField(max_length=100, blank=True)
    is_used     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'NIK Whitelist'
        verbose_name_plural = 'NIK Whitelist'

    def __str__(self):
        return self.nik

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('WARGA',   'Warga'),
        ('PETUGAS', 'Petugas Ronda'),
        ('RT',      'Pengurus RT'),
    ]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nik          = models.CharField(max_length=16, unique=True, null=True, blank=True)
    nama_lengkap = models.CharField(max_length=100, blank=True)
    no_hp        = models.CharField(max_length=15, blank=True)
    rt = models.CharField(max_length=10, blank=True, null=True)
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default='WARGA')
    is_verified  = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Profil Pengguna'
        verbose_name_plural = 'Profil Pengguna'

    def __str__(self):
        return f"{self.nama_lengkap} ({self.user.username})"