# Dockerfile para backend Django
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements/base.txt requirements/
COPY requirements/production.txt requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs media staticfiles

# Crear usuario no-root
RUN addgroup --system django \
    && adduser --system --ingroup django django

# Cambiar permisos
RUN chown -R django:django /app
USER django

# Exponer puerto
EXPOSE 8000

# Script de inicio
COPY docker/entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER django

ENTRYPOINT ["/entrypoint.sh"]