from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from .models import JadwalRonda, AbsensiShift, LogPatroli
from datetime import date
import json
import base64
from django.core.files.base import ContentFile

#
# CATATAN PENTING:
# Jangan pernah tambahkan 'user_profile': {'role': 'PETUGAS'} di context view manapun.
# user_profile sudah otomatis diinject ke semua template oleh account/context_processors.py
#


def _get_jadwal_repr(jadwal_user):
    """
    Cari jadwal representatif (yang punya item_patroli) dalam satu grup.
    Grup = tanggal + jam_mulai + jam_selesai + dibuat_oleh yang sama.
    RT menyimpan ItemPatroli hanya di jadwal pertama (jadwal_list[0]).
    """
    if not jadwal_user:
        return None
    return (
        JadwalRonda.objects
        .filter(
            tanggal     = jadwal_user.tanggal,
            jam_mulai   = jadwal_user.jam_mulai,
            jam_selesai = jadwal_user.jam_selesai,
            dibuat_oleh = jadwal_user.dibuat_oleh,
        )
        .prefetch_related('item_patroli')
        .order_by('id')
        .first()
    )


# ── View 1: Dashboard Petugas (DINAMIS) ──────────────────────────────────────

@login_required
def petugas_dashboard(request):
    today = date.today()
    user  = request.user

    # Jadwal milik petugas ini hari ini
    jadwal_user = JadwalRonda.objects.filter(petugas=user, tanggal=today).first()

    # Jadwal representatif (yang punya item_patroli)
    jadwal_repr = _get_jadwal_repr(jadwal_user)

    # ── Info shift ────────────────────────────────────────────────
    nama_shift      = 'Shift Ronda Malam'
    jam_mulai_str   = '--:--'
    jam_selesai_str = '--:--'
    sisa_jam        = 0
    sisa_menit      = 0
    dt_selesai_iso  = ''

    if jadwal_user:
        nama_shift      = jadwal_user.nama_shift or 'Shift Ronda Malam'
        jam_mulai_str   = jadwal_user.jam_mulai.strftime('%H:%M')
        jam_selesai_str = jadwal_user.jam_selesai.strftime('%H:%M')
        now             = timezone.now()
        dt_selesai      = jadwal_user.get_datetime_selesai()
        dt_selesai_iso  = dt_selesai.isoformat()
        sisa_total      = max(int((dt_selesai - now).total_seconds()), 0)
        sisa_jam        = sisa_total // 3600
        sisa_menit      = (sisa_total % 3600) // 60

    # ── Checklist item patroli ─────────────────────────────────────
    items_data    = []
    total_items   = 0
    selesai_count = 0

    if jadwal_repr:
        items_qs    = jadwal_repr.item_patroli.all()
        total_items = items_qs.count()

        for item in items_qs:
            log, _ = LogPatroli.objects.get_or_create(
                item    = item,
                petugas = user,
                jadwal  = jadwal_user,
                defaults={'status': 'belum'}
            )
            if log.status == 'selesai':
                selesai_count += 1

            items_data.append({
                'log_id'       : log.id,
                'deskripsi'    : item.deskripsi,
                'status'       : log.status,
                'waktu_mulai'  : log.waktu_mulai_str,
                'waktu_selesai': log.waktu_selesai_str,
            })

    progress_pct = int(selesai_count / total_items * 100) if total_items > 0 else 0

    # ── Alert dari emergency ───────────────────────────────────────
    from emergency.models import LaporanDarurat
    alert_masuk     = LaporanDarurat.objects.filter(status='pending').count()
    sedang_diproses = LaporanDarurat.objects.filter(status='diproses').count()
    terselesaikan   = LaporanDarurat.objects.filter(status='selesai').count()

    # ── Log terbaru (item selesai hari ini) ────────────────────────
    log_terbaru = (
        LogPatroli.objects
        .filter(jadwal__tanggal=today, status='selesai')
        .select_related('petugas__profile', 'item')
        .order_by('-waktu_selesai')[:5]
    )

    # Nama petugas untuk JS
    profile      = getattr(user, 'profile', None)
    nama_petugas = getattr(profile, 'nama_lengkap', None) or user.get_full_name() or user.username

    context = {
        'jadwal'          : jadwal_user,
        'nama_shift'      : nama_shift,
        'jam_mulai_str'   : jam_mulai_str,
        'jam_selesai_str' : jam_selesai_str,
        'sisa_jam'        : sisa_jam,
        'sisa_menit'      : sisa_menit,
        'dt_selesai_iso'  : dt_selesai_iso,
        'items_data'      : items_data,
        'total_items'     : total_items,
        'selesai_count'   : selesai_count,
        'progress_pct'    : progress_pct,
        'alert_masuk'     : alert_masuk,
        'sedang_diproses' : sedang_diproses,
        'terselesaikan'   : terselesaikan,
        'log_terbaru'     : log_terbaru,
        'nama_petugas'    : nama_petugas,
    }
    return render(request, 'patrol/petugas_home.html', context)


