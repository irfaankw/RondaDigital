import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from .forms import LoginForm, RegisterForm
from .models import UserProfile

def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

# Username jadi unik, auto increment.
def _buat_username(nama):
    base = re.sub(r'[^a-z0-9]', '', nama.lower())[:50]  # buang karakter selain huruf/angka
    username = base
    suffix = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}{suffix}"
        suffix += 1
    return username

def landing_index(request):
    return render(request, 'account/splash.html')

def home_index(request):
    if not request.user.is_authenticated:
        return redirect('account:login_view')
    return render(request, 'account/home.html')

def login_view(request):
    if request.method != 'POST':
        return render(request, 'account/auth/login.html')

    form = LoginForm(request.POST)

    if not form.is_valid():
        return render(request, 'account/auth/login.html', {'form': form})

    identifier = form.cleaned_data['identifier']
    password   = form.cleaned_data['password']

    # Cari user berdasarkan email atau no_hp
    user_obj = None
    try:
        user_obj = User.objects.get(email=identifier)
    except User.DoesNotExist:
        try:
            profile  = UserProfile.objects.get(no_hp=identifier)
            user_obj = profile.user
        except UserProfile.DoesNotExist:
            pass

    if user_obj is None:
        form.add_error('password', 'Email/No. HP atau Password yang kamu masukkan salah.')
        return render(request, 'account/auth/login.html', {'form': form})

    if not user_obj.is_active:
        form.add_error('password', 'Akun Anda telah dinonaktifkan. Silakan hubungi admin.')
        return render(request, 'account/auth/login.html', {'form': form})

    user = authenticate(request, username=user_obj.username, password=password)
    if user is None:
        form.add_error('password', 'Email/No. HP atau Password yang kamu masukkan salah.')
        return render(request, 'account/auth/login.html', {'form': form})

    login(request, user)
    _get_or_create_profile(user)
    profile = user.profile
    if profile.role == 'RT':
        return redirect('dashboard_rt:dashboard')
    elif profile.role == 'PETUGAS':
        return redirect('patrol:petugas_home')
    else:
        return redirect('account:home_index')

def register_view(request):
    if request.method != 'POST':
        return render(request, 'account/auth/register.html')

    form = RegisterForm(request.POST)

    if not form.is_valid():
        return render(request, 'account/auth/register.html', {'form': form})

    nama     = form.cleaned_data['nama_lengkap']
    email    = form.cleaned_data['email']
    no_hp    = form.cleaned_data['no_hp']
    password = form.cleaned_data['password']

    # Cek duplikasi
    has_duplicate = False
    if User.objects.filter(email=email).exists():
        form.add_error('email', 'Email sudah terdaftar.')
        has_duplicate = True
    if UserProfile.objects.filter(no_hp=no_hp).exists():
        form.add_error('no_hp', 'No. HP ini sudah terdaftar.')
        has_duplicate = True
    if has_duplicate:
        return render(request, 'account/auth/register.html', {'form': form})

    # Username = nama_lengkap lowercase tanpa spasi (bukan email)
    username   = _buat_username(nama)
    nama_parts = nama.strip().split(' ', 1)

    user = User.objects.create_user(
        username=username,                                   
        email=email,                                         
        password=password,
        first_name=nama_parts[0],
        last_name=nama_parts[1] if len(nama_parts) > 1 else '',
    )

    profile              = _get_or_create_profile(user)
    profile.nama_lengkap = nama
    profile.no_hp        = no_hp
    profile.save()

    login(request, user)
    return redirect('account:home_index')

from django.contrib.auth.forms import PasswordResetForm

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('account:home_index')

    if request.method != 'POST':
        return render(request, 'account/password_reset/forgot_password.html')

    email = request.POST.get('email', '').strip()

    # Validasi kosong
    if not email:
        return render(request, 'account/password_reset/forgot_password.html', {
            'error': 'Email tidak boleh kosong.',
            'old_email': email,
        })

    # Gunakan PasswordResetForm bawaan Django
    form = PasswordResetForm({'email': email})
    if not form.is_valid():
        return render(request, 'account/password_reset/forgot_password.html', {
            'error': 'Format email tidak valid.',
            'old_email': email,
        })

    # Cek apakah email terdaftar
    if not User.objects.filter(email=email, is_active=True).exists():
        return render(request, 'account/password_reset/forgot_password.html', {
            'error': 'Email tersebut tidak terdaftar di sistem kami.',
            'old_email': email,
        })

    # Kirim email reset (link tercetak di terminal saat development)
    form.save(
        request=request,
        use_https=request.is_secure(),
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    )

    return render(request, 'account/password_reset/forgot_password.html', {
        'success': 'Link instruksi reset password telah dikirim ke email kamu!',
    })

def logout_view(request):
    logout(request)
    return redirect('account:landing_index')