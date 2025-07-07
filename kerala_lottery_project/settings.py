import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Environment-specific configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# ALLOWED_HOSTS configuration - IMPROVED
def get_allowed_hosts():
    """Parse ALLOWED_HOSTS from environment variable with better error handling"""
    # Try multiple environment variable names
    hosts_env = (
        os.getenv('DJANGO_ALLOWED_HOSTS') or 
        os.getenv('ALLOWED_HOSTS') or
        'sea-lion-app-begbw.ondigitalocean.app,api.lottokeralalotteries.com'  # Default fallback
    )
    
    # Always include localhost for development
    default_hosts = ['127.0.0.1', 'localhost']
    
    # Start with localhost hosts
    hosts = list(default_hosts)
    
    # Split by comma and clean up each host
    for host in hosts_env.split(','):
        host = host.strip().rstrip('/')  # Remove trailing slash and whitespace
        if host and host not in hosts:  # Only add non-empty, unique hosts
            hosts.append(host)
    
    return hosts

ALLOWED_HOSTS = get_allowed_hosts()
print(f"DEBUG: ALLOWED_HOSTS = {ALLOWED_HOSTS}")

# Debug: Print allowed hosts in development
if DEBUG:
    print(f"DEBUG MODE: {DEBUG}")
    print(f"ENVIRONMENT: {ENVIRONMENT}")
    print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'users',
    'results',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    "django.contrib.sessions.middleware.SessionMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS settings for API - IMPROVED
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development

# Production CORS origins
PRODUCTION_CORS_ORIGINS = [
    "https://sea-lion-app-begbw.ondigitalocean.app",
    "https://lottokeralalotteries.com",
    "https://www.lottokeralalotteries.com",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# Development CORS origins
DEVELOPMENT_CORS_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]

# Set CORS origins based on environment
if DEBUG:
    CORS_ALLOWED_ORIGINS = DEVELOPMENT_CORS_ORIGINS + PRODUCTION_CORS_ORIGINS
else:
    CORS_ALLOWED_ORIGINS = PRODUCTION_CORS_ORIGINS

# CORS settings for API headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

ROOT_URLCONF = "kerala_lottery_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / 'templates',
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "kerala_lottery_project.wsgi.application"

# Database configuration - COMPLETELY FIXED
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Use DATABASE_URL when provided (production or when explicitly set)
    print(f"Using DATABASE_URL connection")
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Override SSL mode for DigitalOcean managed databases
    if 'ondigitalocean.com' in DATABASE_URL:
        DATABASES['default']['OPTIONS'] = {
            'sslmode': 'require',
        }
        print("Applied DigitalOcean SSL configuration")
else:
    # Use local database configuration
    print("Using local database configuration")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'lottery_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'sslmode': 'disable',  # Local development only
            },
        }
    }

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) - IMPROVED
STATIC_URL = '/static/'

# Create static directories if they don't exist
static_dirs = [
    BASE_DIR / "static",
    BASE_DIR / "results" / "static",
]

# Only add existing directories to STATICFILES_DIRS
STATICFILES_DIRS = []
for static_dir in static_dirs:
    if static_dir.exists():
        STATICFILES_DIRS.append(static_dir)

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Static files storage
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Data upload settings
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Admin URL
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')

# API versioning
API_VERSION = 'v1'

# Lottery-specific settings
LOTTERY_SETTINGS = {
    'DEFAULT_CACHE_TIMEOUT': 300,  # 5 minutes
    'TODAY_RESULTS_CACHE_TIMEOUT': 60,  # 1 minute for today's results
    'PREVIOUS_RESULTS_CACHE_TIMEOUT': 3600,  # 1 hour for previous results
    'MAX_CONSOLATION_PRIZES': 10,
    'MAX_FIFTH_PRIZES': 20,
    'ENABLE_AUTO_CONSOLATION_GENERATION': True,
    'ENABLE_BULK_ENTRY': True,
    'MAX_SEARCH_RESULTS': 100,
    'DEFAULT_PAGINATION_SIZE': 20,
}

# Environment-specific overrides
if ENVIRONMENT == 'production':
    # Production-specific settings
    CORS_ALLOW_ALL_ORIGINS = False
    # Security settings for production
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
# elif ENVIRONMENT == 'staging':
#     # Staging-specific settings
#     DEBUG = False
#     ALLOWED_HOSTS = ['staging.lottery.com', 'localhost']

# Feature flags
FEATURE_FLAGS = {
    'ENABLE_API_RATE_LIMITING': True,
    'ENABLE_DETAILED_LOGGING': True,
    'ENABLE_CACHING': True,
    'ENABLE_EMAIL_NOTIFICATIONS': not DEBUG,
    'ENABLE_ADMIN_HONEYPOT': not DEBUG,
}

# Enhanced logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
