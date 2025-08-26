from django.contrib import admin
from .models import Empresa, UsuarioEmpresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'rfc', 'limite_usuarios', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'rfc']
    readonly_fields = ['creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion']


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa', 'rol', 'empresa_default', 'ultimo_acceso', 'activo']
    list_filter = ['rol', 'empresa_default', 'activo']
    search_fields = ['usuario__username', 'empresa__nombre']
    readonly_fields = ['creado_por', 'modificado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario', 'empresa')