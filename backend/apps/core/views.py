from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import date, datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transacciones.models import TransaccionContable, MovimientoContable
from apps.catalogo_cuentas.models import CuentaContable
from apps.empresas.models import Empresa, UsuarioEmpresa
from django.contrib.auth.models import User


@login_required
def dashboard(request):
    """Vista principal del dashboard"""
    # Obtener empresa actual
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Fechas para los cálculos
    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)
    
    # Calcular estadísticas del mes
    stats = calcular_estadisticas_mes(empresa, inicio_mes, hoy)
    
    # Obtener transacciones recientes
    transacciones_recientes = TransaccionContable.objects.filter(
        empresa=empresa,
        activo=True
    ).defer('tipo_personalizado').order_by('-fecha', '-id')[:10]
    
    context = {
        'fecha_actual': hoy,
        'empresa_actual': empresa.nombre,
        'stats': stats,
        'transacciones_recientes': transacciones_recientes,
    }
    
    return render(request, 'dashboard/index.html', context)


@login_required
def transacciones_view(request):
    """Vista de transacciones"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    transacciones = TransaccionContable.objects.filter(
        empresa=empresa,
        activo=True
    ).defer('tipo_personalizado').prefetch_related(
        'movimientos__cuenta', 
        'movimientos__centro_costo', 
        'movimientos__proyecto'
    ).order_by('-fecha', '-id')
    
    # Obtener centros de costo y proyectos para filtros
    centros_costo = []
    proyectos = []
    try:
        from apps.centros_costo.models import CentroCosto, Proyecto
        centros_costo = CentroCosto.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')
        proyectos = Proyecto.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')
    except ImportError:
        pass  # App no instalada aún
    
    context = {
        'empresa_actual': empresa.nombre,
        'transacciones': transacciones,
        'centros_costo': centros_costo,
        'proyectos': proyectos,
    }
    
    return render(request, 'dashboard/transacciones.html', context)


@login_required
def catalogo_view(request):
    """Vista del catálogo de cuentas"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener cuentas en estructura jerárquica
    cuentas_raiz = CuentaContable.objects.filter(
        empresa=empresa,
        cuenta_padre__isnull=True,
        activo=True
    ).order_by('codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'cuentas_raiz': cuentas_raiz,
    }
    
    return render(request, 'dashboard/catalogo.html', context)


