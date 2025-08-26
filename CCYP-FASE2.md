# CCYP-FASE2: Configuración y Administración

## 🎯 **Objetivo de la Fase 2**
Crear las interfaces de administración y configuración para gestionar centros de costo y proyectos, incluyendo la integración con el sistema de configuración existente.

## 📋 **Tareas de la Fase 2**

### ✅ **Completadas**
- [ ] Crear vista de gestión de centros de costo
- [ ] Crear vista de gestión de proyectos  
- [ ] Implementar CRUD completo para centros de costo
- [ ] Implementar CRUD completo para proyectos
- [ ] Crear templates de gestión
- [ ] Integrar con sistema de configuración
- [ ] Reemplazar placeholder en configuración
- [ ] Crear API endpoints básicos

### 🎯 **En Progreso**
- *Ninguna tarea en progreso actualmente*

### ⏳ **Pendientes**
- [ ] Todas las tareas listadas arriba

## 🏗️ **Detalles de Implementación**

### **2.1 URLs y Vistas**
```python
# apps/centros_costo/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'centros', views.CentroCostoViewSet, basename='centro-costo')
router.register(r'proyectos', views.ProyectoViewSet, basename='proyecto')

urlpatterns = [
    # Vistas web
    path('', views.centros_costo_root, name='centros-costo-root'),
    path('centros/', views.centros_costo_list, name='centros-costo-list'),
    path('centros/crear/', views.centro_costo_create, name='centro-costo-create'),
    path('centros/<int:pk>/editar/', views.centro_costo_edit, name='centro-costo-edit'),
    path('proyectos/', views.proyectos_list, name='proyectos-list'),
    path('proyectos/crear/', views.proyecto_create, name='proyecto-create'),
    path('proyectos/<int:pk>/editar/', views.proyecto_edit, name='proyecto-edit'),
    
    # API
    path('api/', include(router.urls)),
]
```

### **2.2 ViewSets para API**
```python
# apps/centros_costo/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import CentroCosto, Proyecto
from .serializers import CentroCostoSerializer, ProyectoSerializer

class CentroCostoViewSet(viewsets.ModelViewSet):
    serializer_class = CentroCostoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        empresa = self.get_empresa_actual()
        if empresa:
            return CentroCosto.objects.filter(empresa=empresa, activo=True).order_by('codigo')
        return CentroCosto.objects.none()
    
    def get_empresa_actual(self):
        # Lógica similar a otras vistas para obtener empresa
        from apps.empresas.models import UsuarioEmpresa
        empresa_id = self.request.session.get('empresa_id')
        if empresa_id:
            try:
                from apps.empresas.models import Empresa
                return Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        acceso = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
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
        empresa = self.get_empresa_actual()
        if empresa:
            return Proyecto.objects.filter(empresa=empresa, activo=True).order_by('-fecha_inicio')
        return Proyecto.objects.none()
    
    def get_empresa_actual(self):
        # Similar al ViewSet de CentroCosto
        pass
```

### **2.3 Vista Web de Centros de Costo**
```python
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
            
            centro = CentroCosto.objects.create(
                empresa=empresa,
                codigo=request.POST.get('codigo'),
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                tipo=request.POST.get('tipo'),
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
        permite_movimientos=False  # Solo centros que no permiten movimientos pueden ser padre
    ).order_by('codigo')
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_disponibles': centros_disponibles,
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
```

### **2.4 Templates de Gestión**

#### **2.4.1 Template Lista de Centros de Costo**
```html
<!-- templates/centros_costo/centros_list.html -->
{% extends 'base.html' %}

{% block title %}Centros de Costo - ZivaBSuite{% endblock %}

{% block content %}
<div class="py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Header -->
        <div class="mb-8">
            <div class="flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
                        <i class="fas fa-sitemap text-indigo-600 mr-3"></i>Centros de Costo
                    </h2>
                    <p class="mt-1 text-sm text-gray-500">
                        Gestión de departamentos y centros de costo - {{ empresa_actual }}
                    </p>
                </div>
                <div class="flex space-x-3">
                    <a href="{% url 'configuracion' %}" class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                        <i class="fas fa-arrow-left mr-2"></i>Volver
                    </a>
                    <a href="{% url 'centro-costo-create' %}" class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
                        <i class="fas fa-plus mr-2"></i>Nuevo Centro
                    </a>
                </div>
            </div>
        </div>

        <!-- Tabla Jerárquica -->
        <div class="bg-white shadow rounded-lg">
            <div class="px-4 py-5 sm:p-6">
                {% if centros_raiz %}
                    <div class="tree-view">
                        {% for centro in centros_raiz %}
                            {% include 'centros_costo/centro_tree_item.html' with centro=centro nivel=0 %}
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="text-center py-12">
                        <i class="fas fa-sitemap text-gray-300 text-6xl mb-4"></i>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No hay centros de costo</h3>
                        <p class="text-gray-500 mb-4">Crea tu primer centro de costo para comenzar</p>
                        <a href="{% url 'centro-costo-create' %}" class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
                            <i class="fas fa-plus mr-2"></i>Crear Centro de Costo
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### **2.4.2 Template Item de Árbol**
```html
<!-- templates/centros_costo/centro_tree_item.html -->
<div class="tree-item" style="margin-left: {{ nivel|mul:20 }}px;">
    <div class="flex items-center justify-between py-3 border-b border-gray-100 hover:bg-gray-50">
        <div class="flex items-center">
            <div class="flex items-center mr-3">
                {% if centro.subcentros.count > 0 %}
                    <button onclick="toggleSubcentros(this)" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-chevron-right transform transition-transform"></i>
                    </button>
                {% else %}
                    <i class="fas fa-circle text-xs text-gray-300 ml-2"></i>
                {% endif %}
            </div>
            <div class="flex items-center">
                <div class="w-4 h-4 rounded bg-{{ centro.color_interfaz }}-500 mr-3"></div>
                <div>
                    <div class="font-medium text-gray-900">{{ centro.codigo }} - {{ centro.nombre }}</div>
                    <div class="text-sm text-gray-500">
                        {{ centro.get_tipo_display }} 
                        {% if not centro.permite_movimientos %}
                            · <span class="text-orange-600">Solo agrupación</span>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        <div class="flex items-center space-x-2">
            <a href="#" onclick="editarCentro({{ centro.id }})" class="text-indigo-600 hover:text-indigo-900">
                <i class="fas fa-edit"></i>
            </a>
            <button onclick="eliminarCentro({{ centro.id }})" class="text-red-600 hover:text-red-900">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    </div>
    
    <!-- Subcentros -->
    {% if centro.subcentros.count > 0 %}
        <div class="subcentros hidden">
            {% for subcentro in centro.subcentros.all %}
                {% if subcentro.activo %}
                    {% include 'centros_costo/centro_tree_item.html' with centro=subcentro nivel=nivel|add:1 %}
                {% endif %}
            {% endfor %}
        </div>
    {% endif %}
