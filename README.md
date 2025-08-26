# ZivaBSuite - Sistema de Contabilidad

Sistema contable modular desarrollado con Django y React, implementado por etapas según el documento de especificaciones.

## 📁 Estructura del Proyecto

```
ZivaBSuite/
├── backend/                    # Backend Django
│   ├── apps/                   # Aplicaciones modulares
│   │   ├── core/              # ✅ Etapa 1: Infraestructura base
│   │   ├── empresas/          # 🟡 Etapa 2: Gestión de empresas
│   │   ├── catalogo_cuentas/  # 🟡 Etapa 3: Catálogo de cuentas
│   │   ├── transacciones/     # 🟡 Etapa 4: Sistema de transacciones
│   │   └── reportes/          # 🟡 Etapa 5: Módulo de reportes
│   ├── config/                # Configuración Django
│   ├── docker/                # Archivos Docker
│   └── requirements/          # Dependencias Python
├── frontend/                  # Frontend React (pendiente)
├── docker-compose.yml         # Configuración Docker
└── etapas/                    # Documentación de etapas
```

## 🎉 Estado Actual: Etapa 1 OPERATIVA

### ✅ Completamente Implementado y Funcionando:
- **✅ Servicios Activos**: Backend Django + PostgreSQL + Redis
- **✅ URLs Operativas**: Admin (localhost:8000/admin) + API (localhost:8000/api)
- **✅ Infraestructura**: BaseModel con auditoría completa + soft delete
- **✅ Modelos**: Configuración, LogCambio, Empresa (básico)
- **✅ Utilidades**: 12+ funciones (RFC, cuadratura, folios, etc.)
- **✅ Validadores**: 10+ validadores personalizados
- **✅ Docker**: Configuración específica `docker-compose.etapa1.yml`
- **✅ Tests**: Unitarios implementados y funcionando
- **✅ Admin**: Accesible con usuario admin/admin123

## 🛠️ Instalación y Configuración

### Prerrequisitos
- Docker y Docker Compose
- Python 3.11+ (opcional, para desarrollo local)
- Node.js 18+ (para frontend)

### 1. Instalación Automática (Recomendada)
```bash
# Windows
setup.bat

# El script automáticamente:
# - Configura variables de entorno
# - Construye contenedores
# - Aplica migraciones  
# - Crea superusuario (admin/admin123)
# - Levanta todos los servicios
```

### 2. Instalación Manual (Alternativa)
```bash
# Configurar variables de entorno
# El archivo .env ya está listo para desarrollo

# Para Etapa 1 (solo backend - ACTUAL)
docker-compose -f docker-compose.etapa1.yml up --build

# Aplicar migraciones
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py migrate

# Crear superusuario
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py createsuperuser
```

### 3. Archivos Docker Disponibles
- **`docker-compose.etapa1.yml`** ✅ - Solo backend (Etapa 1 actual)
- **`docker-compose.yml`** 🟡 - Backend + Frontend (etapas futuras)  
- **`docker-compose.prod.yml`** 🟡 - Producción completa

### 4. Verificar instalación
```bash
# Verificar que todos los servicios estén corriendo
docker-compose -f docker-compose.etapa1.yml ps

# Resultado esperado:
# backend-1  ✅ Up (puerto 8000)
# db-1       ✅ Up healthy (puerto 5432) 
# redis-1    ✅ Up (puerto 6379)

# Probar API
curl http://localhost:8000/api/
# Debe retornar JSON con endpoints disponibles
```

### 🌐 URLs Operativas
- **Backend Django**: http://localhost:8000/
- **Admin Interface**: http://localhost:8000/admin/ 
- **API Root**: http://localhost:8000/api/ (público)
- **Credenciales Admin**: admin / admin123

## 🧪 Ejecutar Tests

```bash
# Todos los tests del core
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test apps.core.tests

# Tests específicos 
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test apps.core.tests.test_models

# Ver output detallado
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test --verbosity=2
```

## 📊 Comandos Útiles (Etapa 1)

```bash
# Ver estado de servicios
docker-compose -f docker-compose.etapa1.yml ps

# Ver logs
docker-compose -f docker-compose.etapa1.yml logs -f backend

# Shell de Django
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py shell

# Verificar migraciones
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py showmigrations

# Parar servicios
docker-compose -f docker-compose.etapa1.yml down
```

## 🔄 Próximas Etapas

### Etapa 2: Gestión de Usuarios y Empresas
- [ ] Modelo Usuario-Empresa con roles y permisos
- [ ] Sistema de autenticación multiempresa
- [ ] Middleware de contexto de empresa
- [ ] API de gestión de usuarios

### Etapa 3: Catálogo de Cuentas Mejorado
- [ ] Estructura jerárquica de cuentas
- [ ] Centros de costo
- [ ] Tags de proyectos
- [ ] Códigos agrupadores SAT
- [ ] Importación/exportación masiva

### Etapa 4: Sistema de Transacciones
- [ ] Refactorización de Pólizas a TransaccionContable
- [ ] Validaciones contables automáticas
- [ ] Estados de transacciones
- [ ] Integración CFDI/SAT

### Etapa 5: Módulo de Reportes
- [ ] Balance General
- [ ] Estado de Resultados
- [ ] Balanza de Comprobación
- [ ] Libro Mayor/Diario
- [ ] Exportación a diferentes formatos

## 📝 Documentación Técnica

- [Etapa 1: Infraestructura Base](etapa_1_infraestructura_base.md)
- [Etapa 2: Usuarios y Empresas](etapa_2_usuarios_empresas.md)  
- [Etapa 3: Catálogo Mejorado](etapa_3_catalogo_mejorado.md)
- [Estructura de Módulos](ESTRUCTURA_MODULOS.md)
- [Plan de Integración SAT](SAT_INTEGRATION_PLAN.md)

## 🐛 Troubleshooting

### Problemas Resueltos en Etapa 1

1. **✅ ERR_CONNECTION_REFUSED** 
   - **Solución**: Usar `docker-compose.etapa1.yml` en lugar de `docker-compose.yml`
   ```bash
   # Correcto para Etapa 1:
   docker-compose -f docker-compose.etapa1.yml up --build
   ```

2. **✅ Error Frontend Not Found**
   - **Causa**: Frontend no implementado en Etapa 1
   - **Solución**: Usar configuración específica de backend únicamente

3. **✅ Error 404 en /api/**
   - **Solución**: Agregada vista API root que lista endpoints disponibles
   ```bash
   curl http://localhost:8000/api/  # Ahora retorna JSON válido
   ```

### Comandos de Diagnóstico

```bash
# Verificar estado completo
docker-compose -f docker-compose.etapa1.yml ps

# Ver logs en tiempo real
docker-compose -f docker-compose.etapa1.yml logs -f

# Verificar conectividad de DB
docker-compose -f docker-compose.etapa1.yml exec backend python manage.py dbshell

# Reiniciar servicios si hay problemas
docker-compose -f docker-compose.etapa1.yml restart
```

## 📞 Soporte

Para reportar problemas o solicitar funcionalidades, crear un issue en el repositorio del proyecto.

---

**Desarrollado siguiendo las especificaciones del documento de análisis comparativo ejemplo_basico.txt vs ESTRUCTURA_MODULOS.md**