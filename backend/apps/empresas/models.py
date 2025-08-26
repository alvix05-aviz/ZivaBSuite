from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from apps.core.models import BaseModel

User = get_user_model()

class Empresa(BaseModel):
    """Modelo de Empresa - MVP"""
    # Información esencial
    nombre = models.CharField(
        max_length=200,
        verbose_name='Razón Social'
    )
    nombre_comercial = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nombre Comercial'
    )
    rfc = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$',
                message='RFC inválido'
            )
        ],
        verbose_name='RFC'
    )
    
    # Configuración básica del sistema
    limite_usuarios = models.IntegerField(
        default=5,
        verbose_name='Límite de usuarios'
    )
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']
        
    def __str__(self):
        return f"{self.nombre} ({self.rfc})"


class UsuarioEmpresa(BaseModel):
    """
    Relación Usuario-Empresa con roles básicos
    NÚCLEO del sistema multiempresa MVP
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='empresas_asignadas'
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios_asignados'
    )
    
    # Roles básicos MVP
    ROL_CHOICES = [
        ('PROPIETARIO', 'Propietario'),
        ('ADMINISTRADOR', 'Administrador'),
        ('CONTADOR', 'Contador'),
        ('AUXILIAR', 'Auxiliar'),
        ('CONSULTA', 'Solo Consulta'),
    ]
    
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='CONSULTA'
    )
    
    empresa_default = models.BooleanField(
        default=False,
        verbose_name='Empresa por defecto'
    )
    
    ultimo_acceso = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último acceso'
    )
    
    class Meta:
        unique_together = ['usuario', 'empresa']
        verbose_name = 'Usuario-Empresa'
        verbose_name_plural = 'Usuarios-Empresas'
        ordering = ['empresa', 'usuario']
        
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nombre} ({self.rol})"
    
    def tiene_permiso(self, permiso):
        """Sistema de permisos básico MVP"""
        permisos_por_rol = {
            'PROPIETARIO': ['*'],  # Todos los permisos
            'ADMINISTRADOR': ['ver', 'crear', 'editar', 'eliminar'],
            'CONTADOR': ['ver', 'crear', 'editar'],
            'AUXILIAR': ['ver', 'crear'],
            'CONSULTA': ['ver']
        }
        
        rol_permisos = permisos_por_rol.get(self.rol, [])
        return '*' in rol_permisos or permiso in rol_permisos