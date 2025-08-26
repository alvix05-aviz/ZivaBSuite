from django.contrib import admin
from .models import SATCredentials, CFDIDownloadJob, CFDI, CFDIStatusLog

@admin.register(SATCredentials)
class SATCredentialsAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'rfc', 'validadas', 'fecha_validacion', 'fecha_vencimiento']
    list_filter = ['validadas', 'fecha_validacion', 'empresa']
    search_fields = ['rfc', 'empresa__nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'fecha_validacion']

@admin.register(CFDIDownloadJob)
class CFDIDownloadJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'empresa', 'fecha_inicio', 'fecha_fin', 'tipo_cfdi', 'estado', 'progreso_porcentaje', 'total_cfdi', 'procesados']
    list_filter = ['estado', 'tipo_cfdi', 'empresa', 'fecha_creacion']
    search_fields = ['solicitud_id', 'empresa__nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'progreso_porcentaje', 'fecha_inicio_proceso', 'fecha_fin_proceso']
    date_hierarchy = 'fecha_creacion'

@admin.register(CFDI)
class CFDIAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'serie', 'folio', 'fecha_emision', 'rfc_emisor', 'rfc_receptor', 'total', 'estado_sat', 'validado_sat']
    list_filter = ['estado_sat', 'tipo_comprobante', 'validado_sat', 'moneda', 'empresa']
    search_fields = ['uuid', 'serie', 'folio', 'nombre_emisor', 'nombre_receptor', 'rfc_emisor', 'rfc_receptor']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'es_emitido', 'es_recibido']
    date_hierarchy = 'fecha_emision'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'trabajo_descarga', 'uuid', 'serie', 'folio')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_certificacion', 'fecha_validacion')
        }),
        ('Emisor y Receptor', {
            'fields': ('rfc_emisor', 'nombre_emisor', 'rfc_receptor', 'nombre_receptor')
        }),
        ('Información Fiscal', {
            'fields': ('tipo_comprobante', 'estado_sat', 'moneda')
        }),
        ('Montos', {
            'fields': ('subtotal', 'iva', 'total')
        }),
        ('Archivos', {
            'fields': ('archivo_xml', 'archivo_pdf')
        }),
        ('Estado y Validación', {
            'fields': ('validado_sat',)
        }),
        ('Cancelación', {
            'fields': ('fecha_cancelacion', 'motivo_cancelacion'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion', 'es_emitido', 'es_recibido'),
            'classes': ('collapse',)
        })
    )

@admin.register(CFDIStatusLog)
class CFDIStatusLogAdmin(admin.ModelAdmin):
    list_display = ['cfdi', 'estado_anterior', 'estado_nuevo', 'fecha_consulta', 'fecha_creacion']
    list_filter = ['estado_anterior', 'estado_nuevo', 'fecha_consulta']
    search_fields = ['cfdi__uuid', 'cfdi__nombre_emisor', 'cfdi__nombre_receptor']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    date_hierarchy = 'fecha_consulta'
