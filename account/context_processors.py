from django.contrib.auth.models import User

def user_profile(request):
    """
    Menyuntikkan 'user_profile' ke semua template secara global.
    Menggunakan internal request caching + select_related
    agar hanya 1 query per request, tidak N+1.
    """
    if not request.user.is_authenticated:
        return {'user_profile': None}

    if not hasattr(request, '_cached_user_profile'):
        try:
            user_with_profile = User.objects.select_related('profile').get(
                pk=request.user.pk
            )
            request._cached_user_profile = user_with_profile.profile
        except Exception:
            request._cached_user_profile = None

    return {'user_profile': request._cached_user_profile}