from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Empresa, UsuarioEmpresa
from .serializers import (
    EmpresaSerializer, 
    UsuarioEmpresaSerializer, 
    UserEmpresasSerializer
)


class EmpresaViewSet(viewsets.ModelViewSet):
    """ViewSet básico para gestión de empresas MVP"""
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo empresas donde el usuario tiene acceso
        user_empresas = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
            activo=True
        ).values_list('empresa_id', flat=True)
        
        return Empresa.objects.filter(
            id__in=user_empresas,
            activo=True
        )


class UsuarioEmpresaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de relaciones Usuario-Empresa MVP"""
    serializer_class = UsuarioEmpresaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Obtener empresas donde el usuario tiene acceso
        user_empresas = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
            activo=True
        ).values_list('empresa_id', flat=True)
        
        queryset = UsuarioEmpresa.objects.filter(
            empresa_id__in=user_empresas,
            activo=True
        ).select_related('usuario', 'empresa')
        
        # Filtrar por empresa si se especifica
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
            
        return queryset
    
    def get_permissions(self):
        """Permisos específicos según la acción"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Solo propietarios y administradores pueden modificar
            return [IsAuthenticated()]
        return [IsAuthenticated()]
        
    def perform_create(self, serializer):
        """Al crear, verificar que el usuario tenga permisos de admin"""
        empresa_id = self.request.data.get('empresa')
        user_rol = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
            empresa_id=empresa_id,
            rol__in=['PROPIETARIO', 'ADMINISTRADOR'],
            activo=True
        ).first()
        
        if not user_rol:
            raise PermissionError('No tiene permisos para agregar usuarios a esta empresa')
        
        serializer.save(creado_por=self.request.user)
    
    def perform_update(self, serializer):
        """Al actualizar, verificar permisos"""
        empresa_id = serializer.instance.empresa_id
        user_rol = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
            empresa_id=empresa_id,
            rol__in=['PROPIETARIO', 'ADMINISTRADOR'],
            activo=True
        ).first()
        
        if not user_rol:
            raise PermissionError('No tiene permisos para modificar usuarios en esta empresa')
        
        serializer.save(modificado_por=self.request.user)


class MultiEmpresaViewSet(viewsets.ViewSet):
    """ViewSet para funcionalidades multiempresa MVP"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Lista de endpoints disponibles"""
        return Response({
            'endpoints': [
                'mis_empresas/ - GET - Obtiene empresas del usuario',
                'cambiar_empresa/ - POST - Cambia empresa activa',
                'empresa_actual/ - GET - Obtiene empresa actual'
            ]
        })
    
    @action(detail=False, methods=['get'])
    def mis_empresas(self, request):
        """Obtiene todas las empresas del usuario autenticado"""
        serializer = UserEmpresasSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def cambiar_empresa(self, request):
        """Cambia la empresa activa en la sesión"""
        empresa_id = request.data.get('empresa_id')
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            acceso = UsuarioEmpresa.objects.select_related('empresa').get(
                usuario=request.user,
                empresa_id=empresa_id,
                activo=True
            )
            
            # Cambiar empresa en la sesión
            request.session['empresa_id'] = empresa_id
            
            # Actualizar último acceso
            acceso.ultimo_acceso = timezone.now()
            acceso.save(update_fields=['ultimo_acceso'])
            
            return Response({
                'empresa': EmpresaSerializer(acceso.empresa).data,
                'rol': acceso.rol,
                'mensaje': f'Empresa cambiada a {acceso.empresa.nombre}'
            })
            
        except UsuarioEmpresa.DoesNotExist:
            return Response(
                {'error': 'No tiene acceso a esta empresa'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['get'])
    def empresa_actual(self, request):
        """Obtiene la empresa activa en la sesión actual"""
        if hasattr(request, 'empresa') and request.empresa:
            return Response({
                'empresa': EmpresaSerializer(request.empresa).data,
                'rol': getattr(request, 'rol', None)
            })
        else:
            return Response(
                {'mensaje': 'No hay empresa seleccionada'},
                status=status.HTTP_204_NO_CONTENT
            )


