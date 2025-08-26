# CCYP-FASE4: Reportes y Análisis

## 🎯 **Objetivo de la Fase 4**
Implementar sistema completo de reportes y análisis por centros de costo y proyectos, incluyendo dashboards analíticos y reportes específicos para toma de decisiones.

## 📋 **Tareas de la Fase 4**

### ✅ **Completadas**
- [ ] Crear módulo de reportes para centros de costo
- [ ] Implementar reportes por proyecto
- [ ] Desarrollar dashboard analítico
- [ ] Crear estado de resultados por centro
- [ ] Implementar análisis presupuestal por proyecto
- [ ] Agregar comparativos entre centros/proyectos
- [ ] Crear exportación a Excel/PDF
- [ ] Implementar gráficas y visualizaciones

### 🎯 **En Progreso**
- *Ninguna tarea en progreso actualmente*

### ⏳ **Pendientes**
- [ ] Todas las tareas listadas arriba

## 🏗️ **Detalles de Implementación**

### **4.1 Crear Vistas de Reportes**
```python
# apps/centros_costo/views.py - Agregar vistas de reportes

from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json

@login_required
def reporte_centros_costo(request):
    """Reporte de resultados por centro de costo"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Parámetros de fecha
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio:
        fecha_inicio = date.today().replace(day=1).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = date.today().strftime('%Y-%m-%d')
    
    # Obtener movimientos por centro de costo
    from apps.transacciones.models import MovimientoContable
    
    movimientos = MovimientoContable.objects.filter(
        transaccion__empresa=empresa,
        transaccion__estado='CONTABILIZADA',
        transaccion__fecha__gte=fecha_inicio,
        transaccion__fecha__lte=fecha_fin,
        centro_costo__isnull=False,
        activo=True
    ).select_related('centro_costo', 'cuenta')
    
    # Agrupar por centro de costo
    centros_data = {}
    
    for mov in movimientos:
        centro_codigo = mov.centro_costo.codigo
        if centro_codigo not in centros_data:
            centros_data[centro_codigo] = {
                'centro': mov.centro_costo,
                'ingresos': Decimal('0.00'),
                'gastos': Decimal('0.00'),
                'activos': Decimal('0.00'),
                'pasivos': Decimal('0.00'),
                'movimientos_count': 0
            }
        
        # Clasificar por tipo de cuenta
        if mov.cuenta.tipo == 'INGRESO':
            centros_data[centro_codigo]['ingresos'] += mov.haber - mov.debe
        elif mov.cuenta.tipo in ['GASTO', 'COSTO']:
            centros_data[centro_codigo]['gastos'] += mov.debe - mov.haber
        elif mov.cuenta.tipo == 'ACTIVO':
            centros_data[centro_codigo]['activos'] += mov.debe - mov.haber
        elif mov.cuenta.tipo == 'PASIVO':
            centros_data[centro_codigo]['pasivos'] += mov.haber - mov.debe
        
        centros_data[centro_codigo]['movimientos_count'] += 1
    
    # Calcular utilidades
    for data in centros_data.values():
        data['utilidad'] = data['ingresos'] - data['gastos']
        data['margen'] = (data['utilidad'] / data['ingresos'] * 100) if data['ingresos'] > 0 else 0
    
    # Ordenar por utilidad descendente
    centros_ordenados = sorted(
        centros_data.values(),
        key=lambda x: x['utilidad'],
        reverse=True
    )
    
    context = {
        'empresa_actual': empresa.nombre,
        'centros_data': centros_ordenados,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ingresos': sum(d['ingresos'] for d in centros_data.values()),
        'total_gastos': sum(d['gastos'] for d in centros_data.values()),
        'total_utilidad': sum(d['utilidad'] for d in centros_data.values()),
    }
    
    return render(request, 'centros_costo/reporte_centros.html', context)

@login_required
def reporte_proyectos(request):
    """Reporte de avance y presupuesto por proyecto"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Obtener proyectos activos
    proyectos = Proyecto.objects.filter(
        empresa=empresa,
        activo=True
    ).order_by('-fecha_inicio')
    
    proyectos_data = []
    
    for proyecto in proyectos:
        # Calcular gastos del proyecto
        gastos = MovimientoContable.objects.filter(
            proyecto=proyecto,
            transaccion__estado='CONTABILIZADA',
            cuenta__tipo__in=['GASTO', 'COSTO'],
            activo=True
        ).aggregate(
            total=Sum('debe') - Sum('haber')
        )['total'] or Decimal('0.00')
        
        # Calcular ingresos del proyecto
        ingresos = MovimientoContable.objects.filter(
            proyecto=proyecto,
            transaccion__estado='CONTABILIZADA',
            cuenta__tipo='INGRESO',
            activo=True
        ).aggregate(
            total=Sum('haber') - Sum('debe')
        )['total'] or Decimal('0.00')
        
        # Calcular progreso presupuestal
        progreso_presupuesto = 0
        if proyecto.presupuesto and proyecto.presupuesto > 0:
            progreso_presupuesto = float(gastos / proyecto.presupuesto * 100)
        
        proyectos_data.append({
            'proyecto': proyecto,
            'gastos': gastos,
            'ingresos': ingresos,
            'utilidad': ingresos - gastos,
            'progreso_presupuesto': min(100, progreso_presupuesto),
            'presupuesto_restante': (proyecto.presupuesto or Decimal('0.00')) - gastos,
            'roi': float((ingresos - gastos) / gastos * 100) if gastos > 0 else 0,
        })
    
    context = {
        'empresa_actual': empresa.nombre,
        'proyectos_data': proyectos_data,
    }
    
    return render(request, 'centros_costo/reporte_proyectos.html', context)

@login_required
def dashboard_analitico(request):
    """Dashboard con gráficas y análisis avanzado"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return redirect('seleccionar_empresa')
    
    # Datos para gráficas
    
    # 1. Distribución de gastos por centro
    gastos_por_centro = MovimientoContable.objects.filter(
        transaccion__empresa=empresa,
        transaccion__estado='CONTABILIZADA',
        centro_costo__isnull=False,
        cuenta__tipo__in=['GASTO', 'COSTO'],
        transaccion__fecha__gte=date.today().replace(day=1),
        activo=True
    ).values(
        'centro_costo__nombre',
        'centro_costo__color_interfaz'
    ).annotate(
        total=Sum('debe') - Sum('haber')
    ).order_by('-total')[:10]
    
    # 2. Evolución mensual por centro (últimos 6 meses)
    hace_6_meses = date.today() - timedelta(days=180)
    evolucion_centros = {}
    
    centros_top = CentroCosto.objects.filter(
        empresa=empresa,
        activo=True,
        movimientos__transaccion__fecha__gte=hace_6_meses
    ).distinct()[:5]
    
    for centro in centros_top:
        evolucion_centros[centro.nombre] = []
        for i in range(6):
            mes_fecha = date.today().replace(day=1) - timedelta(days=30*i)
            mes_siguiente = (mes_fecha.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            gasto_mes = MovimientoContable.objects.filter(
                centro_costo=centro,
                transaccion__estado='CONTABILIZADA',
                cuenta__tipo__in=['GASTO', 'COSTO'],
                transaccion__fecha__gte=mes_fecha,
                transaccion__fecha__lt=mes_siguiente,
                activo=True
            ).aggregate(
                total=Sum('debe') - Sum('haber')
            )['total'] or Decimal('0.00')
            
            evolucion_centros[centro.nombre].insert(0, {
                'mes': mes_fecha.strftime('%Y-%m'),
                'total': float(gasto_mes)
            })
    
    # 3. Estado de proyectos
    proyectos_stats = {
        'activos': Proyecto.objects.filter(empresa=empresa, estado='ACTIVO', activo=True).count(),
        'terminados': Proyecto.objects.filter(empresa=empresa, estado='TERMINADO', activo=True).count(),
        'suspendidos': Proyecto.objects.filter(empresa=empresa, estado='SUSPENDIDO', activo=True).count(),
        'en_planificacion': Proyecto.objects.filter(empresa=empresa, estado='PLANIFICACION', activo=True).count(),
    }
    
    # 4. ROI de proyectos terminados
    proyectos_terminados = Proyecto.objects.filter(
        empresa=empresa,
        estado='TERMINADO',
        activo=True
    )
    
    roi_proyectos = []
    for proyecto in proyectos_terminados[:10]:
        gastos = MovimientoContable.objects.filter(
            proyecto=proyecto,
            cuenta__tipo__in=['GASTO', 'COSTO'],
            activo=True
        ).aggregate(total=Sum('debe') - Sum('haber'))['total'] or Decimal('0.00')
        
        ingresos = MovimientoContable.objects.filter(
            proyecto=proyecto,
            cuenta__tipo='INGRESO',
            activo=True
        ).aggregate(total=Sum('haber') - Sum('debe'))['total'] or Decimal('0.00')
        
        roi = float((ingresos - gastos) / gastos * 100) if gastos > 0 else 0
        
        roi_proyectos.append({
            'nombre': proyecto.nombre,
            'roi': roi,
            'ingresos': float(ingresos),
            'gastos': float(gastos)
        })
    
    roi_proyectos.sort(key=lambda x: x['roi'], reverse=True)
    
    context = {
        'empresa_actual': empresa.nombre,
        'gastos_por_centro': list(gastos_por_centro),
        'evolucion_centros': evolucion_centros,
        'proyectos_stats': proyectos_stats,
        'roi_proyectos': roi_proyectos,
    }
    
    return render(request, 'centros_costo/dashboard_analitico.html', context)

@login_required
def exportar_reporte_excel(request):
    """Exportar reporte a Excel"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from django.http import HttpResponse
    
    empresa = get_empresa_actual(request)
    tipo_reporte = request.GET.get('tipo', 'centros')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    if tipo_reporte == 'centros':
        ws.title = "Reporte Centros de Costo"
        
        # Headers
        headers = ['Centro', 'Código', 'Ingresos', 'Gastos', 'Utilidad', 'Margen %']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Data (reutilizar lógica del reporte)
        # ... código para llenar datos ...
        
    elif tipo_reporte == 'proyectos':
        ws.title = "Reporte Proyectos"
        # Similar para proyectos
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo_reporte}.xlsx"'
    
    wb.save(response)
    return response
```