</div>
```

### **2.5 Integración con Configuración**
```python
# Modificar apps/core/views.py - configuracion_placeholder_view
# Cambiar la redirección para centros-costo:

@login_required
def configuracion_placeholder_view(request, seccion):
    """Vista placeholder para secciones en desarrollo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Redirigir secciones implementadas
    if seccion == 'general':
        return redirect('configuracion_general')
    elif seccion == 'centros-costo':
        return redirect('centros-costo-list')
    
    # ... resto del código existente
```

### **2.6 Serializers**
```python
# apps/centros_costo/serializers.py
from rest_framework import serializers
from .models import CentroCosto, Proyecto

class CentroCostoSerializer(serializers.ModelSerializer):
    ruta_completa = serializers.ReadOnlyField(source='get_ruta_completa')
    
    class Meta:
        model = CentroCosto
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'tipo',
            'centro_padre', 'permite_movimientos', 'color_interfaz',
            'ruta_completa', 'activo'
        ]
        read_only_fields = ['id']

class ProyectoSerializer(serializers.ModelSerializer):
    dias_transcurridos = serializers.ReadOnlyField()
    progreso_tiempo = serializers.ReadOnlyField()
    
    class Meta:
        model = Proyecto
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'fecha_inicio',
            'fecha_fin_estimada', 'fecha_fin_real', 'estado', 'presupuesto',
            'centro_costo', 'responsable', 'color_interfaz', 'dias_transcurridos',
            'progreso_tiempo', 'activo'
        ]
        read_only_fields = ['id', 'dias_transcurridos', 'progreso_tiempo']
```

## 🔧 **Configuración de URLs Principales**
```python
# Modificar config/urls.py para incluir:
from apps.centros_costo.views import centros_costo_list

urlpatterns = [
    # ... URLs existentes
    path('configuracion/centros-costo/', centros_costo_list, name='centros_costo'),
    
    # APIs
    path('api/centros-costo/', include('apps.centros_costo.urls')),
]
```

## ✅ **Criterios de Aceptación**

- [ ] Vista de lista de centros de costo funcional con estructura jerárquica
- [ ] Formularios de creación y edición para centros de costo
- [ ] Vista de lista de proyectos funcional
- [ ] Formularios de creación y edición para proyectos
- [ ] Integración completa con sistema de configuración existente
- [ ] API REST funcional para ambos modelos
- [ ] Templates responsive y consistentes con el diseño actual
- [ ] Validaciones de front-end y back-end funcionando
- [ ] Enlaces correctos desde el dashboard de configuración

## 📝 **JavaScript y Funcionalidad**
```javascript
// Para ser incluido en templates

function toggleSubcentros(button) {
    const item = button.closest('.tree-item');
    const subcentros = item.querySelector('.subcentros');
    const icon = button.querySelector('i');
    
    if (subcentros.classList.contains('hidden')) {
        subcentros.classList.remove('hidden');
        icon.classList.add('rotate-90');
    } else {
        subcentros.classList.add('hidden');
        icon.classList.remove('rotate-90');
    }
}

function editarCentro(id) {
    window.location.href = `/configuracion/centros-costo/centros/${id}/editar/`;
}

function eliminarCentro(id) {
    if (confirm('¿Está seguro de eliminar este centro de costo?')) {
        // Implementar eliminación vía AJAX
        fetch(`/api/centros-costo/centros/${id}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        }).then(response => {
            if (response.ok) {
                location.reload();
            }
        });
    }
}
```

## 📊 **Métricas de Éxito**
- ✅ Navegación fluida entre configuración y gestión de centros
- ✅ CRUD completo funcional para ambos modelos
- ✅ Interfaz jerárquica intuitiva para centros de costo
- ✅ APIs REST completamente funcionales
- ✅ Integración perfecta con sistema existente