from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReporteViewSet, reportes_root

router = DefaultRouter()
router.register(r'reportes', ReporteViewSet, basename='reporte')

urlpatterns = [
    path('', reportes_root, name='reportes-root'),
    path('', include(router.urls)),
]