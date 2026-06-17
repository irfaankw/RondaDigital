
from django.contrib.auth.models import User
from django.conf import settings


def user_profile(request):
    """
    Menyuntikkan 'user_profile' dan 'NOMOR_WA_RT' ke semua template secara global.
    Menggunakan internal request caching + select_related
    agar hanya 1 query per request, tidak N+1.
    """
    if not request.user.is_authenticated:
        return {
            'user_profile': None,
            'NOMOR_WA_RT': getattr(settings, 'NOMOR_WA_RT', ''),
        }

    if not hasattr(request, '_cached_user_profile'):
        try:
            user_with_profile = User.objects.select_related('profile').get(
                pk=request.user.pk
            )
            request._cached_user_profile = user_with_profile.profile
        except Exception:
            request._cached_user_profile = None

    return {
        'user_profile': request._cached_user_profile,
        'NOMOR_WA_RT': getattr(settings, 'NOMOR_WA_RT', ''),
    }