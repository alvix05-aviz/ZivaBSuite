from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.empresas.models import Empresa


class CuentaContable(BaseModel):
    """Catálogo de cuentas MVP - Estructura jerárquica básica"""
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cuentas_contables'
    )
    
    # Estructura de cuenta
    codigo = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex='^[0-9]+([-\.][0-9]+)*$',
                message='Código debe ser numérico con separadores - o .'
            )
        ],
        verbose_name='Código'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Cuenta'
    )
    cuenta_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcuentas',
        verbose_name='Cuenta Padre'
    )
    
    # Clasificación básica
    nivel = models.IntegerField(
        verbose_name='Nivel',
        help_text='1=Mayor, 2=Subcuenta, 3=Sub-subcuenta'
    )
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVO', 'Activo'),
            ('PASIVO', 'Pasivo'),
            ('CAPITAL', 'Capital'),
            ('INGRESO', 'Ingreso'),
            ('COSTO', 'Costo'),
            ('GASTO', 'Gasto'),
        ],
        verbose_name='Tipo'
    )
    naturaleza = models.CharField(
        max_length=10,
        choices=[
            ('DEUDORA', 'Deudora'),
            ('ACREEDORA', 'Acreedora'),
        ],
        verbose_name='Naturaleza'
    )
    
    # Estado
    afectable = models.BooleanField(
        default=True,
        verbose_name='Afectable',
        help_text='Si puede recibir movimientos contables'
    )
    
    class Meta:
        unique_together = ['empresa', 'codigo']
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Cuentas Contables'
        ordering = ['codigo']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
        
    def clean(self):
        """Validaciones del modelo"""
        if self.cuenta_padre:
            # Verificar que la cuenta padre pertenezca a la misma empresa
            if self.cuenta_padre.empresa != self.empresa:
                raise ValidationError('La cuenta padre debe pertenecer a la misma empresa')
            
            # Verificar que el nivel sea correcto
            if self.nivel != self.cuenta_padre.nivel + 1:
                raise ValidationError('El nivel debe ser uno más que la cuenta padre')
                
        # Si es cuenta de primer nivel, debe ser nivel 1
        elif self.nivel != 1:
            raise ValidationError('Las cuentas sin padre deben ser de nivel 1')
            
    def get_saldo_actual(self):
        """Placeholder para saldo - se implementará con transacciones"""
        return 0
        
    def is_cuenta_mayor(self):
        """Indica si es cuenta mayor (nivel 1)"""
        return self.nivel == 1
        
    def get_ruta_completa(self):
        """Obtiene la ruta completa de la cuenta"""
        if self.cuenta_padre:
            return f"{self.cuenta_padre.get_ruta_completa()} > {self.nombre}"
        return self.nombre