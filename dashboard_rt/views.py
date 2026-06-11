from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone as tz
from datetime import timedelta
from collections import defaultdict
from django.views.decorators.http import require_POST
from django.db import transaction
from patrol.models import JadwalRonda
from account.models import UserProfile, NIKWhitelist
from .models import ItemPatroli
from .decorators import rt_required
from .forms import JadwalRondaForm

import json
import csv
import io
import json as _json


@login_required
@rt_required
def dashboard(request):
    return render(request, 'dashboard_rt/dashboard.html')


@login_required
@rt_required
def cctv_monitoring(request):
    """Halaman Monitoring CCTV khusus Ketua RT (Statis)."""
    return render(request, 'dashboard_rt/cctv.html')


@login_required
@rt_required
def verifikasi_warga_list(request):
    rt_pengurus = request.user.profile.rt
    daftar_warga = (
        UserProfile.objects
        .filter(rt=rt_pengurus)
        .exclude(role='RT')
        .select_related('user')
        .order_by('submission_status', '-created_at')
    )
    context = {
        'daftar_warga': daftar_warga,
        'rt_pengurus' : rt_pengurus,
    }
    return render(request, 'dashboard_rt/verifikasi_warga.html', context)


@login_required
@rt_required
@require_POST
def verifikasi_aksi_lama(request, profile_id):
    """Proses verifikasi setuju atau tolak warga lewat AJAX atau POST."""
    rt_pengurus   = request.user.profile.rt
    profile_warga = get_object_or_404(UserProfile, id=profile_id, rt=rt_pengurus)
    aksi = request.POST.get('action')

    if aksi == 'setuju':
        profile_warga.is_verified        = True
        profile_warga.submission_status  = 'verified'
        profile_warga.save()
        return JsonResponse({'ok': True, 'pesan': f'Profil {profile_warga.nama_lengkap} berhasil diverifikasi.'})
    elif aksi == 'tolak':
        profile_warga.is_verified        = False
        profile_warga.submission_status  = 'draft'
        profile_warga.save()
        return JsonResponse({'ok': True, 'pesan': f'Berkas {profile_warga.nama_lengkap} berhasil ditolak.'})

    return JsonResponse({'ok': False, 'pesan': 'Aksi tidak valid.'})

