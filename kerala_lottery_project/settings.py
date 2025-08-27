import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
# Firebase Configuration
import firebase_admin
from firebase_admin import credentials

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir(exist_ok=True)

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
        'anon': '60/hour',  # Reduced from 100 for safety
        'user': '300/hour',  # Reduced from 1000 for safety
        'prediction': '30/hour',  # New: specific for predictions
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




# SMART CACHING STRATEGY - DATABASE CACHE WITH REDIS UPGRADE PATH


REDIS_URL = os.getenv('REDIS_URL', None)

if REDIS_URL:
    # Redis cache (for future upgrade)
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 20,
                    'retry_on_timeout': True,
                },
                'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            },
            'KEY_PREFIX': 'lottery_app',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    print("⚡ Redis cache enabled - Premium performance!")
else:
    # Database cache (current strategy)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'lottery_cache_table',
            'TIMEOUT': 300,  # 5 minutes
            'OPTIONS': {
                'MAX_ENTRIES': 1000,  # Limit cache size
                'CULL_FREQUENCY': 3,  # Clean old entries
            }
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    print("Database cache enabled - Fast and free!")

# Use Redis for sessions (optional but recommended)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'




# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 7200  # 2 hours
SESSION_SAVE_EVERY_REQUEST = True
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
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'lottery_app.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'lottery_app': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}



def get_firebase_credentials():
    """Get Firebase credentials from environment variables"""
    try:
        # Option 1: Use service account file (development)
        firebase_file = BASE_DIR / 'firebase-service-account-key.json'
        if firebase_file.exists() and not ENVIRONMENT == 'production':
            return firebase_file
        
        # Option 2: Use environment variables (production)
        firebase_creds = {
            "type": "service_account",
            "project_id": os.environ.get('FIREBASE_PROJECT_ID', 'lotto-app-f3440'),
            "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_CLIENT_EMAIL')}"
        }
        
        # Validate required fields
        required_fields = ['private_key_id', 'private_key', 'client_email', 'client_id']
        if all(firebase_creds.get(field) for field in required_fields):
            return firebase_creds
        else:
            print("⚠️ Firebase credentials incomplete, falling back to test mode")
            return None
            
    except Exception as e:
        print(f"❌ Firebase credential error: {e}")
        return None

# Set Firebase credentials
FIREBASE_CREDENTIALS = get_firebase_credentials()

# If we have a file path, use that instead
if isinstance(FIREBASE_CREDENTIALS, Path):
    FIREBASE_CREDENTIALS_FILE = FIREBASE_CREDENTIALS

# Production Security Settings
if ENVIRONMENT == 'production':
    # Security settings
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Only allow production domains
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        "https://sea-lion-app-begbw.ondigitalocean.app",
        "https://api.lottokeralalotteries.com",
        "https://lottokeralalotteries.com",
        "https://www.lottokeralalotteries.com",  # Replace with your actual domain
    ]

# Initialize Firebase when Django starts
def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if firebase_admin._apps:
        return  # Already initialized
    
    try:
        firebase_creds = get_firebase_credentials()
        
        if firebase_creds is None:
            print("⚠️ Firebase not initialized - credentials missing")
            return
        
        if isinstance(firebase_creds, Path):
            # Using service account file (development)
            cred = credentials.Certificate(str(firebase_creds))
            print("🔥 Using Firebase service account file")
        else:
            # Using environment variables (production)
            cred = credentials.Certificate(firebase_creds)
            print("Using Firebase environment variables")
        
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
        
    except Exception as e:
        print(f"Firebase initialization failed: {e}")

# Initialize Firebase when settings load
initialize_firebase()