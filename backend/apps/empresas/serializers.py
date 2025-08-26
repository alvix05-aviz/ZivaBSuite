from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Empresa, UsuarioEmpresa

User = get_user_model()


class EmpresaSerializer(serializers.ModelSerializer):
    """Serializer básico para Empresa MVP"""
    usuarios_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = [
            'id', 'nombre', 'nombre_comercial', 'rfc', 
            'limite_usuarios', 'usuarios_count'
        ]
        read_only_fields = ['creado_por', 'modificado_por']
        
    def get_usuarios_count(self, obj):
        return obj.usuarios_asignados.filter(activo=True).count()


class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    """Serializer para relación Usuario-Empresa MVP"""
    usuario_nombre = serializers.ReadOnlyField(source='usuario.get_full_name')
    usuario_email = serializers.ReadOnlyField(source='usuario.email')
    empresa_nombre = serializers.ReadOnlyField(source='empresa.nombre')
    
    class Meta:
        model = UsuarioEmpresa
        fields = [
            'id', 'usuario', 'empresa', 'rol', 'empresa_default',
            'ultimo_acceso', 'usuario_nombre', 'usuario_email', 'empresa_nombre', 'activo'
        ]
        read_only_fields = ['creado_por', 'modificado_por', 'ultimo_acceso']
        
    def validate(self, data):
        """Validación básica MVP"""
        if 'empresa' in data:
            empresa = data['empresa']
            usuarios_activos = UsuarioEmpresa.objects.filter(
                empresa=empresa,
                activo=True
            ).count()
            
            if usuarios_activos >= empresa.limite_usuarios:
                raise serializers.ValidationError(
                    f"La empresa ha alcanzado el límite de {empresa.limite_usuarios} usuarios"
                )
                
        return data


class UserEmpresasSerializer(serializers.ModelSerializer):
    """Serializer para usuario con sus empresas MVP"""
    empresas = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'empresas']
        
    def get_empresas(self, obj):
        """Empresas a las que tiene acceso el usuario"""
        accesos = UsuarioEmpresa.objects.filter(
            usuario=obj,
            activo=True
        ).select_related('empresa')
        
        return [
            {
                'id': acceso.empresa.id,
                'nombre': acceso.empresa.nombre,
                'rfc': acceso.empresa.rfc,
                'rol': acceso.rol,
                'es_default': acceso.empresa_default
            }
            for acceso in accesos
        ]