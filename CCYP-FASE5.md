# CCYP-FASE5: Mejoras UX/UI

## 🎯 **Objetivo de la Fase 5**
Optimizar la experiencia de usuario (UX) y la interfaz de usuario (UI) para el sistema de centros de costo y proyectos, implementando funcionalidades avanzadas que mejoren la productividad y usabilidad.

## 📋 **Tareas de la Fase 5**

### ✅ **Completadas**
- [ ] Implementar selector inteligente con autocompletar
- [ ] Agregar memoria de últimas selecciones
- [ ] Crear validación cruzada centro-proyecto en tiempo real
- [ ] Mejorar vista de transacciones con indicadores visuales
- [ ] Implementar filtros avanzados con búsqueda múltiple
- [ ] Agregar shortcuts de teclado para power users
- [ ] Optimizar rendimiento con lazy loading
- [ ] Crear wizard de configuración inicial

### 🎯 **En Progreso**
- *Ninguna tarea en progreso actualmente*

### ⏳ **Pendientes**
- [ ] Todas las tareas listadas arriba

## 🏗️ **Detalles de Implementación**

### **5.1 Selector Inteligente con Autocompletar**
```javascript
// static/js/centros-costo-selector.js
class CentroCostoSelector {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            placeholder: 'Buscar centro de costo...',
            allowClear: true,
            rememberSelection: true,
            validateProject: true,
            ...options
        };
        
        this.init();
    }
    
    init() {
        this.createSearchInput();
        this.loadRecentSelections();
        this.attachEventListeners();
    }
    
    createSearchInput() {
        const wrapper = document.createElement('div');
        wrapper.className = 'relative';
        
        wrapper.innerHTML = `
            <input type="text" 
                   class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                   placeholder="${this.options.placeholder}">
            <div class="absolute inset-y-0 right-0 flex items-center pr-3">
                <i class="fas fa-search text-gray-400"></i>
            </div>
            <div class="suggestions-dropdown hidden absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
            </div>
        `;
        
        this.container.appendChild(wrapper);
        this.input = wrapper.querySelector('input');
        this.dropdown = wrapper.querySelector('.suggestions-dropdown');
    }
    
    attachEventListeners() {
        let debounceTimer;
        
        this.input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.search(e.target.value);
            }, 300);
        });
        
        this.input.addEventListener('focus', () => {
            if (!this.input.value) {
                this.showRecentSelections();
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.dropdown.classList.add('hidden');
            }
        });
    }
    
    async search(query) {
        if (query.length < 2) {
            this.dropdown.classList.add('hidden');
            return;
        }
        
        try {
            const response = await fetch(`/api/centros-costo/centros/?search=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderSuggestions(data.results || data, query);
        } catch (error) {
            console.error('Error buscando centros de costo:', error);
        }
    }
    
    renderSuggestions(centros, query = '') {
        if (!centros.length) {
            this.dropdown.innerHTML = '<div class="p-3 text-gray-500 text-sm">No se encontraron centros de costo</div>';
            this.dropdown.classList.remove('hidden');
            return;
        }
        
        let html = '';
        
        // Mostrar recientes primero si no hay query
        if (!query && this.recentSelections.length > 0) {
            html += '<div class="p-2 text-xs text-gray-400 border-b bg-gray-50">Recientes</div>';
            this.recentSelections.forEach(centro => {
                html += this.renderSuggestionItem(centro, true);
            });
            html += '<div class="p-2 text-xs text-gray-400 border-b bg-gray-50">Todos</div>';
        }
        
        centros.forEach(centro => {
            // Evitar duplicados con recientes
            if (!this.recentSelections.find(r => r.id === centro.id)) {
                html += this.renderSuggestionItem(centro);
            }
        });
        
        this.dropdown.innerHTML = html;
        this.dropdown.classList.remove('hidden');
        
        // Agregar event listeners a los items
        this.dropdown.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const centroData = JSON.parse(item.dataset.centro);
                this.selectCentro(centroData);
            });
        });
    }
    
    renderSuggestionItem(centro, isRecent = false) {
        const bgColorClass = `bg-${centro.color_interfaz}-100`;
        const textColorClass = `text-${centro.color_interfaz}-800`;
        
        return `
            <div class="suggestion-item p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0" 
                 data-centro='${JSON.stringify(centro)}'>
                <div class="flex items-center">
                    <div class="w-3 h-3 rounded-full ${bgColorClass} mr-3"></div>
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">
                            ${centro.codigo} - ${centro.nombre}
                            ${isRecent ? '<i class="fas fa-clock text-gray-400 ml-2 text-xs"></i>' : ''}
                        </div>
                        <div class="text-xs text-gray-500">${centro.ruta_completa || centro.tipo}</div>
                    </div>
                    <div class="text-xs ${textColorClass} px-2 py-1 ${bgColorClass} rounded">
                        ${centro.get_tipo_display || centro.tipo}
                    </div>
                </div>
            </div>
        `;
    }
    
    selectCentro(centro) {
        this.input.value = `${centro.codigo} - ${centro.nombre}`;
        this.input.dataset.centroId = centro.id;
        this.dropdown.classList.add('hidden');
        
        // Guardar en selecciones recientes
        this.saveToRecentSelections(centro);
        
        // Validar proyecto si está habilitado
        if (this.options.validateProject) {
            this.validateProjectCompatibility(centro);
        }
        
        // Disparar evento personalizado
        this.container.dispatchEvent(new CustomEvent('centroSelected', {
            detail: { centro }
        }));
    }
    
    loadRecentSelections() {
        const saved = localStorage.getItem('centros_recientes');
        this.recentSelections = saved ? JSON.parse(saved) : [];
    }
    
    saveToRecentSelections(centro) {
        // Remover si ya existe
        this.recentSelections = this.recentSelections.filter(r => r.id !== centro.id);
        
        // Agregar al inicio
        this.recentSelections.unshift(centro);
        
        // Mantener solo los últimos 5
        this.recentSelections = this.recentSelections.slice(0, 5);
        
        // Guardar en localStorage
        localStorage.setItem('centros_recientes', JSON.stringify(this.recentSelections));
    }
    
    showRecentSelections() {
        if (this.recentSelections.length > 0) {
            this.renderSuggestions([], '');
        }
    }
    
    validateProjectCompatibility(centro) {
        // Buscar selector de proyecto en la misma fila
        const row = this.container.closest('tr');
        if (!row) return;
        
        const projectSelector = row.querySelector('.project-selector');
        if (!projectSelector) return;
        
        const projectId = projectSelector.dataset.projectId;
        if (!projectId) return;
        
        // Validar compatibilidad via AJAX
        fetch(`/api/centros-costo/validate-compatibility/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                centro_id: centro.id,
                project_id: projectId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.compatible) {
                this.showCompatibilityWarning(data.message);
            }
        });
    }
    
    showCompatibilityWarning(message) {
        // Mostrar tooltip o modal de advertencia
        const warning = document.createElement('div');
        warning.className = 'absolute top-full left-0 mt-1 p-2 bg-yellow-100 border border-yellow-300 rounded text-xs text-yellow-800 z-50';
        warning.innerHTML = `
            <i class="fas fa-exclamation-triangle mr-1"></i>
            ${message}
        `;
        
        this.container.style.position = 'relative';
        this.container.appendChild(warning);
        
        setTimeout(() => {
            warning.remove();
        }, 5000);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    clear() {
        this.input.value = '';
        this.input.removeAttribute('data-centro-id');
        this.dropdown.classList.add('hidden');
    }
}

// Inicialización automática
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.centro-costo-selector').forEach(container => {
        new CentroCostoSelector(container.id);
    });
});
```

### **5.2 Mejorar Template de Creación con UX Avanzada**
```html
<!-- Actualizar templates/transacciones/crear.html -->

<!-- Agregar CSS personalizado -->
<style>
.input-group-enhanced {
    position: relative;
}

.smart-selector {
    position: relative;
}

.recent-badge {
    background: linear-gradient(45deg, #3B82F6, #1D4ED8);
    color: white;
    font-size: 0.6rem;
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
    margin-left: 0.5rem;
}

.compatibility-indicator {
    position: absolute;
    top: -0.5rem;
    right: -0.5rem;
    width: 1rem;
    height: 1rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6rem;
    color: white;
}

.compatibility-ok { background-color: #10B981; }
.compatibility-warning { background-color: #F59E0B; }
.compatibility-error { background-color: #EF4444; }

.floating-help {
    position: fixed;
    top: 50%;
    right: 2rem;
    transform: translateY(-50%);
    background: white;
    padding: 1rem;
    border-radius: 0.5rem;
    shadow: 0 10px 25px rgba(0,0,0,0.1);
    border: 1px solid #E5E7EB;
    z-index: 1000;
    max-width: 250px;
}

.keyboard-shortcut {
    font-family: monospace;
    background: #F3F4F6;
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
}
</style>

<!-- Modificar tabla de movimientos debe -->
<table class="w-full" id="tabla-debe">
    <thead class="bg-gray-50">
        <tr>
            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Cuenta
                <div class="text-xs font-normal text-gray-400 mt-1">
                    <kbd class="keyboard-shortcut">F2</kbd> Buscar
                </div>
            </th>
            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Centro Costo
                <div class="text-xs font-normal text-gray-400 mt-1">
                    <kbd class="keyboard-shortcut">F3</kbd> Recientes
                </div>
            </th>
            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Proyecto
                <div class="text-xs font-normal text-gray-400 mt-1">
                    <kbd class="keyboard-shortcut">F4</kbd> Activos
                </div>
            </th>
            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Concepto</th>
            <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                Monto
                <div class="text-xs font-normal text-gray-400 mt-1">
                    <kbd class="keyboard-shortcut">Tab</kbd> Siguiente
                </div>
            </th>
            <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Acción</th>
        </tr>
    </thead>
    <tbody>
        <tr class="border-t" id="row-debe-1">
            <!-- Cuenta con autocompletar -->
            <td class="px-3 py-2">
                <div class="input-group-enhanced">
                    <div id="cuenta-selector-debe-1" class="smart-selector cuenta-selector"></div>
                    <input type="hidden" name="cuenta_debe[]" id="cuenta_debe_1">
                </div>
            </td>
            
            <!-- Centro de Costo con selector inteligente -->
            <td class="px-3 py-2">
                <div class="input-group-enhanced">
                    <div id="centro-selector-debe-1" class="smart-selector centro-costo-selector"></div>
                    <input type="hidden" name="centro_costo_debe[]" id="centro_debe_1">
                    <div class="compatibility-indicator compatibility-ok hidden" id="centro-indicator-debe-1">
                        <i class="fas fa-check"></i>
                    </div>
                </div>
            </td>
            
            <!-- Proyecto con selector inteligente -->
            <td class="px-3 py-2">
                <div class="input-group-enhanced">
                    <div id="proyecto-selector-debe-1" class="smart-selector project-selector"></div>
                    <input type="hidden" name="proyecto_debe[]" id="proyecto_debe_1">
                    <div class="compatibility-indicator compatibility-ok hidden" id="proyecto-indicator-debe-1">
                        <i class="fas fa-check"></i>
                    </div>
                </div>
            </td>
            
            <!-- Concepto con sugerencias -->
            <td class="px-3 py-2">
                <input type="text" name="concepto_debe[]" id="concepto_debe_1"
                       class="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                       placeholder="Concepto específico..."
                       list="conceptos-sugeridos">
                <datalist id="conceptos-sugeridos">
                    <!-- Se llenarán via JavaScript -->
                </datalist>
            </td>
            
            <!-- Monto con validación en vivo -->
            <td class="px-3 py-2">
                <div class="relative">
                    <input type="number" name="monto_debe[]" id="monto_debe_1"
                           step="0.01" min="0" required
                           class="w-full px-2 py-1 border border-gray-300 rounded text-sm text-right pr-8"
                           onchange="calcularTotales()" 
                           oninput="formatearMonto(this)">
                    <div class="absolute inset-y-0 right-0 flex items-center pr-2">
                        <span class="text-xs text-gray-400">$</span>
                    </div>
                </div>
            </td>
            
            <!-- Acciones con confirmación -->
            <td class="px-3 py-2 text-center">
                <button type="button" onclick="eliminarFilaConConfirmacion(this, 'debe')" 
                        class="text-red-600 hover:text-red-900 p-1 rounded hover:bg-red-50"
                        title="Eliminar fila (Del)">
                    <i class="fas fa-trash text-sm"></i>
                </button>
            </td>
        </tr>
    </tbody>
</table>

<!-- Widget de ayuda flotante -->
<div class="floating-help" id="floating-help" style="display: none;">
    <div class="flex items-center justify-between mb-3">
        <h4 class="font-medium text-gray-900">Atajos de Teclado</h4>
        <button onclick="toggleFloatingHelp()" class="text-gray-400 hover:text-gray-600">
            <i class="fas fa-times"></i>
        </button>
    </div>
    <div class="space-y-2 text-sm">
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">F2</kbd></span>
            <span class="text-gray-600">Buscar cuenta</span>
        </div>
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">F3</kbd></span>
            <span class="text-gray-600">Centros recientes</span>
        </div>
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">F4</kbd></span>
            <span class="text-gray-600">Proyectos activos</span>
        </div>
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">Ctrl+Enter</kbd></span>
            <span class="text-gray-600">Guardar</span>
        </div>
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">Ctrl+N</kbd></span>
            <span class="text-gray-600">Nueva fila</span>
        </div>
        <div class="flex justify-between">
            <span><kbd class="keyboard-shortcut">Del</kbd></span>
            <span class="text-gray-600">Eliminar fila</span>
        </div>
    </div>
</div>

<!-- Botón de ayuda -->
<button type="button" onclick="toggleFloatingHelp()" 
        class="fixed bottom-4 right-4 bg-indigo-600 text-white p-3 rounded-full shadow-lg hover:bg-indigo-700 z-50"
        title="Mostrar atajos de teclado (F1)">
    <i class="fas fa-question"></i>
</button>
```

### **5.3 JavaScript Avanzado para UX**
```javascript
// static/js/transacciones-ux-enhanced.js

class TransaccionesUXEnhanced {
    constructor() {
        this.initKeyboardShortcuts();
        this.initSmartValidation();
        this.initAutoSave();
        this.initAccessibilityFeatures();
    }
    
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // F1 - Mostrar ayuda
            if (e.key === 'F1') {
                e.preventDefault();
                toggleFloatingHelp();
            }
            
            // Ctrl+Enter - Guardar formulario
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                const form = document.querySelector('form');
                if (form && this.validateForm()) {
                    form.submit();
                }
            }
            
            // Ctrl+N - Nueva fila debe
            if (e.ctrlKey && e.key === 'n') {
                e.preventDefault();
                agregarFilaDebe();
            }
            
            // Ctrl+Shift+N - Nueva fila haber  
            if (e.ctrlKey && e.shiftKey && e.key === 'N') {
                e.preventDefault();
                agregarFilaHaber();
            }
            
            // Delete - Eliminar fila actual
            if (e.key === 'Delete' && !e.target.matches('input, textarea, select')) {
                const activeRow = document.activeElement.closest('tr');
                if (activeRow && activeRow.parentElement.children.length > 1) {
                    eliminarFilaConConfirmacion(activeRow.querySelector('button[onclick*="eliminarFila"]'));
                }
            }
            
            // Tab - Navegación inteligente
            if (e.key === 'Tab') {
                this.handleIntelligentTab(e);
            }
        });
    }
    
    handleIntelligentTab(e) {
        const activeElement = document.activeElement;
        
        // Si estamos en el último campo de una fila, crear nueva fila automáticamente
        if (activeElement.matches('input[name*="monto_"]')) {
            const row = activeElement.closest('tr');
            const tbody = row.parentElement;
            const isLastRow = row === tbody.lastElementChild;
            
            if (isLastRow && activeElement.value) {
                setTimeout(() => {
                    if (row.closest('#tabla-debe')) {
                        agregarFilaDebe();
                    } else {
                        agregarFilaHaber();
                    }
                    
                    // Enfocar primera celda de la nueva fila
                    setTimeout(() => {
                        const newRow = tbody.lastElementChild;
                        const firstInput = newRow.querySelector('input, select');
                        if (firstInput) firstInput.focus();
                    }, 100);
                }, 50);
            }
        }
    }
    
    initSmartValidation() {
        // Validación en tiempo real
        document.addEventListener('input', (e) => {
            if (e.target.matches('input[name*="monto_"]')) {
                this.validateAmount(e.target);
            }
        });
        
        // Validación de compatibilidad centro-proyecto
        document.addEventListener('centroSelected', (e) => {
            this.validateCentroProjectCompatibility(e.target);
        });
        
        document.addEventListener('projectSelected', (e) => {
            this.validateCentroProjectCompatibility(e.target);
        });
    }
    
    validateAmount(input) {
        const value = parseFloat(input.value) || 0;
        const row = input.closest('tr');
        
        // Indicador visual para montos grandes
        if (value > 100000) {
            input.classList.add('border-yellow-400', 'bg-yellow-50');
            this.showTooltip(input, 'Monto elevado - Verificar', 'warning');
        } else {
            input.classList.remove('border-yellow-400', 'bg-yellow-50', 'border-red-400', 'bg-red-50');
        }
        
        // Formateo automático
        if (value > 0) {
            const formatted = new Intl.NumberFormat('es-MX', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(value);
            
            // Mostrar formato visual sin alterar el value
            input.title = `$${formatted}`;
        }
    }
    
    validateCentroProjectCompatibility(element) {
        const row = element.closest('tr');
        const centroId = row.querySelector('input[name*="centro_costo"]')?.dataset.centroId;
        const projectId = row.querySelector('input[name*="proyecto"]')?.dataset.projectId;
        
        if (centroId && projectId) {
            fetch('/api/centros-costo/validate-compatibility/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    centro_id: centroId,
                    project_id: projectId
                })
            })
            .then(response => response.json())
            .then(data => {
                this.updateCompatibilityIndicators(row, data);
            });
        }
    }
    
    updateCompatibilityIndicators(row, compatibilityData) {
        const centroIndicator = row.querySelector('[id*="centro-indicator"]');
        const projectIndicator = row.querySelector('[id*="proyecto-indicator"]');
        
        const indicatorClass = compatibilityData.compatible ? 'compatibility-ok' : 
                             compatibilityData.warning ? 'compatibility-warning' : 'compatibility-error';
        const icon = compatibilityData.compatible ? 'fa-check' : 
                    compatibilityData.warning ? 'fa-exclamation' : 'fa-times';
        
        [centroIndicator, projectIndicator].forEach(indicator => {
            if (indicator) {
                indicator.className = `compatibility-indicator ${indicatorClass}`;
                indicator.innerHTML = `<i class="fas ${icon}"></i>`;
                indicator.classList.remove('hidden');
                indicator.title = compatibilityData.message || '';
            }
        });
    }
    
    initAutoSave() {
        let autoSaveTimer;
        const formData = new Map();
        
        document.addEventListener('input', (e) => {
            if (e.target.matches('input, select, textarea')) {
                // Guardar estado cada 30 segundos
                clearTimeout(autoSaveTimer);
                autoSaveTimer = setTimeout(() => {
                    this.saveFormState();
                }, 30000);
            }
        });
        
        // Recuperar estado al cargar
        this.loadFormState();
        
        // Guardar antes de salir
        window.addEventListener('beforeunload', (e) => {
            this.saveFormState();
        });
    }
    
    saveFormState() {
        const formData = {};
        const form = document.querySelector('form');
        
        new FormData(form).forEach((value, key) => {
            formData[key] = value;
        });
        
        localStorage.setItem('transaccion_draft', JSON.stringify({
            data: formData,
            timestamp: new Date().toISOString()
        }));
        
        this.showNotification('Borrador guardado automáticamente', 'info', 2000);
    }
    
    loadFormState() {
        const savedData = localStorage.getItem('transaccion_draft');
        if (!savedData) return;
        
        try {
            const { data, timestamp } = JSON.parse(savedData);
            const savedDate = new Date(timestamp);
            const hoursDiff = (new Date() - savedDate) / (1000 * 60 * 60);
            
            // Solo recuperar si es menor a 24 horas
            if (hoursDiff < 24) {
                const modal = this.createRecoveryModal();
                modal.querySelector('#recover-yes').onclick = () => {
                    this.restoreFormData(data);
                    modal.remove();
                };
                modal.querySelector('#recover-no').onclick = () => {
                    localStorage.removeItem('transaccion_draft');
                    modal.remove();
                };
                
                document.body.appendChild(modal);
            }
        } catch (error) {
            console.error('Error recovering form state:', error);
        }
    }
    
    createRecoveryModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md mx-4">
                <div class="flex items-center mb-4">
                    <i class="fas fa-history text-blue-600 text-xl mr-3"></i>
                    <h3 class="text-lg font-medium">Borrador Encontrado</h3>
                </div>
                <p class="text-gray-600 mb-6">Se encontró un borrador de transacción guardado anteriormente. ¿Deseas recuperarlo?</p>
                <div class="flex justify-end space-x-3">
                    <button id="recover-no" class="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50">
                        No, comenzar nuevo
                    </button>
                    <button id="recover-yes" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Sí, recuperar
                    </button>
                </div>
            </div>
        `;
        return modal;
    }
    
    restoreFormData(data) {
        Object.entries(data).forEach(([key, value]) => {
            const element = document.querySelector(`[name="${key}"]`);
            if (element) {
                element.value = value;
                element.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
        
        this.showNotification('Borrador recuperado exitosamente', 'success');
    }
    
    initAccessibilityFeatures() {
        // Focus trap para modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modal = document.querySelector('.fixed.inset-0');
                if (modal) {
                    modal.remove();
                }
            }
        });
        
        // Navegación por arrow keys en tablas
        document.addEventListener('keydown', (e) => {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                this.handleArrowKeyNavigation(e);
            }
        });
        
        // Anuncios para screen readers
        this.setupScreenReaderAnnouncements();
    }
    
    handleArrowKeyNavigation(e) {
        const activeElement = document.activeElement;
        if (!activeElement.closest('table')) return;
        
        const cell = activeElement.closest('td');
        const row = activeElement.closest('tr');
        
        let targetCell;
        
        switch(e.key) {
            case 'ArrowUp':
                const prevRow = row.previousElementSibling;
                if (prevRow) {
                    const cellIndex = Array.from(row.children).indexOf(cell);
                    targetCell = prevRow.children[cellIndex];
                }
                break;
            case 'ArrowDown':
                const nextRow = row.nextElementSibling;
                if (nextRow) {
                    const cellIndex = Array.from(row.children).indexOf(cell);
                    targetCell = nextRow.children[cellIndex];
                }
                break;
            case 'ArrowLeft':
                targetCell = cell.previousElementSibling;
                break;
            case 'ArrowRight':
                targetCell = cell.nextElementSibling;
                break;
        }
        
        if (targetCell) {
            const input = targetCell.querySelector('input, select, textarea');
            if (input) {
                e.preventDefault();
                input.focus();
            }
        }
    }
    
    setupScreenReaderAnnouncements() {
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'live-announcements';
        document.body.appendChild(liveRegion);
    }
    
    announceToScreenReader(message) {
        const liveRegion = document.getElementById('live-announcements');
        if (liveRegion) {
            liveRegion.textContent = message;
        }
    }
    
    showNotification(message, type = 'info', duration = 4000) {
        const notification = document.createElement('div');
        const bgColor = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        }[type] || 'bg-blue-500';
        
        notification.className = `fixed top-4 right-4 ${bgColor} text-white p-4 rounded-lg shadow-lg z-50 transform translate-x-full transition-transform`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-info-circle mr-2"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animación de entrada
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remove
        if (duration > 0) {
            setTimeout(() => {
                notification.classList.add('translate-x-full');
                setTimeout(() => notification.remove(), 300);
            }, duration);
        }
        
        this.announceToScreenReader(message);
    }
    
    showTooltip(element, message, type = 'info') {
        const tooltip = document.createElement('div');
        const bgColor = {
            success: 'bg-green-600',
            error: 'bg-red-600', 
            warning: 'bg-yellow-600',
            info: 'bg-gray-600'
        }[type] || 'bg-gray-600';
        
        tooltip.className = `absolute z-50 px-2 py-1 text-xs text-white ${bgColor} rounded shadow-lg pointer-events-none`;
        tooltip.textContent = message;
        
        element.style.position = 'relative';
        element.appendChild(tooltip);
        
        // Posicionar tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.top = '-2rem';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translateX(-50%)';
        
        setTimeout(() => tooltip.remove(), 3000);
    }
    
    validateForm() {
        const errors = [];
        
        // Validar balance
        const totalDebe = parseFloat(document.getElementById('total-debe').textContent);
        const totalHaber = parseFloat(document.getElementById('total-haber').textContent);
        
        if (Math.abs(totalDebe - totalHaber) > 0.01) {
            errors.push('La transacción debe estar balanceada (Debe = Haber)');
        }
        
        // Validar campos requeridos
        const requiredFields = document.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                errors.push(`El campo ${field.getAttribute('name')} es requerido`);
            }
        });
        
        if (errors.length > 0) {
            this.showNotification(errors.join('\n'), 'error');
            return false;
        }
        
        return true;
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Funciones globales mejoradas
function toggleFloatingHelp() {
    const help = document.getElementById('floating-help');
    help.style.display = help.style.display === 'none' ? 'block' : 'none';
}