### **4.2 Templates de Reportes**

#### **4.2.1 Reporte de Centros de Costo**
```html
<!-- templates/centros_costo/reporte_centros.html -->
{% extends 'base.html' %}

{% block title %}Reporte Centros de Costo - ZivaBSuite{% endblock %}

{% block content %}
<div class="py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Header -->
        <div class="mb-8">
            <div class="flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
                        <i class="fas fa-chart-line text-blue-600 mr-3"></i>Reporte por Centros de Costo
                    </h2>
                    <p class="mt-1 text-sm text-gray-500">
                        Análisis de resultados por centro de costo - {{ empresa_actual }}
                    </p>
                </div>
                <div class="flex space-x-3">
                    <a href="?tipo=centros&formato=excel" class="inline-flex items-center px-4 py-2 border border-green-300 rounded-md shadow-sm text-sm font-medium text-green-700 bg-white hover:bg-green-50">
                        <i class="fas fa-file-excel mr-2"></i>Excel
                    </a>
                    <a href="{% url 'dashboard_analitico' %}" class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                        <i class="fas fa-arrow-left mr-2"></i>Volver
                    </a>
                </div>
            </div>
        </div>

        <!-- Filtros de Fecha -->
        <div class="mb-6 bg-white p-4 rounded-lg shadow">
            <form method="GET" class="flex items-end space-x-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Fecha Inicio</label>
                    <input type="date" name="fecha_inicio" value="{{ fecha_inicio }}" 
                           class="border border-gray-300 rounded-md px-3 py-2 text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Fecha Fin</label>
                    <input type="date" name="fecha_fin" value="{{ fecha_fin }}" 
                           class="border border-gray-300 rounded-md px-3 py-2 text-sm">
                </div>
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm hover:bg-blue-700">
                    <i class="fas fa-search mr-1"></i>Filtrar
                </button>
            </form>
        </div>

        <!-- Resumen Ejecutivo -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-arrow-up text-green-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Total Ingresos</dt>
                                <dd class="text-2xl font-semibold text-gray-900">${{ total_ingresos|floatformat:2 }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-arrow-down text-red-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Total Gastos</dt>
                                <dd class="text-2xl font-semibold text-gray-900">${{ total_gastos|floatformat:2 }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-chart-line text-blue-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Utilidad Total</dt>
                                <dd class="text-2xl font-semibold {% if total_utilidad >= 0 %}text-green-600{% else %}text-red-600{% endif %}">
                                    ${{ total_utilidad|floatformat:2 }}
                                </dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabla Detallada -->
        <div class="bg-white shadow rounded-lg overflow-hidden">
            <div class="px-4 py-5 sm:p-6">
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Centro de Costo
                                </th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Ingresos
                                </th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Gastos
                                </th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Utilidad
                                </th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Margen %
                                </th>
                                <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Movimientos
                                </th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for data in centros_data %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="w-4 h-4 rounded bg-{{ data.centro.color_interfaz }}-500 mr-3"></div>
                                        <div>
                                            <div class="text-sm font-medium text-gray-900">
                                                {{ data.centro.nombre }}
                                            </div>
                                            <div class="text-sm text-gray-500">{{ data.centro.codigo }}</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-green-600 font-medium">
                                    ${{ data.ingresos|floatformat:2 }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-red-600 font-medium">
                                    ${{ data.gastos|floatformat:2 }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium
                                    {% if data.utilidad >= 0 %}text-green-600{% else %}text-red-600{% endif %}">
                                    ${{ data.utilidad|floatformat:2 }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium
                                    {% if data.margen >= 0 %}text-green-600{% else %}text-red-600{% endif %}">
                                    {{ data.margen|floatformat:1 }}%
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                                    {{ data.movimientos_count }}
                                </td>
                            </tr>
                            {% empty %}
                            <tr>
                                <td colspan="6" class="px-6 py-4 text-center text-sm text-gray-500">
                                    No hay datos para el período seleccionado
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### **4.2.2 Dashboard Analítico**
```html
<!-- templates/centros_costo/dashboard_analitico.html -->
{% extends 'base.html' %}

