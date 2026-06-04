from django.utils.deprecation import MiddlewareMixin


class AutoResetPetugasRoleMiddleware(MiddlewareMixin):
    """
    Setiap request yang masuk, cek apakah petugas yang sedang
    mode PETUGAS masih punya shift aktif.
    Kalau shift sudah selesai → reset active_role ke WARGA otomatis.
    """

    def process_request(self, request):
        # Lewati kalau belum login atau akses admin/static
        if not request.user.is_authenticated:
            return
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return

        try:
            profile = request.user.profile
        except Exception:
            return

        # Hanya proses kalau sedang aktif sebagai petugas
        if profile.get_active_role() != 'PETUGAS':
            return

        from patrol.models import JadwalRonda
        from datetime import date

        today  = date.today()
        jadwal = JadwalRonda.objects.filter(
            petugas=request.user, tanggal=today
        ).first()

        # Shift selesai atau tidak ada jadwal → reset ke warga
        if not jadwal or jadwal.is_shift_selesai():
            profile.active_role = 'WARGA'
            profile.save(update_fields=['active_role'])