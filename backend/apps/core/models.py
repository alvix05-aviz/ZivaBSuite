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
            ('GENERAL', 'General'),
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


class ConfiguracionGeneral(BaseModel):
    """
    Configuraciones generales del sistema por empresa
    """
    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='configuracion_general'
    )
    
    # Configuraciones de moneda
    moneda_principal = models.CharField(
        max_length=3,
        default='MXN',
        verbose_name='Moneda principal',
        help_text='Código ISO de 3 letras (ej: MXN, USD, EUR)'
    )
    simbolo_moneda = models.CharField(
        max_length=5,
        default='$',
        verbose_name='Símbolo de moneda'
    )
    decimales_moneda = models.IntegerField(
        default=2,
        verbose_name='Decimales en moneda'
    )
    
    # Configuraciones de formato
    formato_fecha = models.CharField(
        max_length=20,
        choices=[
            ('DD/MM/YYYY', 'DD/MM/YYYY'),
            ('MM/DD/YYYY', 'MM/DD/YYYY'),
            ('YYYY-MM-DD', 'YYYY-MM-DD'),
            ('DD-MM-YYYY', 'DD-MM-YYYY'),
        ],
        default='DD/MM/YYYY',
        verbose_name='Formato de fecha'
    )
    separador_miles = models.CharField(
        max_length=1,
        choices=[
            (',', 'Coma (,)'),
            ('.', 'Punto (.)'),
            (' ', 'Espacio ( )'),
        ],
        default=',',
        verbose_name='Separador de miles'
    )
    separador_decimal = models.CharField(
        max_length=1,
        choices=[
            ('.', 'Punto (.)'),
            (',', 'Coma (,)'),
        ],
        default='.',
        verbose_name='Separador decimal'
    )
    
    # Configuraciones de zona horaria
    zona_horaria = models.CharField(
        max_length=50,
        default='America/Mexico_City',
        verbose_name='Zona horaria',
        help_text='Zona horaria de la empresa'
    )
    
    # Configuraciones de notificaciones
    notificaciones_email = models.BooleanField(
        default=True,
        verbose_name='Notificaciones por email'
    )
    notificaciones_sistema = models.BooleanField(
        default=True,
        verbose_name='Notificaciones del sistema'
    )
    email_notificaciones = models.EmailField(
        blank=True,
        null=True,
        verbose_name='Email para notificaciones'
    )
    
    # Configuraciones de interfaz
    tema_interfaz = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Claro'),
            ('dark', 'Oscuro'),
            ('auto', 'Automático'),
        ],
        default='light',
        verbose_name='Tema de la interfaz'
    )
    idioma = models.CharField(
        max_length=5,
        choices=[
            ('es', 'Español'),
            ('en', 'English'),
        ],
        default='es',
        verbose_name='Idioma'
    )
    
    # Configuraciones de períodos contables
    inicio_ejercicio_fiscal = models.CharField(
        max_length=5,
        default='01-01',
        verbose_name='Inicio ejercicio fiscal',
        help_text='Formato MM-DD (ej: 01-01 para enero 1)'
    )
    fin_ejercicio_fiscal = models.CharField(
        max_length=5,
        default='12-31',
        verbose_name='Fin ejercicio fiscal',
        help_text='Formato MM-DD (ej: 12-31 para diciembre 31)'
    )
    
    # Configuraciones de backup
    backup_automatico = models.BooleanField(
        default=True,
        verbose_name='Backup automático'
    )
    frecuencia_backup = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Diario'),
            ('weekly', 'Semanal'),
            ('monthly', 'Mensual'),
        ],
        default='daily',
        verbose_name='Frecuencia de backup'
    )
    
    class Meta:
        verbose_name = 'Configuración General'
        verbose_name_plural = 'Configuraciones Generales'
        
    def __str__(self):
        return f"Configuración General - {self.empresa.nombre}"
    
    @classmethod
    def get_for_empresa(cls, empresa):
        """Obtiene o crea la configuración general para una empresa"""
        from django.contrib.auth.models import User
        try:
            return cls.objects.get(empresa=empresa)
        except cls.DoesNotExist:
            # Obtener el primer superuser como fallback para creado_por
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.first()
            
            config = cls.objects.create(
                empresa=empresa,
                creado_por=admin_user
            )
            return config


class LogCambio(models.Model):
    """
    Log detallado de cambios para auditoría
    SUGERENCIA: Tracking completo de modificaciones
    """
    modelo = models.CharField(
        max_length=100,
        verbose_name='Modelo afectado'
    )
    registro_id = models.IntegerField(
        verbose_name='ID del registro'
    )
    campo = models.CharField(
        max_length=100,
        verbose_name='Campo modificado'
    )
    valor_anterior = models.TextField(
        blank=True,
        verbose_name='Valor anterior'
    )
    valor_nuevo = models.TextField(
        blank=True,
        verbose_name='Valor nuevo'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Usuario que realizó el cambio'
    )
    fecha_cambio = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del cambio'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Dirección IP'
    )
    
    class Meta:
        verbose_name = 'Log de Cambio'
        verbose_name_plural = 'Logs de Cambios'
        ordering = ['-fecha_cambio']
        indexes = [
            models.Index(fields=['modelo', 'registro_id']),
            models.Index(fields=['usuario', 'fecha_cambio']),
        ]
        
    def __str__(self):
        return f"{self.modelo}({self.registro_id}) - {self.campo} - {self.fecha_cambio}"