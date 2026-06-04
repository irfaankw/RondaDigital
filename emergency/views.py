from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta
from .models import LaporanDarurat


# ── Riwayat Laporan (Warga) ──────────────────────────────────────────────────

@login_required
def riwayat_laporan(request):
    status_filter = request.GET.get('status', 'all')

    semua_laporan  = LaporanDarurat.objects.filter(user=request.user)
    total_semua    = semua_laporan.count()
    total_pending  = semua_laporan.filter(status='pending').count()
    total_diproses = semua_laporan.filter(status='diproses').count()
    total_selesai  = semua_laporan.filter(status='selesai').count()

    if status_filter in ('pending', 'diproses', 'selesai'):
        laporan_list = semua_laporan.filter(status=status_filter)
    else:
        status_filter = 'all'
        laporan_list  = semua_laporan

    filter_tabs = [
        {'value': 'all',      'label': 'Semua',    'count': total_semua,    'active_class': 'bg-[#0d2a45] border-cyan-500/60 text-white'},
        {'value': 'pending',  'label': 'Menunggu',  'count': total_pending,  'active_class': 'bg-yellow-500/10 border-yellow-500/60 text-yellow-400'},
        {'value': 'diproses', 'label': 'Diproses',  'count': total_diproses, 'active_class': 'bg-cyan-500/10 border-cyan-500/60 text-cyan-400'},
        {'value': 'selesai',  'label': 'Selesai',   'count': total_selesai,  'active_class': 'bg-emerald-500/10 border-emerald-500/60 text-emerald-400'},
    ]

    return render(request, 'emergency/riwayat.html', {
        'laporan_list':   laporan_list,
        'status_filter':  status_filter,
        'filter_tabs':    filter_tabs,
        'total_semua':    total_semua,
        'total_pending':  total_pending,
        'total_diproses': total_diproses,
        'total_selesai':  total_selesai,
    })


# ── Existing API Views ────────────────────────────────────────────────────────

@login_required
@require_GET
def cek_pending(request):
    laporan = LaporanDarurat.objects.filter(
        user=request.user,
        status__in=['pending', 'diproses']
    ).first()

    if laporan:
        return JsonResponse({
            'ada': True,
            'id': laporan.id,
            'kategori': laporan.kategori,
            'deskripsi': laporan.deskripsi,
            'status': laporan.status,
        })
    return JsonResponse({'ada': False})


@login_required
@require_POST
def kirim_laporan(request):
    kategori  = request.POST.get('kategori', '').strip()
    deskripsi = request.POST.get('deskripsi', '').strip()

    valid = [c[0] for c in LaporanDarurat.KATEGORI_CHOICES]
    if kategori not in valid:
        return JsonResponse({'ok': False, 'pesan': 'Kategori tidak valid.'}, status=400)

    laporan_aktif = LaporanDarurat.objects.filter(
        user=request.user,
        status__in=['pending', 'diproses']
    ).first()

    if laporan_aktif:
        if laporan_aktif.status == 'diproses':
            return JsonResponse({
                'ok': False,
                'pesan': 'Laporan kamu sedang diproses petugas. Tunggu hingga selesai.'
            }, status=400)
        try:
            lat = float(request.POST.get('latitude'))
        except (TypeError, ValueError):
            lat = None
        try:
            lng = float(request.POST.get('longitude'))
        except (TypeError, ValueError):
            lng = None

        laporan_aktif.kategori  = kategori
        laporan_aktif.deskripsi = deskripsi
        if lat is not None:
            laporan_aktif.latitude  = lat
        if lng is not None:
            laporan_aktif.longitude = lng
        laporan_aktif.save(update_fields=['kategori', 'deskripsi', 'latitude', 'longitude'])
        return JsonResponse({'ok': True, 'id': laporan_aktif.id})

    tiga_detik_lalu = timezone.now() - timedelta(seconds=3)
    if LaporanDarurat.objects.filter(user=request.user, dibuat__gte=tiga_detik_lalu).exists():
        return JsonResponse({'ok': True, 'pesan': 'Laporan sudah terkirim.'})

    try:
        lat = float(request.POST.get('latitude'))
    except (TypeError, ValueError):
        lat = None
    try:
        lng = float(request.POST.get('longitude'))
    except (TypeError, ValueError):
        lng = None

    laporan = LaporanDarurat.objects.create(
        user      = request.user,
        kategori  = kategori,
        deskripsi = deskripsi,
        latitude  = lat,
        longitude = lng,
    )
    return JsonResponse({'ok': True, 'id': laporan.id})


@login_required
@require_POST
def update_status(request, laporan_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PETUGAS':
        return JsonResponse({'ok': False, 'pesan': 'Akses ditolak.'}, status=403)

    try:
        laporan = LaporanDarurat.objects.get(id=laporan_id)
    except LaporanDarurat.DoesNotExist:
        return JsonResponse({'ok': False, 'pesan': 'Laporan tidak ditemukan.'}, status=404)

    aksi = request.POST.get('aksi', '').strip()

    if aksi == 'proses' and laporan.status == 'pending':
        nama_petugas = ''
        if hasattr(request.user, 'profile') and request.user.profile.nama_lengkap:
            nama_petugas = request.user.profile.nama_lengkap
        else:
            nama_petugas = request.user.get_full_name() or request.user.username

        laporan.status         = 'diproses'
        laporan.ditangani_oleh = nama_petugas
        laporan.save(update_fields=['status', 'ditangani_oleh'])
        return JsonResponse({'ok': True, 'status_baru': 'diproses', 'ditangani_oleh': nama_petugas})

    elif aksi == 'selesai' and laporan.status == 'diproses':
        laporan.status = 'selesai'
        laporan.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'status_baru': 'selesai'})

    return JsonResponse({'ok': False, 'pesan': 'Aksi tidak valid atau status tidak sesuai.'}, status=400)

# ── API Alert Petugas (AJAX Polling) ─────────────────────────────────────────

@login_required
@require_GET
def api_alert_petugas(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PETUGAS':
        return JsonResponse({'ok': False, 'pesan': 'Akses ditolak.'}, status=403)

    laporan_qs = LaporanDarurat.objects.select_related('user__profile').order_by('-dibuat')

    data = []
    for lap in laporan_qs:
        profile = getattr(lap.user, 'profile', None)
        nama_pelapor = ''
        if profile and profile.nama_lengkap:
            nama_pelapor = profile.nama_lengkap
        else:
            nama_pelapor = lap.user.get_full_name() or lap.user.username

        data.append({
            'id':            lap.id,
            'kategori':      lap.kategori,
            'kategori_label': lap.get_kategori_display(),
            'deskripsi':     lap.deskripsi,
            'alamat':        lap.alamat or '',
            'maps_url':      lap.maps_url or '',
            'status':        lap.status,
            'ditangani_oleh': lap.ditangani_oleh or '',
            'nama_pelapor':  nama_pelapor,
            'dibuat':        lap.dibuat.strftime('%H:%M') + ' WIB',
        })

    total_pending = LaporanDarurat.objects.filter(status='pending').count()

    return JsonResponse({'ok': True, 'laporan': data, 'total_pending': total_pending})

@login_required
def alert_petugas(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'PETUGAS':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    return render(request, 'emergency/alert_petugas.html')