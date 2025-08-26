from rest_framework import serializers
from .models import CentroCosto, Proyecto

class CentroCostoSerializer(serializers.ModelSerializer):
    ruta_completa = serializers.ReadOnlyField(source='get_ruta_completa')
    tipo = serializers.StringRelatedField()

    class Meta:
        model = CentroCosto
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'tipo',
            'centro_padre', 'permite_movimientos', 'color_interfaz',
            'ruta_completa', 'activo'
        ]
        read_only_fields = ['id']

class ProyectoSerializer(serializers.ModelSerializer):
    dias_transcurridos = serializers.ReadOnlyField()
    progreso_tiempo = serializers.ReadOnlyField()
    
    class Meta:
        model = Proyecto
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'fecha_inicio',
            'fecha_fin_estimada', 'fecha_fin_real', 'estado', 'presupuesto',
            'centro_costo', 'responsable', 'color_interfaz', 'dias_transcurridos',
            'progreso_tiempo', 'activo'
        ]
        read_only_fields = ['id', 'dias_transcurridos', 'progreso_tiempo']
