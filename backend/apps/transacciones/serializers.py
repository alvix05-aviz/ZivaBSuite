from rest_framework import serializers
from decimal import Decimal
from .models import TransaccionContable, MovimientoContable


class MovimientoContableSerializer(serializers.ModelSerializer):
    """Serializer para movimientos contables"""
    cuenta_codigo = serializers.ReadOnlyField(source='cuenta.codigo')
    cuenta_nombre = serializers.ReadOnlyField(source='cuenta.nombre')
    centro_costo_codigo = serializers.ReadOnlyField(source='centro_costo.codigo')
    centro_costo_nombre = serializers.ReadOnlyField(source='centro_costo.nombre')
    proyecto_codigo = serializers.ReadOnlyField(source='proyecto.codigo')
    proyecto_nombre = serializers.ReadOnlyField(source='proyecto.nombre')
    importe = serializers.ReadOnlyField(source='get_importe')
    naturaleza = serializers.ReadOnlyField(source='get_naturaleza')
    
    class Meta:
        model = MovimientoContable
        fields = [
            'id', 'cuenta', 'cuenta_codigo', 'cuenta_nombre',
            'centro_costo', 'centro_costo_codigo', 'centro_costo_nombre',
            'proyecto', 'proyecto_codigo', 'proyecto_nombre',
            'concepto', 'debe', 'haber', 'importe', 'naturaleza'
        ]
        
    def validate(self, data):
        """Validaciones del movimiento"""
        debe = data.get('debe', Decimal('0.00'))
        haber = data.get('haber', Decimal('0.00'))
        
        if debe > 0 and haber > 0:
            raise serializers.ValidationError(
                "Un movimiento no puede tener tanto debe como haber"
            )
            
        if debe == 0 and haber == 0:
            raise serializers.ValidationError(
                "Un movimiento debe tener importe en debe o haber"
            )
            
        return data


class TransaccionContableSerializer(serializers.ModelSerializer):
    """Serializer básico para transacciones contables"""
    movimientos = MovimientoContableSerializer(many=True, read_only=True)
    balanceada = serializers.ReadOnlyField(source='esta_balanceada')
    total_movimientos = serializers.SerializerMethodField()
    empresa_nombre = serializers.ReadOnlyField(source='empresa.nombre')
    
    class Meta:
        model = TransaccionContable
        fields = [
            'id', 'folio', 'fecha', 'tipo', 'concepto', 'estado',
            'total_debe', 'total_haber', 'balanceada', 'total_movimientos',
            'fecha_contabilizacion', 'empresa_nombre', 'movimientos'
        ]
        read_only_fields = [
            'total_debe', 'total_haber', 'fecha_contabilizacion'
        ]
        
    def get_total_movimientos(self, obj):
        return obj.movimientos.count()
        
    def validate_folio(self, value):
        """Validar que el folio sea único por empresa"""
        empresa = self.context['request'].user.empresas_asignadas.first().empresa if hasattr(self.context['request'], 'user') else None
        
        if empresa:
            queryset = TransaccionContable.objects.filter(
                empresa=empresa,
                folio=value
            ).defer('tipo_personalizado')
            
            # Excluir la instancia actual en caso de actualización
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
                
            if queryset.exists():
                raise serializers.ValidationError(
                    f"Ya existe una transacción con folio '{value}' en esta empresa"
                )
                
        return value


class TransaccionContableCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear transacciones con movimientos"""
    movimientos = MovimientoContableSerializer(many=True)
    
    class Meta:
        model = TransaccionContable
        fields = [
            'folio', 'fecha', 'tipo', 'concepto', 'movimientos'
        ]
        
    def create(self, validated_data):
        """Crear transacción con sus movimientos"""
        movimientos_data = validated_data.pop('movimientos')
        
        # Obtener empresa del contexto o del usuario
        request = self.context.get('request')
        if hasattr(request, 'empresa') and request.empresa:
            empresa = request.empresa
        else:
            # Fallback a primera empresa del usuario
            from apps.empresas.models import UsuarioEmpresa
            acceso = UsuarioEmpresa.objects.filter(
                usuario=request.user,
                activo=True
            ).first()
            empresa = acceso.empresa if acceso else None
            
        if not empresa:
            raise serializers.ValidationError("No se pudo determinar la empresa")
            
        # Crear la transacción
        transaccion = TransaccionContable.objects.create(
            empresa=empresa,
            **validated_data
        )
        # Asignar creado_por después de la creación
        transaccion.creado_por = request.user
        transaccion.save()
        
        # Crear los movimientos
        for movimiento_data in movimientos_data:
            movimiento = MovimientoContable.objects.create(
                transaccion=transaccion,
                **movimiento_data
            )
            movimiento.creado_por = request.user
            movimiento.save()
            
        # Recalcular totales
        transaccion.calcular_totales()
        
        return transaccion
        
    def validate(self, data):
        """Validaciones de la transacción completa"""
        movimientos_data = data.get('movimientos', [])
        
        if len(movimientos_data) < 2:
            raise serializers.ValidationError(
                "Una transacción debe tener al menos 2 movimientos"
            )
            
        # Validar balance
        total_debe = sum(m.get('debe', 0) for m in movimientos_data)
        total_haber = sum(m.get('haber', 0) for m in movimientos_data)
        
        if total_debe != total_haber:
            raise serializers.ValidationError(
                f"La transacción no está balanceada. Debe: {total_debe}, Haber: {total_haber}"
            )
            
        return data


class TransaccionContableListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    balanceada = serializers.ReadOnlyField(source='esta_balanceada')
    total_movimientos = serializers.SerializerMethodField()
    
    class Meta:
        model = TransaccionContable
        fields = [
            'id', 'folio', 'fecha', 'tipo', 'concepto', 'estado',
            'total_debe', 'total_haber', 'balanceada', 'total_movimientos'
        ]
        
    def get_total_movimientos(self, obj):
        return obj.movimientos.count()