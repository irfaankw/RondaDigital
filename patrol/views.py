from django.shortcuts import render

def petugas_home(request):
    return render(request, 'patrol/petugas_home.html')
