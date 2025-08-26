# Etapa 1: Infraestructura Base y Modelos Fundamentales

## 📋 Objetivo
Establecer la arquitectura base del sistema

## 🎯 Alcance
- Crear estructura modular de aplicaciones Django
- Implementar modelo base con auditoría completa
- Configurar entorno de desarrollo con Docker
- Establecer configuración centralizada

## 📁 Estructura de Directorios

```
ZivaBSuite/
├── backend/                     # Backend Django
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── core/                # ✅ App base del sistema
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # BaseModel y Configuracion
│   │   │   ├── utils.py         # Utilidades compartidas
│   │   │   ├── validators.py    # Validadores comunes
│   │   │   └── migrations/
│   │   ├── empresas/            # ✅ Modelo básico de Empresa
│   │   ├── catalogo_cuentas/    # 🟡 Placeholder para Etapa 3
│   │   ├── transacciones/       # 🟡 Placeholder para Etapa 4
│   │   └── reportes/            # 🟡 Placeholder para Etapa 5
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py          # Configuración base
│   │   │   ├── development.py   # Desarrollo
│   │   │   ├── production.py    # Producción
│   │   │   └── testing.py       # Pruebas
│   │   ├── urls.py              # URLs principales
│   │   ├── wsgi.py              # WSGI config
│   │   └── asgi.py              # ASGI config
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   └── production.txt
│   └── docker/
│       ├── Dockerfile           # Producción
│       ├── Dockerfile.dev       # Desarrollo
│       ├── entrypoint.sh        # Script de inicio
│       └── init.sql             # Inicialización DB
├── docker-compose.etapa1.yml    # ✅ Solo backend (Etapa 1)
├── docker-compose.yml           # 🟡 Backend + Frontend (etapas futuras)
├── docker-compose.prod.yml      # 🟡 Producción completa
├── .env                         # Variables de entorno
├── .env.example                 # Ejemplo de configuración
├── setup.bat                    # Script instalación Windows
└── README.md                    # Documentación principal
```

## 🔧 Tareas de Implementación

### 1.1 Crear App Core con BaseModel
**Archivo:** `backend/apps/core/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class BaseModel(models.Model):
    """
    Modelo base con campos de auditoría para todas las entidades
    MEJORA: Incluye soft delete y tracking de cambios
    """
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='%(class)s_creados',
        verbose_name='Creado por'
    )
    modificado_por = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='%(class)s_modificados',
        verbose_name='Modificado por',
        null=True,
        blank=True
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Soft delete: False indica registro eliminado'
    )
    version = models.IntegerField(
        default=1,
        verbose_name='Versión del registro'
    )
    
    class Meta:
        abstract = True
        ordering = ['-fecha_creacion']
        
    def save(self, *args, **kwargs):
        """Override para incrementar versión en actualizaciones"""
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        """Soft delete por defecto"""
        self.activo = False
        self.save()
        
    def hard_delete(self):
        """Eliminación física cuando sea necesaria"""
        super(BaseModel, self).delete()
```

### 1.2 Modelo de Configuración Centralizada
**Archivo:** `backend/apps/core/models.py` (continuación)

```python
class Configuracion(BaseModel):
    """
    Almacena configuraciones del sistema por empresa
    NUEVO: No existía en ejemplo_basico
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='configuraciones'
    )
    clave = models.CharField(
        max_length=100,
        verbose_name='Clave de configuración'
    )
    valor = models.JSONField(
        verbose_name='Valor de configuración'
    )
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('SISTEMA', 'Sistema'),
            ('CONTABILIDAD', 'Contabilidad'),
            ('FISCAL', 'Fiscal'),
            ('REPORTES', 'Reportes'),
        ],
        default='SISTEMA'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    class Meta:
        unique_together = ['empresa', 'clave']
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuraciones'
        
    def __str__(self):
        return f"{self.empresa.nombre} - {self.clave}"
```

### 1.3 Utilidades Compartidas
**Archivo:** `backend/apps/core/utils.py`

```python
import decimal
from datetime import datetime
from django.db import transaction

def validar_cuadratura(debe_total, haber_total, tolerancia=0.01):
    """
    Valida que una transacción contable esté cuadrada
    MEJORA: Tolerancia configurable para redondeos
    """
    diferencia = abs(debe_total - haber_total)
    return diferencia <= tolerancia

def generar_folio(prefijo, empresa_id, modelo):
    """
    Genera folios consecutivos por empresa
    NUEVO: Sistema de foliación automática
    """
    with transaction.atomic():
        ultimo = modelo.objects.filter(
            empresa_id=empresa_id,
            folio__startswith=prefijo
        ).order_by('-folio').first()
        
        if ultimo:
            numero = int(ultimo.folio.replace(prefijo, '')) + 1
        else:
            numero = 1
            
        return f"{prefijo}{numero:06d}"

class AuditMixin:
    """
    Mixin para tracking detallado de cambios
    SUGERENCIA: Implementar log de cambios completo
    """
    def log_cambio(self, campo, valor_anterior, valor_nuevo, usuario):
        from apps.core.models import LogCambio
        LogCambio.objects.create(
            modelo=self.__class__.__name__,
            registro_id=self.pk,
            campo=campo,
            valor_anterior=str(valor_anterior),
            valor_nuevo=str(valor_nuevo),
            usuario=usuario
        )
```

