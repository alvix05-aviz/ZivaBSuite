from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-test-key-only-for-testing'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Base de datos en memoria para tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Password hashers más rápidos para tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Cache simple para tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Desactivar migraciones para tests más rápidos
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Email backend para tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Logging mínimo para tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Media files para tests
MEDIA_ROOT = BASE_DIR / 'test_media'

# Deshabilitar throttling en tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Configuración específica para tests
AUDIT_SETTINGS.update({
    'TRACK_CHANGES': False,  # No trackear cambios en tests
    'LOG_IP_ADDRESS': False,
})

# Tests específicos
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Deshabilitar validaciones de password para tests
AUTH_PASSWORD_VALIDATORS = []