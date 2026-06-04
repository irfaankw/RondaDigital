from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
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
def jadwal_ronda(request):
    """Halaman daftar jadwal ronda — dikelola oleh Ketua RT."""
    semua_jadwal = (
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user)
        .prefetch_related('item_patroli')
        .select_related('petugas__profile')
        .order_by('-tanggal', 'jam_mulai')
    )

    warga_terverifikasi = (
        User.objects
        .filter(profile__is_verified=True)
        .select_related('profile')
        .order_by('profile__nama_lengkap')
    )

    # Group jadwal berdasarkan tanggal+jam_mulai supaya terlihat seperti 1 sesi
    from itertools import groupby
    from collections import defaultdict

    jadwal_data = []
    grouped = defaultdict(list)
    for j in semua_jadwal:
        key = (j.tanggal, j.jam_mulai, j.jam_selesai)
        grouped[key].append(j)

    for (tanggal, jam_mulai, jam_selesai), jadwal_list in grouped.items():
        petugas_info = []
        for j in jadwal_list:
            profile = getattr(j.petugas, 'profile', None)
            nama    = profile.nama_lengkap if profile else j.petugas.username
            inisial = ''.join([k[0].upper() for k in nama.split()[:2]])
            petugas_info.append({'nama': nama, 'inisial': inisial, 'id': j.petugas.pk})

        # Ambil items dari jadwal pertama (semua jadwal dalam grup sama)
        j0 = jadwal_list[0]
        jadwal_data.append({
            'obj'         : j0,
            'ids'         : [j.pk for j in jadwal_list],
            'petugas_info': petugas_info,
            'items'       : list(j0.item_patroli.all()),
        })

    context = {
        'jadwal_data'        : jadwal_data,
        'warga_terverifikasi': warga_terverifikasi,
        'total'              : len(jadwal_data),
    }
    return render(request, 'dashboard_rt/jadwal_ronda.html', context)


@login_required
@rt_required
@require_POST
def jadwal_buat(request):
    """AJAX — Buat jadwal ronda baru. 1 row per petugas, tanggal+jam sama."""
    try:
        data = json.loads(request.body)

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
            'blok_area'  : '',
            'catatan_rt' : '',
            'items'      : '',
        }
        form = JadwalRondaForm(form_data)
        form.data = dict(form.data)
        form.data['petugas_ids_list'] = petugas_ids
        form.data['items_list']       = items

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

            # Bulk update role petugas
            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)
            if profiles_to_update:
                UserProfile.objects.bulk_update(profiles_to_update, ['role', 'active_role'])

            # Item patroli hanya di jadwal pertama (representatif grup)
            item_objs = [
                ItemPatroli(jadwal=jadwal_list[0], urutan=i+1, deskripsi=d)
                for i, d in enumerate(form.get_items())
            ]
            if item_objs:
                ItemPatroli.objects.bulk_create(item_objs)

        return JsonResponse({
            'ok'   : True,
            'pesan': 'Jadwal berhasil dibuat.',
            'id'   : jadwal_list[0].pk,
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})


@login_required
@rt_required
def jadwal_detail(request, pk):
    """AJAX GET — Ambil data jadwal untuk ditampilkan/diedit di modal."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    items  = list(jadwal.item_patroli.values('id', 'urutan', 'deskripsi'))

    # Cari semua jadwal dalam grup yang sama (tanggal+jam sama)
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

    return JsonResponse({
        'ok'         : True,
        'id'         : jadwal.pk,
        'petugas'    : petugas_data,
        'tanggal'    : str(jadwal.tanggal),
        'jam_mulai'  : jadwal.jam_mulai.strftime('%H:%M'),
        'jam_selesai': jadwal.jam_selesai.strftime('%H:%M'),
        'blok_area'  : '',
        'catatan_rt' : '',
        'items'      : items,
    })


@login_required
@rt_required
@require_POST
def jadwal_edit(request, pk):
    """AJAX POST — Edit jadwal yang sudah ada (hapus grup lama, buat baru)."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    try:
        data = json.loads(request.body)

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
            'blok_area'  : '',
            'catatan_rt' : '',
            'items'      : '',
        }
        form = JadwalRondaForm(form_data)
        form.data = dict(form.data)
        form.data['petugas_ids_list'] = petugas_ids
        form.data['items_list']       = items

        if not form.is_valid():
            for field, errors in form.errors.items():
                return JsonResponse({'ok': False, 'pesan': errors[0]})

        petugas_users = form.cleaned_data['petugas_ids']

        with transaction.atomic():
            # Hapus semua jadwal dalam grup yang sama
            JadwalRonda.objects.filter(
                dibuat_oleh = request.user,
                tanggal     = jadwal.tanggal,
                jam_mulai   = jadwal.jam_mulai,
                jam_selesai = jadwal.jam_selesai,
            ).delete()

            # Buat ulang 1 row per petugas
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

            # Bulk update role
            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)
            if profiles_to_update:
                UserProfile.objects.bulk_update(profiles_to_update, ['role', 'active_role'])

            # Item patroli di jadwal pertama
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
    # Hapus semua dalam grup
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
    """Halaman daftar warga menunggu/sudah verifikasi."""
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
    """AJAX — Setujui atau tolak verifikasi warga."""
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
            nik  = str(row.get('nik', '') or '').strip()
            nama = str(row.get('nama_lengkap', '') or '').strip()

            if not nik:
                baris_kosong += 1
                continue
            if not nik.isdigit() or len(nik) != 16:
                baris_kosong += 1
                continue
            if nik in existing_niks:
                duplikat.append(nik)
                continue

            existing_niks.add(nik)
            to_create.append(NIKWhitelist(nik=nik, nama_sesuai=nama))

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