@login_required
@rt_required
def jadwal_ronda(request):
    semua_jadwal = (
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user)
        .prefetch_related('item_patroli')
        .select_related('petugas__profile', 'absensi')
        .order_by('-tanggal', 'jam_mulai')
    )

    warga_terverifikasi = (
        User.objects
        .filter(profile__is_verified=True)
        .select_related('profile')
        .order_by('profile__nama_lengkap')
    )

    now         = tz.now()
    jadwal_data = []
    grouped     = defaultdict(list)

    for j in semua_jadwal:
        key = (j.tanggal, j.jam_mulai, j.jam_selesai)
        grouped[key].append(j)

    # Tanggal yang sudah ada jadwal dalam 7 hari ke depan → di-disable di date picker
    from datetime import timedelta
    today       = tz.localdate()
    batas_akhir = today + timedelta(days=6)

    tanggal_terpakai = list(
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user, tanggal__range=[today, batas_akhir])
        .values_list('tanggal', flat=True)
        .distinct()
    )
    tanggal_terpakai_str = [str(t) for t in tanggal_terpakai]

    for (tanggal, jam_mulai, jam_selesai), jadwal_list in grouped.items():
        petugas_info = []
        for j in jadwal_list:
            profile = getattr(j.petugas, 'profile', None)
            nama    = profile.nama_lengkap if profile else j.petugas.username
            inisial = ''.join([k[0].upper() for k in nama.split()[:2]])
            petugas_info.append({'nama': nama, 'inisial': inisial, 'id': j.petugas.pk})

        j0           = jadwal_list[0]
        absensi_info = []
        for j in jadwal_list:
            absensi_obj = getattr(j, 'absensi', None)
            profile     = getattr(j.petugas, 'profile', None)
            nama        = profile.nama_lengkap if profile else j.petugas.username
            inisial     = ''.join([k[0].upper() for k in nama.split()[:2]])

            if absensi_obj:
                waktu_lokal = tz.localtime(absensi_obj.waktu_absen)
                absensi_info.append({
                    'nama'     : nama,
                    'inisial'  : inisial,
                    'status'   : absensi_obj.status_absen,
                    'waktu'    : waktu_lokal.strftime('%H:%M'),
                    'jarak'    : absensi_obj.jarak_dari_pos,
                    'foto_url' : absensi_obj.foto_absen.url if absensi_obj.foto_absen else None,
                    'latitude' : str(absensi_obj.latitude)  if absensi_obj.latitude  else '',
                    'longitude': str(absensi_obj.longitude) if absensi_obj.longitude else '',
                })
            else:
                absensi_info.append({
                    'nama'     : nama,
                    'inisial'  : inisial,
                    'status'   : 'belum',
                    'waktu'    : None,
                    'jarak'    : None,
                    'foto_url' : None,
                    'latitude' : '',
                    'longitude': '',
                })

        sudah_absen = sum(1 for a in absensi_info if a['status'] != 'belum')
        dt_mulai    = j0.get_datetime_mulai()
        dt_selesai  = j0.get_datetime_selesai()

        if now < dt_mulai:
            status_jadwal = 'akan_datang'
        elif dt_mulai <= now <= dt_selesai:
            status_jadwal = 'aktif'
        else:
            status_jadwal = 'selesai'

        jadwal_data.append({
            'obj'          : j0,
            'ids'          : [j.pk for j in jadwal_list],
            'petugas_info' : petugas_info,
            'items'        : list(j0.item_patroli.all()),
            'absensi_info' : absensi_info,
            'sudah_absen'  : sudah_absen,
            'total_petugas': len(jadwal_list),
            'status'       : status_jadwal,
            'label_waktu'  : f"{jam_mulai.strftime('%H:%M')} — {jam_selesai.strftime('%H:%M')}",
        })

    context = {
        'jadwal_data'          : jadwal_data,
        'warga_terverifikasi'  : warga_terverifikasi,
        'total'                : len(jadwal_data),
        'tanggal_terpakai_json': _json.dumps(tanggal_terpakai_str),
    }
    return render(request, 'dashboard_rt/jadwal_ronda.html', context)

@login_required
@rt_required
def jadwal_petugas_tersedia(request):
    """
    AJAX GET — Return daftar petugas_id yang TIDAK BISA dipilih untuk tanggal tertentu.
    Logika: petugas yang bertugas di tanggal X tidak bisa dipilih untuk tanggal X+1 (libur sehari).
    Dipanggil dari JS setiap kali RT memilih tanggal di modal.
    """
    tanggal_str = request.GET.get('tanggal')
    if not tanggal_str:
        return JsonResponse({'ok': False, 'pesan': 'Parameter tanggal wajib diisi.'})

    try:
        from datetime import date
        tanggal = date.fromisoformat(tanggal_str)
    except ValueError:
        return JsonResponse({'ok': False, 'pesan': 'Format tanggal tidak valid.'})

    # Petugas yang bertugas di tanggal X-1 → tidak bisa dipilih untuk tanggal X
    tanggal_sebelumnya = tanggal - timedelta(days=1)

    petugas_libur_ids = list(
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user, tanggal=tanggal_sebelumnya)
        .values_list('petugas_id', flat=True)
        .distinct()
    )

    # Petugas yang sudah terdaftar di tanggal yang sama (duplikat)
    petugas_sudah_dijadwal = list(
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user, tanggal=tanggal)
        .values_list('petugas_id', flat=True)
        .distinct()
    )

    tidak_tersedia = list(set(petugas_libur_ids + petugas_sudah_dijadwal))

    return JsonResponse({'ok': True, 'tidak_tersedia': tidak_tersedia})

