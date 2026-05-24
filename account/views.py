from django.shortcuts import render, redirect

def landing_index(request):
    # Cukup render file splash screen
    return render(request, "account/splash.html")

def home_index(request):
    # Pastikan user login dulu, kalau lolos baru render dashboard utama
    if not request.user.is_authenticated:
        return redirect('account:login')
    return render(request, "account/index.html")

def login_view(request):
    return render(request, "account/login.html")

def register_view(request):
    return render(request, "account/register.html")

def logout_view(request):
    return render(request, "account/logout.html")
