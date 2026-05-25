from django.shortcuts import render
from .decorators import rt_required

@rt_required
def dashboard_utama(request):
    return render(request, 'dashboard_rt/dashboard.html')