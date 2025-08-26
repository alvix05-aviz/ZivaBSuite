# Etapa 2: Gestión de Usuarios y Empresas

## 📋 Objetivo
Implementar sistema completo de gestión multiempresa con control de accesos y permisos granulares.

## 🎯 Alcance
- Modelo Usuario-Empresa para acceso multiempresa
- Sistema de roles y permisos
- Gestión de sesiones por empresa
- API de autenticación mejorada

## 🔧 Tareas de Implementación

### 2.1 Modelo Empresa Mejorado
**Archivo:** `backend/apps/empresas/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel
from django.core.validators import RegexValidator

User = get_user_model()

class Empresa(BaseModel):
    """
    Modelo de Empresa con campos fiscales completos
    MEJORA: Añade más campos fiscales y de configuración
    """
    # Información básica
    nombre = models.CharField(
        max_length=200,
        verbose_name='Razón Social'
    )
    nombre_comercial = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nombre Comercial'
    )
    rfc = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$',
                message='RFC inválido'
            )
        ],
        verbose_name='RFC'
    )
    
    # Información fiscal
    regimen_fiscal = models.CharField(
        max_length=3,
        choices=[
            ('601', 'General de Ley Personas Morales'),
            ('603', 'Personas Morales con Fines no Lucrativos'),
            ('605', 'Sueldos y Salarios'),
            ('606', 'Arrendamiento'),
            ('607', 'Régimen de Enajenación o Adquisición'),
            ('608', 'Demás ingresos'),
            ('610', 'Residentes en el Extranjero'),
            ('611', 'Ingresos por Dividendos'),
            ('612', 'Personas Físicas con Actividades Empresariales'),
            ('614', 'Ingresos por intereses'),
            ('615', 'Régimen de los ingresos por obtención de premios'),
            ('616', 'Sin obligaciones fiscales'),
            ('620', 'Sociedades Cooperativas de Producción'),
            ('621', 'Incorporación Fiscal'),
            ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
            ('623', 'Opcional para Grupos de Sociedades'),
            ('624', 'Coordinados'),
            ('625', 'Régimen de Actividades Empresariales con ingresos a través de Plataformas'),
            ('626', 'Régimen Simplificado de Confianza'),
        ],
        verbose_name='Régimen Fiscal'
    )
    
    # Certificados SAT
    certificado_sello = models.FileField(
        upload_to='certificados/',
        blank=True,
        null=True,
        verbose_name='Certificado de Sello Digital (.cer)'
    )
    llave_privada = models.FileField(
        upload_to='certificados/',
        blank=True,
        null=True,
        verbose_name='Llave Privada (.key)'
    )
    contrasena_llave = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Contraseña de Llave Privada'
    )
    
    # Dirección
    calle = models.CharField(max_length=200, blank=True)
    numero_exterior = models.CharField(max_length=20, blank=True)
    numero_interior = models.CharField(max_length=20, blank=True)
    colonia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=5, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, default='México')
    
    # Configuración contable
    ejercicio_fiscal_actual = models.IntegerField(
        verbose_name='Ejercicio Fiscal Actual'
    )
    periodo_actual = models.IntegerField(
        verbose_name='Periodo Contable Actual',
        help_text='Mes actual (1-12)'
    )
    moneda_base = models.CharField(
        max_length=3,
        default='MXN',
        choices=[
            ('MXN', 'Peso Mexicano'),
            ('USD', 'Dólar Americano'),
            ('EUR', 'Euro'),
        ]
    )
    
    # Configuración del sistema
    logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True
    )
    timezone = models.CharField(
        max_length=50,
        default='America/Mexico_City'
    )
    plan = models.CharField(
        max_length=20,
        choices=[
            ('BASICO', 'Básico'),
            ('PROFESIONAL', 'Profesional'),
            ('EMPRESARIAL', 'Empresarial'),
        ],
        default='BASICO'
    )
    limite_usuarios = models.IntegerField(default=5)
    limite_transacciones_mes = models.IntegerField(default=1000)
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']
        
    def __str__(self):
        return f"{self.nombre} ({self.rfc})"
    
    def get_direccion_completa(self):
        """Retorna dirección formateada"""
        partes = [
            self.calle,
            f"#{self.numero_exterior}" if self.numero_exterior else "",
            f"Int. {self.numero_interior}" if self.numero_interior else "",
            self.colonia,
            f"C.P. {self.codigo_postal}" if self.codigo_postal else "",
            self.municipio,
            self.estado,
            self.pais
        ]
        return ", ".join(filter(None, partes))
```

