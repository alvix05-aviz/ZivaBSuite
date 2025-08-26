from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'centros', views.CentroCostoViewSet, basename='centro-costo')
router.register(r'proyectos', views.ProyectoViewSet, basename='proyecto')

urlpatterns = [
    # API - Must come FIRST to prevent conflicts with web views
    path('', include(router.urls)),
    
    # Vistas web
    path('web/', views.centros_costo_root, name='centros-costo-root'),
    path('web/centros/', views.centros_costo_list, name='centros-costo-list'),
    path('web/centros/crear/', views.centro_costo_create, name='centro-costo-create'),
    path('web/centros/<int:pk>/editar/', views.centro_costo_edit, name='centro-costo-edit'),
    path('web/proyectos/', views.proyectos_list, name='proyectos-list'),
    path('web/proyectos/crear/', views.proyecto_create, name='proyecto-create'),
    path('web/proyectos/<int:pk>/editar/', views.proyecto_edit, name='proyecto-edit'),
    path('web/tipos/', views.tipos_centro_list, name='tipos-centro-list'),
    path('web/tipos/crear/', views.tipo_centro_create, name='tipo-centro-create'),
    path('web/tipos/<int:pk>/editar/', views.tipo_centro_edit, name='tipo-centro-edit'),
]