### 1.4 Configuración de Settings Modular
**Archivo:** `backend/config/settings/base.py`

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Apps organizadas por módulos
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.core',
    'apps.empresas',
    'apps.catalogo_cuentas',
    'apps.transacciones',  # Renombrado de 'polizas'
    'apps.reportes',       # NUEVO
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Configuración REST Framework mejorada
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Configuración de auditoría
AUDIT_SETTINGS = {
    'TRACK_CHANGES': True,
    'SOFT_DELETE': True,
    'VERSION_CONTROL': True,
}
```

### 1.5 Docker Compose para Etapa 1 (Solo Backend)
**Archivo:** `docker-compose.etapa1.yml`

```yaml
version: '3.8'

services:
  db:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: ziva_contabilidad
      POSTGRES_USER: ziva_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-ziva_password123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ziva_user"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ziva-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - ziva-network

  backend:
    build:
      context: ./backend
      dockerfile: docker/Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://ziva_user:${DB_PASSWORD:-ziva_password123}@db:5432/ziva_contabilidad
      - DJANGO_SETTINGS_MODULE=config.settings.development
      - PYTHONUNBUFFERED=1
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=ziva_contabilidad
      - DB_USER=ziva_user
      - DB_PASSWORD=${DB_PASSWORD:-ziva_password123}
      - REDIS_URL=redis://redis:6379/1
    networks:
      - ziva-network

volumes:
  postgres_data:
  redis_data:

networks:
  ziva-network:
    driver: bridge
```

**Nota:** El frontend se implementará en etapas posteriores. Por ahora, solo trabajamos con backend, base de datos y Redis.

## ✅ Criterios de Aceptación

### Instalación y Configuración
```bash
# Instalación automática (recomendada)
setup.bat

# O instalación manual:
docker-compose -f docker-compose.etapa1.yml up --build
```

### Verificación de Servicios
```bash
# Verificar que todos los servicios estén corriendo
docker-compose -f docker-compose.etapa1.yml ps

# Resultado esperado:
# backend-1  ✅ Up (puerto 8000)
# db-1       ✅ Up healthy (puerto 5432) 
# redis-1    ✅ Up (puerto 6379)
```

### Verificación de APIs
```bash
# API Root (público)
curl http://localhost:8000/api/
# Debe retornar JSON con endpoints disponibles

# Admin Django (redirección al login)
curl -I http://localhost:8000/admin/
# Debe retornar 302 Found
```

### Aplicación de Migraciones
```bash
# Crear migraciones
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py makemigrations core empresas

# Aplicar migraciones  
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py migrate
```

### Tests Unitarios
```bash
# Ejecutar todos los tests
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test apps.core.tests

# Ejecutar tests específicos
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test apps.core.tests.test_models
```

### Verificación del Admin
1. Ir a: http://localhost:8000/admin/
2. Login con: `admin` / `admin123`  
3. Verificar que se puede acceder sin errores

## 🚨 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Migración de datos existentes | Alta | Alto | Script de migración incremental |
| Conflictos con código legacy | Media | Medio | Mantener compatibilidad temporal |
| Performance con soft delete | Baja | Medio | Índices en campo 'activo' |

## 📊 Métricas de Éxito Alcanzadas

- [x] ✅ 100% de modelos heredan de BaseModel (BaseModel, Configuracion, LogCambio, Empresa)
- [x] ✅ Configuración modular funcionando (4 archivos de settings)
- [x] ✅ Docker compose sin errores (`docker-compose.etapa1.yml`)
- [x] ✅ Tests implementados y funcionando
- [x] ✅ Servicios operativos (Backend + DB + Redis)
- [x] ✅ Admin Django accesible (http://localhost:8000/admin/)
- [x] ✅ API REST respondiendo (http://localhost:8000/api/)

## 🎯 URLs Operativas

### Servicios Principales
- **Backend Django**: http://localhost:8000/
- **Admin Interface**: http://localhost:8000/admin/ (admin/admin123)  
- **API Root**: http://localhost:8000/api/ (público)
- **API Endpoints**: http://localhost:8000/api/{core,empresas,catalogo,transacciones,reportes}/

### Base de Datos y Cache
- **PostgreSQL**: localhost:5432 (ziva_user/ziva_password123)
- **Redis**: localhost:6379

## 🚨 Problemas Resueltos en Esta Etapa

1. **✅ Error Frontend No Encontrado**
   - Solución: Creado `docker-compose.etapa1.yml` específico para backend
   
2. **✅ Error Requirements Missing** 
   - Solución: Corregido Dockerfile.dev para copiar todas las dependencias
   
3. **✅ Error Middleware No Encontrado**
   - Solución: Comentado middleware de empresas (se implementará en Etapa 2)
   
4. **✅ Error 404 en /api/**
   - Solución: Agregada vista API root con endpoints disponibles

5. **✅ ERR_CONNECTION_REFUSED**
   - Solución: Todos los servicios funcionando correctamente

## 🔄 Siguiente Etapa
**Estado**: ✅ Etapa 1 completamente funcional y lista para usar

[Etapa 2: Gestión de Usuarios y Empresas →](etapa_2_usuarios_empresas.md)

### Comandos Rápidos para Continuar
```bash
# Verificar estado actual
docker-compose -f docker-compose.etapa1.yml ps

# Acceder al admin  
http://localhost:8000/admin/

# Ver API disponible
curl http://localhost:8000/api/
```