# Guía Rápida: Importación/Exportación de Transacciones en Excel

## 🎯 Objetivo
Implementar funcionalidad para importar y exportar transacciones contables en formato Excel (.xlsx) con soporte completo para centros de costo y proyectos.

## 📋 Estructura de Implementación

### 1. Dependencias Requeridas

```bash
# Agregar al requirements.txt
openpyxl==3.1.2
xlsxwriter==3.1.9
pandas==2.1.4
```

### 2. Estructura del Archivo Excel

#### **Hoja 1: Transacciones**
| Campo | Columna | Tipo | Requerido | Ejemplo |
|-------|---------|------|-----------|---------|
| Folio | A | Texto | Sí | EXP-001 |
| Fecha | B | Fecha | Sí | 2024-08-24 |
| Concepto | C | Texto | Sí | Compra de materiales |
| Tipo | D | Lista | Sí | DIARIO, INGRESO, EGRESO, AJUSTE |
| Estado | E | Lista | No | BORRADOR (default) |

#### **Hoja 2: Movimientos**
| Campo | Columna | Tipo | Requerido | Ejemplo |
|-------|---------|------|-----------|---------|
| Folio_Transaccion | A | Texto | Sí | EXP-001 |
| Codigo_Cuenta | B | Texto | Sí | 1.1.1.001 |
| Concepto_Movimiento | C | Texto | No | Detalle específico |
| Debe | D | Decimal | Condicional | 1000.00 |
| Haber | E | Decimal | Condicional | 0.00 |
| Codigo_Centro | F | Texto | No | VENT-01 |
| Codigo_Proyecto | G | Texto | No | PROJ-2024-001 |

## 🔧 Implementación Técnica

### 1. Crear ViewSet de Importación/Exportación

```python
# apps/transacciones/views.py
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import openpyxl
import pandas as pd
from io import BytesIO

class TransaccionImportExportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def importar_excel(self, request):
        """Importar transacciones desde Excel"""
        # Implementación de importación
        pass
    
    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """Exportar transacciones a Excel"""
        # Implementación de exportación
        pass
    
    @action(detail=False, methods=['get'])
    def template_excel(self, request):
        """Descargar template de Excel"""
        # Generar template vacío
        pass
```

### 2. Funciones de Utilidad

```python
# apps/transacciones/utils/excel_handler.py
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from decimal import Decimal

class ExcelTransactionHandler:
    
    def __init__(self, empresa):
        self.empresa = empresa
    
    def crear_template(self):
        """Crear template de Excel para importación"""
        wb = openpyxl.Workbook()
        
        # Hoja de transacciones
        ws_trans = wb.active
        ws_trans.title = "Transacciones"
        headers_trans = ['Folio', 'Fecha', 'Concepto', 'Tipo', 'Estado']
        ws_trans.append(headers_trans)
        
        # Hoja de movimientos  
        ws_movs = wb.create_sheet("Movimientos")
        headers_movs = ['Folio_Transaccion', 'Codigo_Cuenta', 'Concepto_Movimiento', 
                       'Debe', 'Haber', 'Codigo_Centro', 'Codigo_Proyecto']
        ws_movs.append(headers_movs)
        
        # Hoja de referencias (catálogos)
        ws_ref = wb.create_sheet("Referencias")
        self._agregar_referencias(ws_ref)
        
        return wb
    
    def exportar_transacciones(self, transacciones):
        """Exportar transacciones existentes a Excel"""
        wb = openpyxl.Workbook()
        
        # Exportar datos reales
        ws_trans = wb.active
        ws_trans.title = "Transacciones"
        
        # Headers con estilo
        headers = ['Folio', 'Fecha', 'Concepto', 'Tipo', 'Estado', 'Total_Debe', 'Total_Haber']
        ws_trans.append(headers)
        
        for trans in transacciones:
            ws_trans.append([
                trans.folio,
                trans.fecha,
                trans.concepto,
                trans.tipo,
                trans.estado,
                float(trans.total_debe),
                float(trans.total_haber)
            ])
        
        # Movimientos
        ws_movs = wb.create_sheet("Movimientos")
        headers_movs = ['Folio_Transaccion', 'Codigo_Cuenta', 'Nombre_Cuenta',
                       'Concepto', 'Debe', 'Haber', 'Centro_Costo', 'Proyecto']
        ws_movs.append(headers_movs)
        
        for trans in transacciones:
            for mov in trans.movimientos.all():
                ws_movs.append([
                    trans.folio,
                    mov.cuenta.codigo,
                    mov.cuenta.nombre,
                    mov.concepto,
                    float(mov.debe),
                    float(mov.haber),
                    mov.centro_costo.codigo if mov.centro_costo else '',
                    mov.proyecto.codigo if mov.proyecto else ''
                ])
        
        return wb
    
    def importar_desde_excel(self, archivo):
        """Importar transacciones desde archivo Excel"""
        wb = openpyxl.load_workbook(archivo)
        
        # Validar estructura
        if not self._validar_estructura(wb):
            raise ValueError("Estructura de Excel inválida")
        
        # Procesar transacciones
        transacciones_creadas = []
        ws_trans = wb['Transacciones']
        ws_movs = wb['Movimientos']
        
        # Leer transacciones
        for row in ws_trans.iter_rows(min_row=2, values_only=True):
            if not row[0]:  # Si no hay folio, terminar
                break
                
            trans_data = {
                'folio': row[0],
                'fecha': row[1],
                'concepto': row[2],
                'tipo': row[3],
                'estado': row[4] or 'BORRADOR'
            }
            
            # Crear transacción
            transaccion = self._crear_transaccion(trans_data)
            
            # Crear movimientos
            movimientos = self._obtener_movimientos_por_folio(ws_movs, row[0])
            for mov_data in movimientos:
                self._crear_movimiento(transaccion, mov_data)
            
            transacciones_creadas.append(transaccion)
        
        return transacciones_creadas
```