{% block title %}Dashboard Analítico - ZivaBSuite{% endblock %}

{% block extra_css %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
<div class="py-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Header -->
        <div class="mb-8">
            <div class="flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
                        <i class="fas fa-analytics text-purple-600 mr-3"></i>Dashboard Analítico
                    </h2>
                    <p class="mt-1 text-sm text-gray-500">
                        Análisis avanzado de centros de costo y proyectos - {{ empresa_actual }}
                    </p>
                </div>
                <div class="flex space-x-3">
                    <a href="{% url 'reporte_centros' %}" class="inline-flex items-center px-4 py-2 border border-blue-300 rounded-md shadow-sm text-sm font-medium text-blue-700 bg-white hover:bg-blue-50">
                        <i class="fas fa-chart-bar mr-2"></i>Reporte Centros
                    </a>
                    <a href="{% url 'reporte_proyectos' %}" class="inline-flex items-center px-4 py-2 border border-green-300 rounded-md shadow-sm text-sm font-medium text-green-700 bg-white hover:bg-green-50">
                        <i class="fas fa-project-diagram mr-2"></i>Reporte Proyectos
                    </a>
                </div>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-play text-green-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Proyectos Activos</dt>
                                <dd class="text-2xl font-semibold text-gray-900">{{ proyectos_stats.activos }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-check-circle text-blue-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Terminados</dt>
                                <dd class="text-2xl font-semibold text-gray-900">{{ proyectos_stats.terminados }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-pause text-yellow-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Suspendidos</dt>
                                <dd class="text-2xl font-semibold text-gray-900">{{ proyectos_stats.suspendidos }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-clipboard-list text-purple-500 text-2xl"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">En Planificación</dt>
                                <dd class="text-2xl font-semibold text-gray-900">{{ proyectos_stats.en_planificacion }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Gráficas -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Gastos por Centro -->
            <div class="bg-white shadow rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                        Distribución de Gastos por Centro
                    </h3>
                    <div class="relative h-64">
                        <canvas id="gastosCentrosChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- ROI de Proyectos -->
            <div class="bg-white shadow rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                        ROI de Proyectos Terminados
                    </h3>
                    <div class="relative h-64">
                        <canvas id="roiProyectosChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Evolución Temporal -->
        <div class="bg-white shadow rounded-lg">
            <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                    Evolución Mensual - Top 5 Centros
                </h3>
                <div class="relative h-80">
                    <canvas id="evolucionChart"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Gráfico de gastos por centro
    const gastosCtx = document.getElementById('gastosCentrosChart').getContext('2d');
    new Chart(gastosCtx, {
        type: 'doughnut',
        data: {
            labels: [{% for gasto in gastos_por_centro %}'{{ gasto.centro_costo__nombre }}'{% if not forloop.last %},{% endif %}{% endfor %}],
            datasets: [{
                data: [{% for gasto in gastos_por_centro %}{{ gasto.total }}{% if not forloop.last %},{% endif %}{% endfor %}],
                backgroundColor: [
                    '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
                    '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });

    // Gráfico de ROI de proyectos
    const roiCtx = document.getElementById('roiProyectosChart').getContext('2d');
    new Chart(roiCtx, {
        type: 'bar',
        data: {
            labels: [{% for proyecto in roi_proyectos %}'{{ proyecto.nombre }}'{% if not forloop.last %},{% endif %}{% endfor %}],
            datasets: [{
                label: 'ROI (%)',
                data: [{% for proyecto in roi_proyectos %}{{ proyecto.roi }}{% if not forloop.last %},{% endif %}{% endfor %}],
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    return value >= 0 ? '#10B981' : '#EF4444';
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Gráfico de evolución temporal
    const evolucionCtx = document.getElementById('evolucionChart').getContext('2d');
    const evolucionData = {{ evolucion_centros|safe }};
    
    const datasets = [];
    const colors = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6'];
    let colorIndex = 0;
    
    for (const [centro, datos] of Object.entries(evolucionData)) {
        datasets.push({
            label: centro,
            data: datos.map(d => d.total),
            borderColor: colors[colorIndex % colors.length],
            backgroundColor: colors[colorIndex % colors.length] + '20',
            fill: false,
            tension: 0.1
        });
        colorIndex++;
    }
    
    new Chart(evolucionCtx, {
        type: 'line',
        data: {
            labels: evolucionData[Object.keys(evolucionData)[0]]?.map(d => d.mes) || [],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
});
</script>
{% endblock %}
```

### **4.3 URLs para Reportes**
```python
# Agregar a apps/centros_costo/urls.py

urlpatterns = [
    # ... URLs existentes ...
    
    # Reportes
    path('reportes/centros/', views.reporte_centros_costo, name='reporte_centros'),
    path('reportes/proyectos/', views.reporte_proyectos, name='reporte_proyectos'),
    path('reportes/dashboard/', views.dashboard_analitico, name='dashboard_analitico'),
    path('reportes/exportar/', views.exportar_reporte_excel, name='exportar_excel'),
]

# Agregar a config/urls.py
path('reportes/centros-costo/', views.dashboard_analitico, name='reportes_centros_costo'),
```

## ✅ **Criterios de Aceptación**

- [ ] Dashboard analítico con gráficas interactivas funcional
- [ ] Reportes detallados por centro de costo con filtros de fecha
- [ ] Reportes de proyectos con análisis presupuestal y ROI
- [ ] Exportación a Excel completamente funcional
- [ ] Gráficas responsive y visualmente atractivas
- [ ] Cálculos financieros precisos y auditables
- [ ] Navegación fluida entre diferentes vistas de reporte
- [ ] Performance optimizada para empresas con grandes volúmenes

## 📊 **Métricas y KPIs Implementados**

### **4.4.1 Métricas por Centro de Costo**
- **Ingresos por centro**: Suma de movimientos de cuentas tipo INGRESO
- **Gastos por centro**: Suma de movimientos de cuentas tipo GASTO/COSTO
- **Utilidad por centro**: Ingresos - Gastos
- **Margen por centro**: (Utilidad / Ingresos) × 100
- **Número de movimientos**: Conteo de transacciones por centro

### **4.4.2 Métricas por Proyecto**
- **Gastos ejecutados**: Total gastado vs presupuesto
- **Progreso presupuestal**: % de presupuesto utilizado
- **ROI del proyecto**: ((Ingresos - Gastos) / Gastos) × 100
- **Días transcurridos**: Tiempo desde inicio
- **Progreso temporal**: % de tiempo transcurrido vs planificado
- **Presupuesto restante**: Presupuesto - Gastos ejecutados

### **4.4.3 Análisis Comparativo**
- **Ranking de centros por utilidad**
- **Evolución temporal de gastos por centro**
- **Distribución porcentual de gastos**
- **Estados de proyectos (activos, terminados, suspendidos)**
- **Comparativo de ROI entre proyectos**

## 🔧 **Configuración Adicional**

### **4.5 Dependencias Requeridas**
```python
# requirements/base.txt - Agregar:
openpyxl>=3.0.10
reportlab>=3.6.0  # Para PDFs futuros
```

### **4.6 Settings de Cache**
```python
# Para optimizar performance de reportes
# settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'TIMEOUT': 3600,  # 1 hora para reportes
    }
}
```

## 📈 **Métricas de Éxito**
- ✅ Reportes se generan en menos de 5 segundos
- ✅ Gráficas se cargan correctamente en todos los navegadores
- ✅ Exportación Excel funciona sin errores
- ✅ Cálculos financieros son precisos al céntimo
- ✅ Dashboard responsive en dispositivos móviles
- ✅ Performance estable con +10,000 transacciones