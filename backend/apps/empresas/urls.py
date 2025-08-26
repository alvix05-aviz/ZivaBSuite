from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmpresaViewSet, UsuarioEmpresaViewSet, MultiEmpresaViewSet

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'usuario-empresas', UsuarioEmpresaViewSet, basename='usuario-empresa')
router.register(r'multiempresa', MultiEmpresaViewSet, basename='multiempresa')

urlpatterns = [
    path('', include(router.urls)),
]