### 2.2 Modelo Usuario-Empresa (NUEVO - No existía en ejemplo_basico)
**Archivo:** `backend/apps/empresas/models.py` (continuación)

```python
class UsuarioEmpresa(BaseModel):
    """
    Relación Usuario-Empresa con roles y permisos
    NUEVO: Permite acceso multiempresa con diferentes roles
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='empresas_asignadas'
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios_asignados'
    )
    rol = models.CharField(
        max_length=20,
        choices=[
            ('PROPIETARIO', 'Propietario'),
            ('ADMINISTRADOR', 'Administrador'),
            ('CONTADOR', 'Contador'),
            ('AUXILIAR', 'Auxiliar Contable'),
            ('AUDITOR', 'Auditor'),
            ('CONSULTA', 'Solo Consulta'),
        ],
        default='CONSULTA'
    )
    
    # Permisos específicos (sobrescriben rol si están definidos)
    permisos = models.JSONField(
        default=dict,
        blank=True,
        help_text='Permisos específicos en formato JSON'
    )
    
    # Control de acceso
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de inicio de acceso'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de fin de acceso'
    )
    empresa_default = models.BooleanField(
        default=False,
        verbose_name='Empresa por defecto al iniciar sesión'
    )
    ultimo_acceso = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último acceso'
    )
    
    # Notificaciones
    notificaciones_email = models.BooleanField(
        default=True,
        verbose_name='Recibir notificaciones por email'
    )
    notificaciones_sistema = models.BooleanField(
        default=True,
        verbose_name='Recibir notificaciones del sistema'
    )
    
    class Meta:
        unique_together = ['usuario', 'empresa']
        verbose_name = 'Usuario-Empresa'
        verbose_name_plural = 'Usuarios-Empresas'
        ordering = ['empresa', 'usuario']
        
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nombre} ({self.rol})"
    
    def tiene_permiso(self, permiso):
        """Verifica si el usuario tiene un permiso específico"""
        # Primero verificar permisos específicos
        if permiso in self.permisos:
            return self.permisos[permiso]
            
        # Luego verificar por rol
        permisos_por_rol = {
            'PROPIETARIO': ['*'],  # Todos los permisos
            'ADMINISTRADOR': [
                'ver_*', 'crear_*', 'editar_*', 'eliminar_*',
                'aprobar_polizas', 'cerrar_periodo'
            ],
            'CONTADOR': [
                'ver_*', 'crear_polizas', 'editar_polizas',
                'crear_cuentas', 'editar_cuentas', 'generar_reportes'
            ],
            'AUXILIAR': [
                'ver_*', 'crear_polizas', 'editar_polizas_propias'
            ],
            'AUDITOR': [
                'ver_*', 'generar_reportes', 'exportar_datos'
            ],
            'CONSULTA': [
                'ver_*'
            ]
        }
        
        rol_permisos = permisos_por_rol.get(self.rol, [])
        
        # Verificar si tiene el permiso o un wildcard que lo cubra
        for p in rol_permisos:
            if p == '*' or p == permiso:
                return True
            if p.endswith('*') and permiso.startswith(p[:-1]):
                return True
                
        return False
    
    def esta_activo(self):
        """Verifica si el acceso está vigente"""
        from datetime import date
        hoy = date.today()
        
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
            
        return self.activo
```

### 2.3 Perfil de Usuario Extendido
**Archivo:** `backend/apps/empresas/models.py` (continuación)

```python
class PerfilUsuario(models.Model):
    """
    Información adicional del usuario
    SUGERENCIA: Centralizar preferencias del usuario
    """
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    telefono = models.CharField(
        max_length=20,
        blank=True
    )
    celular = models.CharField(
        max_length=20,
        blank=True
    )
    foto = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True
    )
    
    # Preferencias de UI
    tema = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Claro'),
            ('dark', 'Oscuro'),
            ('auto', 'Automático'),
        ],
        default='light'
    )
    idioma = models.CharField(
        max_length=5,
        choices=[
            ('es', 'Español'),
            ('en', 'English'),
        ],
        default='es'
    )
    
    # Configuración de sesión
    duracion_sesion = models.IntegerField(
        default=30,
        help_text='Minutos de inactividad antes de cerrar sesión'
    )
    doble_factor = models.BooleanField(
        default=False,
        verbose_name='Autenticación de dos factores'
    )
    
    # Auditoría
    ultimo_cambio_password = models.DateTimeField(
        null=True,
        blank=True
    )
    intentos_fallidos = models.IntegerField(
        default=0
    )
    bloqueado = models.BooleanField(
        default=False
    )
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'
        
    def __str__(self):
        return f"Perfil de {self.usuario.username}"
```

