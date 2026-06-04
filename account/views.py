from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm, ProfileForm
from .models import NIKWhitelist, UserProfile

import urllib.parse

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def _buat_username(nik):
    base     = f"warga_{nik}"
    username = base
    suffix   = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}_{suffix}"
        suffix  += 1
    return username


def _get_jadwal_aktif(user):
    """
    Cari JadwalRonda hari ini untuk user ini yang sedang aktif.
    Return jadwal jika ada dan masih aktif, None jika tidak.
    """
    from patrol.models import JadwalRonda
    from datetime import date
    today = date.today()
    jadwal = JadwalRonda.objects.filter(petugas=user, tanggal=today).first()
    if jadwal and jadwal.is_absen_masih_bisa():
        return jadwal
    return None

def _auto_reset_active_role(profile):
    """
    Jika user sedang mode PETUGAS tapi shift-nya sudah selesai,
    reset active_role ke WARGA secara otomatis.
    Dipanggil saat page load di home_index, profile_view, switch_role_view.
    """
    if profile.get_active_role() == 'PETUGAS':
        from patrol.models import JadwalRonda
        from datetime import date
        today  = date.today()
        jadwal = JadwalRonda.objects.filter(petugas=profile.user, tanggal=today).first()
        if not jadwal or jadwal.is_shift_selesai():
            profile.active_role = 'WARGA'
            profile.save(update_fields=['active_role'])

def _redirect_after_login(user):
    """Tentukan halaman tujuan setelah login berdasarkan role."""
    if user.is_staff or user.is_superuser:
        return redirect('/admin/')
    profile = _get_or_create_profile(user)
    if profile.role == 'RT':
        return redirect('dashboard_rt:dashboard')
    elif profile.role == 'PETUGAS':
        return redirect('patrol:petugas_home')
    else:
        return redirect('account:home_index')

# ── Views ─────────────────────────────────────────────────────────────────────

def landing_index(request):
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)
    return render(request, 'account/splash.html')