@login_required
def reportes_view(request):
    """Vista de reportes"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener centros de costo y proyectos para reportes
    centros_costo = []
    proyectos = []
    try:
        from apps.centros_costo.models import CentroCosto, Proyecto
        centros_costo = CentroCosto.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')
        proyectos = Proyecto.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')
    except ImportError:
        pass  # App no instalada aún
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_costo': centros_costo,
        'proyectos': proyectos,
        'fecha_hoy': date.today().strftime('%Y-%m-%d'),
    }
    
    return render(request, 'dashboard/reportes.html', context)


@login_required
def seleccionar_empresa(request):
    """Seleccionar empresa activa"""
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        if empresa_id:
            request.session['empresa_id'] = empresa_id
            return redirect('dashboard')
    
    # Obtener empresas del usuario
    accesos = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        activo=True
    ).select_related('empresa')
    
    context = {
        'accesos': accesos,
    }
    
    return render(request, 'dashboard/seleccionar_empresa.html', context)


def logout_view(request):
    """Cerrar sesión"""
    auth_logout(request)
    return redirect('login')


# Funciones auxiliares
def get_empresa_actual(request):
    """Obtiene la empresa actual del usuario"""
    empresa_id = request.session.get('empresa_id')
    
    if empresa_id:
        try:
            # Verificar que el usuario tenga acceso
            acceso = UsuarioEmpresa.objects.get(
                usuario=request.user,
                empresa_id=empresa_id,
                activo=True
            )
            return acceso.empresa
        except UsuarioEmpresa.DoesNotExist:
            pass
    
    # Si no hay empresa en sesión, buscar la default
    acceso = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        empresa_default=True,
        activo=True
    ).first()
    
    if acceso:
        request.session['empresa_id'] = acceso.empresa.id
        return acceso.empresa
    
    # Si no hay default, usar la primera
    acceso = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        activo=True
    ).first()
    
    if acceso:
        request.session['empresa_id'] = acceso.empresa.id
        return acceso.empresa
    
    return None


def calcular_estadisticas_mes(empresa, fecha_inicio, fecha_fin):
    """Calcula las estadísticas del mes"""
    # Filtro base
    filtro = Q(
        transaccion__empresa=empresa,
        transaccion__estado='CONTABILIZADA',
        transaccion__fecha__gte=fecha_inicio,
        transaccion__fecha__lte=fecha_fin,
        activo=True
    )
    
    # Calcular ingresos
    ingresos = MovimientoContable.objects.filter(
        filtro,
        cuenta__tipo='INGRESO'
    ).aggregate(
        total=Sum('haber') - Sum('debe')
    )['total'] or Decimal('0.00')
    
    # Calcular gastos
    gastos = MovimientoContable.objects.filter(
        filtro,
        cuenta__tipo__in=['GASTO', 'COSTO']
    ).aggregate(
        total=Sum('debe') - Sum('haber')
    )['total'] or Decimal('0.00')
    
    # Saldo en caja
    caja = MovimientoContable.objects.filter(
        transaccion__empresa=empresa,
        transaccion__estado='CONTABILIZADA',
        cuenta__codigo='1.1.1',  # Asumiendo que 1.1.1 es CAJA
        activo=True
    ).aggregate(
        total=Sum('debe') - Sum('haber')
    )['total'] or Decimal('0.00')
    
    return {
        'ingresos': float(ingresos),
        'gastos': float(gastos),
        'utilidad': float(ingresos - gastos),
        'saldo_caja': float(caja),
    }


@login_required
def configuracion_view(request):
    """Vista de configuración del sistema"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener estadísticas para mostrar en la página
    stats = {
        'empresas': Empresa.objects.filter(activo=True).count(),
        'usuarios': User.objects.filter(is_active=True).count(),
        'cuentas': CuentaContable.objects.filter(empresa=empresa, activo=True).count(),
        'transacciones': TransaccionContable.objects.filter(
            empresa=empresa,
            fecha__month=date.today().month,
            fecha__year=date.today().year,
            activo=True
        ).defer('tipo_personalizado').count(),
    }
    
    context = {
        'empresa_actual': empresa.nombre,
        'stats': stats,
    }
    
    return render(request, 'dashboard/configuracion.html', context)


@login_required
def configuracion_empresas_view(request):
    """Vista de configuración de empresas"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener todas las empresas donde el usuario es admin o propietario
    empresas_admin = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        rol__in=['PROPIETARIO', 'ADMINISTRADOR'],
        activo=True
    ).values_list('empresa_id', flat=True)
    
    empresas = Empresa.objects.filter(
        Q(id__in=empresas_admin) | Q(id=empresa.id)
    ).distinct()
    
    context = {
        'empresa_actual': empresa.nombre,
        'empresas': empresas,
    }
    
    return render(request, 'configuracion/empresas.html', context)


@login_required
def configuracion_catalogo_view(request):
    """Vista de configuración del catálogo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener estadísticas por tipo de cuenta
    stats = {}
    tipos = ['ACTIVO', 'PASIVO', 'CAPITAL', 'INGRESO', 'GASTO', 'COSTO']
    for tipo in tipos:
        stats[tipo.lower() + 's'] = CuentaContable.objects.filter(
            empresa=empresa,
            tipo=tipo,
            activo=True
        ).count()
    
    context = {
        'empresa_actual': empresa.nombre,
        'stats': stats,
    }
    
    return render(request, 'configuracion/catalogo.html', context)