### 2.4 Serializers y ViewSets
**Archivo:** `backend/apps/empresas/serializers.py`

```python
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Empresa, UsuarioEmpresa, PerfilUsuario

User = get_user_model()

class EmpresaSerializer(serializers.ModelSerializer):
    direccion_completa = serializers.ReadOnlyField(
        source='get_direccion_completa'
    )
    usuarios_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = '__all__'
        read_only_fields = ['creado_por', 'modificado_por']
        
    def get_usuarios_count(self, obj):
        return obj.usuarios_asignados.filter(activo=True).count()

class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.get_full_name')
    empresa_nombre = serializers.ReadOnlyField(source='empresa.nombre')
    permisos_efectivos = serializers.SerializerMethodField()
    
    class Meta:
        model = UsuarioEmpresa
        fields = '__all__'
        
    def get_permisos_efectivos(self, obj):
        """Lista todos los permisos efectivos del usuario"""
        permisos = []
        # Aquí implementar lógica de permisos según rol
        return permisos
        
    def validate(self, data):
        """Validaciones personalizadas"""
        # Verificar límite de usuarios por empresa
        if 'empresa' in data:
            empresa = data['empresa']
            usuarios_activos = UsuarioEmpresa.objects.filter(
                empresa=empresa,
                activo=True
            ).count()
            
            if usuarios_activos >= empresa.limite_usuarios:
                raise serializers.ValidationError(
                    f"La empresa ha alcanzado el límite de {empresa.limite_usuarios} usuarios"
                )
                
        return data

class UserSerializer(serializers.ModelSerializer):
    empresas = serializers.SerializerMethodField()
    perfil = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 
            'last_name', 'empresas', 'perfil'
        ]
        
    def get_empresas(self, obj):
        """Empresas a las que tiene acceso el usuario"""
        accesos = UsuarioEmpresa.objects.filter(
            usuario=obj,
            activo=True
        ).select_related('empresa')
        
        return [
            {
                'id': acceso.empresa.id,
                'nombre': acceso.empresa.nombre,
                'rfc': acceso.empresa.rfc,
                'rol': acceso.rol,
                'default': acceso.empresa_default
            }
            for acceso in accesos if acceso.esta_activo()
        ]
        
    def get_perfil(self, obj):
        """Información del perfil del usuario"""
        try:
            perfil = obj.perfil
            return {
                'tema': perfil.tema,
                'idioma': perfil.idioma,
                'foto': perfil.foto.url if perfil.foto else None
            }
        except PerfilUsuario.DoesNotExist:
            return None
```

### 2.5 Middleware de Contexto de Empresa
**Archivo:** `backend/apps/empresas/middleware.py`

```python
from django.utils.functional import SimpleLazyObject
from .models import UsuarioEmpresa

def get_empresa_actual(request):
    """Obtiene la empresa activa en la sesión"""
    if not hasattr(request, '_cached_empresa'):
        empresa_id = request.session.get('empresa_id')
        
        if empresa_id and request.user.is_authenticated:
            try:
                acceso = UsuarioEmpresa.objects.select_related('empresa').get(
                    usuario=request.user,
                    empresa_id=empresa_id,
                    activo=True
                )
                if acceso.esta_activo():
                    request._cached_empresa = acceso.empresa
                else:
                    request._cached_empresa = None
            except UsuarioEmpresa.DoesNotExist:
                request._cached_empresa = None
        else:
            request._cached_empresa = None
            
    return request._cached_empresa

class EmpresaMiddleware:
    """
    Middleware para manejar el contexto de empresa
    MEJORA: Gestión automática de empresa activa
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        request.empresa = SimpleLazyObject(lambda: get_empresa_actual(request))
        response = self.get_response(request)
        return response
```

### 2.6 Vistas de Autenticación Mejoradas
**Archivo:** `backend/apps/empresas/views.py`

