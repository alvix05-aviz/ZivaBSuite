# CCYP-FASE1: Modelos y Base de Datos - Centros de Costo y Proyectos

## 🎯 **Objetivo de la Fase 1**
Crear la estructura de base de datos necesaria para soportar centros de costo y proyectos, incluyendo la integración con el sistema de movimientos contables existente.

## 📋 **Tareas de la Fase 1**

### ✅ **Completadas**
- [ ] Crear nueva app `centros_costo`
- [ ] Implementar modelo `CentroCosto`
- [ ] Implementar modelo `Proyecto`
- [ ] Modificar modelo `MovimientoContable`
- [ ] Crear migraciones correspondientes
- [ ] Aplicar migraciones en base de datos
- [ ] Configurar admin básico para modelos
- [ ] Pruebas unitarias básicas

### 🎯 **En Progreso**
- *Ninguna tarea en progreso actualmente*

### ⏳ **Pendientes**
- [ ] Todas las tareas listadas arriba

## 🏗️ **Detalles de Implementación**

### **1.1 Crear nueva app `centros_costo`**
```bash
cd D:\ZivaBSuite\backend
python manage.py startapp centros_costo
```

**Archivos a crear:**
- `apps/centros_costo/__init__.py`
- `apps/centros_costo/apps.py`
- `apps/centros_costo/models.py`
- `apps/centros_costo/admin.py`
- `apps/centros_costo/views.py`
- `apps/centros_costo/urls.py`
- `apps/centros_costo/serializers.py`

### **1.2 Modelo CentroCosto**
```python
# apps/centros_costo/models.py
from django.db import models
from apps.core.models import BaseModel
from apps.empresas.models import Empresa

class CentroCosto(BaseModel):
    """
    Centros de costo para clasificación de gastos e ingresos
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='centros_costo',
        verbose_name='Empresa'
    )
    
    # Información básica
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código único del centro de costo'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # Clasificación
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('DEPARTAMENTO', 'Departamento'),
            ('SUCURSAL', 'Sucursal'),
            ('ACTIVIDAD', 'Actividad'),
            ('PRODUCTO', 'Producto'),
            ('SERVICIO', 'Servicio'),
            ('OTRO', 'Otro')
        ],
        default='DEPARTAMENTO',
        verbose_name='Tipo'
    )
    
    # Estructura jerárquica
    centro_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcentros',
        verbose_name='Centro Padre'
    )
    
    # Configuración
    permite_movimientos = models.BooleanField(
        default=True,
        verbose_name='Permite movimientos',
        help_text='Si permite asignar movimientos contables directamente'
    )
    color_interfaz = models.CharField(
        max_length=20,
        default='blue',
        choices=[
            ('blue', 'Azul'),
            ('green', 'Verde'),
            ('purple', 'Morado'),
            ('red', 'Rojo'),
            ('yellow', 'Amarillo'),
            ('indigo', 'Índigo'),
            ('pink', 'Rosa'),
            ('gray', 'Gris'),
        ],
        verbose_name='Color en interfaz'
    )
    
    class Meta:
        unique_together = ['empresa', 'codigo']
        verbose_name = 'Centro de Costo'
        verbose_name_plural = 'Centros de Costo'
        ordering = ['codigo']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
        
    def get_ruta_completa(self):
        """Devuelve la ruta completa del centro de costo"""
        if self.centro_padre:
            return f"{self.centro_padre.get_ruta_completa()} > {self.nombre}"
        return self.nombre
        
    def get_subcentros_ids(self):
        """Devuelve IDs de todos los subcentros recursivamente"""
        ids = [self.id]
        for subcentro in self.subcentros.filter(activo=True):
            ids.extend(subcentro.get_subcentros_ids())
        return ids
```

### **1.3 Modelo Proyecto**
```python
class Proyecto(BaseModel):
    """
    Proyectos específicos para seguimiento de costos e ingresos
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='proyectos',
        verbose_name='Empresa'
    )
    
    # Información básica
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código único del proyecto'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # Fechas
    fecha_inicio = models.DateField(
        verbose_name='Fecha de inicio'
    )
    fecha_fin_estimada = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha fin estimada'
    )
    fecha_fin_real = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha fin real'
    )
    
    # Estado del proyecto
    estado = models.CharField(
        max_length=20,
        choices=[
            ('PLANIFICACION', 'En Planificación'),
            ('ACTIVO', 'Activo'),
            ('SUSPENDIDO', 'Suspendido'),
            ('TERMINADO', 'Terminado'),
            ('CANCELADO', 'Cancelado')
        ],
        default='PLANIFICACION',
        verbose_name='Estado'
    )
    
    # Presupuesto
    presupuesto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Presupuesto'
    )
    
    # Relaciones
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos',
        verbose_name='Centro de Costo'
    )
    responsable = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_responsable',
        verbose_name='Responsable'
    )
    
    # Configuración
    color_interfaz = models.CharField(
        max_length=20,
        default='green',
        choices=[
            ('blue', 'Azul'),
            ('green', 'Verde'),
            ('purple', 'Morado'),
            ('red', 'Rojo'),
            ('yellow', 'Amarillo'),
            ('indigo', 'Índigo'),
            ('pink', 'Rosa'),
            ('gray', 'Gris'),
        ],
        verbose_name='Color en interfaz'
    )
    
    class Meta:
        unique_together = ['empresa', 'codigo']
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-fecha_inicio']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
        
    @property
    def dias_transcurridos(self):
        """Días transcurridos desde el inicio"""
        from datetime import date
        return (date.today() - self.fecha_inicio).days
        
    @property
    def progreso_tiempo(self):
        """Porcentaje de progreso basado en tiempo"""
        if not self.fecha_fin_estimada:
            return None
        
        from datetime import date
        total_dias = (self.fecha_fin_estimada - self.fecha_inicio).days
        dias_transcurridos = (date.today() - self.fecha_inicio).days
        
        if total_dias <= 0:
            return 100
        
        progreso = (dias_transcurridos / total_dias) * 100
        return min(100, max(0, progreso))
```

