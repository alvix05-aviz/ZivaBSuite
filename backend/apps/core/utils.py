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

def obtener_ip_cliente(request):
    """
    Obtiene la IP del cliente desde el request
    Útil para logging de auditoría
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def formatear_moneda(cantidad, moneda='MXN'):
    """
    Formatea cantidades monetarias según la moneda
    """
    if moneda == 'MXN':
        return f"${cantidad:,.2f}"
    elif moneda == 'USD':
        return f"${cantidad:,.2f} USD"
    elif moneda == 'EUR':
        return f"€{cantidad:,.2f}"
    else:
        return f"{cantidad:,.2f} {moneda}"

def validar_rfc(rfc):
    """
    Valida formato de RFC mexicano
    """
    import re
    
    # Patrón para RFC de personas físicas (AAAA######AAA)
    patron_fisica = r'^[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}$'
    # Patrón para RFC de personas morales (AAA######AAA)
    patron_moral = r'^[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}$'
    
    rfc = rfc.upper().strip()
    
    return bool(re.match(patron_fisica, rfc) or re.match(patron_moral, rfc))

def calcular_ejercicio_fiscal():
    """
    Calcula el ejercicio fiscal actual
    """
    return datetime.now().year

def validar_periodo_contable(periodo):
    """
    Valida que el periodo esté entre 1 y 12
    """
    return 1 <= periodo <= 12