from django.utils.functional import SimpleLazyObject
from .models import UsuarioEmpresa


def get_empresa_actual(request):
    """Obtiene la empresa activa en la sesión - MVP"""
    if not hasattr(request, '_cached_empresa'):
        empresa_id = request.session.get('empresa_id')
        
        if empresa_id and request.user.is_authenticated:
            try:
                acceso = UsuarioEmpresa.objects.select_related('empresa').get(
                    usuario=request.user,
                    empresa_id=empresa_id,
                    activo=True
                )
                request._cached_empresa = acceso.empresa
            except UsuarioEmpresa.DoesNotExist:
                request._cached_empresa = None
        else:
            request._cached_empresa = None
            
    return request._cached_empresa


class EmpresaMiddleware:
    """
    Middleware para contexto de empresa MVP
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        request.empresa = SimpleLazyObject(lambda: get_empresa_actual(request))
        response = self.get_response(request)
        return response