@login_required
def configuracion_transacciones_view(request):
    """Vista de configuración de tipos de transacción"""
    from django.http import JsonResponse
    import json
    
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Verificar si la tabla transacciones_tipotransaccion existe
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM transacciones_tipotransaccion LIMIT 1")
        model_available = True
        from apps.transacciones.models import TipoTransaccion
    except Exception:
        model_available = False
        TipoTransaccion = None
    
    if request.method == 'POST':
        if not model_available:
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': False, 'error': 'Funcionalidad no disponible - ejecutar migraciones'})
            return redirect('configuracion_transacciones')
        action = request.POST.get('action')
        
        if action == 'crear_tipo':
            try:
                tipo = TipoTransaccion.objects.create(
                    empresa=empresa,
                    codigo=request.POST.get('codigo'),
                    nombre=request.POST.get('nombre'),
                    descripcion=request.POST.get('descripcion', ''),
                    prefijo=request.POST.get('prefijo', ''),
                    sufijo=request.POST.get('sufijo', ''),
                    longitud_numero=int(request.POST.get('longitud_numero', 4)),
                    requiere_validacion=request.POST.get('requiere_validacion') == 'on',
                    permite_edicion=request.POST.get('permite_edicion') == 'on',
                    color_interfaz=request.POST.get('color_interfaz', 'blue'),
                    creado_por=request.user,
                    modificado_por=request.user
                )
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True, 'id': tipo.id})
                return redirect('configuracion_transacciones')
            except Exception as e:
                print(f"Error creando tipo de transacción: {e}")  # Debug
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'error': str(e)})
                return redirect('configuracion_transacciones')
                
        elif action == 'editar_tipo':
            try:
                tipo = TipoTransaccion.objects.get(
                    id=request.POST.get('tipo_id'),
                    empresa=empresa
                )
                tipo.codigo = request.POST.get('codigo')
                tipo.nombre = request.POST.get('nombre')
                tipo.descripcion = request.POST.get('descripcion', '')
                tipo.prefijo = request.POST.get('prefijo', '')
                tipo.sufijo = request.POST.get('sufijo', '')
                tipo.longitud_numero = int(request.POST.get('longitud_numero', 4))
                tipo.requiere_validacion = request.POST.get('requiere_validacion') == 'on'
                tipo.permite_edicion = request.POST.get('permite_edicion') == 'on'
                tipo.color_interfaz = request.POST.get('color_interfaz', 'blue')
                tipo.save()
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True})
                return redirect('configuracion_transacciones')
            except Exception as e:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'error': str(e)})
                    
        elif action == 'eliminar_tipo':
            try:
                tipo = TipoTransaccion.objects.get(
                    id=request.POST.get('tipo_id'),
                    empresa=empresa
                )
                # Verificar que no tenga transacciones asociadas
                if tipo.transacciones.exists():
                    raise ValidationError('No se puede eliminar un tipo que tiene transacciones asociadas')
                tipo.delete()
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True})
                return redirect('configuracion_transacciones')
            except Exception as e:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request
    if model_available:
        tipos_personalizados = TipoTransaccion.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo')
    else:
        tipos_personalizados = []
    
    context = {
        'empresa_actual': empresa.nombre,
        'tipos_personalizados': tipos_personalizados,
        'model_available': model_available,
    }
    
    return render(request, 'configuracion/transacciones.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar_usuario(request):
    """Buscar usuario por email"""
    email = request.GET.get('email')
    
    if not email:
        return Response({'error': 'Email requerido'}, status=400)
    
    try:
        usuario = User.objects.get(email=email)
        return Response({
            'id': usuario.id,
            'username': usuario.username,
            'email': usuario.email,
            'first_name': usuario.first_name,
            'last_name': usuario.last_name,
            'full_name': usuario.get_full_name()
        })
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)


@login_required 
def configuracion_transacciones_get(request, tipo_id):
    """API endpoint para obtener datos de un tipo de transacción"""
    from django.http import JsonResponse
    
    empresa = get_empresa_actual(request)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'No hay empresa seleccionada'})
    
    # Verificar si el modelo TipoTransaccion está disponible
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM transacciones_tipotransaccion LIMIT 1")
        from apps.transacciones.models import TipoTransaccion
    except Exception:
        return JsonResponse({'success': False, 'error': 'Función no disponible - ejecutar migraciones'})
    
    try:
        tipo = TipoTransaccion.objects.get(
            id=tipo_id,
            empresa=empresa,
            activo=True
        )
        
        data = {
            'codigo': tipo.codigo,
            'nombre': tipo.nombre,
            'descripcion': tipo.descripcion,
            'prefijo': tipo.prefijo,
            'sufijo': tipo.sufijo,
            'longitud_numero': tipo.longitud_numero,
            'color_interfaz': tipo.color_interfaz,
            'requiere_validacion': tipo.requiere_validacion,
            'permite_edicion': tipo.permite_edicion,
        }
        
        return JsonResponse({'success': True, 'tipo': data})
        
    except TipoTransaccion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tipo no encontrado'})


