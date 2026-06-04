from django.db import models
from django.conf import settings

class LaporanDarurat(models.Model):
    KATEGORI_CHOICES = [
        ('pencurian',    'Pencurian / Perampokan'),
        ('kebakaran',    'Kebakaran / Asap'),
        ('medis',        'Medis Darurat'),
        ('mencurigakan', 'Orang Mencurigakan'),
    ]
    STATUS_CHOICES = [
        ('pending',  'Menunggu'),
        ('diproses', 'Diproses'),
        ('selesai',  'Selesai'),
    ]

    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='laporan_darurat')
    kategori     = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    deskripsi    = models.TextField(blank=True)
    alamat       = models.CharField(max_length=255, blank=True)
    latitude     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    ditangani_oleh = models.CharField(max_length=100, blank=True, help_text='Nama petugas atau instansi yang menangani')
    dibuat       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dibuat']

    def __str__(self):
        return f"{self.user} - {self.kategori} - {self.dibuat:%d/%m/%Y %H:%M}"

    @property
    def maps_url(self):
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return None