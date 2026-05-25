from django.db import models
from django.contrib.auth.models import User

ROLE_WARGA   = 'WARGA'
ROLE_PETUGAS = 'PETUGAS'
ROLE_RT      = 'RT'

ROLE_CHOICES = [
    ('WARGA',   'Warga'),
    ('PETUGAS', 'Petugas Ronda'),
    ('RT',      'Ketua RT'),
]

class UserProfile(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nama_lengkap = models.CharField(max_length=150)
    no_hp        = models.CharField(max_length=15, unique=True)

    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_WARGA)
    is_verified  = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nama_lengkap} ({self.user.email})"

    class Meta:
        verbose_name        = "Profil Pengguna"
        verbose_name_plural = "Profil Pengguna"