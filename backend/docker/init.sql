-- Script de inicialización de la base de datos
-- Se ejecuta automáticamente cuando se crea el contenedor de PostgreSQL

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Crear esquemas si son necesarios
-- CREATE SCHEMA IF NOT EXISTS contabilidad;
-- CREATE SCHEMA IF NOT EXISTS reportes;

-- Configurar timezone
SET timezone = 'America/Mexico_City';

-- Configuraciones de rendimiento
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';

-- Reload configuration
SELECT pg_reload_conf();