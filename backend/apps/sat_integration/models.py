from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel

User = get_user_model()

class SATCredentials(BaseModel):
    """
    Almacena las credenciales de la FIEL para comunicación con el SAT
    """
    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='credenciales_sat'
    )
    
    # RFC de la empresa
    rfc = models.CharField(
        max_length=13,
        verbose_name='RFC'
    )
    
    # Archivos de la FIEL - almacenados encriptados
    certificado_cer = models.FileField(
        upload_to='sat_credentials/cer/',
        verbose_name='Archivo .cer'
    )
    llave_privada_key = models.FileField(
        upload_to='sat_credentials/key/',
        verbose_name='Archivo .key'
    )
    password_llave = models.CharField(
        max_length=255,
        verbose_name='Contraseña de llave privada',
        help_text='Se almacena encriptada'
    )
    
    # Estado de las credenciales
    validadas = models.BooleanField(
        default=False,
        verbose_name='Credenciales validadas'
    )
    fecha_validacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de validación'
    )
    fecha_vencimiento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de vencimiento del certificado'
    )
    
    class Meta:
        verbose_name = 'Credenciales SAT'
        verbose_name_plural = 'Credenciales SAT'
        
    def __str__(self):
        return f"Credenciales SAT - {self.empresa.nombre} ({self.rfc})"


class CFDIDownloadJob(BaseModel):
    """
    Trabajos de descarga masiva de CFDI
    """
    
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('COMPLETADO', 'Completado'),
        ('ERROR', 'Error'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    TIPO_CHOICES = [
        ('RECIBIDOS', 'CFDI Recibidos'),
        ('EMITIDOS', 'CFDI Emitidos'),
        ('TODOS', 'Todos los CFDI'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='trabajos_descarga_cfdi'
    )
    
    # Parámetros de la descarga
    fecha_inicio = models.DateField(
        verbose_name='Fecha de inicio'
    )
    fecha_fin = models.DateField(
        verbose_name='Fecha de fin'
    )
    tipo_cfdi = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='RECIBIDOS',
        verbose_name='Tipo de CFDI'
    )
    
    # Estado del trabajo
    estado = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    
    # Información del proceso
    solicitud_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID de solicitud SAT'
    )
    total_cfdi = models.IntegerField(
        default=0,
        verbose_name='Total de CFDI'
    )
    procesados = models.IntegerField(
        default=0,
        verbose_name='CFDI procesados'
    )
    
    # Resultados
    archivo_descarga = models.FileField(
        upload_to='cfdi_downloads/',
        blank=True,
        null=True,
        verbose_name='Archivo de descarga'
    )
    mensaje_error = models.TextField(
        blank=True,
        verbose_name='Mensaje de error'
    )
    
    # Fechas de proceso
    fecha_inicio_proceso = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Inicio del proceso'
    )
    fecha_fin_proceso = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fin del proceso'
    )
    
    class Meta:
        verbose_name = 'Trabajo de Descarga CFDI'
        verbose_name_plural = 'Trabajos de Descarga CFDI'
        ordering = ['-fecha_creacion']
        
    def __str__(self):
        return f"Descarga CFDI {self.empresa.nombre} - {self.fecha_inicio} a {self.fecha_fin} ({self.estado})"
    
    @property
    def progreso_porcentaje(self):
        """Calcula el porcentaje de progreso"""
        if self.total_cfdi == 0:
            return 0
        return int((self.procesados / self.total_cfdi) * 100)


class CFDI(BaseModel):
    """
    Información de CFDI individuales obtenidos del SAT
    """
    
    ESTADO_CHOICES = [
        ('VIGENTE', 'Vigente'),
        ('CANCELADO', 'Cancelado'),
        ('PENDIENTE', 'Pendiente de validación'),
    ]
    
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
        ('TRASLADO', 'Traslado'),
        ('NOMINA', 'Nómina'),
        ('PAGO', 'Pago'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='cfdi_registros'
    )
    
    trabajo_descarga = models.ForeignKey(
        CFDIDownloadJob,
        on_delete=models.CASCADE,
        related_name='cfdi_descargados',
        null=True,
        blank=True
    )
    
    # Identificadores del CFDI
    uuid = models.CharField(
        max_length=36,
        unique=True,
        verbose_name='UUID/Folio Fiscal'
    )
    serie = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Serie'
    )
    folio = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Folio'
    )
    
    # Información básica
    fecha_emision = models.DateTimeField(
        verbose_name='Fecha de emisión'
    )
    fecha_certificacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de certificación'
    )
    
    # Emisor y receptor
    rfc_emisor = models.CharField(
        max_length=13,
        verbose_name='RFC Emisor'
    )
    nombre_emisor = models.CharField(
        max_length=254,
        verbose_name='Nombre Emisor'
    )
    rfc_receptor = models.CharField(
        max_length=13,
        verbose_name='RFC Receptor'
    )
    nombre_receptor = models.CharField(
        max_length=254,
        verbose_name='Nombre Receptor'
    )
    
    # Información fiscal
    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de comprobante'
    )
    estado_sat = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado en SAT'
    )
    
    # Montos
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Subtotal'
    )
    iva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='IVA'
    )
    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Total'
    )
    moneda = models.CharField(
        max_length=3,
        default='MXN',
        verbose_name='Moneda'
    )
    
    # Archivos
    archivo_xml = models.FileField(
        upload_to='cfdi_xml/',
        blank=True,
        null=True,
        verbose_name='Archivo XML'
    )
    archivo_pdf = models.FileField(
        upload_to='cfdi_pdf/',
        blank=True,
        null=True,
        verbose_name='Archivo PDF'
    )
    
    # Cancelación (si aplica)
    fecha_cancelacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de cancelación'
    )
    motivo_cancelacion = models.TextField(
        blank=True,
        verbose_name='Motivo de cancelación'
    )
    
    # Validaciones
    validado_sat = models.BooleanField(
        default=False,
        verbose_name='Validado en SAT'
    )
    fecha_validacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de validación'
    )
    
    class Meta:
        verbose_name = 'CFDI'
        verbose_name_plural = 'CFDIs'
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['rfc_emisor', 'fecha_emision']),
            models.Index(fields=['rfc_receptor', 'fecha_emision']),
            models.Index(fields=['empresa', 'estado_sat']),
        ]
        
    def __str__(self):
        return f"CFDI {self.uuid} - {self.nombre_emisor} -> {self.nombre_receptor} (${self.total})"
    
    @property
    def es_emitido(self):
        """Determina si el CFDI fue emitido por la empresa"""
        return self.rfc_emisor == self.empresa.rfc
    
    @property
    def es_recibido(self):
        """Determina si el CFDI fue recibido por la empresa"""
        return self.rfc_receptor == self.empresa.rfc


class CFDIStatusLog(BaseModel):
    """
    Log de cambios de estado de CFDI para auditoría
    """
    cfdi = models.ForeignKey(
        CFDI,
        on_delete=models.CASCADE,
        related_name='logs_estado'
    )
    
    estado_anterior = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Estado anterior'
    )
    estado_nuevo = models.CharField(
        max_length=20,
        verbose_name='Estado nuevo'
    )
    
    fecha_consulta = models.DateTimeField(
        verbose_name='Fecha de consulta al SAT'
    )
    respuesta_sat = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Respuesta completa del SAT'
    )
    
    class Meta:
        verbose_name = 'Log de Estado CFDI'
        verbose_name_plural = 'Logs de Estado CFDI'
        ordering = ['-fecha_creacion']
        
    def __str__(self):
        return f"Estado CFDI {self.cfdi.uuid}: {self.estado_anterior} -> {self.estado_nuevo}"
