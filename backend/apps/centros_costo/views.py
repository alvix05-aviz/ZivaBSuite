from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import CentroCosto, Proyecto, TipoCentroCosto
from .serializers import CentroCostoSerializer, ProyectoSerializer
from apps.empresas.models import Empresa, UsuarioEmpresa

def get_empresa_actual(request):
    empresa_id = request.session.get('empresa_id')
    if empresa_id:
        try:
            return Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            pass
    
    acceso = UsuarioEmpresa.objects.filter(
        usuario=request.user,
        activo=True
    ).first()
    return acceso.empresa if acceso else None

class CentroCostoViewSet(viewsets.ModelViewSet):
    serializer_class = CentroCostoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        empresa = self.get_empresa_from_request(self.request)
        if empresa:
            return CentroCosto.objects.filter(empresa=empresa, activo=True).order_by('codigo')
        return CentroCosto.objects.none()

    def get_empresa_from_request(self, request):
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            try:
                return Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        acceso = UsuarioEmpresa.objects.filter(
            usuario=request.user,
            activo=True
        ).first()
        return acceso.empresa if acceso else None

    @action(detail=False, methods=['get'])
    def jerarquicos(self, request):
        """Devuelve centros de costo en estructura jerárquica"""
        centros_raiz = self.get_queryset().filter(centro_padre__isnull=True)
        data = []
        for centro in centros_raiz:
            data.append(self._serialize_with_children(centro))
        return Response(data)
    
    def _serialize_with_children(self, centro):
        serializer = self.get_serializer(centro)
        data = serializer.data
        children = centro.subcentros.filter(activo=True).order_by('codigo')
        data['children'] = [self._serialize_with_children(child) for child in children]
        return data

class ProyectoViewSet(viewsets.ModelViewSet):
    serializer_class = ProyectoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        empresa = self.get_empresa_from_request(self.request)
        if empresa:
            return Proyecto.objects.filter(empresa=empresa, activo=True).order_by('-fecha_inicio')
        return Proyecto.objects.none()

    def get_empresa_from_request(self, request):
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            try:
                return Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        acceso = UsuarioEmpresa.objects.filter(
            usuario=request.user,
            activo=True
        ).first()
        return acceso.empresa if acceso else None

@login_required
def centros_costo_root(request):
    return redirect('centros-costo-list')

@login_required
def centros_costo_list(request):
    """Lista de centros de costo con vista jerárquica"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    centros_raiz = CentroCosto.objects.filter(
        empresa=empresa,
        centro_padre__isnull=True,
        activo=True
    ).order_by('codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_raiz': centros_raiz,
    }
    
    return render(request, 'centros_costo/centros_list.html', context)

@login_required 
def centro_costo_create(request):
    """Crear nuevo centro de costo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    if request.method == 'POST':
        try:
            centro_padre_id = request.POST.get('centro_padre')
            centro_padre = None
            if centro_padre_id:
                centro_padre = CentroCosto.objects.get(
                    id=centro_padre_id,
                    empresa=empresa
                )
            
            tipo_id = request.POST.get('tipo')
            tipo_obj = None
            if tipo_id:
                tipo_obj = TipoCentroCosto.objects.get(id=tipo_id, empresa=empresa)

            centro = CentroCosto.objects.create(
                empresa=empresa,
                codigo=request.POST.get('codigo'),
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                tipo=tipo_obj,
                centro_padre=centro_padre,
                permite_movimientos=request.POST.get('permite_movimientos') == 'on',
                color_interfaz=request.POST.get('color_interfaz', 'blue'),
                creado_por=request.user
            )
            
            messages.success(request, f'Centro de costo {centro.codigo} creado exitosamente')
            return redirect('centros-costo-list')
            
        except Exception as e:
            messages.error(request, f'Error al crear centro de costo: {str(e)}')
    
    # Obtener centros para dropdown de padre
    centros_disponibles = CentroCosto.objects.filter(
        empresa=empresa,
        activo=True,
        #permite_movimientos=False  # Solo centros que no permiten movimientos pueden ser padre
    ).order_by('codigo')
    
    tipos_disponibles = TipoCentroCosto.objects.filter(empresa=empresa, activo=True).order_by('orden', 'codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_disponibles': centros_disponibles,
        'tipos_disponibles': tipos_disponibles,
    }
    
    return render(request, 'centros_costo/centro_form.html', context)

