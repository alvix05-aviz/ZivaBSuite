
# Plan de Implementación: Integración con Servicios del SAT

## 0. Estado Actual (23 de Agosto, 2025)

**La Fase 2 (Lógica de Negocio y API) ha sido parcialmente completada.**

Se ha creado la estructura de los archivos para la API REST (`serializers.py`, `viewsets.py`, `urls.py`) y para las tareas asíncronas (`tasks.py`). El código incluye la estructura básica y comentarios que describen la lógica pendiente de implementación.

**Próximos Pasos:**
1.  Implementar la lógica de negocio completa dentro de la tarea de Celery `process_massive_download` para comunicarse con el SAT.
2.  Completar la lógica en los `ViewSets` para manejar las solicitudes de la API y las consultas de estado.
3.  Iniciar la **Fase 3: Integración con el Frontend**.

---

## 1. Resumen Ejecutivo

Este documento describe el plan técnico para integrar la funcionalidad de **Descarga Masiva y Consulta de Estado de CFDI** desde el portal del SAT directamente en la plataforma Ziva Suite.

El objetivo es crear una solución robusta, escalable y segura que se integre de forma nativa con la arquitectura existente de Ziva Suite, sin interferir con el desarrollo en curso.

La arquitectura propuesta se basa en la creación de una nueva **app de Django aislada** (`sat_integration`) dentro del proyecto, que orquestará la comunicación con el SAT a través de la librería `satcfdi` y expondrá los servicios al resto de la aplicación mediante una **API REST interna**.

---

## 2. Arquitectura de la Solución

La integración se compondrá de los siguientes elementos:

1.  **Nueva App Django (`sat_integration`):**
    *   Contendrá todo el código relacionado con la lógica de negocio del SAT.
    *   Será responsable de la comunicación con los web services del SAT.
    *   Definirá los modelos de datos para almacenar la información de los CFDI.
    *   Se desarrollará en una rama de Git (`feature/sat-integration`) para no interferir con la rama principal.

2.  **Librería `satcfdi`:**
    *   Será la dependencia clave para interactuar con el SAT.
    *   Se añadirá al archivo `requirements.txt`.
    *   Gestionará la autenticación con la FIEL, las solicitudes de descarga y las consultas de estado.

3.  **Tareas en Segundo Plano (Celery):**
    *   El proceso de descarga masiva se ejecutará como una tarea asíncrona de Celery para no bloquear la interfaz de usuario.
    *   Se creará una nueva cola de Celery si es necesario para priorizar estas tareas.
    *   El estado de la tarea (ej: "Pendiente", "Procesando", "Completado") se almacenará en la base de datos para poder consultarlo desde el frontend.

4.  **API REST Interna:**
    *   Será el punto de entrada a la funcionalidad desde el frontend de React o cualquier otra parte de Ziva Suite.
    *   Expondrá endpoints claros y seguros para iniciar descargas y realizar consultas.

---

## 3. Plan de Implementación Paso a Paso

### Fase 1: Configuración del Backend (Completada)

1.  **Crear la Nueva App: [✓ Completado]**
    *   Se ejecutó: `python manage.py startapp sat_integration`
    *   Se añadió `'apps.sat_integration'` a la lista de `INSTALLED_APPS`.

2.  **Añadir Dependencias: [✓ Completado]**
    *   Se añadió `satcfdi` y `requests` al archivo `requirements.txt`.
    *   Se instalaron las dependencias en el entorno de desarrollo.

3.  **Definir Modelos de Datos: [✓ Completado]**
    *   Se crearon los modelos `SATCredentials`, `CFDIDownloadJob` y `CFDI` en `apps/sat_integration/models.py` con la documentación correspondiente.

4.  **Crear Migraciones: [✓ Completado]**
    *   Se ejecutó: `python manage.py makemigrations sat_integration`
    *   Se ejecutó: `python manage.py migrate`

### Fase 2: Lógica de Negocio y API (En Progreso)

5.  **Implementar Tareas de Celery: [✓ Estructura Creada]**
    *   Se creó el archivo `apps/sat_integration/tasks.py`.
    *   Se definió la estructura de la tarea `process_massive_download` con comentarios para la lógica pendiente.

6.  **Definir y Crear la API: [✓ Estructura Creada]**
    *   Se crearon los archivos `serializers.py`, `viewsets.py` y `urls.py`.
    *   Se definieron los Serializers y ViewSets básicos.
    *   Se registraron las rutas de la API en `ziva_suite/urls.py`.
    *   La lógica de negocio dentro de los endpoints está pendiente de implementación.

### Fase 3: Integración con el Frontend (Pendiente)

7.  **Desarrollar Componentes en React:**
    *   **Página de "Conexión con SAT"**: Un formulario seguro para que el administrador de la empresa pueda cargar y guardar sus credenciales de la FIEL.
    *   **Página de "Descarga Masiva"**: Una interfaz donde el usuario selecciona un rango de fechas y lanza el proceso de descarga. Deberá mostrar una lista de los trabajos de descarga y su estado actual.
    *   **Actualización de Vistas Existentes**: En las vistas donde se listen facturas o asientos, añadir un indicador del estado del CFDI en el SAT (ej: un ícono verde para "Vigente" y rojo para "Cancelado") y un botón para forzar la re-consulta del estado.

---

## 4. Pruebas (Pendiente)

*   **Pruebas Unitarias:** Se crearán pruebas para la lógica de las tareas de Celery y los endpoints de la API, usando "mocks" para simular las respuestas del SAT.
*   **Pruebas de Integración:** Se probará el flujo completo desde el frontend hasta la base de datos en un entorno de "staging".
*   **Pruebas de Seguridad:** Se auditará el almacenamiento de credenciales y el acceso a los endpoints de la API.