# ── View 2: Update Status Checklist (AJAX) ────────────────────────────────────

@login_required
@require_POST
def update_item_patroli(request, log_id):
    try:
        log = LogPatroli.objects.select_related('item', 'jadwal').get(
            id=log_id, petugas=request.user
        )
    except LogPatroli.DoesNotExist:
        return JsonResponse({'ok': False, 'pesan': 'Data tidak ditemukan.'}, status=404)

    aksi = request.POST.get('aksi', '').strip()
    now  = timezone.now()

    if aksi == 'mulai' and log.status == 'belum':
        log.status      = 'berjalan'
        log.waktu_mulai = now
        log.save(update_fields=['status', 'waktu_mulai'])
        return JsonResponse({
            'ok'         : True,
            'status_baru': 'berjalan',
            'waktu_mulai': log.waktu_mulai_str,
        })

    elif aksi == 'selesai' and log.status == 'berjalan':
        log.status        = 'selesai'
        log.waktu_selesai = now
        log.save(update_fields=['status', 'waktu_selesai'])

        # Hitung ulang progress
        total   = LogPatroli.objects.filter(petugas=request.user, jadwal=log.jadwal).count()
        selesai = LogPatroli.objects.filter(petugas=request.user, jadwal=log.jadwal, status='selesai').count()
        progress = int(selesai / total * 100) if total > 0 else 0

        profile      = getattr(request.user, 'profile', None)
        nama_petugas = getattr(profile, 'nama_lengkap', None) or request.user.get_full_name() or request.user.username

        return JsonResponse({
            'ok'           : True,
            'status_baru'  : 'selesai',
            'waktu_selesai': log.waktu_selesai_str,
            'deskripsi'    : log.item.deskripsi,
            'nama_petugas' : nama_petugas,
            'progress_pct' : progress,
            'selesai_count': selesai,
            'total_items'  : total,
        })

    return JsonResponse({'ok': False, 'pesan': 'Aksi tidak valid.'}, status=400)


# ── View 3: CCTV ──────────────────────────────────────────────────────────────

@login_required
def petugas_cctv(request):
    context = {
        'cctv_list': [
            {'id': 1, 'lokasi': 'Gapura Utama RT 01',  'status': 'Online'},
            {'id': 2, 'lokasi': 'Pertigaan Pos Ronda',  'status': 'Online'},
            {'id': 3, 'lokasi': 'Area Lapangan Warga',  'status': 'Offline'},
        ]
    }
    return render(request, 'patrol/petugas_cctv.html', context)


# ── View 4: Alert ─────────────────────────────────────────────────────────────

@login_required
def petugas_alert(request):
    return render(request, 'patrol/alert.html', {})


# ── View 5: Shift ─────────────────────────────────────────────────────────────

