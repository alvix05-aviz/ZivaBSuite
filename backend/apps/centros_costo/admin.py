from django.contrib import admin
from .models import CentroCosto, Proyecto

@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'centro_padre', 'empresa', 'activo']
    list_filter = ['tipo', 'empresa', 'activo']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['empresa', 'codigo']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'codigo', 'nombre', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('tipo', 'centro_padre')
        }),
        ('Configuración', {
            'fields': ('permite_movimientos', 'color_interfaz', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por'),
            'classes': ('collapse',)
        })
    )

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'estado', 'fecha_inicio', 'fecha_fin_estimada', 'presupuesto', 'empresa']
    list_filter = ['estado', 'empresa', 'fecha_inicio']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering = ['empresa', '-fecha_inicio']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'codigo', 'nombre', 'descripcion')
        }),
        ('Planificación', {
            'fields': ('fecha_inicio', 'fecha_fin_estimada', 'fecha_fin_real', 'estado')
        }),
        ('Presupuesto y Asignación', {
            'fields': ('presupuesto', 'centro_costo', 'responsable')
        }),
        ('Configuración', {
            'fields': ('color_interfaz', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'modificado_por'),
            'classes': ('collapse',)
        })
    )
