from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',      admin.site.urls),
    path('',            include('account.urls',      namespace='account')),
<<<<<<< HEAD
=======
    path('', include('pwa.urls')),
>>>>>>> 524ca24b4e9a22b70aa44e7202354cbb8b013f39
    path('panel-rt/',   include('dashboard_rt.urls', namespace='dashboard_rt')),
    path('patroli/',    include('patrol.urls',        namespace='patrol')),
    path('emergency/', include('emergency.urls',   namespace='emergency')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)