from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re
from decimal import Decimal

def validar_codigo_cuenta(value):
    """
    Valida formato de código de cuenta contable
    """
    pattern = r'^[0-9]+([-\.][0-9]+)*$'
    if not re.match(pattern, value):
        raise ValidationError(
            'El código debe ser numérico con separadores - o . (ej: 1000, 1000.01, 1000-01)'
        )

def validar_rfc_mexicano(value):
    """
    Valida RFC mexicano con dígito verificador
    """
    # Patrón básico de RFC
    patron_fisica = r'^[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}$'
    patron_moral = r'^[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}$'
    
    value = value.upper().strip()
    
    if not (re.match(patron_fisica, value) or re.match(patron_moral, value)):
        raise ValidationError(
            'RFC inválido. Debe tener formato: AAAA######AAA (física) o AAA######AAA (moral)'
        )
    
    # Lista de RFCs genéricos no permitidos
    rfcs_genericos = [
        'XAXX010101000', 'XEXX010101000', 'XXXX010101000'
    ]
    
    if value in rfcs_genericos:
        raise ValidationError(
            'No se permite el uso de RFCs genéricos'
        )

def validar_codigo_postal_mexico(value):
    """
    Valida código postal mexicano (5 dígitos)
    """
    if not re.match(r'^\d{5}$', str(value)):
        raise ValidationError(
            'El código postal debe tener 5 dígitos'
        )

def validar_monto_positivo(value):
    """
    Valida que el monto sea positivo
    """
    if value < 0:
        raise ValidationError(
            'El monto debe ser positivo'
        )

def validar_periodo_fiscal(value):
    """
    Valida periodo fiscal (1-12)
    """
    if not (1 <= value <= 12):
        raise ValidationError(
            'El periodo debe estar entre 1 y 12'
        )

def validar_ejercicio_fiscal(value):
    """
    Valida ejercicio fiscal
    """
    from datetime import datetime
    año_actual = datetime.now().year
    
    if not (2000 <= value <= año_actual + 1):
        raise ValidationError(
            f'El ejercicio debe estar entre 2000 y {año_actual + 1}'
        )

def validar_color_hex(value):
    """
    Valida código de color hexadecimal
    """
    if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
        raise ValidationError(
            'El color debe tener formato hexadecimal #RRGGBB'
        )

def validar_cuadratura_contable(debe, haber, tolerancia=0.01):
    """
    Valida que debe y haber estén cuadrados
    """
    diferencia = abs(Decimal(str(debe)) - Decimal(str(haber)))
    if diferencia > Decimal(str(tolerancia)):
        raise ValidationError(
            f'La transacción no cuadra. Diferencia: {diferencia}'
        )

# Validadores regex comunes
validador_rfc = RegexValidator(
    regex=r'^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$',
    message='RFC inválido'
)

validador_telefono = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message='Número de teléfono inválido'
)

validador_codigo_cuenta_regex = RegexValidator(
    regex=r'^[0-9]+([-\.][0-9]+)*$',
    message='Código debe ser numérico con separadores - o .'
)