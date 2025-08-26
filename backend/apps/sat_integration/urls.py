from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configurar router para la API
router = DefaultRouter()
router.register(r'credentials', views.SATCredentialsViewSet, basename='sat-credentials')
router.register(r'download-jobs', views.CFDIDownloadJobViewSet, basename='cfdi-download-jobs')
router.register(r'cfdi', views.CFDIViewSet, basename='cfdi')
router.register(r'status-logs', views.CFDIStatusLogViewSet, basename='cfdi-status-logs')

# URLs de la aplicación
urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Vistas HTML (opcional)
    path('credentials/', views.sat_credentials_view, name='sat-credentials'),
    path('dashboard/', views.cfdi_dashboard_view, name='cfdi-dashboard'),
    path('downloads/', views.cfdi_downloads_view, name='cfdi-downloads'),
]

# Para desarrollo: agregar nombres explícitos a las rutas de la API
app_name = 'sat_integration'