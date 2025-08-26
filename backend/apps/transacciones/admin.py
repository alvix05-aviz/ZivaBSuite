from django.contrib import admin
from .models import TransaccionContable, MovimientoContable


class MovimientoContableInline(admin.TabularInline):
    model = MovimientoContable
    extra = 2
    fields = ['cuenta', 'concepto', 'debe', 'haber']
    readonly_fields = []
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado in ['CONTABILIZADA', 'CANCELADA']:
            return ['cuenta', 'concepto', 'debe', 'haber']
        return []


@admin.register(TransaccionContable)
class TransaccionContableAdmin(admin.ModelAdmin):
    list_display = [
        'folio', 'fecha', 'tipo', 'concepto_truncado', 
        'estado', 'total_debe', 'total_haber', 'balanceada'
    ]
    list_filter = ['estado', 'tipo', 'fecha', 'empresa']
    search_fields = ['folio', 'concepto']
    readonly_fields = [
        'total_debe', 'total_haber', 'fecha_contabilizacion',
        'creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion'
    ]
    inlines = [MovimientoContableInline]
    date_hierarchy = 'fecha'
    ordering = ['-fecha', '-folio']
    
    fieldsets = (
        (None, {
            'fields': ('empresa', 'folio', 'fecha', 'tipo', 'concepto')
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_contabilizacion')
        }),
        ('Totales', {
            'fields': ('total_debe', 'total_haber'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def concepto_truncado(self, obj):
        return obj.concepto[:50] + '...' if len(obj.concepto) > 50 else obj.concepto
    concepto_truncado.short_description = 'Concepto'
    
    def balanceada(self, obj):
        return '✅' if obj.esta_balanceada() else '❌'
    balanceada.short_description = 'Balanceada'
    balanceada.admin_order_field = 'total_debe'
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        
        if obj and obj.estado in ['CONTABILIZADA', 'CANCELADA']:
            readonly.extend(['folio', 'fecha', 'tipo', 'concepto'])
            
        return readonly
        
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('empresa')
    
    actions = ['validar_transacciones', 'contabilizar_transacciones']
    
    def validar_transacciones(self, request, queryset):
        validadas = 0
        errores = []
        
        for transaccion in queryset.filter(estado='BORRADOR'):
            try:
                transaccion.validar()
                validadas += 1
            except Exception as e:
                errores.append(f'{transaccion.folio}: {str(e)}')
                
        if validadas:
            self.message_user(request, f'{validadas} transacciones validadas correctamente.')
        if errores:
            self.message_user(request, f'Errores: {"; ".join(errores)}', level='ERROR')
            
    validar_transacciones.short_description = 'Validar transacciones seleccionadas'
    
    def contabilizar_transacciones(self, request, queryset):
        contabilizadas = 0
        errores = []
        
        for transaccion in queryset.filter(estado='VALIDADA'):
            try:
                transaccion.contabilizar()
                contabilizadas += 1
            except Exception as e:
                errores.append(f'{transaccion.folio}: {str(e)}')
                
        if contabilizadas:
            self.message_user(request, f'{contabilizadas} transacciones contabilizadas correctamente.')
        if errores:
            self.message_user(request, f'Errores: {"; ".join(errores)}', level='ERROR')
            
    contabilizar_transacciones.short_description = 'Contabilizar transacciones seleccionadas'


@admin.register(MovimientoContable)
class MovimientoContableAdmin(admin.ModelAdmin):
    list_display = ['transaccion', 'cuenta', 'concepto_truncado', 'debe', 'haber', 'naturaleza']
    list_filter = ['transaccion__estado', 'transaccion__tipo', 'cuenta__tipo']
    search_fields = ['transaccion__folio', 'cuenta__codigo', 'cuenta__nombre', 'concepto']
    readonly_fields = ['creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def concepto_truncado(self, obj):
        concepto = obj.concepto or obj.transaccion.concepto
        return concepto[:30] + '...' if len(concepto) > 30 else concepto
    concepto_truncado.short_description = 'Concepto'
    
    def naturaleza(self, obj):
        return obj.get_naturaleza()
    naturaleza.short_description = 'D/H'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'transaccion', 'cuenta', 'transaccion__empresa'
        )