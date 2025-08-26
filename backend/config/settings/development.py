from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dev-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']

# Database para desarrollo
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ziva_contabilidad'),
        'USER': os.environ.get('DB_USER', 'ziva_user'),  # Corregido a ziva_user
        'PASSWORD': os.environ.get('DB_PASSWORD', 'ziva_password123'),  # Corregido a ziva_password123
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# CORS settings para desarrollo
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# Configuración adicional para desarrollo
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug Toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

# Configuración de email para desarrollo (consola)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging más detallado en desarrollo
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG'

# Cache simple para desarrollo
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Deshabilitar algunas validaciones para desarrollo
AUTH_PASSWORD_VALIDATORS = []

# Configuración de archivos estáticos para desarrollo
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Configuración específica para desarrollo
AUDIT_SETTINGS.update({
    'LOG_IP_ADDRESS': False,  # No logear IP en desarrollo
})