import os
from pathlib import Path
import urllib.parse

BASE_DIR = Path(__file__).resolve().parent.parent

# Security & Environment Fallbacks
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure--*px@z-y1mxj$z3*!wgt-buqg+do0798*hjsxeg22*=wo4x%ui')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,.railway.app').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'ingestion',
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

ROOT_URLCONF = 'breathe.urls'

# Path pointing to your production frontend bundle
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'frontend' / 'dist'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'breathe.wsgi.application'

# Database Engine (Unified)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static Assets (Production Ready)
# Static files configuration (Preserved for unified single-container execution)
STATIC_URL = '/static/'  # Enforce leading and trailing slashes for path matching

# Where collectstatic gathers assets for production compression
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Point directly to the React production build root directory
STATICFILES_DIRS = [
    BASE_DIR.parent / 'frontend' / 'dist',
]

# Enable WhiteNoise compression and caching for fast asset delivery
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'