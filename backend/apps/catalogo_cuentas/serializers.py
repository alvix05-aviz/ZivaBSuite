from rest_framework import serializers
from .models import CuentaContable


class CuentaContableSerializer(serializers.ModelSerializer):
    """Serializer básico para CuentaContable MVP"""
    cuenta_padre_nombre = serializers.ReadOnlyField(source='cuenta_padre.nombre')
    ruta_completa = serializers.ReadOnlyField(source='get_ruta_completa')
    saldo_actual = serializers.ReadOnlyField(source='get_saldo_actual')
    subcuentas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CuentaContable
        fields = [
            'id', 'codigo', 'nombre', 'cuenta_padre', 'cuenta_padre_nombre',
            'tipo', 'naturaleza', 'nivel', 'afectable', 'ruta_completa',
            'saldo_actual', 'subcuentas_count'
        ]
        read_only_fields = ['creado_por', 'modificado_por']
        
    def get_subcuentas_count(self, obj):
        return obj.subcuentas.filter(activo=True).count()
        
    def validate(self, data):
        """Validaciones básicas MVP"""
        # Si tiene cuenta padre, verificar que no sea circular
        cuenta_padre = data.get('cuenta_padre')
        if cuenta_padre and self.instance:
            current = cuenta_padre
            while current:
                if current == self.instance:
                    raise serializers.ValidationError(
                        "No se puede crear una referencia circular"
                    )
                current = current.cuenta_padre
                
        return data


class CuentaContableTreeSerializer(serializers.ModelSerializer):
    """Serializer para vista en árbol de cuentas"""
    subcuentas = serializers.SerializerMethodField()
    
    class Meta:
        model = CuentaContable
        fields = [
            'id', 'codigo', 'nombre', 'tipo', 'naturaleza', 
            'nivel', 'afectable', 'subcuentas'
        ]
        
    def get_subcuentas(self, obj):
        """Obtiene subcuentas recursivamente"""
        subcuentas = obj.subcuentas.filter(activo=True).order_by('codigo')
        return CuentaContableTreeSerializer(subcuentas, many=True).data