```python
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from .models import UsuarioEmpresa, Empresa
from .serializers import UserSerializer, EmpresaSerializer

class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet para autenticación y gestión de sesión
    MEJORA: Incluye selección de empresa y validación de permisos
    """
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login con selección de empresa"""
        username = request.data.get('username')
        password = request.data.get('password')
        empresa_id = request.data.get('empresa_id')
        
        user = authenticate(username=username, password=password)
        
        if user:
            # Obtener empresas disponibles
            empresas_usuario = UsuarioEmpresa.objects.filter(
                usuario=user,
                activo=True
            ).select_related('empresa')
            
            empresas_activas = [
                ue for ue in empresas_usuario if ue.esta_activo()
            ]
            
            if not empresas_activas:
                return Response(
                    {'error': 'No tiene acceso a ninguna empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Si no especifica empresa, usar la default o la primera
            if not empresa_id:
                empresa_default = next(
                    (ue for ue in empresas_activas if ue.empresa_default),
                    empresas_activas[0]
                )
                empresa_id = empresa_default.empresa.id
            
            # Verificar acceso a la empresa especificada
            acceso = next(
                (ue for ue in empresas_activas if ue.empresa.id == empresa_id),
                None
            )
            
            if not acceso:
                return Response(
                    {'error': 'No tiene acceso a esta empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Login exitoso
            login(request, user)
            request.session['empresa_id'] = empresa_id
            
            # Actualizar último acceso
            acceso.ultimo_acceso = timezone.now()
            acceso.save(update_fields=['ultimo_acceso'])
            
            return Response({
                'user': UserSerializer(user).data,
                'empresa': EmpresaSerializer(acceso.empresa).data,
                'rol': acceso.rol,
                'token': generate_token(user)  # Implementar generación de token
            })
        else:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def cambiar_empresa(self, request):
        """Cambiar empresa activa en la sesión"""
        empresa_id = request.data.get('empresa_id')
        
        try:
            acceso = UsuarioEmpresa.objects.select_related('empresa').get(
                usuario=request.user,
                empresa_id=empresa_id,
                activo=True
            )
            
            if not acceso.esta_activo():
                return Response(
                    {'error': 'Acceso no vigente a esta empresa'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            request.session['empresa_id'] = empresa_id
            
            return Response({
                'empresa': EmpresaSerializer(acceso.empresa).data,
                'rol': acceso.rol
            })
            
        except UsuarioEmpresa.DoesNotExist:
            return Response(
                {'error': 'No tiene acceso a esta empresa'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Cerrar sesión"""
        logout(request)
        return Response({'message': 'Sesión cerrada'})
```

## �?Criterios de Aceptación

### Tests de Integración
```python
# backend/apps/empresas/tests/test_multiempresa.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa, UsuarioEmpresa

class MultiEmpresaTest(TestCase):
    def test_usuario_multiple_empresas(self):
        """Usuario puede acceder a múltiples empresas con diferentes roles"""
        user = get_user_model().objects.create_user(
            username='multi', password='test123'
        )
        
        empresa1 = Empresa.objects.create(
            nombre='Empresa 1',
            rfc='EMP000000001',
            creado_por=user
        )
        
        empresa2 = Empresa.objects.create(
            nombre='Empresa 2',
            rfc='EMP000000002',
            creado_por=user
        )
        
        # Asignar diferentes roles
        UsuarioEmpresa.objects.create(
            usuario=user,
            empresa=empresa1,
            rol='ADMINISTRADOR',
            creado_por=user
        )
        
        UsuarioEmpresa.objects.create(
            usuario=user,
            empresa=empresa2,
            rol='CONTADOR',
            creado_por=user
        )
        
        # Verificar accesos
        accesos = UsuarioEmpresa.objects.filter(usuario=user)
        self.assertEqual(accesos.count(), 2)
        self.assertTrue(accesos[0].tiene_permiso('crear_polizas'))
        self.assertTrue(accesos[1].tiene_permiso('crear_polizas'))
        self.assertFalse(accesos[1].tiene_permiso('cerrar_periodo'))
```

### Validación de Permisos
```bash
# Verificar middleware
python manage.py shell
>>> from django.test import RequestFactory
>>> from apps.empresas.middleware import EmpresaMiddleware
>>> # Test middleware functionality

# Verificar API
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123"}'
```

## 📊 Métricas de Éxito

- [ ] Sistema multiempresa funcionando
- [ ] Roles y permisos implementados
- [ ] Middleware de contexto activo
- [ ] API de autenticación completa
- [ ] Tests con cobertura > 80%

## 🔄 Siguiente Etapa
[Etapa 3: Catálogo de Cuentas Mejorado →](etapa_3_catalogo_mejorado.md)