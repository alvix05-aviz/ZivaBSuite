from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from celery.result import AsyncResult
from .models import SATCredentials, CFDIDownloadJob, CFDI, CFDIStatusLog
from .serializers import (
    SATCredentialsSerializer, SATCredentialsUploadSerializer,
    CFDIDownloadJobSerializer, CFDIDownloadJobCreateSerializer,
    CFDIListSerializer, CFDIDetailSerializer, CFDIStatusLogSerializer
)
from .tasks import process_massive_download, verify_cfdi_status, validate_sat_credentials
import logging

logger = logging.getLogger(__name__)


class SATCredentialsViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar credenciales SAT
    """
    queryset = SATCredentials.objects.all()
    serializer_class = SATCredentialsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'validadas', 'activo']
    
    def get_queryset(self):
        """Filtrar por empresa actual del usuario"""
        queryset = super().get_queryset()
        if hasattr(self.request, 'empresa') and self.request.empresa:
            queryset = queryset.filter(empresa=self.request.empresa)
        return queryset
    
    def get_serializer_class(self):
        """Usar serializer específico para upload"""
        if self.action == 'create':
            return SATCredentialsUploadSerializer
        return super().get_serializer_class()
    
    @action(detail=True, methods=['post'])
    def validate_credentials(self, request, pk=None):
        """
        Validar credenciales SAT usando Celery
        """
        credentials = self.get_object()
        
        # Lanzar tarea de validación
        task = validate_sat_credentials.delay(credentials.id)
        
        return Response({
            'message': 'Validación iniciada',
            'task_id': task.id,
            'status': 'PENDING'
        })
    
    @action(detail=False, methods=['get'])
    def validation_status(self, request):
        """
        Consultar estado de validación por task_id
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_result = AsyncResult(task_id)
        
        return Response({
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        })


class CFDIDownloadJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar trabajos de descarga CFDI
    """
    queryset = CFDIDownloadJob.objects.all()
    serializer_class = CFDIDownloadJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['empresa', 'estado', 'tipo_cfdi']
    search_fields = ['solicitud_id', 'mensaje_error']
    ordering_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_fin']
    ordering = ['-fecha_creacion']
    
    def get_queryset(self):
        """Filtrar por empresa actual del usuario"""
        queryset = super().get_queryset()
        if hasattr(self.request, 'empresa') and self.request.empresa:
            queryset = queryset.filter(empresa=self.request.empresa)
        return queryset
    
    def get_serializer_class(self):
        """Usar serializer específico para creación"""
        if self.action == 'create':
            return CFDIDownloadJobCreateSerializer
        return super().get_serializer_class()
    
    def perform_create(self, serializer):
        """Crear trabajo y lanzar tarea de descarga"""
        job = serializer.save()
        
        # Lanzar tarea de descarga masiva
        task = process_massive_download.delay(job.id)
        
        # Opcional: guardar task_id para seguimiento
        logger.info(f"Tarea de descarga iniciada: {task.id} para job {job.id}")
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar trabajo de descarga
        """
        job = self.get_object()
        
        if job.estado in ['COMPLETADO', 'ERROR']:
            return Response(
                {'error': 'No se puede cancelar un trabajo ya finalizado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.estado = 'CANCELADO'
        job.save()
        
        return Response({'message': 'Trabajo cancelado exitosamente'})
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Obtener progreso del trabajo de descarga
        """
        job = self.get_object()
        
        response_data = {
            'job_id': job.id,
            'estado': job.estado,
            'progreso_porcentaje': job.progreso_porcentaje,
            'total_cfdi': job.total_cfdi,
            'procesados': job.procesados,
            'mensaje_error': job.mensaje_error
        }
        
        # Si hay task_id guardado, obtener progreso de Celery
        # Por ahora, usar la información del modelo
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Estadísticas de trabajos de descarga
        """
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pendientes': queryset.filter(estado='PENDIENTE').count(),
            'procesando': queryset.filter(estado='PROCESANDO').count(),
            'completados': queryset.filter(estado='COMPLETADO').count(),
            'errores': queryset.filter(estado='ERROR').count(),
            'cancelados': queryset.filter(estado='CANCELADO').count(),
        }
        
        return Response(stats)


class CFDIViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar CFDIs descargados
    """
    queryset = CFDI.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'empresa', 'estado_sat', 'tipo_comprobante', 'validado_sat',
        'rfc_emisor', 'rfc_receptor'
    ]
    search_fields = [
        'uuid', 'serie', 'folio', 'nombre_emisor', 'nombre_receptor'
    ]
    ordering_fields = [
        'fecha_emision', 'fecha_certificacion', 'total', 'fecha_creacion'
    ]
    ordering = ['-fecha_emision']
    
    def get_queryset(self):
        """Filtrar por empresa actual del usuario"""
        queryset = super().get_queryset()
        if hasattr(self.request, 'empresa') and self.request.empresa:
            queryset = queryset.filter(empresa=self.request.empresa)
        
        # Filtros adicionales por query params
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        
        if fecha_desde:
            queryset = queryset.filter(fecha_emision__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
        
        # Filtro por tipo (emitidos/recibidos)
        tipo_filtro = self.request.query_params.get('tipo')
        if tipo_filtro == 'emitidos':
            queryset = queryset.filter(rfc_emisor=self.request.empresa.rfc)
        elif tipo_filtro == 'recibidos':
            queryset = queryset.filter(rfc_receptor=self.request.empresa.rfc)
        
        return queryset
    
    def get_serializer_class(self):
        """Usar serializer detallado para retrieve"""
        if self.action == 'retrieve':
            return CFDIDetailSerializer
        return CFDIListSerializer
    
    @action(detail=False, methods=['post'])
    def verify_status(self, request):
        """
        Verificar estado de CFDIs seleccionados en el SAT
        """
        cfdi_ids = request.data.get('cfdi_ids', [])
        
        if not cfdi_ids:
            return Response(
                {'error': 'cfdi_ids es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filtrar solo CFDIs de la empresa actual
        queryset = self.get_queryset().filter(id__in=cfdi_ids)
        valid_ids = list(queryset.values_list('id', flat=True))
        
        if not valid_ids:
            return Response(
                {'error': 'No se encontraron CFDIs válidos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lanzar tarea de verificación
        task = verify_cfdi_status.delay(valid_ids)
        
        return Response({
            'message': 'Verificación iniciada',
            'task_id': task.id,
            'cfdi_count': len(valid_ids)
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Resumen de CFDIs por estado, tipo, etc.
        """
        queryset = self.get_queryset()
        
        # Resumen por estado SAT
        estados = {}
        for estado, nombre in CFDI.ESTADO_CHOICES:
            estados[estado] = {
                'nombre': nombre,
                'count': queryset.filter(estado_sat=estado).count()
            }
        
        # Resumen por tipo de comprobante
        tipos = {}
        for tipo, nombre in CFDI.TIPO_CHOICES:
            tipos[tipo] = {
                'nombre': nombre,
                'count': queryset.filter(tipo_comprobante=tipo).count()
            }
        
        # Montos totales
        from django.db.models import Sum
        montos = queryset.aggregate(
            total_subtotal=Sum('subtotal'),
            total_iva=Sum('iva'),
            total_general=Sum('total')
        )
        
        # CFDIs emitidos vs recibidos
        empresa_rfc = getattr(self.request.empresa, 'rfc', '')
        emitidos = queryset.filter(rfc_emisor=empresa_rfc).count()
        recibidos = queryset.filter(rfc_receptor=empresa_rfc).count()
        
        return Response({
            'total_cfdi': queryset.count(),
            'estados': estados,
            'tipos_comprobante': tipos,
            'montos': montos,
            'emitidos': emitidos,
            'recibidos': recibidos,
            'validados': queryset.filter(validado_sat=True).count(),
            'pendientes_validacion': queryset.filter(validado_sat=False).count()
        })
    
    @action(detail=True, methods=['get'])
    def download_xml(self, request, pk=None):
        """
        Descargar archivo XML del CFDI
        """
        cfdi = self.get_object()
        
        if not cfdi.archivo_xml:
            return Response(
                {'error': 'No hay archivo XML disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from django.http import FileResponse
        response = FileResponse(
            cfdi.archivo_xml.open('rb'),
            content_type='application/xml'
        )
        response['Content-Disposition'] = f'attachment; filename="{cfdi.uuid}.xml"'
        
        return response
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Descargar archivo PDF del CFDI
        """
        cfdi = self.get_object()
        
        if not cfdi.archivo_pdf:
            return Response(
                {'error': 'No hay archivo PDF disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from django.http import FileResponse
        response = FileResponse(
            cfdi.archivo_pdf.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{cfdi.uuid}.pdf"'
        
        return response


class CFDIStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar logs de estado de CFDI
    """
    queryset = CFDIStatusLog.objects.all()
    serializer_class = CFDIStatusLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['cfdi', 'estado_anterior', 'estado_nuevo']
    ordering = ['-fecha_creacion']
    
    def get_queryset(self):
        """Filtrar por empresa actual del usuario"""
        queryset = super().get_queryset()
        if hasattr(self.request, 'empresa') and self.request.empresa:
            queryset = queryset.filter(cfdi__empresa=self.request.empresa)
        return queryset


# Vista para renderizar templates HTML (opcional)
def sat_credentials_view(request):
    """
    Vista para la página de gestión de credenciales SAT
    """
    return render(request, 'sat_integration/credentials.html')


def cfdi_dashboard_view(request):
    """
    Vista para el dashboard de CFDIs
    """
    return render(request, 'sat_integration/dashboard.html')


def cfdi_downloads_view(request):
    """
    Vista para la página de descargas masivas
    """
    return render(request, 'sat_integration/downloads.html')