@login_required
@rt_required
@require_POST
def jadwal_buat(request):
    """AJAX — Buat jadwal ronda baru. 1 row per petugas, tanggal+jam sama."""
    try:
        data        = json.loads(request.body)
        petugas_ids = data.get('petugas_ids', [])
        tanggal     = data.get('tanggal')
        jam_mulai   = data.get('jam_mulai')
        jam_selesai = data.get('jam_selesai')
        items       = data.get('items', [])

        form_data = {
            'petugas_ids': ','.join(str(i) for i in petugas_ids),
            'tanggal'    : tanggal,
            'jam_mulai'  : jam_mulai,
            'jam_selesai': jam_selesai,
            'blok_area'  : data.get('blok_area', ''),
            'catatan_rt' : data.get('catatan_rt', ''),
            'items'      : '',
        }
        form                          = JadwalRondaForm(form_data)
        form.data                     = dict(form.data)
        form.data['petugas_ids_list'] = petugas_ids
        form.data['items_list']       = items
        form.data['dibuat_oleh_user'] = request.user   # ← untuk validasi tanggal duplikat

        if not form.is_valid():
            for field, errors in form.errors.items():
                return JsonResponse({'ok': False, 'pesan': errors[0]})

        petugas_users = form.cleaned_data['petugas_ids']

        with transaction.atomic():
            jadwal_list = []
            for u in petugas_users:
                jadwal = JadwalRonda.objects.create(
                    petugas     = u,
                    tanggal     = form.cleaned_data['tanggal'],
                    jam_mulai   = form.cleaned_data['jam_mulai'],
                    jam_selesai = form.cleaned_data['jam_selesai'],
                    dibuat_oleh = request.user,
                )
                jadwal_list.append(jadwal)

            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)
            if profiles_to_update:
                UserProfile.objects.bulk_update(profiles_to_update, ['role', 'active_role'])

            item_objs = [
                ItemPatroli(jadwal=jadwal_list[0], urutan=i+1, deskripsi=d)
                for i, d in enumerate(form.get_items())
            ]
            if item_objs:
                ItemPatroli.objects.bulk_create(item_objs)

        return JsonResponse({'ok': True, 'pesan': 'Jadwal berhasil dibuat.', 'id': jadwal_list[0].pk})

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})

@login_required
@rt_required
def jadwal_detail(request, pk):
    """AJAX GET — Ambil data jadwal untuk ditampilkan/diedit di modal."""
    jadwal     = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    items      = list(jadwal.item_patroli.values('id', 'urutan', 'deskripsi'))
    jadwal_grup = JadwalRonda.objects.filter(
        dibuat_oleh = request.user,
        tanggal     = jadwal.tanggal,
        jam_mulai   = jadwal.jam_mulai,
        jam_selesai = jadwal.jam_selesai,
    ).select_related('petugas__profile')

    petugas_data = []
    for j in jadwal_grup:
        profile = getattr(j.petugas, 'profile', None)
        petugas_data.append({
            'id'  : j.petugas.pk,
            'nama': profile.nama_lengkap if profile else j.petugas.username,
        })

    # Tanggal terpakai untuk modal edit (exclude tanggal jadwal ini sendiri)
    tanggal_terpakai = list(
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user)
        .exclude(tanggal=jadwal.tanggal, jam_mulai=jadwal.jam_mulai)
        .values_list('tanggal', flat=True)
        .distinct()
    )

    # Petugas libur sehari: hitung relatif ke tanggal jadwal yang diedit
    # Petugas tidak bisa dipilih jika bertugas di tanggal jadwal ini (tgl X)
    # atau sehari sebelumnya (tgl X-1)
    tgl_jadwal = jadwal.tanggal
    jadwal_konflik = (
        JadwalRonda.objects
        .filter(
            dibuat_oleh=request.user,
            tanggal__in=[tgl_jadwal, tgl_jadwal - timedelta(days=1)]
        )
        # Exclude petugas yang memang sudah ada di jadwal ini (boleh tetap dipilih)
        .exclude(tanggal=tgl_jadwal, jam_mulai=jadwal.jam_mulai)
        .values_list('petugas_id', flat=True)
        .distinct()
    )
    petugas_libur_ids = list(jadwal_konflik)

    return JsonResponse({
        'ok'               : True,
        'id'               : jadwal.pk,
        'petugas'          : petugas_data,
        'tanggal'          : str(jadwal.tanggal),
        'jam_mulai'        : jadwal.jam_mulai.strftime('%H:%M'),
        'jam_selesai'      : jadwal.jam_selesai.strftime('%H:%M'),
        'blok_area'        : '',
        'catatan_rt'       : '',
        'items'            : items,
        'tanggal_terpakai' : [str(t) for t in tanggal_terpakai],
        'petugas_libur'    : petugas_libur_ids,
    })

