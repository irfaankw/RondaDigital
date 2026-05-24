from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nama_lengkap = models.CharField(max_length=150)
    no_hp       = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return f"{self.nama_lengkap} ({self.user.email})"

    class Meta:
        verbose_name        = "Profil Pengguna"
        verbose_name_plural = "Profil Pengguna"