### 3. Endpoint para Template de Excel

```python
@action(detail=False, methods=['get'])
def template_excel(self, request):
    """Descargar template de Excel para importación"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return Response({'error': 'Sin empresa seleccionada'}, status=400)
    
    handler = ExcelTransactionHandler(empresa)
    wb = handler.crear_template()
    
    # Crear respuesta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="template_transacciones_{empresa.codigo}.xlsx"'
    
    # Guardar workbook en response
    wb.save(response)
    return response
```

### 4. Validaciones Críticas

```python
def validar_archivo_excel(self, archivo):
    """Validaciones previas a la importación"""
    errores = []
    
    try:
        wb = openpyxl.load_workbook(archivo)
        
        # Validar hojas requeridas
        if 'Transacciones' not in wb.sheetnames:
            errores.append("Falta hoja 'Transacciones'")
        
        if 'Movimientos' not in wb.sheetnames:
            errores.append("Falta hoja 'Movimientos'")
        
        # Validar headers
        ws_trans = wb['Transacciones']
        headers_esperados = ['Folio', 'Fecha', 'Concepto', 'Tipo']
        headers_actuales = [cell.value for cell in ws_trans[1]]
        
        for header in headers_esperados:
            if header not in headers_actuales:
                errores.append(f"Falta columna '{header}' en Transacciones")
        
        # Validar datos
        for row_num, row in enumerate(ws_trans.iter_rows(min_row=2, values_only=True), 2):
            if not row[0]:  # Sin folio
                continue
                
            # Validar folio único
            if TransaccionContable.objects.filter(folio=row[0], empresa=self.empresa).exists():
                errores.append(f"Fila {row_num}: Folio '{row[0]}' ya existe")
            
            # Validar fecha
            if not isinstance(row[1], datetime.date):
                errores.append(f"Fila {row_num}: Fecha inválida")
            
            # Validar tipo
            if row[3] not in ['DIARIO', 'INGRESO', 'EGRESO', 'AJUSTE']:
                errores.append(f"Fila {row_num}: Tipo '{row[3]}' inválido")
        
        return errores
        
    except Exception as e:
        return [f"Error al procesar archivo: {str(e)}"]
```

## 🌐 Frontend: Interfaz de Usuario

### 1. Botones de Acción en Transacciones

