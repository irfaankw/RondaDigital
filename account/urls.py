from django.urls import path
from . import views

app_name = 'account'
urlpatterns = [
    path('', views.landing_index, name='landing_index'),
    path('home/', views.home_index, name='home_index'),
    path('login/', views.login_view, name='login_view'),
    path('register/', views.register_view, name='register_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('profile/', views.profile_view, name='profile'),
    path('switch-role/', views.switch_role_view, name='switch_role'),
]