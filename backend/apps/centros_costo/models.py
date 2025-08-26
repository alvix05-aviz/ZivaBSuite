from django.db import models
from apps.core.models import BaseModel
from apps.empresas.models import Empresa


class TipoCentroCosto(BaseModel):
    """Tipos configurables para centros de costo"""
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='tipos_centro_costo',
        verbose_name='Empresa'
    )
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código único del tipo'
    )
    nombre = models.CharField(
        max_length=50,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    color_interfaz = models.CharField(
        max_length=20,
        choices=[
            ('blue', 'Azul'),
            ('green', 'Verde'),
            ('yellow', 'Amarillo'),
            ('red', 'Rojo'),
            ('purple', 'Morado'),
            ('indigo', 'Índigo'),
            ('gray', 'Gris')
        ],
        default='blue',
        verbose_name='Color'
    )
    orden = models.PositiveIntegerField(
        default=0,
        verbose_name='Orden'
    )
    
    class Meta:
        verbose_name = 'Tipo de Centro'
        verbose_name_plural = 'Tipos de Centro'
        unique_together = [['empresa', 'codigo']]
        ordering = ['orden', 'codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

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
    
    # Clasificación - Campo actualizado según estructura real de BD
    tipo = models.ForeignKey(
        TipoCentroCosto,
        on_delete=models.PROTECT,
        related_name='centros',
        verbose_name='Tipo',
        help_text='Tipo de centro de costo'
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