@login_required
def centro_costo_edit(request, pk):
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')

    centro = get_object_or_404(CentroCosto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        try:
            centro_padre_id = request.POST.get('centro_padre')
            centro_padre = None
            if centro_padre_id:
                centro_padre = CentroCosto.objects.get(id=centro_padre_id, empresa=empresa)

            tipo_id = request.POST.get('tipo')
            if tipo_id:
                centro.tipo = TipoCentroCosto.objects.get(id=tipo_id, empresa=empresa)

            centro.codigo = request.POST.get('codigo')
            centro.nombre = request.POST.get('nombre')
            centro.descripcion = request.POST.get('descripcion', '')
            centro.centro_padre = centro_padre
            centro.permite_movimientos = request.POST.get('permite_movimientos') == 'on'
            centro.color_interfaz = request.POST.get('color_interfaz', 'blue')
            centro.modificado_por = request.user
            centro.save()

            messages.success(request, f'Centro de costo {centro.codigo} actualizado exitosamente')
            return redirect('centros-costo-list')

        except Exception as e:
            messages.error(request, f'Error al actualizar centro de costo: {str(e)}')

    centros_disponibles = CentroCosto.objects.filter(empresa=empresa, activo=True).exclude(pk=pk).order_by('codigo')
    tipos_disponibles = TipoCentroCosto.objects.filter(empresa=empresa, activo=True).order_by('orden', 'codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'centro': centro,
        'centros_disponibles': centros_disponibles,
        'tipos_disponibles': tipos_disponibles,
    }
    
    return render(request, 'centros_costo/centro_form.html', context)

@login_required
def proyectos_list(request):
    """Lista de proyectos"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    proyectos = Proyecto.objects.filter(
        empresa=empresa,
        activo=True
    ).order_by('-fecha_inicio')
    
    context = {
        'empresa_actual': empresa.nombre,
        'proyectos': proyectos,
    }
    
    return render(request, 'centros_costo/proyectos_list.html', context)

@login_required 
def proyecto_create(request):
    """Crear nuevo proyecto"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    if request.method == 'POST':
        try:
            centro_costo_id = request.POST.get('centro_costo')
            centro_costo = None
            if centro_costo_id:
                centro_costo = CentroCosto.objects.get(
                    id=centro_costo_id,
                    empresa=empresa
                )
            
            proyecto = Proyecto.objects.create(
                empresa=empresa,
                codigo=request.POST.get('codigo'),
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                estado=request.POST.get('estado', 'PLANIFICACION'),
                fecha_inicio=request.POST.get('fecha_inicio'),
                fecha_fin=request.POST.get('fecha_fin') or None,
                presupuesto_inicial=request.POST.get('presupuesto_inicial', 0),
                centro_costo=centro_costo,
                creado_por=request.user
            )
            
            messages.success(request, f'Proyecto {proyecto.codigo} creado exitosamente')
            return redirect('proyectos-list')
            
        except Exception as e:
            messages.error(request, f'Error al crear proyecto: {str(e)}')
    
    # Obtener centros para dropdown
    centros_disponibles = CentroCosto.objects.filter(
        empresa=empresa,
        activo=True
    ).order_by('codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_disponibles': centros_disponibles,
    }
    
    return render(request, 'centros_costo/proyecto_form.html', context)

@login_required
def proyecto_edit(request, pk):
    """Editar proyecto existente"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')

    proyecto = get_object_or_404(Proyecto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        try:
            centro_costo_id = request.POST.get('centro_costo')
            centro_costo = None
            if centro_costo_id:
                centro_costo = CentroCosto.objects.get(id=centro_costo_id, empresa=empresa)

            proyecto.codigo = request.POST.get('codigo')
            proyecto.nombre = request.POST.get('nombre')
            proyecto.descripcion = request.POST.get('descripcion', '')
            proyecto.estado = request.POST.get('estado')
            proyecto.fecha_inicio = request.POST.get('fecha_inicio')
            proyecto.fecha_fin = request.POST.get('fecha_fin') or None
            proyecto.presupuesto_inicial = request.POST.get('presupuesto_inicial', 0)
            proyecto.centro_costo = centro_costo
            proyecto.modificado_por = request.user
            proyecto.save()

            messages.success(request, f'Proyecto {proyecto.codigo} actualizado exitosamente')
            return redirect('proyectos-list')

        except Exception as e:
            messages.error(request, f'Error al actualizar proyecto: {str(e)}')

    centros_disponibles = CentroCosto.objects.filter(empresa=empresa, activo=True).order_by('codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'proyecto': proyecto,
        'centros_disponibles': centros_disponibles,
    }
    
    return render(request, 'centros_costo/proyecto_form.html', context)

@login_required
def tipos_centro_list(request):
    """Lista de tipos de centro de costo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    tipos = TipoCentroCosto.objects.filter(
        empresa=empresa,
        activo=True
    ).order_by('orden', 'codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'tipos': tipos,
    }
    
    return render(request, 'centros_costo/tipos_list.html', context)

@login_required
def tipo_centro_create(request):
    """Crear nuevo tipo de centro de costo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    if request.method == 'POST':
        try:
            tipo = TipoCentroCosto.objects.create(
                empresa=empresa,
                codigo=request.POST.get('codigo'),
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                color_interfaz=request.POST.get('color_interfaz', 'blue'),
                orden=request.POST.get('orden', 0),
                creado_por=request.user
            )
            
            messages.success(request, f'Tipo {tipo.codigo} creado exitosamente')
            return redirect('tipos-centro-list')
            
        except Exception as e:
            messages.error(request, f'Error al crear tipo: {str(e)}')
    
    context = {
        'empresa_actual': empresa.nombre,
    }
    
    return render(request, 'centros_costo/tipo_form.html', context)

@login_required
def tipo_centro_edit(request, pk):
    """Editar tipo de centro de costo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')

    tipo = get_object_or_404(TipoCentroCosto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        try:
            tipo.codigo = request.POST.get('codigo')
            tipo.nombre = request.POST.get('nombre')
            tipo.descripcion = request.POST.get('descripcion', '')
            tipo.color_interfaz = request.POST.get('color_interfaz', 'blue')
            tipo.orden = request.POST.get('orden', 0)
            tipo.modificado_por = request.user
            tipo.save()

            messages.success(request, f'Tipo {tipo.codigo} actualizado exitosamente')
            return redirect('tipos-centro-list')

        except Exception as e:
            messages.error(request, f'Error al actualizar tipo: {str(e)}')
    
    context = {
        'empresa_actual': empresa.nombre,
        'tipo': tipo,
    }
    
    return render(request, 'centros_costo/tipo_form.html', context)
