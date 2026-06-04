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
def verifikasi_warga_list(request):
    """Menampilkan daftar warga yang berada di bawah wilayah RT ketua RT yang login."""
    # Ambil nomor RT dari pengurus RT yang sedang login
    rt_pengurus = request.user.profile.rt

    # Ambil data warga di RT tersebut, urutkan berdasarkan status 'pending' (Menunggu) terlebih dahulu
    # Kita tidak menampilkan sesama akun RT di daftar verifikasi
    daftar_warga = (
        UserProfile.objects
        .filter(rt=rt_pengurus)
        .exclude(role='RT')
        .select_related('user')
        .order_by('submission_status', '-created_at')
    )

    context = {
        'daftar_warga': daftar_warga,
        'rt_pengurus': rt_pengurus,
    }
    return render(request, 'dashboard_rt/verifikasi_warga.html', context)


@login_required
@rt_required
@require_POST
def verifikasi_aksi(request, profile_id):
    """Proses verifikasi setuju atau tolak warga lewat AJAX atau POST."""
    rt_pengurus = request.user.profile.rt
    # Pastikan profile yang diakses benar-benar sewilayah RT untuk keamanan
    profile_warga = get_object_or_404(UserProfile, id=profile_id, rt=rt_pengurus)
    
    aksi = request.POST.get('action') # 'setuju' atau 'tolak'
    
    if aksi == 'setuju':
        profile_warga.is_verified = True
        profile_warga.submission_status = 'verified'
        profile_warga.save()
        return JsonResponse({'ok': True, 'pesan': f'Profil {profile_warga.nama_lengkap} berhasil diverifikasi.'})
        
    elif aksi == 'tolak':
        profile_warga.is_verified = False
        profile_warga.submission_status = 'draft'  # Dikembalikan ke draft agar bisa diedit warga lagi
        profile_warga.save()
        return JsonResponse({'ok': True, 'pesan': f'Berkas {profile_warga.nama_lengkap} berhasil ditolak.'})

    return JsonResponse({'ok': False, 'pesan': 'Aksi tidak valid.'})