@login_required
def configuracion_general_view(request):
    """Vista funcional para configuración general del sistema"""
    from django.contrib import messages
    from django.http import JsonResponse
    from apps.core.models import ConfiguracionGeneral
    
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener o crear configuración general
    config_general = ConfiguracionGeneral.get_for_empresa(empresa)
    
    if request.method == 'POST':
        try:
            # Procesar formulario
            config_general.moneda_principal = request.POST.get('moneda_principal', 'MXN')
            config_general.simbolo_moneda = request.POST.get('simbolo_moneda', '$')
            config_general.decimales_moneda = int(request.POST.get('decimales_moneda', 2))
            
            config_general.formato_fecha = request.POST.get('formato_fecha', 'DD/MM/YYYY')
            config_general.separador_miles = request.POST.get('separador_miles', ',')
            config_general.separador_decimal = request.POST.get('separador_decimal', '.')
            
            config_general.zona_horaria = request.POST.get('zona_horaria', 'America/Mexico_City')
            
            config_general.notificaciones_email = request.POST.get('notificaciones_email') == 'on'
            config_general.notificaciones_sistema = request.POST.get('notificaciones_sistema') == 'on'
            config_general.email_notificaciones = request.POST.get('email_notificaciones', '')
            
            config_general.tema_interfaz = request.POST.get('tema_interfaz', 'light')
            config_general.idioma = request.POST.get('idioma', 'es')
            
            config_general.inicio_ejercicio_fiscal = request.POST.get('inicio_ejercicio_fiscal', '01-01')
            config_general.fin_ejercicio_fiscal = request.POST.get('fin_ejercicio_fiscal', '12-31')
            
            config_general.backup_automatico = request.POST.get('backup_automatico') == 'on'
            config_general.frecuencia_backup = request.POST.get('frecuencia_backup', 'daily')
            
            config_general.modificado_por = request.user
            config_general.save()
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': True, 'message': 'Configuración guardada exitosamente'})
            
            messages.success(request, 'Configuración guardada exitosamente')
            return redirect('configuracion_general')
            
        except Exception as e:
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': False, 'error': str(e)})
            
            messages.error(request, f'Error al guardar configuración: {str(e)}')
    
    # Lista de zonas horarias más comunes
    zonas_horaria = [
        ('America/Mexico_City', 'Ciudad de México (GMT-6)'),
        ('America/Cancun', 'Cancún (GMT-5)'),
        ('America/Tijuana', 'Tijuana (GMT-8)'),
        ('America/Chihuahua', 'Chihuahua (GMT-7)'),
        ('UTC', 'UTC (GMT+0)'),
        ('America/New_York', 'Nueva York (GMT-5)'),
        ('America/Los_Angeles', 'Los Ángeles (GMT-8)'),
    ]
    
    context = {
        'empresa_actual': empresa.nombre,
        'config_general': config_general,
        'zonas_horaria': zonas_horaria,
    }
    
    return render(request, 'configuracion/general.html', context)


@login_required
def configuracion_placeholder_view(request, seccion):
    """Vista placeholder para secciones en desarrollo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Redirigir secciones implementadas
    if seccion == 'general':
        return redirect('configuracion_general')
    elif seccion == 'centros-costo':
        return redirect('centros-costo-list')
    
    secciones = {
        'reportes': {
            'titulo': 'Formatos de Reportes',
            'icono': 'fas fa-file-alt',
            'color': 'yellow',
            'descripcion': 'Plantillas y diseños de reportes'
        },
        'fiscal': {
            'titulo': 'Configuración Fiscal',
            'icono': 'fas fa-receipt',
            'color': 'red',
            'descripcion': 'Impuestos y regulaciones fiscales'
        },
        'seguridad': {
            'titulo': 'Respaldos y Seguridad',
            'icono': 'fas fa-shield-alt',
            'color': 'gray',
            'descripcion': 'Protección de datos y respaldos'
        },
        'integraciones': {
            'titulo': 'Integraciones',
            'icono': 'fas fa-plug',
            'color': 'teal',
            'descripcion': 'APIs y conexiones externas'
        }
    }
    
    if seccion not in secciones:
        return redirect('configuracion')
    
    info = secciones[seccion]
    
    context = {
        'empresa_actual': empresa.nombre,
        'seccion': info,
        'seccion_key': seccion
    }
    
    return render(request, 'configuracion/placeholder.html', context)