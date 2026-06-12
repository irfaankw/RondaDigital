from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime


class JadwalRonda(models.Model):
    petugas     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jadwal_ronda')
    tanggal     = models.DateField()
    jam_mulai   = models.TimeField()
    jam_selesai = models.TimeField()
    nama_shift  = models.CharField(max_length=100, blank=True)
    dibuat_oleh = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='jadwal_dibuat'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Jadwal Ronda'
        verbose_name_plural = 'Jadwal Ronda'
        ordering            = ['tanggal', 'jam_mulai']
        unique_together     = ['petugas', 'tanggal', 'jam_mulai']

    def __str__(self):
        profile = getattr(self.petugas, 'profile', None)
        nama    = profile.nama_lengkap if profile else self.petugas.username
        return f"{nama} | {self.tanggal} {self.jam_mulai}"

    def get_datetime_mulai(self):
        dt = datetime.combine(self.tanggal, self.jam_mulai)
        return timezone.make_aware(dt)

    def get_datetime_selesai(self):
        from datetime import timedelta as td
        dt_mulai   = datetime.combine(self.tanggal, self.jam_mulai)
        dt_selesai = datetime.combine(self.tanggal, self.jam_selesai)
        if self.jam_selesai < self.jam_mulai:
            dt_selesai += td(days=1)
        return timezone.make_aware(dt_selesai)

    def batas_absen(self):
        return self.get_datetime_mulai() + timedelta(minutes=15)

    def is_terlambat(self):
        return timezone.now() > self.batas_absen()

    def is_shift_selesai(self):
        return timezone.now() > self.get_datetime_selesai()

    def is_absen_masih_bisa(self):
        now = timezone.now()
        return self.get_datetime_mulai() <= now <= self.get_datetime_selesai()


class AbsensiShift(models.Model):
    STATUS_ABSEN = [
        ('hadir',       'Hadir'),
        ('terlambat',   'Terlambat'),
        ('tidak_hadir', 'Tidak Hadir'),
    ]

    jadwal         = models.OneToOneField(JadwalRonda, on_delete=models.CASCADE, related_name='absensi')
    waktu_absen    = models.DateTimeField(auto_now_add=True)
    foto_absen     = models.ImageField(upload_to='absensi/foto/', null=True, blank=True)
    latitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    akurasi_gps    = models.FloatField(null=True, blank=True)
    jarak_dari_pos = models.FloatField(null=True, blank=True)
    status_absen   = models.CharField(max_length=15, choices=STATUS_ABSEN, default='hadir')

    class Meta:
        verbose_name        = 'Absensi Shift'
        verbose_name_plural = 'Absensi Shift'

    def __str__(self):
        return f"Absensi {self.jadwal} — {self.status_absen}"
    

class LogPatroli(models.Model):
    """
    Mencatat aktivitas petugas per item checklist patroli.
    Alur: belum → berjalan (klik Mulai) → selesai (klik Selesai).
 
    Karena semua petugas dalam 1 sesi ronda berbagi ItemPatroli yang sama
    (ItemPatroli hanya di jadwal[0]/representatif), maka tiap petugas
    punya LogPatroli masing-masing untuk item yang sama.
    """
    STATUS_CHOICES = [
        ('belum',    'Belum Dimulai'),
        ('berjalan', 'Sedang Berjalan'),
        ('selesai',  'Selesai'),
    ]
 
    item    = models.ForeignKey(
        'dashboard_rt.ItemPatroli',
        on_delete=models.CASCADE,
        related_name='log_patroli'
    )
    petugas = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='log_patroli'
    )
    jadwal  = models.ForeignKey(
        JadwalRonda,
        on_delete=models.CASCADE,
        related_name='log_patroli',
        null=True,
        blank=True,
    )
 
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='belum')
    waktu_mulai   = models.DateTimeField(null=True, blank=True)
    waktu_selesai = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name        = 'Log Patroli'
        verbose_name_plural = 'Log Patroli'
        unique_together     = ['item', 'petugas', 'jadwal']
        ordering            = ['item__urutan']
 
    def __str__(self):
        return f"[{self.get_status_display()}] {self.petugas} — {self.item.deskripsi}"
 
    @property
    def waktu_mulai_str(self):
        if self.waktu_mulai:
            return timezone.localtime(self.waktu_mulai).strftime('%H:%M')
        return None
 
    @property
    def waktu_selesai_str(self):
        if self.waktu_selesai:
            return timezone.localtime(self.waktu_selesai).strftime('%H:%M')
        return None