from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm, ProfileForm
from .models import NIKWhitelist, UserProfile

import urllib.parse

# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def _get_or_create_profile(user):
    """Ambil atau buat UserProfile untuk user."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _buat_username(nik):
    """Generate username unik berbasis NIK."""
    base     = f"warga_{nik}"
    username = base
    suffix   = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}_{suffix}"
        suffix  += 1
    return username


def _get_jadwal_aktif(user):
    """
    Cari JadwalRonda hari ini untuk user yang sedang berjalan.
    Return objek jadwal kalau aktif, None kalau tidak ada / belum mulai / sudah selesai.
    """
    from patrol.models import JadwalRonda
    from datetime import date

    today  = date.today()
    jadwal = JadwalRonda.objects.filter(petugas=user, tanggal=today).first()
    if jadwal and jadwal.is_absen_masih_bisa():
        return jadwal
    return None


def _redirect_after_login(user):
    """
    Tentukan halaman tujuan setelah login berdasarkan role/active_role.
    Urutan prioritas:
      1. Admin/superuser → halaman admin Django
      2. RT → dashboard RT
      3. Sedang mode PETUGAS → dashboard petugas
      4. Selainnya → dashboard warga
    """
    if user.is_staff or user.is_superuser:
        return redirect('/admin/')

    profile = _get_or_create_profile(user)

    if profile.role == 'RT':
        return redirect('dashboard_rt:dashboard')
    elif profile.get_active_role() == 'PETUGAS':
        # Middleware sudah jalan sebelum view, jadi kalau get_active_role()
        # masih PETUGAS berarti shift masih aktif
        return redirect('patrol:petugas_home')
    else:
        return redirect('account:home_index')


# ─────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────

def landing_index(request):
    """Halaman splash/landing. Kalau sudah login, langsung redirect."""
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)
    return render(request, 'account/splash.html')


@login_required
def home_index(request):
    """
    Dashboard warga. Kalau active_role PETUGAS (shift masih jalan),
    redirect ke dashboard petugas.
    Middleware sudah handle auto-reset sebelum view ini dipanggil.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')

    profile = _get_or_create_profile(request.user)

    if profile.get_active_role() == 'PETUGAS':
        return redirect('patrol:petugas_home')

    return render(request, 'account/home.html')


def login_view(request):
    """Login dengan NIK + password."""
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)

    if request.method != 'POST':
        return render(request, 'account/auth/login.html')

    form = LoginForm(request.POST)
    if not form.is_valid():
        return render(request, 'account/auth/login.html', {'form': form})

    nik      = form.cleaned_data['nik']
    password = form.cleaned_data['password']

    try:
        profile  = UserProfile.objects.select_related('user').get(nik=nik)
        user_obj = profile.user
    except UserProfile.DoesNotExist:
        form.add_error('nik', 'NIK atau Password yang kamu masukkan salah.')
        return render(request, 'account/auth/login.html', {'form': form})

    if not user_obj.is_active:
        form.add_error('nik', 'Akun kamu telah dinonaktifkan. Silakan hubungi RT.')
        return render(request, 'account/auth/login.html', {'form': form})

    user = authenticate(request, username=user_obj.username, password=password)
    if user is None:
        form.add_error('nik', 'NIK atau Password yang kamu masukkan salah.')
        return render(request, 'account/auth/login.html', {'form': form})

    login(request, user)
    return _redirect_after_login(user)

def register_view(request):
    """Registrasi dengan NIK yang sudah di-whitelist oleh RT."""
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)

    if request.method != 'POST':
        return render(request, 'account/auth/register.html')

    form = RegisterForm(request.POST)
    if not form.is_valid():
        return render(request, 'account/auth/register.html', {'form': form})

    nik      = form.cleaned_data['nik']
    nama     = form.cleaned_data['nama_lengkap']
    no_hp    = form.cleaned_data['no_hp']
    password = form.cleaned_data['password']

    nama_parts = nama.strip().split(' ', 1)
    user = User.objects.create_user(
        username   = _buat_username(nik),
        password   = password,
        first_name = nama_parts[0],
        last_name  = nama_parts[1] if len(nama_parts) > 1 else '',
    )

    # Ambil rt/rw dari profile RT yang mengelola sistem ini
    rt_profile = UserProfile.objects.filter(role='RT').first()
    rt_val     = rt_profile.rt if rt_profile else ''
    rw_val     = rt_profile.rw if rt_profile else ''

    profile              = _get_or_create_profile(user)
    profile.nik          = nik
    profile.nama_lengkap = nama
    profile.no_hp        = no_hp
    profile.rt           = rt_val
    profile.rw           = rw_val
    profile.is_verified  = False
    profile.save()

    # Tandai NIK sudah dipakai
    NIKWhitelist.objects.filter(nik=nik).update(is_used=True)

    user = authenticate(request, username=user.username, password=password)
    if user:
        login(request, user)

    return redirect('account:home_index')

def forgot_password_view(request):
    """Tampilkan link WhatsApp ke RT untuk minta reset password."""
    nomor_wa_rt    = getattr(settings, 'NOMOR_WA_RT', None)
    pesan_template = getattr(
        settings,
        'WA_RESET_PASSWORD_TEXT',
        'Assalamualaikum Pak RT, saya ingin meminta reset password akun RondaDigital saya. '
        'NIK: [isi NIK kamu]. Nama: [isi nama kamu]. Terima kasih.'
    )

    wa_url = None
    if nomor_wa_rt:
        wa_url = f"https://wa.me/{nomor_wa_rt}?text={urllib.parse.quote(pesan_template)}"

    return render(request, 'account/auth/forgot_password.html', {'wa_url': wa_url})