```html
<!-- En templates/dashboard/transacciones.html -->
<div class="mt-4 flex md:mt-0 md:ml-4 space-x-2">
    <button onclick="importarExcel()" 
            class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
        <i class="fas fa-upload mr-2"></i>Importar Excel
    </button>
    <button onclick="exportarExcel()" 
            class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
        <i class="fas fa-download mr-2"></i>Exportar Excel
    </button>
    <button onclick="descargarTemplate()" 
            class="inline-flex items-center px-4 py-2 border border-indigo-300 rounded-md shadow-sm text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100">
        <i class="fas fa-file-excel mr-2"></i>Template Excel
    </button>
</div>
```

### 2. Modal de Importación

```html
<!-- Modal para importación -->
<div id="modal-importar" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden">
    <div class="flex items-center justify-center min-h-screen p-4">
        <div class="bg-white rounded-lg max-w-md w-full p-6">
            <h3 class="text-lg font-semibold mb-4">Importar Transacciones</h3>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Archivo Excel (.xlsx)
                </label>
                <input type="file" id="archivo-excel" accept=".xlsx" 
                       class="w-full border border-gray-300 rounded px-3 py-2">
            </div>
            
            <div class="mb-4">
                <label class="flex items-center">
                    <input type="checkbox" id="validar-previo" checked 
                           class="rounded border-gray-300 text-indigo-600">
                    <span class="ml-2 text-sm text-gray-700">
                        Validar antes de importar
                    </span>
                </label>
            </div>
            
            <div class="flex justify-end space-x-3">
                <button onclick="cerrarModalImportar()" 
                        class="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50">
                    Cancelar
                </button>
                <button onclick="ejecutarImportacion()" 
                        class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
                    Importar
                </button>
            </div>
        </div>
    </div>
</div>
```

## 📊 JavaScript para Funcionalidad

```javascript
// static/js/transacciones_excel.js
function descargarTemplate() {
    window.location.href = '/api/transacciones/template_excel/';
}

function exportarExcel() {
    // Obtener filtros actuales
    const filtros = obtenerFiltrosActuales();
    const params = new URLSearchParams(filtros);
    
    window.location.href = `/api/transacciones/exportar_excel/?${params.toString()}`;
}

function importarExcel() {
    document.getElementById('modal-importar').classList.remove('hidden');
}

async function ejecutarImportacion() {
    const archivo = document.getElementById('archivo-excel').files[0];
    const validarPrevio = document.getElementById('validar-previo').checked;
    
    if (!archivo) {
        alert('Selecciona un archivo Excel');
        return;
    }
    
    const formData = new FormData();
    formData.append('archivo', archivo);
    formData.append('validar_previo', validarPrevio);
    
    try {
        const response = await fetch('/api/transacciones/importar_excel/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Importación exitosa: ${result.transacciones_creadas} transacciones`);
            location.reload();
        } else {
            mostrarErroresValidacion(result.errores);
        }
        
    } catch (error) {
        alert('Error en la importación: ' + error.message);
    }
    
    cerrarModalImportar();
}
```

## 🚀 Orden de Implementación

### Fase 1: Exportación (2-3 horas)
1. Instalar dependencias `pip install openpyxl xlsxwriter`
2. Crear `ExcelTransactionHandler` básico
3. Implementar `exportar_excel` endpoint
4. Agregar botón "Exportar Excel" al frontend
5. Probar exportación básica

### Fase 2: Template (1-2 horas)  
1. Implementar `template_excel` endpoint
2. Crear template con hojas y validaciones
3. Agregar referencias de catálogos
4. Probar descarga de template

### Fase 3: Importación (4-6 horas)
1. Implementar validaciones de archivo
2. Crear lógica de importación
3. Manejar errores y conflictos
4. Agregar modal de importación
5. Implementar JavaScript frontend
6. Pruebas completas con diferentes escenarios

### Fase 4: Refinamiento (1-2 horas)
1. Mejorar validaciones
2. Agregar indicadores de progreso
3. Optimizar rendimiento para archivos grandes
4. Documentar proceso

## 🔍 Casos de Prueba Críticos

1. **Archivo válido**: Importar 10 transacciones con centros de costo
2. **Folios duplicados**: Manejar error correctamente  
3. **Cuentas inexistentes**: Mostrar errores claros
4. **Centros inválidos**: Validar códigos de centros de costo
5. **Balances incorrectos**: Validar que debe = haber por transacción
6. **Archivos grandes**: Probar con 1000+ transacciones

**Tiempo estimado total: 8-12 horas de desarrollo**