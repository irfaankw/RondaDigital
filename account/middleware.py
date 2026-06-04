from django.utils.deprecation import MiddlewareMixin


class AutoResetPetugasRoleMiddleware(MiddlewareMixin):
    """
    Dijalankan di setiap request.
    Kalau user sedang mode PETUGAS tapi shift-nya sudah selesai
    atau tidak ada jadwal hari ini → reset active_role ke WARGA otomatis.
    Ini yang membuat switch mode otomatis kembali ke warga tanpa perlu
    klik apapun, cukup refresh halaman.
    """

    def process_request(self, request):
        # Lewati kalau belum login
        if not request.user.is_authenticated:
            return

        # Lewati untuk URL yang tidak perlu dicek
        skip_prefixes = ('/admin/', '/static/', '/media/')
        if any(request.path.startswith(p) for p in skip_prefixes):
            return

        # Ambil profile, lewati kalau tidak ada
        try:
            profile = request.user.profile
        except Exception:
            return

        # Hanya proses kalau sedang aktif sebagai PETUGAS
        if profile.get_active_role() != 'PETUGAS':
            return

        from patrol.models import JadwalRonda
        from datetime import date

        today  = date.today()
        jadwal = JadwalRonda.objects.filter(
            petugas=request.user, tanggal=today
        ).first()

        # Tidak ada jadwal hari ini, atau shift sudah selesai → reset ke WARGA
        if not jadwal or jadwal.is_shift_selesai():
            profile.active_role = 'WARGA'
            profile.save(update_fields=['active_role'])