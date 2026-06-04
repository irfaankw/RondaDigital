from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from .models import JadwalRonda, AbsensiShift
from datetime import date
import json
import base64
from django.core.files.base import ContentFile

#
# CATATAN PENTING:
# Jangan pernah tambahkan 'user_profile': {'role': 'PETUGAS'} di context view manapun.
# user_profile sudah otomatis diinject ke semua template oleh account/context_processors.py
# Kalau ditimpa dengan dict hardcode, get_active_role() tidak bisa dipanggil
# dan navbar akan salah.
#


@login_required
def petugas_dashboard(request):
    context = {
        'total_laporan': 12,
        'status_ronda' : 'Aman Kondusif',
    }
    return render(request, 'patrol/petugas_home.html', context)


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


@login_required
def petugas_alert(request):
    context = {
        'laporan_list': [
            {
                'id'     : 1,
                'judul'  : 'Pencurian Motor',
                'pelapor': 'M. Nurkholis',
                'tanggal': '25 Mei 2026',
                'status' : 'menunggu',
                'detail' : 'Motor Scoopy hitam plat KT XXXX hilang di parkiran depan.'
            },
            {
                'id'     : 2,
                'judul'  : 'Kecelakaan Beruntun',
                'pelapor': 'Alfito Rayzha',
                'tanggal': '24 Mei 2026',
                'status' : 'direspons',
                'detail' : 'Ada mobil nabrak tiang listrik dekat pos ronda.'
            },
            {
                'id'     : 3,
                'judul'  : 'Pencurian Helm',
                'pelapor': 'Siswan Aryadi',
                'tanggal': '20 Mei 2026',
                'status' : 'selesai',
                'detail' : 'Helm KYT di atas motor hilang, tapi pelakunya sudah damai.'
            },
        ]
    }
    return render(request, 'patrol/alert.html', context)


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