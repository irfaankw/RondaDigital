from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('account.urls', namespace='account')),
    path('panel-rt/', include('dashboard_rt.urls', namespace='dashboard_rt')),
    path('patroli/', include('patrol.urls', namespace='patrol')),
    # path('emergency/', include('emergency.urls', namespace='emergency')),
    
    # ── Password Reset Confirm & Complete (bawaan Django) ──
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='account/password_reset/password_reset_confirm.html',
            post_reset_login=False,
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='account/password_reset/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)