function eliminarFilaConConfirmacion(button, tipo = '') {
    const row = button.closest('tr');
    const tbody = row.parentElement;
    
    if (tbody.children.length === 1) {
        uxEnhanced.showNotification('Debe mantener al menos un movimiento', 'warning');
        return;
    }
    
    // Confirmación con context
    const monto = row.querySelector('input[name*="monto"]')?.value || '0';
    const cuenta = row.querySelector('select[name*="cuenta"] option:checked')?.textContent || 'Sin cuenta';
    
    if (parseFloat(monto) > 0) {
        const confirmed = confirm(`¿Eliminar movimiento de $${monto} en ${cuenta}?`);
        if (!confirmed) return;
    }
    
    row.remove();
    calcularTotales();
    uxEnhanced.announceToScreenReader(`Fila ${tipo} eliminada`);
}

function formatearMonto(input) {
    const value = parseFloat(input.value) || 0;
    if (value > 0) {
        uxEnhanced.validateAmount(input);
    }
}

// Inicialización
let uxEnhanced;
document.addEventListener('DOMContentLoaded', function() {
    uxEnhanced = new TransaccionesUXEnhanced();
});
```

### **5.4 API Endpoints para Funcionalidades Avanzadas**
```python
# apps/centros_costo/views.py - Agregar endpoints