@login_required
@rt_required
@require_POST
def jadwal_edit(request, pk):
    """AJAX POST — Edit jadwal yang sudah ada (hapus grup lama, buat baru)."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    try:
        data        = json.loads(request.body)
        petugas_ids = data.get('petugas_ids', [])
        tanggal     = data.get('tanggal')
        jam_mulai   = data.get('jam_mulai')
        jam_selesai = data.get('jam_selesai')
        items       = data.get('items', [])

        form_data = {
            'petugas_ids': ','.join(str(i) for i in petugas_ids),
            'tanggal'    : tanggal,
            'jam_mulai'  : jam_mulai,
            'jam_selesai': jam_selesai,
            'blok_area'  : data.get('blok_area', ''),
            'catatan_rt' : data.get('catatan_rt', ''),
            'items'      : '',
        }
        form                          = JadwalRondaForm(form_data)
        form.data                     = dict(form.data)
        form.data['petugas_ids_list'] = petugas_ids
        form.data['items_list']       = items
        form.data['dibuat_oleh_user'] = request.user   # ← untuk validasi tanggal
        form.edit_pk                  = pk              # ← skip validasi tanggal sendiri

        if not form.is_valid():
            for field, errors in form.errors.items():
                return JsonResponse({'ok': False, 'pesan': errors[0]})

        petugas_users = form.cleaned_data['petugas_ids']

        with transaction.atomic():
            JadwalRonda.objects.filter(
                dibuat_oleh = request.user,
                tanggal     = jadwal.tanggal,
                jam_mulai   = jadwal.jam_mulai,
                jam_selesai = jadwal.jam_selesai,
            ).delete()

            jadwal_list = []
            for u in petugas_users:
                j = JadwalRonda.objects.create(
                    petugas     = u,
                    tanggal     = form.cleaned_data['tanggal'],
                    jam_mulai   = form.cleaned_data['jam_mulai'],
                    jam_selesai = form.cleaned_data['jam_selesai'],
                    dibuat_oleh = request.user,
                )
                jadwal_list.append(j)

            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)
            if profiles_to_update:
                UserProfile.objects.bulk_update(profiles_to_update, ['role', 'active_role'])

            item_objs = [
                ItemPatroli(jadwal=jadwal_list[0], urutan=i+1, deskripsi=d)
                for i, d in enumerate(form.get_items())
            ]
            if item_objs:
                ItemPatroli.objects.bulk_create(item_objs)

        return JsonResponse({'ok': True, 'pesan': 'Jadwal berhasil diperbarui.'})

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})


@login_required
@rt_required
@require_POST
def jadwal_hapus(request, pk):
    """AJAX POST — Hapus seluruh grup jadwal (tanggal+jam sama)."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    JadwalRonda.objects.filter(
        dibuat_oleh = request.user,
        tanggal     = jadwal.tanggal,
        jam_mulai   = jadwal.jam_mulai,
        jam_selesai = jadwal.jam_selesai,
    ).delete()
    return JsonResponse({'ok': True, 'pesan': 'Jadwal berhasil dihapus.'})


