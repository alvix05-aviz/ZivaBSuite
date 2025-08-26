from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel
from apps.empresas.models import Empresa
from apps.catalogo_cuentas.models import CuentaContable


class TipoTransaccion(BaseModel):
    """Tipos de transacción personalizables por empresa"""
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='tipos_transaccion'
    )
    
    # Información básica
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código único del tipo de transacción'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # Configuración de numeración
    prefijo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Prefijo',
        help_text='Ej: ING-, EGR-, DIA-'
    )
    sufijo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Sufijo'
    )
    longitud_numero = models.IntegerField(
        default=4,
        verbose_name='Longitud del número',
        help_text='Número de dígitos para la numeración automática'
    )
    ultimo_folio = models.IntegerField(
        default=0,
        verbose_name='Último folio utilizado'
    )
    
    # Configuración funcional
    requiere_validacion = models.BooleanField(
        default=True,
        verbose_name='Requiere validación',
        help_text='Si requiere validación antes de contabilizar'
    )
    permite_edicion = models.BooleanField(
        default=True,
        verbose_name='Permite edición',
        help_text='Si permite editar después de crear'
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
        verbose_name = 'Tipo de Transacción'
        verbose_name_plural = 'Tipos de Transacción'
        ordering = ['codigo']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
        
    def generar_folio(self):
        """Genera el siguiente folio para este tipo"""
        self.ultimo_folio += 1
        numero = str(self.ultimo_folio).zfill(self.longitud_numero)
        folio = f"{self.prefijo}{numero}{self.sufijo}"
        self.save(update_fields=['ultimo_folio'])
        return folio


class TransaccionContable(BaseModel):
    """Transacción contable MVP - Equivale a una Póliza"""
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('VALIDADA', 'Validada'),
        ('CONTABILIZADA', 'Contabilizada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
        ('DIARIO', 'Diario'),
        ('AJUSTE', 'Ajuste'),
    ]
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='transacciones'
    )
    
    # Identificación
    folio = models.CharField(
        max_length=20,
        verbose_name='Folio',
        help_text='Número de póliza o transacción'
    )
    fecha = models.DateField(
        default=timezone.now,
        verbose_name='Fecha'
    )
    
    # Clasificación
    tipo = models.CharField(
        max_length=15,
        choices=TIPO_CHOICES,
        default='DIARIO',
        verbose_name='Tipo'
    )
    tipo_personalizado = models.ForeignKey(
        TipoTransaccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacciones',
        verbose_name='Tipo Personalizado',
        help_text='Tipo de transacción personalizado (opcional)'
    )
    concepto = models.CharField(
        max_length=500,
        verbose_name='Concepto',
        help_text='Descripción de la transacción'
    )
    
    # Estado y control
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='BORRADOR',
        verbose_name='Estado'
    )
    fecha_contabilizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Contabilización'
    )
    
    # Totales (se calculan automáticamente)
    total_debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Debe'
    )
    total_haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Haber'
    )
    
    class Meta:
        unique_together = ['empresa', 'folio']
        verbose_name = 'Transacción Contable'
        verbose_name_plural = 'Transacciones Contables'
        ordering = ['-fecha', '-folio']
        
    def __str__(self):
        return f"{self.folio} - {self.concepto[:50]}"
        
    def clean(self):
        """Validaciones del modelo"""
        # Solo permitir cancelación si está contabilizada
        if self.estado == 'CANCELADA':
            if self.pk:  # Si ya existe
                old_instance = TransaccionContable.objects.defer('tipo_personalizado').get(pk=self.pk)
                if old_instance.estado != 'CONTABILIZADA':
                    raise ValidationError('Solo se pueden cancelar transacciones contabilizadas')
                    
    def calcular_totales(self):
        """Calcula y actualiza los totales debe/haber"""
        movimientos = self.movimientos.all()
        self.total_debe = sum(m.debe for m in movimientos)
        self.total_haber = sum(m.haber for m in movimientos)
        self.save(update_fields=['total_debe', 'total_haber'])
        
    def esta_balanceada(self):
        """Verifica si la transacción está balanceada (debe = haber)"""
        return self.total_debe == self.total_haber
        
    def validar(self):
        """Valida la transacción"""
        if self.estado != 'BORRADOR':
            raise ValidationError('Solo se pueden validar transacciones en borrador')
            
        self.calcular_totales()
        
        if not self.esta_balanceada():
            raise ValidationError(f'La transacción no está balanceada. Debe: {self.total_debe}, Haber: {self.total_haber}')
            
        if self.movimientos.count() < 2:
            raise ValidationError('Una transacción debe tener al menos 2 movimientos')
            
        self.estado = 'VALIDADA'
        self.save(update_fields=['estado'])
        
    def contabilizar(self):
        """Contabiliza la transacción"""
        if self.estado != 'VALIDADA':
            raise ValidationError('Solo se pueden contabilizar transacciones validadas')
            
        self.estado = 'CONTABILIZADA'
        self.fecha_contabilizacion = timezone.now()
        self.save(update_fields=['estado', 'fecha_contabilizacion'])
        
    def cancelar(self):
        """Cancela la transacción"""
        if self.estado != 'CONTABILIZADA':
            raise ValidationError('Solo se pueden cancelar transacciones contabilizadas')
            
        self.estado = 'CANCELADA'
        self.save(update_fields=['estado'])


class MovimientoContable(BaseModel):
    """Movimiento contable individual - Asientos debe/haber"""
    
    transaccion = models.ForeignKey(
        TransaccionContable,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    cuenta = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name='movimientos',
        verbose_name='Cuenta Contable'
    )
    
    # Descripción del movimiento
    concepto = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Concepto',
        help_text='Concepto específico del movimiento (opcional)'
    )
    
    # Importes
    debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Debe'
    )
    haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Haber'
    )
    
    # Relaciones con Centros de Costo y Proyectos
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
    
    class Meta:
        verbose_name = 'Movimiento Contable'
        verbose_name_plural = 'Movimientos Contables'
        ordering = ['id']
        
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
            base_str += f" [{' - '.join(extras)}]"
        
        return base_str
        
    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Verificar que la cuenta pertenezca a la misma empresa
        if self.cuenta and self.transaccion:
            if self.cuenta.empresa != self.transaccion.empresa:
                raise ValidationError('La cuenta debe pertenecer a la misma empresa que la transacción')
                
        # Verificar que solo uno de debe/haber tenga valor
        if self.debe > 0 and self.haber > 0:
            raise ValidationError('Un movimiento no puede tener tanto debe como haber')
            
        if self.debe == 0 and self.haber == 0:
            raise ValidationError('Un movimiento debe tener importe en debe o haber')
            
        # Verificar que la cuenta sea afectable
        if self.cuenta and not self.cuenta.afectable:
            raise ValidationError(f'La cuenta {self.cuenta.codigo} - {self.cuenta.nombre} no es afectable')
            
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
            
    def save(self, *args, **kwargs):
        """Guardar y recalcular totales de la transacción"""
        super().save(*args, **kwargs)
        # Recalcular totales de la transacción padre
        self.transaccion.calcular_totales()
        
    def delete(self, *args, **kwargs):
        """Eliminar y recalcular totales de la transacción"""
        transaccion = self.transaccion
        super().delete(*args, **kwargs)
        transaccion.calcular_totales()
        
    def get_importe(self):
        """Obtiene el importe del movimiento"""
        return self.debe if self.debe > 0 else self.haber
        
    def get_naturaleza(self):
        """Obtiene la naturaleza del movimiento"""
        return 'DEBE' if self.debe > 0 else 'HABER' 