@login_required
@require_http_methods(["POST"])
def validate_compatibility(request):
    """Validar compatibilidad entre centro de costo y proyecto"""
    data = json.loads(request.body)
    centro_id = data.get('centro_id')
    project_id = data.get('project_id')
    
    empresa = get_empresa_actual(request)
    if not empresa:
        return JsonResponse({'error': 'No hay empresa seleccionada'}, status=400)
    
    try:
        centro = CentroCosto.objects.get(id=centro_id, empresa=empresa)
        proyecto = Proyecto.objects.get(id=project_id, empresa=empresa)
        
        # Validaciones de compatibilidad
        compatible = True
        warning = False
        message = "Centro y proyecto compatibles"
        
        # Verificar si el proyecto tiene un centro de costo asignado diferente
        if proyecto.centro_costo and proyecto.centro_costo.id != centro.id:
            # Verificar si el centro seleccionado es hijo del centro del proyecto
            if not is_child_of(centro, proyecto.centro_costo):
                compatible = False
                message = f"El proyecto está asignado al centro '{proyecto.centro_costo.nombre}'"
            else:
                warning = True
                message = f"El centro es subcento de '{proyecto.centro_costo.nombre}'"
        
        # Verificar estados
        if proyecto.estado not in ['ACTIVO', 'PLANIFICACION']:
            compatible = False
            message = f"El proyecto está en estado '{proyecto.estado}'"
        
        if not centro.permite_movimientos:
            compatible = False
            message = "El centro de costo no permite movimientos directos"
        
        return JsonResponse({
            'compatible': compatible,
            'warning': warning,
            'message': message
        })
        
    except (CentroCosto.DoesNotExist, Proyecto.DoesNotExist):
        return JsonResponse({
            'compatible': False,
            'message': 'Centro de costo o proyecto no encontrado'
        }, status=404)