@login_required
def petugas_shift(request):
    today = date.today()
    user  = request.user

    jadwal_saya  = JadwalRonda.objects.filter(petugas=user, tanggal=today).first()
    semua_jadwal = (
        JadwalRonda.objects
        .filter(tanggal=today)
        .select_related('petugas__profile')
        .order_by('jam_mulai')
    )

    sudah_absen  = bool(jadwal_saya and hasattr(jadwal_saya, 'absensi'))
    absensi_saya = jadwal_saya.absensi if sudah_absen else None

    jadwal_shift_list = []
    for j in semua_jadwal:
        profile     = getattr(j.petugas, 'profile', None)
        nama        = profile.nama_lengkap if profile else j.petugas.username
        inisial     = ''.join([k[0].upper() for k in nama.split()[:2]])
        absensi_obj = getattr(j, 'absensi', None)

        if absensi_obj:
            if absensi_obj.status_absen == 'hadir':
                status, bg = 'Hadir', 'bg-green-500'
            elif absensi_obj.status_absen == 'terlambat':
                status, bg = 'Terlambat', 'bg-yellow-500'
            else:
                status, bg = 'Tidak Hadir', 'bg-red-500'
        elif j.is_shift_selesai():
            status, bg = 'Tidak Hadir', 'bg-red-500'
        else:
            status, bg = 'Alpha', 'bg-slate-600'

        lokasi_absen = None
        if absensi_obj and absensi_obj.latitude:
            lokasi_absen = {'jarak': absensi_obj.jarak_dari_pos}

        jadwal_shift_list.append({
            'inisial'     : inisial,
            'nama'        : nama,
            'waktu'       : f"{j.jam_mulai.strftime('%H:%M')} - {j.jam_selesai.strftime('%H:%M')}",
            'status'      : status,
            'bg_inisial'  : bg,
            'lokasi_absen': lokasi_absen,
            'is_me'       : j.petugas == user,
        })

    context = {
        'shift_aktif'      : jadwal_saya,
        'jadwal_shift_list': jadwal_shift_list,
        'sudah_absen'      : sudah_absen,
        'absensi_saya'     : absensi_saya,
        'is_terlambat'     : jadwal_saya.is_terlambat() if jadwal_saya else False,
        'shift_selesai'    : jadwal_saya.is_shift_selesai() if jadwal_saya else False,
        'tanggal_hari_ini' : today,
    }
    return render(request, 'patrol/petugas_shift.html', context)


# ── View 6: Simpan Absensi ────────────────────────────────────────────────────

@login_required
@require_POST
def simpan_absensi(request):
    try:
        data   = json.loads(request.body)
        today  = date.today()
        jadwal = JadwalRonda.objects.filter(petugas=request.user, tanggal=today).first()

        if not jadwal:
            return JsonResponse({'ok': False, 'pesan': 'Tidak ada jadwal ronda hari ini.'})
        if hasattr(jadwal, 'absensi'):
            return JsonResponse({'ok': False, 'pesan': 'Kamu sudah melakukan absensi.'})
        if jadwal.is_shift_selesai():
            return JsonResponse({'ok': False, 'pesan': 'Shift sudah selesai. Tidak bisa absen.'})

        latitude  = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is None or longitude is None:
            return JsonResponse({'ok': False, 'pesan': 'GPS tidak terdeteksi.'})

        from .utils import validasi_lokasi
        dalam_radius, jarak = validasi_lokasi(latitude, longitude)
        if not dalam_radius:
            return JsonResponse({
                'ok'   : False,
                'pesan': f'Kamu berada {jarak}m dari pos ronda. Absensi hanya bisa dalam radius 500m.'
            })

        status_absen = 'terlambat' if jadwal.is_terlambat() else 'hadir'

        absensi = AbsensiShift(
            jadwal         = jadwal,
            latitude       = latitude,
            longitude      = longitude,
            akurasi_gps    = data.get('akurasi'),
            jarak_dari_pos = jarak,
            status_absen   = status_absen,
        )

        foto_b64 = data.get('foto_base64')
        if foto_b64 and ';base64,' in foto_b64:
            fmt, imgstr        = foto_b64.split(';base64,')
            ext                = fmt.split('/')[-1]
            absensi.foto_absen = ContentFile(
                base64.b64decode(imgstr),
                name=f"absen_{request.user.id}_{today}.{ext}"
            )

        absensi.save()
        waktu_lokal = timezone.localtime(absensi.waktu_absen)

        return JsonResponse({
            'ok'         : True,
            'status'     : status_absen,
            'jarak'      : jarak,
            'waktu_absen': waktu_lokal.strftime('%H:%M'),
            'pesan'      : 'Hadir tepat waktu!' if status_absen == 'hadir' else 'Absensi tercatat — Terlambat.',
            'foto_url'   : absensi.foto_absen.url if absensi.foto_absen else None,
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': f'Error: {str(e)}'})