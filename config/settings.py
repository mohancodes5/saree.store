"""
Django settings — Saree Store (localhost + Vercel / serverless).
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-change-in-production-9xk2m!q#v',
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() in ('1', 'true', 'yes')

# Vercel sets VERCEL=1; include .vercel.app for preview deployments
_default_hosts = 'localhost,127.0.0.1,testserver,.vercel.app'
ALLOWED_HOSTS = [h for h in os.environ.get('DJANGO_ALLOWED_HOSTS', _default_hosts).split(',') if h]

ON_VERCEL = bool(os.environ.get('VERCEL'))

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'apps.accounts',
    'apps.products',
    'apps.cart',
    'apps.orders',
    'apps.payments',
    'apps.adminpanel',
    'apps.reviews',
    'apps.wishlist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.cart.context_processors.cart_summary',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Database: PostgreSQL on Vercel (DATABASE_URL); SQLite locally ---
_database_url = (os.environ.get('DATABASE_URL') or '').strip()
if ON_VERCEL and not _database_url:
    raise RuntimeError(
        'Vercel requires DATABASE_URL (PostgreSQL). SQLite cannot write on serverless. '
        'Add Vercel Postgres or Neon/Supabase and set DATABASE_URL in project Environment Variables.'
    )
if _database_url:
    # Serverless / hosted Postgres (Neon, Supabase, Railway, etc.)
    _ssl = os.environ.get('DATABASE_SSL_REQUIRE', 'true').lower() in ('1', 'true', 'yes')
    DATABASES = {
        'default': dj_database_url.config(
            default=_database_url,
            conn_max_age=int(os.environ.get('DB_CONN_MAX_AGE', '0')),
            ssl_require=_ssl,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-in'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
# Vercel filesystem is read-only except /tmp — uploads work but are ephemeral unless you use S3, etc.
if ON_VERCEL:
    MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', '/tmp/saree_media'))
else:
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'products:home'
LOGOUT_REDIRECT_URL = 'products:home'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS / CSRF on Vercel (login POST requires trusted origin)
if ON_VERCEL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    _raw_csrf = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').strip()
    if _raw_csrf:
        CSRF_TRUSTED_ORIGINS = [x.strip() for x in _raw_csrf.split(',') if x.strip()]
    else:
        _vu = (os.environ.get('VERCEL_URL') or '').strip()
        if _vu:
            _vu = _vu.removeprefix('https://').removeprefix('http://').rstrip('/')
            CSRF_TRUSTED_ORIGINS = [f'https://{_vu}']
        else:
            CSRF_TRUSTED_ORIGINS = []

# Razorpay (set in environment for real charges)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# WhatsApp: set Meta *or* Twilio (see WHATSAPP_PROVIDER)
WHATSAPP_PROVIDER = os.environ.get('WHATSAPP_PROVIDER', 'auto').strip().lower()
META_WHATSAPP_TOKEN = os.environ.get('META_WHATSAPP_TOKEN', '')
META_WHATSAPP_PHONE_NUMBER_ID = os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID', '')
META_WHATSAPP_API_VERSION = os.environ.get('META_WHATSAPP_API_VERSION', 'v21.0')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')

DEFAULT_FROM_EMAIL = 'noreply@sareestore.local'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

REFERRAL_DISCOUNT_PERCENT = int(os.environ.get('REFERRAL_DISCOUNT_PERCENT', '5'))
