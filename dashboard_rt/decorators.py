from django.http import Http404
from functools import wraps

def rt_required(view_func):
    """
    Decorator untuk melindungi views khusus Ketua RT.
    Jika user bukan RT, raise Http404 (Information Obfuscation).
    Tidak membocorkan apapun ke publik — URL seolah tidak ada.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise Http404()
        try:
            if request.user.profile.role != 'RT':
                raise Http404()
        except Exception:
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped