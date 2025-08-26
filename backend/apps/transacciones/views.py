from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.http import HttpResponse
from django.db.models import Q, F
from django.db import models
from .models import TransaccionContable, MovimientoContable
from .serializers import (
    TransaccionContableSerializer,
    TransaccionContableCreateSerializer,
    TransaccionContableListSerializer,
    MovimientoContableSerializer
)


class TransaccionContableViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de transacciones contables MVP"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'tipo', 'fecha']
    search_fields = ['folio', 'concepto']
    ordering_fields = ['fecha', 'folio', 'total_debe']
    ordering = ['-fecha', '-folio']
    
    def get_queryset(self):
        """Solo transacciones de la empresa actual"""
        # Usar la misma lógica que en catálogo de cuentas
        empresa = None
        if hasattr(self.request, 'empresa') and self.request.empresa:
            empresa = self.request.empresa
        else:
            empresa_id = self.request.session.get('empresa_id')
            if empresa_id:
                from apps.empresas.models import Empresa
                try:
                    empresa = Empresa.objects.get(id=empresa_id)
                except Empresa.DoesNotExist:
                    pass
            
            if not empresa:
                from apps.empresas.models import UsuarioEmpresa
                acceso = UsuarioEmpresa.objects.filter(
                    usuario=self.request.user,
                    activo=True
                ).first()
                if acceso:
                    empresa = acceso.empresa
        
        if empresa:
            return TransaccionContable.objects.filter(
                empresa=empresa,
                activo=True
            ).defer('tipo_personalizado').prefetch_related('movimientos__cuenta')
        return TransaccionContable.objects.none()
        
    def get_serializer_class(self):
        """Usar diferentes serializers según la acción"""
        if self.action == 'list':
            return TransaccionContableListSerializer
        elif self.action == 'create':
            return TransaccionContableCreateSerializer
        return TransaccionContableSerializer
        
    def perform_create(self, serializer):
        """No hacer nada - el serializer maneja la creación"""
        pass
        
    def perform_update(self, serializer):
        """Asignar usuario modificador"""
        serializer.save(modificado_por=self.request.user)
    
    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        """Validar una transacción"""
        transaccion = self.get_object()
        
        try:
            transaccion.validar()
            return Response({
                'mensaje': f'Transacción {transaccion.folio} validada correctamente',
                'estado': transaccion.estado
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def contabilizar(self, request, pk=None):
        """Contabilizar una transacción"""
        transaccion = self.get_object()
        
        try:
            transaccion.contabilizar()
            return Response({
                'mensaje': f'Transacción {transaccion.folio} contabilizada correctamente',
                'estado': transaccion.estado,
                'fecha_contabilizacion': transaccion.fecha_contabilizacion
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar una transacción"""
        transaccion = self.get_object()
        
        try:
            transaccion.cancelar()
            return Response({
                'mensaje': f'Transacción {transaccion.folio} cancelada correctamente',
                'estado': transaccion.estado
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def estados(self, request):
        """Lista los estados disponibles"""
        estados = TransaccionContable._meta.get_field('estado').choices
        return Response([
            {'valor': valor, 'nombre': nombre}
            for valor, nombre in estados
        ])
        
    @action(detail=False, methods=['get'])
    def tipos(self, request):
        """Lista los tipos disponibles"""
        tipos = TransaccionContable._meta.get_field('tipo').choices
        return Response([
            {'valor': valor, 'nombre': nombre}
            for valor, nombre in tipos
        ])
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado de transacción (endpoint genérico)"""
        transaccion = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if not nuevo_estado:
            return Response(
                {'error': 'Estado requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if nuevo_estado == 'VALIDADA' and transaccion.estado == 'BORRADOR':
                transaccion.validar()
            elif nuevo_estado == 'CONTABILIZADA' and transaccion.estado == 'VALIDADA':
                transaccion.contabilizar()
            elif nuevo_estado == 'CANCELADA':
                transaccion.cancelar()
            else:
                return Response(
                    {'error': f'No se puede cambiar de {transaccion.estado} a {nuevo_estado}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response({
                'mensaje': f'Transacción {transaccion.folio} cambiada a {transaccion.estado}',
                'estado': transaccion.estado,
                'folio': transaccion.folio
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Dashboard con estadísticas básicas"""
        queryset = self.get_queryset()
        
        stats = {
            'total_transacciones': queryset.count(),
            'por_estado': {
                estado[0]: queryset.filter(estado=estado[0]).count()
                for estado in TransaccionContable.ESTADO_CHOICES
            },
            'por_tipo': {
                tipo[0]: queryset.filter(tipo=tipo[0]).count()
                for tipo in TransaccionContable.TIPO_CHOICES
            },
            'no_balanceadas': queryset.exclude(total_debe=models.F('total_haber')).count()
        }
        
        return Response(stats)


class MovimientoContableViewSet(viewsets.ModelViewSet):
    """ViewSet para movimientos contables individuales"""
    serializer_class = MovimientoContableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['cuenta', 'transaccion__estado']
    search_fields = ['concepto', 'cuenta__codigo', 'cuenta__nombre']
    
    def get_queryset(self):
        """Solo movimientos de transacciones de la empresa actual"""
        # Similar lógica para obtener empresa
        empresa = None
        if hasattr(self.request, 'empresa') and self.request.empresa:
            empresa = self.request.empresa
        else:
            from apps.empresas.models import UsuarioEmpresa
            acceso = UsuarioEmpresa.objects.filter(
                usuario=self.request.user,
                activo=True
            ).first()
            if acceso:
                empresa = acceso.empresa
        
        if empresa:
            return MovimientoContable.objects.filter(
                transaccion__empresa=empresa,
                activo=True
            ).select_related('transaccion', 'cuenta')
        return MovimientoContable.objects.none()


@api_view(['GET'])
@permission_classes([AllowAny])
def transacciones_root(request):
    """Página de navegación del módulo de transacciones"""
    if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        html_content = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Transacciones Contables - ZivaBSuite</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                h1 { color: #2c3e50; }
                .endpoint { margin: 15px 0; padding: 15px; background: #f1f2f6; border-radius: 5px; }
                .method { font-weight: bold; color: #27ae60; }
                .url { color: #3498db; font-family: monospace; }
                .back-link { margin-bottom: 20px; }
                .back-link a { color: #7f8c8d; text-decoration: none; }
                .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 15px 0; }
                .feature { background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="back-link"><a href="/">← Volver al inicio</a> | <a href="/api/">API Root</a></div>
                <h1>💰 Transacciones Contables</h1>
                
                <div class="warning">
                    <strong>⚠️ Nota:</strong> Todos los endpoints requieren autenticación (login admin o token API)
                </div>
                
                <div class="feature">
                    <strong>✨ Funciones MVP:</strong> Crear pólizas, validar balance automático, flujo de estados (Borrador → Validada → Contabilizada)
                </div>
                
                <h2>🔗 Endpoints Principales</h2>
                
                <div class="endpoint">
                    <div class="method">GET/POST</div>
                    <div class="url"><a href="/api/transacciones/transacciones/">/api/transacciones/transacciones/</a></div>
                    <p>CRUD de transacciones contables (pólizas)</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">POST</div>
                    <div class="url">/api/transacciones/transacciones/{id}/validar/</div>
                    <p>Validar una transacción (verifica balance debe = haber)</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">POST</div>
                    <div class="url">/api/transacciones/transacciones/{id}/contabilizar/</div>
                    <p>Contabilizar una transacción validada</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/transacciones/transacciones/dashboard/">/api/transacciones/transacciones/dashboard/</a></div>
                    <p>Dashboard con estadísticas de transacciones</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/transacciones/movimientos/">/api/transacciones/movimientos/</a></div>
                    <p>Movimientos contables individuales</p>
                </div>
                
                <h2>🔍 Ejemplos de Filtros</h2>
                <ul>
                    <li><code>/api/transacciones/transacciones/?estado=VALIDADA</code> - Solo transacciones validadas</li>
                    <li><code>/api/transacciones/transacciones/?tipo=INGRESO</code> - Solo ingresos</li>
                    <li><code>/api/transacciones/transacciones/?search=VENTA</code> - Buscar por concepto</li>
                </ul>
                
                <h2>📋 Gestión Administrativa</h2>
                <p><a href="/admin/transacciones/transaccioncontable/">🛡️ Administración de Transacciones</a></p>
                <p><a href="/admin/transacciones/movimientocontable/">🛡️ Administración de Movimientos</a></p>
                
                <h2>🔑 Autenticación</h2>
                <p><code>Authorization: Token 1e0b0f1c08f1359f4c76e55c2fcba894976aeba7</code></p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)
    
    # Para requests JSON
    return Response({
        'message': 'Transacciones Contables API',
        'version': '4.0.0-MVP',
        'endpoints': {
            'transacciones': request.build_absolute_uri('/api/transacciones/transacciones/'),
            'movimientos': request.build_absolute_uri('/api/transacciones/movimientos/'),
            'dashboard': request.build_absolute_uri('/api/transacciones/transacciones/dashboard/'),
        },
        'features': [
            'CRUD de transacciones',
            'Validación automática de balance',
            'Flujo de estados',
            'Dashboard de estadísticas'
        ]
    })


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from decimal import Decimal
from django.db.models import Max
from apps.catalogo_cuentas.models import CuentaContable
from apps.empresas.models import UsuarioEmpresa


@login_required
def crear_transaccion_view(request):
    """Vista para crear nueva transacción"""
    
    # Obtener empresa actual
    empresa = None
    empresa_id = request.session.get('empresa_id')
    
    if empresa_id:
        try:
            from apps.empresas.models import Empresa
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            pass
    
    if not empresa:
        acceso = UsuarioEmpresa.objects.filter(
            usuario=request.user,
            activo=True
        ).first()
        if acceso:
            empresa = acceso.empresa
            request.session['empresa_id'] = empresa.id
    
    if not empresa:
        return render(request, 'error.html', {
            'error': 'No tienes acceso a ninguna empresa',
            'redirect_url': '/seleccionar-empresa/'
        })
    
    # Obtener cuentas contables para el formulario
    cuentas = CuentaContable.objects.filter(
        empresa=empresa,
        activo=True
    ).order_by('codigo')
    
    # Obtener tipos de transacción disponibles
    # Primero los predeterminados
    tipos_predeterminados = [
        ('DIARIO', 'Diario General'),
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
        ('AJUSTE', 'Ajuste'),
    ]
    
    # Luego los personalizados de la empresa
    from .models import TipoTransaccion
    tipos_personalizados = []
    try:
        tipos_personalizados = [(tipo.codigo, f"{tipo.nombre} (Personalizado)") 
                               for tipo in TipoTransaccion.objects.filter(
                                   empresa=empresa,
                                   activo=True
                               ).order_by('codigo')]
    except Exception:
        # Si hay error con TipoTransaccion (tabla no existe), continuar solo con predeterminados
        pass
    
    tipos_disponibles = tipos_predeterminados + tipos_personalizados
    
    # Obtener centros de costo activos
    centros_costo = []
    try:
        from apps.centros_costo.models import CentroCosto
        centros_costo = CentroCosto.objects.filter(
            empresa=empresa,
            activo=True,
            permite_movimientos=True  # Solo centros que permiten movimientos directos
        ).order_by('codigo')
    except ImportError:
        pass  # App no instalada aún
    
    # Obtener proyectos activos
    proyectos = []
    try:
        from apps.centros_costo.models import Proyecto
        proyectos = Proyecto.objects.filter(
            empresa=empresa,
            activo=True,
            estado__in=['ACTIVO', 'PLANIFICACION']
        ).order_by('codigo')
    except ImportError:
        pass  # App no instalada aún
    
    # Para el folio inicial, mostrar un placeholder
    # El folio real se generará al procesar el formulario según el tipo seleccionado
    proximo_folio = "Se generará automáticamente"
    
    if request.method == 'POST':
        # Procesar creación de transacción
        try:
            concepto = request.POST.get('concepto')
            tipo = request.POST.get('tipo', 'DIARIO')
            fecha = request.POST.get('fecha')
            
            # Generar folio según el tipo seleccionado
            folio_generado = None
            tipo_personalizado_obj = None
            
            # Verificar si es un tipo personalizado
            try:
                tipo_personalizado_obj = TipoTransaccion.objects.get(
                    empresa=empresa,
                    codigo=tipo,
                    activo=True
                )
                folio_generado = tipo_personalizado_obj.generar_folio()
            except TipoTransaccion.DoesNotExist:
                # Es un tipo predeterminado, usar numeración tradicional
                try:
                    ultimo_folio_str = TransaccionContable.objects.filter(
                        empresa=empresa,
                        tipo=tipo
                    ).defer('tipo_personalizado').aggregate(max_folio=Max('folio'))['max_folio']
                    
                    if ultimo_folio_str is None:
                        folio_generado = "1"
                    else:
                        try:
                            ultimo_num = int(ultimo_folio_str)
                            folio_generado = str(ultimo_num + 1)
                        except ValueError:
                            import time
                            folio_generado = str(int(time.time()) % 10000)
                except Exception:
                    folio_generado = "1"
            
            # Crear transacción
            transaccion = TransaccionContable.objects.create(
                empresa=empresa,
                folio=folio_generado,
                concepto=concepto,
                tipo=tipo,
                fecha=fecha,
                tipo_personalizado=tipo_personalizado_obj,
                creado_por=request.user
            )
            
            # Procesar movimientos
            cuentas_debe = request.POST.getlist('cuenta_debe[]')
            montos_debe = request.POST.getlist('monto_debe[]')
            conceptos_debe = request.POST.getlist('concepto_debe[]')
            centros_debe = request.POST.getlist('centro_costo_debe[]')
            proyectos_debe = request.POST.getlist('proyecto_debe[]')
            
            cuentas_haber = request.POST.getlist('cuenta_haber[]')
            montos_haber = request.POST.getlist('monto_haber[]')
            conceptos_haber = request.POST.getlist('concepto_haber[]')
            centros_haber = request.POST.getlist('centro_costo_haber[]')
            proyectos_haber = request.POST.getlist('proyecto_haber[]')
            
            # Crear movimientos debe
            for i, cuenta_id in enumerate(cuentas_debe):
                if cuenta_id and montos_debe[i]:
                    cuenta = CuentaContable.objects.get(id=cuenta_id)
                    
                    # Obtener centro de costo si está especificado
                    centro_costo = None
                    if i < len(centros_debe) and centros_debe[i]:
                        try:
                            from apps.centros_costo.models import CentroCosto
                            centro_costo = CentroCosto.objects.get(
                                id=centros_debe[i],
                                empresa=empresa,
                                activo=True
                            )
                        except (CentroCosto.DoesNotExist, ImportError):
                            pass
                    
                    # Obtener proyecto si está especificado
                    proyecto = None
                    if i < len(proyectos_debe) and proyectos_debe[i]:
                        try:
                            from apps.centros_costo.models import Proyecto
                            proyecto = Proyecto.objects.get(
                                id=proyectos_debe[i],
                                empresa=empresa,
                                activo=True
                            )
                        except (Proyecto.DoesNotExist, ImportError):
                            pass
                    
                    MovimientoContable.objects.create(
                        transaccion=transaccion,
                        cuenta=cuenta,
                        debe=Decimal(montos_debe[i]),
                        haber=Decimal('0.00'),
                        concepto=conceptos_debe[i] if i < len(conceptos_debe) else concepto,
                        centro_costo=centro_costo,
                        proyecto=proyecto,
                        creado_por=request.user
                    )
            
            # Crear movimientos haber
            for i, cuenta_id in enumerate(cuentas_haber):
                if cuenta_id and montos_haber[i]:
                    cuenta = CuentaContable.objects.get(id=cuenta_id)
                    
                    # Obtener centro de costo si está especificado
                    centro_costo = None
                    if i < len(centros_haber) and centros_haber[i]:
                        try:
                            from apps.centros_costo.models import CentroCosto
                            centro_costo = CentroCosto.objects.get(
                                id=centros_haber[i],
                                empresa=empresa,
                                activo=True
                            )
                        except (CentroCosto.DoesNotExist, ImportError):
                            pass
                    
                    # Obtener proyecto si está especificado
                    proyecto = None
                    if i < len(proyectos_haber) and proyectos_haber[i]:
                        try:
                            from apps.centros_costo.models import Proyecto
                            proyecto = Proyecto.objects.get(
                                id=proyectos_haber[i],
                                empresa=empresa,
                                activo=True
                            )
                        except (Proyecto.DoesNotExist, ImportError):
                            pass
                    
                    MovimientoContable.objects.create(
                        transaccion=transaccion,
                        cuenta=cuenta,
                        debe=Decimal('0.00'),
                        haber=Decimal(montos_haber[i]),
                        concepto=conceptos_haber[i] if i < len(conceptos_haber) else concepto,
                        centro_costo=centro_costo,
                        proyecto=proyecto,
                        creado_por=request.user
                    )
            
            # Recalcular totales
            transaccion.calcular_totales()
            
            # Redirigir a lista de transacciones con mensaje de éxito
            messages.success(request, f'Transacción {transaccion.folio} creada correctamente')
            return redirect('/transacciones/')
            
        except Exception as e:
            messages.error(request, f'Error al crear transacción: {str(e)}')
    
    context = {
        'empresa': empresa,
        'cuentas': cuentas,
        'tipos_disponibles': tipos_disponibles,
        'centros_costo': centros_costo,
        'proyectos': proyectos,
        'proximo_folio': proximo_folio,
        'fecha_hoy': date.today().strftime('%Y-%m-%d'),
    }
    
    return render(request, 'transacciones/crear.html', context)