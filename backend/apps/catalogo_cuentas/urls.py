from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CuentaContableViewSet, catalogo_root, crear_cuenta_ajax

router = DefaultRouter()
router.register(r'cuentas', CuentaContableViewSet, basename='cuenta-contable')

urlpatterns = [
    path('', catalogo_root, name='catalogo-root'),
    path('crear-cuenta-ajax/', crear_cuenta_ajax, name='crear-cuenta-ajax'),
    path('', include(router.urls)),
]