### **1.4 Modificar MovimientoContable**
```python
# Agregar a apps/transacciones/models.py en MovimientoContable:

# Agregar imports:
# (Se agregarán al principio del archivo)

# Agregar campos al modelo MovimientoContable:
    centro_costo = models.ForeignKey(
        'centros_costo.CentroCosto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos',
        verbose_name='Centro de Costo'
    )
    proyecto = models.ForeignKey(
        'centros_costo.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos',
        verbose_name='Proyecto'
    )

# Agregar al método clean():
    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Verificar que la cuenta pertenezca a la misma empresa
        if self.cuenta and self.transaccion:
            if self.cuenta.empresa != self.transaccion.empresa:
                raise ValidationError('La cuenta debe pertenecer a la misma empresa que la transacción')
        
        # Validar centro de costo
        if self.centro_costo and self.transaccion:
            if self.centro_costo.empresa != self.transaccion.empresa:
                raise ValidationError('El centro de costo debe pertenecer a la misma empresa')
            if not self.centro_costo.permite_movimientos:
                raise ValidationError('El centro de costo seleccionado no permite movimientos directos')
        
        # Validar proyecto
        if self.proyecto and self.transaccion:
            if self.proyecto.empresa != self.transaccion.empresa:
                raise ValidationError('El proyecto debe pertenecer a la misma empresa')
            if self.proyecto.estado not in ['ACTIVO', 'PLANIFICACION']:
                raise ValidationError('Solo se pueden asignar movimientos a proyectos activos o en planificación')

# Agregar al método __str__:
    def __str__(self):
        importe = self.debe if self.debe > 0 else self.haber
        tipo = 'DEBE' if self.debe > 0 else 'HABER'
        extras = []
        if self.centro_costo:
            extras.append(f"CC: {self.centro_costo.codigo}")
        if self.proyecto:
            extras.append(f"PY: {self.proyecto.codigo}")
        
        base_str = f"{self.cuenta.codigo} - ${importe} ({tipo})"
        if extras:
            base_str += f" [{', '.join(extras)}]"
        
        return base_str
```

### **1.5 Configuración de Admin**
```python
# apps/centros_costo/admin.py
from django.contrib import admin
from .models import CentroCosto, Proyecto

@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'centro_padre', 'empresa', 'activo']
    list_filter = ['tipo', 'empresa', 'activo']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['empresa', 'codigo']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'codigo', 'nombre', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('tipo', 'centro_padre')
        }),
        ('Configuración', {
            'fields': ('permite_movimientos', 'color_interfaz', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por'),
            'classes': ('collapse',)
        })
    )

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'estado', 'fecha_inicio', 'fecha_fin_estimada', 'presupuesto', 'empresa']
    list_filter = ['estado', 'empresa', 'fecha_inicio']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['empresa', '-fecha_inicio']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'codigo', 'nombre', 'descripcion')
        }),
        ('Planificación', {
            'fields': ('fecha_inicio', 'fecha_fin_estimada', 'fecha_fin_real', 'estado')
        }),
        ('Presupuesto y Asignación', {
            'fields': ('presupuesto', 'centro_costo', 'responsable')
        }),
        ('Configuración', {
            'fields': ('color_interfaz', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por'),
            'classes': ('collapse',)
        })
    )
```

### **1.6 Configuración de la App**
```python
# apps/centros_costo/apps.py
from django.apps import AppConfig

class CentrosCostoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.centros_costo'
    verbose_name = 'Centros de Costo y Proyectos'
```

```python
# Agregar a INSTALLED_APPS en settings/base.py:
INSTALLED_APPS = [
    # ... otras apps
    'apps.centros_costo',
]
```

## 🧪 **Comandos de Migración**

```bash
# Crear migraciones
python manage.py makemigrations centros_costo
python manage.py makemigrations transacciones

# Aplicar migraciones
python manage.py migrate centros_costo
python manage.py migrate transacciones
```

## ✅ **Criterios de Aceptación**

- [ ] Los modelos CentroCosto y Proyecto se crean correctamente
- [ ] Se pueden crear centros de costo jerárquicos (padre-hijo)
- [ ] Los proyectos se asocian correctamente con centros de costo
- [ ] MovimientoContable acepta asignaciones de centro y proyecto
- [ ] Las validaciones de negocio funcionan correctamente
- [ ] El admin de Django permite gestionar los nuevos modelos
- [ ] Las migraciones se aplican sin errores
- [ ] Los campos son opcionales (null=True) para compatibilidad

## 📝 **Notas de Implementación**

### **Consideraciones Importantes:**
1. **Compatibilidad**: Los campos en MovimientoContable son opcionales para no romper transacciones existentes
2. **Jerarquía**: Los centros de costo soportan estructura padre-hijo ilimitada
3. **Validaciones**: Se valida que centro/proyecto pertenezcan a la misma empresa
4. **Estados**: Los proyectos tienen estados que afectan si pueden recibir movimientos
5. **Colores**: Ambos modelos tienen colores para diferenciación visual en la UI

### **Para Próxima Fase:**
- La Fase 2 se enfocará en crear las vistas de gestión (CRUD)
- Se necesitará actualizar el formulario de transacciones
- Se crearán los serializers para la API REST

## 📊 **Métricas de Éxito**
- ✅ Migraciones aplicadas sin errores
- ✅ Modelos funcionales en admin de Django  
- ✅ Relaciones correctas entre todos los modelos
- ✅ Validaciones funcionando correctamente