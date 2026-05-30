import urllib.parse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm
from .models import NIKWhitelist, UserProfile


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

def _redirect_after_login(user):
    """Tentukan halaman tujuan setelah login berdasarkan role."""
    if user.is_staff or user.is_superuser:
        return redirect('/admin/')
    profile = user.profile
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

def home_index(request):
    if not request.user.is_authenticated:
        return redirect('account:login_view')
    # Admin tidak punya profile, arahkan ke admin panel
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')
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