def is_child_of(centro, parent_centro):
    """Verifica si un centro es hijo de otro centro"""
    current = centro
    while current.centro_padre:
        if current.centro_padre.id == parent_centro.id:
            return True
        current = current.centro_padre
    return False

@login_required
def conceptos_frecuentes(request):
    """API para obtener conceptos más usados"""
    empresa = get_empresa_actual(request)
    if not empresa:
        return JsonResponse({'conceptos': []})
    
    # Obtener los 20 conceptos más frecuentes de los últimos 6 meses
    hace_6_meses = timezone.now() - timedelta(days=180)
    
    conceptos = MovimientoContable.objects.filter(
        transaccion__empresa=empresa,
        transaccion__fecha__gte=hace_6_meses.date(),
        concepto__isnull=False,
        activo=True
    ).exclude(
        concepto__exact=''
    ).values('concepto').annotate(
        count=Count('concepto')
    ).order_by('-count')[:20]
    
    return JsonResponse({
        'conceptos': [c['concepto'] for c in conceptos]
    })
```

## ✅ **Criterios de Aceptación**

- [ ] Selector inteligente con autocompletar funcional
- [ ] Memoria de selecciones recientes implementada  
- [ ] Validación cruzada centro-proyecto en tiempo real
- [ ] Atajos de teclado completamente funcionales
- [ ] Auto-guardado de borradores operativo
- [ ] Navegación mejorada con indicadores visuales
- [ ] Accesibilidad completa (screen readers, navegación por teclado)
- [ ] Performance optimizada para uso intensivo
- [ ] Notificaciones contextuales y útiles

## 📱 **Responsive Design y Mobile**

### **5.5 Adaptaciones para Dispositivos Móviles**
- Selectores táctiles optimizados
- Tablas con scroll horizontal en móviles
- Botones de acción de tamaño adecuado para touch
- Modal fullscreen en dispositivos pequeños
- Gestos swipe para navegación entre pestañas

## 📊 **Métricas de UX**
- ✅ Tiempo de entrada de transacción < 60 segundos
- ✅ Reducción de errores de captura en 70%
- ✅ Satisfacción de usuario > 4.5/5
- ✅ Adopción de atajos de teclado > 40%
- ✅ Tiempo de carga de selectores < 200ms
- ✅ 100% funcional con screen readers