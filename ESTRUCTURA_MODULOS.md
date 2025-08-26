# ZivaSuite - Estructura de Módulos de Contabilidad

### Nueva Estructura Modular

#### 1. **apps/core** - Funcionalidad Base
- Modelo `BaseModel` para herencia común
- Modelo `Configuracion` para configuraciones del sistema
- Funcionalidades compartidas entre módulos

#### 2. **apps/empresas** - Gestión de Entidades
- Modelo `Empresa` - Entidades contables
- Modelo `Usuarios` - Gestión de usuarios
- Modelo `Usuario-empresa` - Gestión de acceso a entidades


#### 3. **apps/catalogo_cuentas** - Plan Contable
- Modelo `CuentaContable` - Catálogo de cuentas con jerarquía
- Modelo `CentroCosto` - Centros de costo para análisis
- Modelo de `Tags` de proyectos
- Soporte para códigos agrupadores SAT

#### 4. **apps/transacciones** - Movimientos Contables
- Modelo `TransaccionContable` - Encabezados de transacciones
- Modelo `MovimientoContable` - Detalle de movimientos
- Modelo de `tags de proyectos` - a nivel detalle de movimiento
- Estados de transacciones (Borrador, Validada, Contabilizada, Cancelada)
- Validaciones de cuadratura contable


#### 5. **apps/reportes** - Estados Financieros
- Configuración de reportes financieros
- Balance General, Estado de Resultados, Flujo de Efectivo
- Balanza de Comprobación, Libro Mayor, Libro Diario

### Próximos Pasos

1. **Implementar funcionalidad específica** en cada módulo según necesidades
2. **Crear URLs y vistas** para cada módulo
3. **Desarrollar APIs REST** usando Django REST Framework
4. **Implementar interfaces de usuario** con templates (react + Material-UI consistente)
5. **Integrar con SAT** `Pythoncfdi` para cumplimiento fiscal mexicano 

### Características del Sistema

- **Arquitectura Modular**: Cada funcionalidad en su propio módulo
- **Herencia Común**: BaseModel con auditoría automática
- **Validaciones Contables**: Cuadratura automática de transacciones
- **Jerarquía de Cuentas**: Soporte para múltiples niveles
- **Análisis Multidimensional**: Centros de costo y unidades de negocio
- **Cumplimiento Fiscal**: Preparado para códigos SAT
- **Multiempresa**: Soporte nativo para múltiples entidades
