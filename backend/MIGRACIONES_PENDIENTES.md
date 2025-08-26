# Migraciones Pendientes - Centros de Costo y Proyectos

## ⚠️ IMPORTANTE: Aplicar Migraciones

Hay migraciones pendientes que deben aplicarse para que las nuevas funcionalidades funcionen correctamente.

## Pasos para aplicar las migraciones:

### 1. Verificar conexión a la base de datos
Asegúrate de que las credenciales de la base de datos en tu archivo `.env` o `settings.py` sean correctas:
- Host: localhost
- Puerto: 5432
- Usuario: ziva_user
- Base de datos: (tu nombre de BD)

### 2. Aplicar las migraciones
```bash
python manage.py migrate centros_costo
```

### 3. Crear tipos por defecto (opcional)
Después de aplicar las migraciones, puedes crear tipos por defecto ejecutando el siguiente script en el shell de Django:

```python
python manage.py shell
```

```python
from apps.centros_costo.models import TipoCentroCosto
from apps.empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

# Para cada empresa
for empresa in Empresa.objects.all():
    tipos_default = [
        ('DEPTO', 'Departamento', 'blue', 0),
        ('SUCUR', 'Sucursal', 'green', 1),
        ('ACTIV', 'Actividad', 'yellow', 2),
        ('PROD', 'Producto', 'red', 3),
        ('SERV', 'Servicio', 'purple', 4),
        ('OTRO', 'Otro', 'gray', 5)
    ]
    
    for codigo, nombre, color, orden in tipos_default:
        TipoCentroCosto.objects.get_or_create(
            empresa=empresa,
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'color_interfaz': color,
                'orden': orden,
                'creado_por': admin,
                'descripcion': f'Tipo {nombre} - creado por defecto'
            }
        )
```

## Migraciones creadas:

### `0002_tipocentrocosto_centrocosto_tipo_nuevo.py`
- Crea el modelo `TipoCentroCosto`
- Agrega el campo temporal `tipo_nuevo` a `CentroCosto`

## Estado actual:

El código está usando `.defer('tipo_nuevo')` temporalmente para evitar errores mientras no se apliquen las migraciones.

Una vez aplicadas las migraciones:
1. Los tipos de centro de costo serán configurables
2. Los proyectos tendrán CRUD completo funcional
3. Se podrá navegar entre Centros → Tipos → Proyectos

## URLs disponibles después de migrar:

- `/centros_costo/tipos/` - Lista de tipos
- `/centros_costo/tipos/crear/` - Crear tipo
- `/centros_costo/tipos/{id}/editar/` - Editar tipo
- `/centros_costo/proyectos/crear/` - Crear proyecto
- `/centros_costo/proyectos/{id}/editar/` - Editar proyecto

## Nota sobre el campo `tipo`:

Actualmente hay dos campos en el modelo `CentroCosto`:
- `tipo` (CharField) - Campo original con choices fijas
- `tipo_nuevo` (ForeignKey) - Nuevo campo que apunta a TipoCentroCosto

En una futura migración se deberá:
1. Migrar los datos de `tipo` a `tipo_nuevo`
2. Eliminar el campo `tipo` antiguo
3. Renombrar `tipo_nuevo` a `tipo`