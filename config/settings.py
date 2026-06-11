from pathlib import Path
import os
from dotenv import load_dotenv
from dotenv import load_dotenv
import os

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = []
ALLOWED_HOSTS = [
    'ronda-digital.vercel.app', 
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "account.apps.AccountConfig",
    "dashboard_rt.apps.DashboardRtConfig",
    "emergency.apps.EmergencyConfig",
    "patrol.apps.PatrolConfig",
    "storages",
    "pwa",
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "account.middleware.AutoResetPetugasRoleMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'account.context_processors.user_profile',
                'emergency.context_processors.emergency_context',
                'dashboard_rt.context_processors.alert_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

LOGIN_URL = 'account:login_view'

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Makassar"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/


# Static files (CSS, JavaScript, Images) - Tetap Lokal/Server Deploy
STATIC_URL = "static/"
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / 'static' 
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# PWA Settings
PWA_APP_NAME = 'RondaDigital'
PWA_APP_DESCRIPTION = "Sistem Keamanan Lingkungan Berbasis Web"
PWA_APP_THEME_COLOR = '#020d20'
PWA_APP_BACKGROUND_COLOR = '#020d20'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {'src': '/static/assets/images/Icon-RondaDigital.png', 'sizes': '160x160'}
]
PWA_APP_ICONS_APPLE = [
    {'src': '/static/assets/images/Icon-RondaDigital.png', 'sizes': '160x160'}
]
PWA_APP_SPLASH_SCREEN = []
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'id-ID'

# Supabase Storage (S3-compatible) - Khusus Media Upload Cloud
AWS_ACCESS_KEY_ID        = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY    = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME  = os.getenv("AWS_STORAGE_BUCKET_NAME", "media")
AWS_S3_ENDPOINT_URL      = os.getenv("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME       = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
SUPABASE_PROJECT_REF     = os.getenv("SUPABASE_PROJECT_REF")    

AWS_S3_FILE_OVERWRITE    = False
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL          = None       
AWS_QUERYSTRING_AUTH     = False      

AWS_S3_CUSTOM_DOMAIN = (
    f"{SUPABASE_PROJECT_REF}.supabase.co"
    f"/storage/v1/object/public/{AWS_STORAGE_BUCKET_NAME}"
)

# Semua file media dikelola django-storages ke Cloud Bucket
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage", 
    },
}

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NOMOR_WA_RT = os.getenv("NOMOR_WA_RT", "6282196636162")
# Template untuk Lupa Password
WA_RESET_PASSWORD_TEXT = (
    "Assalamualaikum Pak RT, saya ingin meminta reset password "
    "akun RondaDigital saya.\n\n"
    "NIK: [isi NIK kamu]\n"
    "Nama: [isi nama kamu]\n\n"
    "Mohon bantuannya. Terima kasih 🙏"
)
# Template untuk Verifikasi Profil
WA_PROFIL_TEXT = (
    "Assalamualaikum Pak RT, saya sudah melengkapi profil saya "
    "di RondaDigital. Mohon verifikasi data saya. Terima kasih."
)