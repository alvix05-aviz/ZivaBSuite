from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SATCredentials, CFDIDownloadJob, CFDI, CFDIStatusLog

User = get_user_model()


class SATCredentialsSerializer(serializers.ModelSerializer):
    """
    Serializer para las credenciales SAT
    """
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    
    class Meta:
        model = SATCredentials
        fields = [
            'id', 'empresa', 'empresa_nombre', 'rfc', 
            'certificado_cer', 'llave_privada_key', 'password_llave',
            'validadas', 'fecha_validacion', 'fecha_vencimiento',
            'creado_por', 'creado_por_nombre', 'fecha_creacion', 'fecha_modificacion',
            'activo'
        ]
        read_only_fields = ['id', 'validadas', 'fecha_validacion', 'fecha_vencimiento', 
                           'creado_por', 'fecha_creacion', 'fecha_modificacion']
        extra_kwargs = {
            'password_llave': {'write_only': True}
        }
    
    def create(self, validated_data):
        # Asignar el usuario que crea el registro
        validated_data['creado_por'] = self.context['request'].user
        return super().create(validated_data)


class CFDIDownloadJobSerializer(serializers.ModelSerializer):
    """
    Serializer para trabajos de descarga CFDI
    """
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    progreso_porcentaje = serializers.IntegerField(read_only=True)
    duracion_proceso = serializers.SerializerMethodField()
    
    class Meta:
        model = CFDIDownloadJob
        fields = [
            'id', 'empresa', 'empresa_nombre', 'fecha_inicio', 'fecha_fin', 'tipo_cfdi',
            'estado', 'solicitud_id', 'total_cfdi', 'procesados', 'progreso_porcentaje',
            'archivo_descarga', 'mensaje_error', 'fecha_inicio_proceso', 'fecha_fin_proceso',
            'duracion_proceso', 'creado_por', 'creado_por_nombre', 
            'fecha_creacion', 'fecha_modificacion', 'activo'
        ]
        read_only_fields = [
            'id', 'estado', 'solicitud_id', 'total_cfdi', 'procesados', 
            'archivo_descarga', 'mensaje_error', 'fecha_inicio_proceso', 'fecha_fin_proceso',
            'creado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
    
    def get_duracion_proceso(self, obj):
        """Calcula la duración del proceso en minutos"""
        if obj.fecha_inicio_proceso and obj.fecha_fin_proceso:
            duracion = obj.fecha_fin_proceso - obj.fecha_inicio_proceso
            return round(duracion.total_seconds() / 60, 2)
        return None
    
    def create(self, validated_data):
        # Asignar el usuario que crea el registro
        validated_data['creado_por'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        """Validaciones personalizadas"""
        if data['fecha_inicio'] > data['fecha_fin']:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )
        
        # Verificar que no exceda 6 meses (limitación del SAT)
        diferencia = data['fecha_fin'] - data['fecha_inicio']
        if diferencia.days > 180:
            raise serializers.ValidationError(
                "El rango de fechas no puede ser mayor a 6 meses"
            )
        
        return data


class CFDIListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listado de CFDIs
    """
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    trabajo_descarga_id = serializers.IntegerField(source='trabajo_descarga.id', read_only=True)
    es_emitido = serializers.BooleanField(read_only=True)
    es_recibido = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CFDI
        fields = [
            'id', 'uuid', 'serie', 'folio', 'fecha_emision', 
            'rfc_emisor', 'nombre_emisor', 'rfc_receptor', 'nombre_receptor',
            'tipo_comprobante', 'estado_sat', 'subtotal', 'iva', 'total', 'moneda',
            'validado_sat', 'fecha_validacion', 'empresa_nombre', 'trabajo_descarga_id',
            'es_emitido', 'es_recibido', 'fecha_creacion'
        ]


class CFDIDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para CFDI individual
    """
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    trabajo_descarga_info = CFDIDownloadJobSerializer(source='trabajo_descarga', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    es_emitido = serializers.BooleanField(read_only=True)
    es_recibido = serializers.BooleanField(read_only=True)
    logs_estado_recientes = serializers.SerializerMethodField()
    
    class Meta:
        model = CFDI
        fields = [
            'id', 'empresa', 'empresa_nombre', 'trabajo_descarga', 'trabajo_descarga_info',
            'uuid', 'serie', 'folio', 'fecha_emision', 'fecha_certificacion',
            'rfc_emisor', 'nombre_emisor', 'rfc_receptor', 'nombre_receptor',
            'tipo_comprobante', 'estado_sat', 'subtotal', 'iva', 'total', 'moneda',
            'archivo_xml', 'archivo_pdf', 'fecha_cancelacion', 'motivo_cancelacion',
            'validado_sat', 'fecha_validacion', 'es_emitido', 'es_recibido',
            'logs_estado_recientes', 'creado_por', 'creado_por_nombre', 
            'fecha_creacion', 'fecha_modificacion', 'activo'
        ]
        read_only_fields = [
            'id', 'uuid', 'serie', 'folio', 'fecha_emision', 'fecha_certificacion',
            'rfc_emisor', 'nombre_emisor', 'rfc_receptor', 'nombre_receptor',
            'tipo_comprobante', 'subtotal', 'iva', 'total', 'moneda', 'archivo_xml',
            'validado_sat', 'fecha_validacion', 'creado_por', 'fecha_creacion', 
            'fecha_modificacion'
        ]
    
    def get_logs_estado_recientes(self, obj):
        """Obtiene los últimos 5 cambios de estado"""
        logs = obj.logs_estado.all()[:5]
        return CFDIStatusLogSerializer(logs, many=True).data


class CFDIStatusLogSerializer(serializers.ModelSerializer):
    """
    Serializer para logs de estado de CFDI
    """
    cfdi_uuid = serializers.CharField(source='cfdi.uuid', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.get_full_name', read_only=True)
    
    class Meta:
        model = CFDIStatusLog
        fields = [
            'id', 'cfdi', 'cfdi_uuid', 'estado_anterior', 'estado_nuevo',
            'fecha_consulta', 'respuesta_sat', 'creado_por', 'creado_por_nombre',
            'fecha_creacion'
        ]
        read_only_fields = ['id', 'creado_por', 'fecha_creacion']


class CFDIDownloadJobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para crear trabajos de descarga
    """
    class Meta:
        model = CFDIDownloadJob
        fields = [
            'empresa', 'fecha_inicio', 'fecha_fin', 'tipo_cfdi'
        ]
    
    def validate(self, data):
        """Validaciones específicas para creación"""
        # Validar que la empresa tenga credenciales SAT válidas
        empresa = data['empresa']
        
        # Verificar si el usuario tiene acceso a la empresa
        request = self.context.get('request')
        if request and hasattr(request, 'empresa'):
            if request.empresa != empresa:
                raise serializers.ValidationError(
                    "No tiene permisos para crear trabajos para esta empresa"
                )
        
        try:
            credentials = empresa.credenciales_sat
            if not credentials.validadas:
                raise serializers.ValidationError(
                    "La empresa no tiene credenciales SAT válidas configuradas"
                )
        except SATCredentials.DoesNotExist:
            raise serializers.ValidationError(
                "La empresa no tiene credenciales SAT configuradas"
            )
        
        # Validar fechas
        if data['fecha_inicio'] > data['fecha_fin']:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )
        
        # Verificar que no exceda 6 meses
        diferencia = data['fecha_fin'] - data['fecha_inicio']
        if diferencia.days > 180:
            raise serializers.ValidationError(
                "El rango de fechas no puede ser mayor a 6 meses"
            )
        
        # Verificar que no haya trabajos activos para el mismo período
        trabajos_activos = CFDIDownloadJob.objects.filter(
            empresa=empresa,
            estado__in=['PENDIENTE', 'PROCESANDO'],
            fecha_inicio=data['fecha_inicio'],
            fecha_fin=data['fecha_fin'],
            tipo_cfdi=data['tipo_cfdi']
        )
        
        if trabajos_activos.exists():
            raise serializers.ValidationError(
                "Ya existe un trabajo de descarga activo para este período y tipo"
            )
        
        return data
    
    def create(self, validated_data):
        validated_data['creado_por'] = self.context['request'].user
        return super().create(validated_data)


class SATCredentialsUploadSerializer(serializers.ModelSerializer):
    """
    Serializer específico para subir credenciales SAT
    """
    class Meta:
        model = SATCredentials
        fields = [
            'empresa', 'rfc', 'certificado_cer', 'llave_privada_key', 'password_llave'
        ]
    
    def validate_rfc(self, value):
        """Validar formato del RFC"""
        import re
        rfc_pattern = r'^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{2}[0-9A]$'
        if not re.match(rfc_pattern, value.upper()):
            raise serializers.ValidationError("Formato de RFC inválido")
        return value.upper()
    
    def validate_certificado_cer(self, value):
        """Validar que el archivo sea un certificado válido"""
        if not value.name.endswith('.cer'):
            raise serializers.ValidationError("El archivo debe tener extensión .cer")
        return value
    
    def validate_llave_privada_key(self, value):
        """Validar que el archivo sea una llave privada válida"""
        if not value.name.endswith('.key'):
            raise serializers.ValidationError("El archivo debe tener extensión .key")
        return value
    
    def create(self, validated_data):
        validated_data['creado_por'] = self.context['request'].user
        return super().create(validated_data)