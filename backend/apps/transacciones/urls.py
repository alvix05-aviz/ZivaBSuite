from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransaccionContableViewSet, MovimientoContableViewSet, transacciones_root, crear_transaccion_view

router = DefaultRouter()
router.register(r'transacciones', TransaccionContableViewSet, basename='transaccion-contable')
router.register(r'movimientos', MovimientoContableViewSet, basename='movimiento-contable')

urlpatterns = [
    path('', transacciones_root, name='transacciones-root'),
    path('crear/', crear_transaccion_view, name='crear-transaccion'),
    path('', include(router.urls)),
]