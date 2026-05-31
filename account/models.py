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
    GENDER_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]
    SUBMISSION_CHOICES = [
        ('draft',    'Belum Dikirim'),
        ('pending',  'Menunggu Verifikasi'),
        ('verified', 'Terverifikasi'),
    ]

    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nik               = models.CharField(max_length=16, unique=True, null=True, blank=True)
    nama_lengkap      = models.CharField(max_length=100, blank=True)
    no_hp             = models.CharField(max_length=15, blank=True)
    rt                = models.CharField(max_length=10, blank=True, null=True)
    role              = models.CharField(max_length=10, choices=ROLE_CHOICES, default='WARGA')
    active_role       = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True)
    is_verified       = models.BooleanField(default=False)
    submission_status = models.CharField(max_length=10, choices=SUBMISSION_CHOICES, default='draft')
    created_at        = models.DateTimeField(auto_now_add=True)

    # Identitas tambahan
    alamat            = models.TextField(blank=True)
    tanggal_lahir     = models.DateField(null=True, blank=True)
    pekerjaan         = models.CharField(max_length=100, blank=True)
    rw                = models.CharField(max_length=10, blank=True, null=True)
    jenis_kelamin     = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    # Dokumen
    foto_profil       = models.ImageField(upload_to='profil/', null=True, blank=True)
    foto_ktp          = models.ImageField(upload_to='dokumen/ktp/', null=True, blank=True)
    foto_kk           = models.ImageField(upload_to='dokumen/kk/', null=True, blank=True)

    class Meta:
        verbose_name        = 'Profil Pengguna'
        verbose_name_plural = 'Profil Pengguna'

    def __str__(self):
        return f"{self.nama_lengkap} ({self.user.username})"

    def get_active_role(self):
        """Return active_role kalau ada, fallback ke role utama."""
        if self.active_role:
            return self.active_role
        else:
            return self.role

    @property
    def progress(self):
        """Hitung progress verifikasi 0-4."""
        if self.is_verified:
            return 4
        score = 1  # Langkah 1: Buat Akun sudah pasti selesai
        if self.nama_lengkap and self.nik and self.no_hp and self.alamat and self.tanggal_lahir and self.pekerjaan:
            score += 1  # Langkah 2: Identitas lengkap
        if self.foto_ktp or self.foto_kk:
            score += 1  # Langkah 3: Dokumen terupload
        return score