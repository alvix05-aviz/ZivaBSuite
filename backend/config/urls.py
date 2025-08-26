from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.shortcuts import render
from django.http import HttpResponse

from apps.core.views import (
    dashboard, transacciones_view, catalogo_view, 
    reportes_view, seleccionar_empresa, logout_view, configuracion_view,
    configuracion_empresas_view, configuracion_catalogo_view, configuracion_transacciones_view,
    configuracion_transacciones_get, configuracion_placeholder_view, configuracion_general_view
)
from apps.transacciones.views import crear_transaccion_view

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API Root - Lista de endpoints disponibles"""
    # Si el request acepta HTML (navegador), devolver página HTML
    if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>ZivaBSuite API</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                h1 {{ color: #2c3e50; }}
                .endpoint {{ margin: 15px 0; padding: 15px; background: #f1f2f6; border-radius: 5px; }}
                .method {{ font-weight: bold; color: #27ae60; }}
                .url {{ color: #3498db; font-family: monospace; }}
                .back-link {{ margin-bottom: 20px; }}
                .back-link a {{ color: #7f8c8d; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="back-link"><a href="/">← Volver al inicio</a></div>
                <h1>🔌 ZivaBSuite API</h1>
                <p><strong>Versión:</strong> 3.0.0-MVP | <strong>Estado:</strong> ✅ Operacional</p>
                
                <h2>📡 Endpoints Disponibles</h2>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/empresas/">/api/empresas/</a></div>
                    <p>Gestión de empresas y sistema multiempresa</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/empresas/multiempresa/">/api/empresas/multiempresa/</a></div>
                    <p>Funciones multiempresa (requiere autenticación)</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/catalogo/">/api/catalogo/</a></div>
                    <p>Catálogo de cuentas contables</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/catalogo/cuentas/">/api/catalogo/cuentas/</a></div>
                    <p>CRUD de cuentas contables (requiere autenticación)</p>
                </div>
                
                <div class="endpoint">
                    <div class="method">GET</div>
                    <div class="url"><a href="/api/catalogo/cuentas/arbol/">/api/catalogo/cuentas/arbol/</a></div>
                    <p>Vista en árbol del catálogo de cuentas</p>
                </div>
                
                <h2>🔑 Autenticación</h2>
                <p>Para endpoints protegidos, usa:</p>
                <p><strong>Header:</strong> <code>Authorization: Token 1e0b0f1c08f1359f4c76e55c2fcba894976aeba7</code></p>
                
                <h2>📋 Enlaces Útiles</h2>
                <p><a href="/admin/">Panel de Administración</a></p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)
    
    # Para requests JSON, devolver respuesta API tradicional
    return Response({
        'message': 'ZivaBSuite API',
        'version': '3.0.0-MVP',
        'endpoints': {
            'home': request.build_absolute_uri('/'),
            'admin': request.build_absolute_uri('/admin/'),
            'empresas': request.build_absolute_uri('/api/empresas/'),
            'catalogo': request.build_absolute_uri('/api/catalogo/'),
            'multiempresa': request.build_absolute_uri('/api/empresas/multiempresa/'),
        },
        'status': 'operational'
    })

def home_view(request):
    """Página principal de ZivaBSuite"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZivaBSuite - Sistema Contable</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .section h2 { color: #34495e; margin-top: 0; }
            .links { list-style: none; padding: 0; }
            .links li { margin: 10px 0; }
            .links a { text-decoration: none; color: #3498db; font-weight: 500; }
            .links a:hover { color: #2980b9; }
            .status { text-align: center; margin: 20px 0; }
            .stage { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .stage-complete { background: #d5f4e6; border-left: 4px solid #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 ZivaBSuite - Sistema Contable</h1>
            
            <div class="section">
                <h2>📋 Administración</h2>
                <ul class="links">
                    <li><a href="/admin/">🛡️ Panel de Administración</a></li>
                    <li><a href="/admin/empresas/empresa/">🏢 Gestión de Empresas</a></li>
                    <li><a href="/admin/empresas/usuarioempresa/">👥 Usuarios por Empresa</a></li>
                    <li><a href="/admin/catalogo_cuentas/cuentacontable/">📊 Catálogo de Cuentas</a></li>
                </ul>
            </div>

            <div class="section">
                <h2>🔌 API Endpoints</h2>
                <ul class="links">
                    <li><a href="/api/">📡 API Root</a></li>
                    <li><a href="/api/empresas/">🏢 API Empresas</a></li>
                    <li><a href="/api/catalogo/">📊 API Catálogo de Cuentas</a></li>
                    <li><a href="/api/transacciones/">💰 API Transacciones</a></li>
                    <li><a href="/api/reportes/">📈 API Reportes</a></li>
                </ul>
            </div>

            <div class="section">
                <h2>📈 Estado del Proyecto</h2>
                <div class="stage stage-complete">
                    <strong>✅ Etapa 1:</strong> Infraestructura y Modelos Base - Completada
                </div>
                <div class="stage stage-complete">
                    <strong>✅ Etapa 2:</strong> Sistema Multiempresa MVP - Completada
                </div>
                <div class="stage stage-complete">
                    <strong>✅ Etapa 3:</strong> Catálogo de Cuentas MVP - Completada
                </div>
                <div class="stage stage-complete">
                    <strong>✅ Etapa 4:</strong> Sistema de Transacciones MVP - Completada
                </div>
                <div class="stage stage-complete">
                    <strong>✅ Etapa 5:</strong> Reportes Contables MVP - Completada
                </div>
            </div>

            <div class="status">
                <p><strong>Estado:</strong> ✅ Operacional</p>
                <p><strong>Versión:</strong> 5.0.0-MVP</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)

urlpatterns = [
    # Frontend moderno
    path('', dashboard, name='dashboard'),
    path('transacciones/', transacciones_view, name='transacciones'),
    path('transacciones/crear/', crear_transaccion_view, name='crear_transaccion'),
    path('catalogo/', catalogo_view, name='catalogo'),
    path('reportes/', reportes_view, name='reportes'),
    path('configuracion/', configuracion_view, name='configuracion'),
    path('configuracion/general/', configuracion_general_view, name='configuracion_general'),
    path('configuracion/empresas/', configuracion_empresas_view, name='configuracion_empresas'),
    path('configuracion/catalogo/', configuracion_catalogo_view, name='configuracion_catalogo'),
    path('configuracion/transacciones/', configuracion_transacciones_view, name='configuracion_transacciones'),
    path('configuracion/transacciones/get/<int:tipo_id>/', configuracion_transacciones_get, name='configuracion_transacciones_get'),
    path('configuracion/<str:seccion>/', configuracion_placeholder_view, name='configuracion_placeholder'),
    path('seleccionar-empresa/', seleccionar_empresa, name='seleccionar_empresa'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Landing page original
    path('home/', home_view, name='home'),
    
    # Admin y API
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/core/', include('apps.core.urls')),
    path('api/empresas/', include('apps.empresas.urls')),
    path('api/catalogo/', include('apps.catalogo_cuentas.urls')),
    path('api/transacciones/', include('apps.transacciones.urls')),
    path('api/reportes/', include('apps.reportes.urls')),
    path('api/centros-costo/', include('apps.centros_costo.urls')),
    path('api/sat/', include('apps.sat_integration.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug Toolbar en desarrollo
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns