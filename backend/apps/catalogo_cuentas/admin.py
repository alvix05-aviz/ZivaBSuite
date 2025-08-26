from django.contrib import admin
from .models import CuentaContable


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'naturaleza', 'nivel', 'afectable', 'activo']
    list_filter = ['tipo', 'naturaleza', 'nivel', 'afectable', 'activo']
    search_fields = ['codigo', 'nombre']
    readonly_fields = ['creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion']
    ordering = ['codigo']
    
    fieldsets = (
        (None, {
            'fields': ('empresa', 'codigo', 'nombre', 'cuenta_padre')
        }),
        ('Clasificación', {
            'fields': ('tipo', 'naturaleza', 'nivel', 'afectable')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('empresa', 'cuenta_padre')