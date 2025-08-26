#!/bin/bash

# Script de configuración inicial para ZivaBSuite
echo "🚀 Configurando ZivaBSuite - Etapa 1"

# Verificar que Docker esté corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo. Por favor, inicia Docker y vuelve a ejecutar."
    exit 1
fi

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env desde .env.example..."
    cp .env.example .env
else
    echo "✅ Archivo .env ya existe"
fi

# Construir y levantar servicios
echo "🐳 Construyendo contenedores Docker..."
docker-compose build

echo "🚀 Levantando servicios..."
docker-compose up -d db redis

echo "⏳ Esperando a que la base de datos esté lista..."
sleep 10

# Ejecutar migraciones
echo "🗄️ Ejecutando migraciones..."
docker-compose run --rm backend python manage.py makemigrations core
docker-compose run --rm backend python manage.py makemigrations empresas
docker-compose run --rm backend python manage.py migrate

# Crear superusuario
echo "👤 Creando superusuario..."
docker-compose run --rm backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@ziva.com', 'admin123')
    print('✅ Superusuario creado: admin/admin123')
else:
    print('✅ Superusuario ya existe')
"

# Levantar todos los servicios
echo "🌟 Levantando todos los servicios..."
docker-compose up -d

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📊 URLs disponibles:"
echo "   - Backend API: http://localhost:8000/api/"
echo "   - Admin Django: http://localhost:8000/admin/ (admin/admin123)"
echo "   - Base de datos: localhost:5432 (ziva_user/ziva_password123)"
echo "   - Redis: localhost:6379"
echo ""
echo "🔧 Comandos útiles:"
echo "   - Ver logs: docker-compose logs -f"
echo "   - Parar servicios: docker-compose down"
echo "   - Shell Django: docker-compose exec backend python manage.py shell"
echo "   - Ejecutar tests: docker-compose exec backend python manage.py test"
echo ""
echo "📚 Documentación: README.md"