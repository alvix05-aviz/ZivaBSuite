@echo off
REM Script de configuración inicial para ZivaBSuite en Windows
echo 🚀 Configurando ZivaBSuite - Etapa 1

REM Verificar que Docker esté corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Docker no está corriendo. Por favor, inicia Docker y vuelve a ejecutar.
    pause
    exit /b 1
)

REM Crear archivo .env si no existe
if not exist .env (
    echo 📝 Creando archivo .env desde .env.example...
    copy .env.example .env
) else (
    echo ✅ Archivo .env ya existe
)

REM Construir y levantar servicios
echo 🐳 Construyendo contenedores Docker...
docker-compose -f docker-compose.etapa1.yml build

echo 🚀 Levantando servicios de base de datos...
docker-compose -f docker-compose.etapa1.yml up -d db redis

echo ⏳ Esperando a que la base de datos esté lista...
timeout /t 10 /nobreak >nul

REM Ejecutar migraciones
echo 🗄️ Ejecutando migraciones...
docker-compose -f docker-compose.etapa1.yml run --rm backend python manage.py makemigrations core
docker-compose -f docker-compose.etapa1.yml run --rm backend python manage.py makemigrations empresas
docker-compose -f docker-compose.etapa1.yml run --rm backend python manage.py migrate

REM Crear superusuario
echo 👤 Creando superusuario...
docker-compose -f docker-compose.etapa1.yml run --rm backend python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@ziva.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Usuario admin ya existe')"

REM Levantar todos los servicios
echo 🌟 Levantando todos los servicios...
docker-compose -f docker-compose.etapa1.yml up -d

echo.
echo 🎉 ¡Configuración completada!
echo.
echo 📊 URLs disponibles:
echo    - Backend API: http://localhost:8000/api/
echo    - Admin Django: http://localhost:8000/admin/ (admin/admin123)
echo    - Base de datos: localhost:5432 (ziva_user/ziva_password123)
echo    - Redis: localhost:6379
echo.
echo 📝 Nota: Solo backend implementado (Etapa 1)
echo    Frontend se implementará en etapas posteriores
echo.
echo 🔧 Comandos útiles:
echo    - Ver logs: docker-compose -f docker-compose.etapa1.yml logs -f
echo    - Parar servicios: docker-compose -f docker-compose.etapa1.yml down
echo    - Shell Django: docker-compose -f docker-compose.etapa1.yml exec backend python manage.py shell
echo    - Ejecutar tests: docker-compose -f docker-compose.etapa1.yml exec backend python manage.py test
echo.
echo 📚 Documentación: README.md
echo.
pause