@login_required
@rt_required
def verifikasi_warga(request):
    semua_profil = (
        UserProfile.objects
        .exclude(submission_status='draft')
        .select_related('user')
        .order_by('-created_at')
    )
    jumlah_menunggu = semua_profil.filter(submission_status='pending').count()
    existing_niks   = list(NIKWhitelist.objects.values_list('nik', flat=True))

    context = {
        'semua_profil'      : semua_profil,
        'jumlah_menunggu'   : jumlah_menunggu,
        'existing_niks_json': _json.dumps(existing_niks),
    }
    return render(request, 'dashboard_rt/verifikasi_warga.html', context)


@login_required
@rt_required
@require_POST
def verifikasi_aksi(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    try:
        data = json.loads(request.body)
        aksi = data.get('aksi')

        if aksi == 'setujui':
            profile.submission_status = 'verified'
            profile.is_verified       = True
        elif aksi == 'tolak':
            profile.submission_status = 'pending'
            profile.is_verified       = False
        elif aksi == 'tinjau_ulang':
            profile.submission_status = 'pending'
            profile.is_verified       = False
        else:
            return JsonResponse({'ok': False, 'pesan': 'Aksi tidak valid.'})

        profile.save(update_fields=['submission_status', 'is_verified'])
        return JsonResponse({'ok': True})

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})

@login_required
@rt_required
def upload_nik_csv(request):
    if request.method == 'GET':
        return render(request, 'dashboard_rt/upload_nik_csv.html')

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'ok': False, 'pesan': 'File CSV tidak ditemukan.'})
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'ok': False, 'pesan': 'File harus berekstensi .csv'})
    if csv_file.size > 5 * 1024 * 1024:
        return JsonResponse({'ok': False, 'pesan': 'Ukuran file maksimal 5 MB.'})

    try:
        raw    = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(raw))
        reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]

        if 'nik' not in reader.fieldnames:
            return JsonResponse({
                'ok'   : False,
                'pesan': 'Kolom "nik" tidak ditemukan. Pastikan baris pertama CSV berisi header.'
            })

        existing_niks = set(NIKWhitelist.objects.values_list('nik', flat=True))
        to_create     = []
        duplikat      = []
        baris_kosong  = 0

        for row in reader:
            nik  = str(row.get('nik', '')         or '').strip()
            nama = str(row.get('nama_lengkap', '') or '').strip()
            rt   = str(row.get('rt', '')           or '').strip()
            rw   = str(row.get('rw', '')           or '').strip()

            if not nik:
                baris_kosong += 1
                continue
            if not nik.isdigit() or len(nik) != 16:
                baris_kosong += 1
                continue
            if nik in existing_niks:
                duplikat.append(nik)
                continue

            # Normalisasi rt/rw ke 2 digit jika diisi
            if rt.isdigit():
                rt = rt.zfill(2)
            if rw.isdigit():
                rw = rw.zfill(2)

            existing_niks.add(nik)
            to_create.append(NIKWhitelist(nik=nik, nama_sesuai=nama, rt=rt, rw=rw))

        with transaction.atomic():
            NIKWhitelist.objects.bulk_create(to_create)

        pesan = f'{len(to_create)} NIK berhasil ditambahkan.'
        if duplikat:
            pesan += f' {len(duplikat)} NIK sudah ada (dilewati).'
        if baris_kosong:
            pesan += f' {baris_kosong} baris dilewati (kosong/format salah).'

        return JsonResponse({
            'ok'      : True,
            'pesan'   : pesan,
            'ditambah': len(to_create),
            'duplikat': len(duplikat),
            'dilewati': baris_kosong,
        })

    except UnicodeDecodeError:
        return JsonResponse({'ok': False, 'pesan': 'Gagal membaca file. Pastikan CSV dalam format UTF-8.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': f'Terjadi kesalahan: {str(e)}'})