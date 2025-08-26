from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CuentaContableViewSet, catalogo_root, crear_cuenta_ajax, aplicar_plantilla_predefinida

router = DefaultRouter()
router.register(r'cuentas', CuentaContableViewSet, basename='cuenta-contable')

urlpatterns = [
    path('', catalogo_root, name='catalogo-root'),
    path('crear-cuenta-ajax/', crear_cuenta_ajax, name='crear-cuenta-ajax'),
    path('aplicar-plantilla/', aplicar_plantilla_predefinida, name='aplicar-plantilla'),
    path('', include(router.urls)),
]