@login_required
@rt_required
def jadwal_ronda(request):
    """Halaman daftar jadwal ronda — dikelola oleh Ketua RT."""
    semua_jadwal = (
        JadwalRonda.objects
        .filter(dibuat_oleh=request.user)
        .prefetch_related('item_patroli', 'petugas__profile')
        .order_by('-tanggal', 'jam_mulai')
    )

    # Ambil semua warga yang sudah diverifikasi oleh RT ini
    # (bukan filter berdasarkan role atau RT — cukup is_verified=True)
    warga_terverifikasi = (
        User.objects
        .filter(profile__is_verified=True)
        .select_related('profile')
        .order_by('profile__nama_lengkap')
    )

    # Bangun data untuk template
    jadwal_data = []
    for j in semua_jadwal:
        petugas_list_j = j.petugas.select_related('profile').all()
        petugas_info = []
        for p in petugas_list_j:
            profile  = getattr(p, 'profile', None)
            nama     = profile.nama_lengkap if profile else p.username
            inisial  = ''.join([k[0].upper() for k in nama.split()[:2]])
            petugas_info.append({'nama': nama, 'inisial': inisial})

        jadwal_data.append({
            'obj'         : j,
            'petugas_info': petugas_info,
            'status'      : j.status_jadwal,
            'label_waktu' : j.label_waktu,
            'items'       : list(j.item_patroli.all()),
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
    """AJAX — Buat jadwal ronda baru beserta item patrolinya."""
    try:
        data = json.loads(request.body)

        petugas_ids = data.get('petugas_ids', [])
        tanggal     = data.get('tanggal')
        jam_mulai   = data.get('jam_mulai')
        jam_selesai = data.get('jam_selesai')
        blok_area   = data.get('blok_area', '').strip()
        catatan_rt  = data.get('catatan_rt', '').strip()
        items       = data.get('items', [])

        form_data = {
            'petugas_ids': ','.join(str(i) for i in petugas_ids),
            'tanggal'    : tanggal,
            'jam_mulai'  : jam_mulai,
            'jam_selesai': jam_selesai,
            'blok_area'  : blok_area,
            'catatan_rt' : catatan_rt,
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
            jadwal = JadwalRonda.objects.create(
                tanggal     = form.cleaned_data['tanggal'],
                jam_mulai   = form.cleaned_data['jam_mulai'],
                jam_selesai = form.cleaned_data['jam_selesai'],
                blok_area   = blok_area,
                catatan_rt  = catatan_rt,
                dibuat_oleh = request.user,
            )
            jadwal.petugas.set(petugas_users)

            # ✅ Bulk update — 1 query, bukan N query
            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)

            if profiles_to_update:
                UserProfile.objects.bulk_update(
                    profiles_to_update, ['role', 'active_role']
                )

            # ✅ Bulk create item patroli — 1 query, bukan N query
            item_list = [
                ItemPatroli(jadwal=jadwal, urutan=i + 1, deskripsi=deskripsi)
                for i, deskripsi in enumerate(form.get_items())
            ]
            if item_list:
                ItemPatroli.objects.bulk_create(item_list)

        return JsonResponse({
            'ok'   : True,
            'pesan': 'Jadwal berhasil dibuat.',
            'id'   : jadwal.pk,
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})

@login_required
@rt_required
def jadwal_detail(request, pk):
    """AJAX GET — Ambil data jadwal untuk ditampilkan/diedit di modal."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    items  = list(jadwal.item_patroli.values('id', 'urutan', 'deskripsi'))

    petugas_data = []
    for p in jadwal.petugas.select_related('profile').all():
        profile = getattr(p, 'profile', None)
        petugas_data.append({
            'id'  : p.pk,
            'nama': profile.nama_lengkap if profile else p.username,
        })

    return JsonResponse({
        'ok'         : True,
        'id'         : jadwal.pk,
        'petugas'    : petugas_data,
        'tanggal'    : str(jadwal.tanggal),
        'jam_mulai'  : jadwal.jam_mulai.strftime('%H:%M'),
        'jam_selesai': jadwal.jam_selesai.strftime('%H:%M'),
        'blok_area'  : jadwal.blok_area,
        'catatan_rt' : jadwal.catatan_rt,
        'items'      : items,
        'status'     : jadwal.status_jadwal,
    })


@login_required
@rt_required
@require_POST
def jadwal_edit(request, pk):
    """AJAX POST — Edit jadwal yang sudah ada."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    try:
        data = json.loads(request.body)

        petugas_ids = data.get('petugas_ids', [])
        tanggal     = data.get('tanggal')
        jam_mulai   = data.get('jam_mulai')
        jam_selesai = data.get('jam_selesai')
        blok_area   = data.get('blok_area', '').strip()
        catatan_rt  = data.get('catatan_rt', '').strip()
        items       = data.get('items', [])

        form_data = {
            'petugas_ids': ','.join(str(i) for i in petugas_ids),
            'tanggal'    : tanggal,
            'jam_mulai'  : jam_mulai,
            'jam_selesai': jam_selesai,
            'blok_area'  : blok_area,
            'catatan_rt' : catatan_rt,
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
            jadwal.tanggal     = form.cleaned_data['tanggal']
            jadwal.jam_mulai   = form.cleaned_data['jam_mulai']
            jadwal.jam_selesai = form.cleaned_data['jam_selesai']
            jadwal.blok_area   = blok_area
            jadwal.catatan_rt  = catatan_rt
            jadwal.save()

            jadwal.petugas.set(petugas_users)

            # ✅ Bulk update — 1 query, bukan N query
            profiles_to_update = []
            for u in petugas_users:
                profile = getattr(u, 'profile', None)
                if profile and profile.role == 'WARGA':
                    profile.role        = 'PETUGAS'
                    profile.active_role = 'PETUGAS'
                    profiles_to_update.append(profile)

            if profiles_to_update:
                UserProfile.objects.bulk_update(
                    profiles_to_update, ['role', 'active_role']
                )

            # ✅ Bulk create item patroli — 1 query, bukan N query
            jadwal.item_patroli.all().delete()
            item_list = [
                ItemPatroli(jadwal=jadwal, urutan=i + 1, deskripsi=deskripsi)
                for i, deskripsi in enumerate(form.get_items())
            ]
            if item_list:
                ItemPatroli.objects.bulk_create(item_list)

        return JsonResponse({'ok': True, 'pesan': 'Jadwal berhasil diperbarui.'})

    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': str(e)})

@login_required
@rt_required
@require_POST
def jadwal_hapus(request, pk):
    """AJAX POST — Hapus jadwal."""
    jadwal = get_object_or_404(JadwalRonda, pk=pk, dibuat_oleh=request.user)
    jadwal.delete()
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

    # Hitung badge notif (menunggu)
    jumlah_menunggu = semua_profil.filter(submission_status='pending').count()

    context = {
        'semua_profil'   : semua_profil,
        'jumlah_menunggu': jumlah_menunggu,
    }
    return render(request, 'dashboard_rt/verifikasi_warga.html', context)

@login_required
@rt_required
@require_POST
def verifikasi_aksi(request, pk):
    """AJAX — Setujui atau tolak verifikasi warga."""
    import json
    profile = get_object_or_404(UserProfile, pk=pk)
    try:
        data   = json.loads(request.body)
        aksi   = data.get('aksi')  # 'setujui' | 'tolak' | 'tinjau_ulang'

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
def verifikasi_warga(request):
    """Halaman daftar warga menunggu/sudah verifikasi."""
    semua_profil = (
        UserProfile.objects
        .exclude(submission_status='draft')
        .select_related('user')
        .order_by('-created_at')
    )

    jumlah_menunggu = semua_profil.filter(submission_status='pending').count()

    # Kirim daftar NIK yang sudah ada di whitelist → untuk cek duplikat di JS
    existing_niks = list(NIKWhitelist.objects.values_list('nik', flat=True))

    context = {
        'semua_profil'    : semua_profil,
        'jumlah_menunggu' : jumlah_menunggu,
        'existing_niks_json': _json.dumps(existing_niks),
    }
    return render(request, 'dashboard_rt/verifikasi_warga.html', context)


############## Upload CSV NIK ##############

@login_required
@rt_required
def upload_nik_csv(request):
    """
    GET  → Halaman form upload CSV.
    POST → Proses CSV, bulk-insert NIK ke NIKWhitelist.

    Format CSV yang diharapkan (header baris pertama):
        nik, nama_lengkap, tanggal_lahir, ...kolom_lain_diabaikan...

    Kolom wajib  : nik
    Kolom opsional: nama_lengkap (kalau ada, disimpan ke nama_sesuai)
    Kolom lain   : diabaikan
    """
    if request.method == 'GET':
        return render(request, 'dashboard_rt/upload_nik_csv.html')

    # ── POST ──────────────────────────────────────────────────────────────────
    csv_file = request.FILES.get('csv_file')

    if not csv_file:
        return JsonResponse({'ok': False, 'pesan': 'File CSV tidak ditemukan.'})

    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'ok': False, 'pesan': 'File harus berekstensi .csv'})

    if csv_file.size > 5 * 1024 * 1024:  # maks 5 MB
        return JsonResponse({'ok': False, 'pesan': 'Ukuran file maksimal 5 MB.'})

    try:
        raw   = csv_file.read().decode('utf-8-sig')   # utf-8-sig → toleran BOM Excel
        reader = csv.DictReader(io.StringIO(raw))

        # Normalisasi nama header → lowercase + strip spasi
        reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]

        if 'nik' not in reader.fieldnames:
            return JsonResponse({
                'ok'   : False,
                'pesan': 'Kolom "nik" tidak ditemukan. Pastikan baris pertama CSV berisi header.'
            })

        # ── Kumpulkan data valid ──────────────────────────────────────────────
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
                # Lewati NIK tidak valid (bukan 16 digit angka)
                baris_kosong += 1
                continue

            if nik in existing_niks:
                duplikat.append(nik)
                continue

            existing_niks.add(nik)          # cegah duplikat dalam file yang sama
            to_create.append(
                NIKWhitelist(nik=nik, nama_sesuai=nama)
            )

        # ── Bulk insert ───────────────────────────────────────────────────────
        with transaction.atomic():
            NIKWhitelist.objects.bulk_create(to_create)

        pesan = f'{len(to_create)} NIK berhasil ditambahkan.'
        if duplikat:
            pesan += f' {len(duplikat)} NIK sudah ada (dilewati).'
        if baris_kosong:
            pesan += f' {baris_kosong} baris dilewati (kosong/format salah).'

        return JsonResponse({
            'ok'       : True,
            'pesan'    : pesan,
            'ditambah' : len(to_create),
            'duplikat' : len(duplikat),
            'dilewati' : baris_kosong,
        })

    except UnicodeDecodeError:
        return JsonResponse({
            'ok'   : False,
            'pesan': 'Gagal membaca file. Pastikan CSV disimpan dalam format UTF-8.'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'pesan': f'Terjadi kesalahan: {str(e)}'})