@login_required
def home_index(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')
    profile = _get_or_create_profile(request.user)
    if profile.get_active_role() == 'PETUGAS':
        return redirect('patrol:petugas_home')
    return render(request, 'account/home.html')

def login_view(request):
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

    profile              = _get_or_create_profile(user)
    profile.nik          = nik
    profile.nama_lengkap = nama
    profile.no_hp        = no_hp
    profile.is_verified  = True   # NIK sudah lolos whitelist RT = langsung verified
    profile.save()

    # Tandai NIK sudah digunakan agar tidak bisa dipakai daftar ulang
    NIKWhitelist.objects.filter(nik=nik).update(is_used=True)

    # Auto-login setelah registrasi berhasil
    user = authenticate(request, username=user.username, password=password)
    if user:
        login(request, user)

    return redirect('account:home_index')

def forgot_password_view(request):
    """
    Tampilkan link WhatsApp ke RT dengan pesan otomatis.
    Nomor WA RT dan template pesan dikonfigurasi di settings.py.
    """
    nomor_wa_rt = getattr(settings, 'NOMOR_WA_RT', None)
    pesan_template = getattr(
        settings,
        'WA_RESET_PASSWORD_TEXT',
        'Assalamualaikum Pak RT, saya ingin meminta reset password akun RondaDigital saya. NIK: [isi NIK kamu]. Nama: [isi nama kamu]. Terima kasih.'
    )
    wa_url = None
    if nomor_wa_rt:
        encoded_pesan = urllib.parse.quote(pesan_template)
        wa_url = f"https://wa.me/{nomor_wa_rt}?text={encoded_pesan}"

    return render(request, 'account/auth/forgot_password.html', {'wa_url': wa_url})

def logout_view(request):
    logout(request)
    return redirect('account:landing_index')

@login_required
def profile_view(request):
    profile = _get_or_create_profile(request.user)                        
    petugas = UserProfile.objects.filter(role='PETUGAS', is_verified=True).select_related('user')
    is_locked = profile.submission_status in ('pending', 'verified')
    jadwal_aktif = _get_jadwal_aktif(request.user) if profile.role == 'PETUGAS' else None 

    # 1. Handle Upload Foto Profil (Bisa dilakukan kapan saja, meski locked)
    if request.method == 'POST' and 'upload_foto_profil' in request.POST:
        if 'foto_profil' in request.FILES:
            profile.foto_profil = request.FILES['foto_profil']
            profile.save(update_fields=['foto_profil'])
            return redirect('account:profile')

    # 2. Handle Clear Dokumen (Hapus file dari storage & database)
    if request.method == 'POST':
        if 'clear_ktp' in request.POST and profile.foto_ktp:
            profile.foto_ktp.delete(save=True)
            return redirect('account:profile')
        
        if 'clear_kk' in request.POST and profile.foto_kk:
            profile.foto_kk.delete(save=True)
            return redirect('account:profile')

    # 3. Handle Update Profile Form (Hanya jika belum locked)
    if request.method == 'POST' and not is_locked:
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.submission_status = 'pending'
            p.save()
            return redirect('account:profile')
    elif request.method == 'POST' and is_locked:
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile)

    # Disable semua field di form jika statusnya locked
    if is_locked:
        for field in form.fields.values():
            field.widget.attrs['disabled'] = True

    # 4. Context Preparation
    nomor_wa_rt = getattr(settings, 'NOMOR_WA_RT', '6282196636162') # Default jika settings kosong
    pesan_profil = getattr(settings, 'WA_PROFIL_TEXT', 
                           'Assalamualaikum Pak RT, saya sudah melengkapi profil saya di RondaDigital. Mohon verifikasi data saya. Terima kasih.')
    
    wa_url = f"https://wa.me/{nomor_wa_rt}?text={urllib.parse.quote(pesan_profil)}" if profile.submission_status == 'pending' else None

    # Data Readonly untuk ditampilkan di atas form
    readonly_data = [
        {'label': 'Nama Lengkap', 'value': profile.nama_lengkap},
        {'label': 'NIK', 'value': profile.nik},
        {'label': 'Nomor HP', 'value': profile.no_hp},
    ]

    shift_info = None
    if profile.role == 'PETUGAS' and jadwal_aktif:
        shift_info = {
            'jam_mulai'  : jadwal_aktif.jam_mulai.strftime('%H:%M'),
            'jam_selesai': jadwal_aktif.jam_selesai.strftime('%H:%M'),
        }

    return render(request, 'account/profile.html', {
        'form': form,
        'profile': profile,
        'petugas': petugas,
        'is_locked': is_locked,
        'wa_url': wa_url,
        'progress': profile.progress,
        'step_list': ['Buat Akun', 'Lengkapi Identitas', 'Upload KTP/KK', 'Disetujui RT'],
        'readonly_data': readonly_data,
        'jadwal_aktif' : jadwal_aktif,  
        'shift_info'   : shift_info,
    })

@login_required
def switch_role_view(request):
    if request.method != 'POST':
        return redirect('account:profile')

    profile = _get_or_create_profile(request.user)
    current = profile.get_active_role()

    if current == 'PETUGAS':
        # Petugas → Warga: bisa kapan saja
        profile.active_role = 'WARGA'
        profile.save(update_fields=['active_role'])
        return redirect('account:home_index')

    elif current == 'WARGA' and profile.role == 'PETUGAS':
        # Warga → Petugas: hanya kalau shift sedang aktif
        jadwal = _get_jadwal_aktif(request.user)
        if jadwal:
            profile.active_role = 'PETUGAS'
            profile.save(update_fields=['active_role'])
            return redirect('patrol:petugas_home')
        else:
            # Shift belum mulai / sudah selesai → tolak
            return redirect('account:profile')

    return redirect('account:profile')