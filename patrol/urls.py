from django.urls import path
from . import views

app_name = 'patrol'
urlpatterns = [
    path('dashboard/', views.petugas_home, name='petugas_home'),
]