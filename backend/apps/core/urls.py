from django.urls import path
from .views import buscar_usuario

urlpatterns = [
    path('buscar-usuario/', buscar_usuario, name='buscar-usuario'),
]
