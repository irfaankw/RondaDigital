from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from patrol.models import JadwalRonda
from account.models import UserProfile  # ← tambah import ini
from .models import ItemPatroli
from .decorators import rt_required
from .forms import JadwalRondaForm
import json

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
def cctv_monitoring(request):
    """Halaman Monitoring CCTV khusus Ketua RT (Statis)."""
    return render(request, 'dashboard_rt/cctv.html')