#!/bin/bash

set -e

# Esperar a que la base de datos esté disponible
echo "Waiting for postgres..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
    sleep 1
done
echo "PostgreSQL started"

# Ejecutar migraciones
echo "Running migrations..."
python manage.py migrate --noinput

# Recopilar archivos estáticos
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Crear superusuario si no existe
if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser(
        username='$DJANGO_SUPERUSER_USERNAME',
        email='$DJANGO_SUPERUSER_EMAIL',
        password='$DJANGO_SUPERUSER_PASSWORD'
    )
    print('Superuser created')
else:
    print('Superuser already exists')
"
fi

# Ejecutar comando
exec "$@"