def logout_view(request):
    logout(request)
    return redirect('account:landing_index')


@login_required
def profile_view(request):
    profile      = _get_or_create_profile(request.user)
    petugas      = UserProfile.objects.filter(role='PETUGAS', is_verified=True).select_related('user')
    is_locked    = profile.submission_status in ('pending', 'verified')

    # jadwal_aktif hanya relevan untuk user yang punya role PETUGAS
    jadwal_aktif = _get_jadwal_aktif(request.user) if profile.role == 'PETUGAS' else None

    # ── 1. Upload Foto Profil ──────────────────────────────────────
    if request.method == 'POST' and 'upload_foto_profil' in request.POST:
        if 'foto_profil' in request.FILES:
            profile.foto_profil = request.FILES['foto_profil']
            profile.save(update_fields=['foto_profil'])
        return redirect('account:profile')

    # ── 2. Hapus Dokumen ───────────────────────────────────────────
    if request.method == 'POST':
        if 'clear_ktp' in request.POST and profile.foto_ktp:
            profile.foto_ktp.delete(save=True)
            return redirect('account:profile')
        if 'clear_kk' in request.POST and profile.foto_kk:
            profile.foto_kk.delete(save=True)
            return redirect('account:profile')

    # ── 3. Update Form Identitas ───────────────────────────────────
    if request.method == 'POST' and not is_locked:
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.submission_status = 'pending'
            p.save()
            return redirect('account:profile')
    else:
        form = ProfileForm(instance=profile)

    if is_locked:
        for field in form.fields.values():
            field.widget.attrs['disabled'] = True

    # ── 4. Context ─────────────────────────────────────────────────
    nomor_wa_rt  = getattr(settings, 'NOMOR_WA_RT', '6282196636162')
    pesan_profil = getattr(
        settings,
        'WA_PROFIL_TEXT',
        'Assalamualaikum Pak RT, saya sudah melengkapi profil saya di RondaDigital. '
        'Mohon verifikasi data saya. Terima kasih.'
    )
    wa_url = (
        f"https://wa.me/{nomor_wa_rt}?text={urllib.parse.quote(pesan_profil)}"
        if profile.submission_status == 'pending'
        else None
    )

    readonly_data = [
        {'label': 'Nama Lengkap', 'value': profile.nama_lengkap or '-'},
        {'label': 'NIK',          'value': profile.nik          or '-'},
        {'label': 'Nomor HP',     'value': profile.no_hp        or '-'},
    ]

    # Info jam shift untuk ditampilkan di modal (hanya kalau ada jadwal aktif)
    shift_info = None
    if profile.role == 'PETUGAS' and jadwal_aktif:
        shift_info = {
            'jam_mulai'  : jadwal_aktif.jam_mulai.strftime('%H:%M'),
            'jam_selesai': jadwal_aktif.jam_selesai.strftime('%H:%M'),
        }

    return render(request, 'account/profile.html', {
        'form'         : form,
        'profile'      : profile,
        'petugas'      : petugas,
        'is_locked'    : is_locked,
        'wa_url'       : wa_url,
        'progress'     : profile.progress,
        'step_list'    : ['Buat Akun', 'Lengkapi Identitas', 'Upload KTP/KK', 'Disetujui RT'],
        'readonly_data': readonly_data,
        'jadwal_aktif' : jadwal_aktif,
        'shift_info'   : shift_info,
    })

@login_required
def cctv_warga(request):
    """
    Menampilkan halaman CCTV untuk warga.
    """
    profile = _get_or_create_profile(request.user)
    
    
    return render(request, 'account/cctv_warga.html', {
        'url_name': 'cctv_warga' 
    })

@login_required
def switch_role_view(request):
    """
    Endpoint untuk beralih mode antara PETUGAS dan WARGA.

    Aturan:
    - PETUGAS → WARGA : bisa kapan saja selama shift belum selesai
                        (middleware akan auto-reset kalau shift sudah selesai)
    - WARGA → PETUGAS : hanya kalau jadwal shift hari ini sedang aktif
                        (is_absen_masih_bisa() = True)
    """
    if request.method != 'POST':
        return redirect('account:profile')

    profile = _get_or_create_profile(request.user)
    current = profile.get_active_role()

    if current == 'PETUGAS':
        # Kembali ke mode warga — selalu bisa
        profile.active_role = 'WARGA'
        profile.save(update_fields=['active_role'])
        return redirect('account:home_index')

    elif current == 'WARGA' and profile.role == 'PETUGAS':
        # Masuk mode petugas — hanya kalau shift sedang aktif
        jadwal = _get_jadwal_aktif(request.user)
        if jadwal:
            profile.active_role = 'PETUGAS'
            profile.save(update_fields=['active_role'])
            return redirect('patrol:petugas_home')
        else:
            # Shift belum mulai atau sudah selesai — tolak, balik ke profil
            return redirect('account:profile')

    # Fallback
    return redirect('account:profile')