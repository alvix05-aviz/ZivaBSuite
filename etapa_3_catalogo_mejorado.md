# Etapa 3: Catálogo de Cuentas Mejorado

## 📋 Objetivo
Implementar un catálogo de cuentas completo con centros de costo, tags de proyectos y códigos agrupadores SAT, elementos faltantes en ejemplo_basico.txt

## 🎯 Alcance
- Catálogo de cuentas con estructura jerárquica
- Centros de costo para análisis dimensional
- Sistema de tags/etiquetas para proyectos
- Integración con códigos agrupadores del SAT
- Importación masiva desde Excel/CSV

## 🔧 Tareas de Implementación

### 3.1 Modelo de Cuenta Contable Mejorado
**Archivo:** `backend/apps/catalogo_cuentas/models.py`

```python
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.empresas.models import Empresa

class CuentaContable(BaseModel):
    """
    Catálogo de cuentas con estructura jerárquica
    MEJORA: Añade nivel, validaciones y códigos SAT
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cuentas_contables'
    )
    
    # Estructura de cuenta
    codigo = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex='^[0-9]+([-\.][0-9]+)*$',
                message='Código debe ser numérico con separadores - o .'
            )
        ],
        verbose_name='Código de Cuenta'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Cuenta'
    )
    cuenta_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcuentas',
        verbose_name='Cuenta Padre'
    )
    
    # Clasificación
    nivel = models.IntegerField(
        verbose_name='Nivel de la Cuenta',
        help_text='1=Mayor, 2=Subcuenta, 3=Sub-subcuenta, etc.'
    )
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVO', 'Activo'),
            ('PASIVO', 'Pasivo'),
            ('CAPITAL', 'Capital'),
            ('INGRESO', 'Ingreso'),
            ('COSTO', 'Costo'),
            ('GASTO', 'Gasto'),
            ('RESULTADO', 'Cuentas de Resultado'),
            ('ORDEN', 'Cuentas de Orden'),
        ],
        verbose_name='Tipo de Cuenta'
    )
    naturaleza = models.CharField(
        max_length=10,
        choices=[
            ('DEUDORA', 'Deudora'),
            ('ACREEDORA', 'Acreedora'),
        ],
        verbose_name='Naturaleza'
    )
    
    # Códigos SAT (NUEVO - No existía en ejemplo_basico)
    codigo_agrupador_sat = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Código Agrupador SAT',
        help_text='Código del catálogo de cuentas del SAT'
    )
    nivel_agrupador_sat = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ('100', 'Activo'),
            ('100.01', 'Activo a corto plazo'),
            ('100.02', 'Activo a largo plazo'),
            ('200', 'Pasivo'),
            ('200.01', 'Pasivo a corto plazo'),
            ('200.02', 'Pasivo a largo plazo'),
            ('300', 'Capital'),
            ('400', 'Ingresos'),
            ('500', 'Costos'),
            ('600', 'Gastos'),
            ('700', 'Resultado integral de financiamiento'),
            ('800', 'Cuentas de orden'),
        ],
        verbose_name='Nivel Agrupador SAT'
    )
    
    # Control y configuración
    es_detalle = models.BooleanField(
        default=False,
        verbose_name='Es cuenta de detalle',
        help_text='Solo las cuentas de detalle pueden recibir movimientos'
    )
    acepta_movimientos = models.BooleanField(
        default=True,
        verbose_name='Acepta movimientos'
    )
    requiere_centro_costo = models.BooleanField(
        default=False,
        verbose_name='Requiere Centro de Costo'
    )
    requiere_proyecto = models.BooleanField(
        default=False,
        verbose_name='Requiere Proyecto/Tag'
    )
    
    # Moneda
    moneda = models.CharField(
        max_length=3,
        default='MXN',
        choices=[
            ('MXN', 'Peso Mexicano'),
            ('USD', 'Dólar Americano'),
            ('EUR', 'Euro'),
        ],
        verbose_name='Moneda'
    )
    
    # Saldos
    saldo_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Inicial del Ejercicio'
    )
    saldo_actual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Actual',
        editable=False
    )
    
    # Presupuesto
    presupuesto_anual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Presupuesto Anual'
    )
    
    class Meta:
        unique_together = ['empresa', 'codigo']
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Cuentas Contables'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['empresa', 'codigo']),
            models.Index(fields=['empresa', 'tipo']),
            models.Index(fields=['codigo_agrupador_sat']),
        ]
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        """Validaciones del modelo"""
        # Validar que cuenta padre sea del mismo tipo
        if self.cuenta_padre and self.cuenta_padre.tipo != self.tipo:
            raise ValidationError(
                'La cuenta padre debe ser del mismo tipo'
            )
        
        # Calcular nivel automáticamente
        if self.cuenta_padre:
            self.nivel = self.cuenta_padre.nivel + 1
        else:
            # Contar separadores en el código para determinar nivel
            separadores = self.codigo.count('-') + self.codigo.count('.')
            self.nivel = separadores + 1
        
        # Solo cuentas de último nivel pueden ser de detalle
        if not self.es_detalle and self.acepta_movimientos:
            subcuentas = CuentaContable.objects.filter(
                cuenta_padre=self
            ).exists()
            if subcuentas:
                raise ValidationError(
                    'Una cuenta con subcuentas no puede aceptar movimientos'
                )
    
    def get_ruta_completa(self):
        """Retorna la ruta completa de la cuenta"""
        if self.cuenta_padre:
            return f"{self.cuenta_padre.get_ruta_completa()} / {self.nombre}"
        return self.nombre
    
    def calcular_saldo(self, fecha_inicio=None, fecha_fin=None):
        """Calcula el saldo de la cuenta en un período"""
        from apps.transacciones.models import MovimientoContable
        from django.db.models import Sum
        
        movimientos = MovimientoContable.objects.filter(
            cuenta=self,
            transaccion__estado='CONTABILIZADA'
        )
        
        if fecha_inicio:
            movimientos = movimientos.filter(
                transaccion__fecha__gte=fecha_inicio
            )
        if fecha_fin:
            movimientos = movimientos.filter(
                transaccion__fecha__lte=fecha_fin
            )
        
        totales = movimientos.aggregate(
            total_debe=Sum('debe'),
            total_haber=Sum('haber')
        )
        
        debe = totales['total_debe'] or 0
        haber = totales['total_haber'] or 0
        
        if self.naturaleza == 'DEUDORA':
            return self.saldo_inicial + debe - haber
        else:
            return self.saldo_inicial + haber - debe
```

### 3.2 Centro de Costo (NUEVO - No existía en ejemplo_basico)
**Archivo:** `backend/apps/catalogo_cuentas/models.py` (continuación)

```python
class CentroCosto(BaseModel):
    """
    Centros de costo para análisis dimensional
    NUEVO: Permite análisis por departamento, proyecto, sucursal, etc.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='centros_costo'
    )
    
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre del Centro de Costo'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # Jerarquía
    centro_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcentros',
        verbose_name='Centro Padre'
    )
    nivel = models.IntegerField(
        default=1,
        verbose_name='Nivel'
    )
    
    # Clasificación
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('DEPARTAMENTO', 'Departamento'),
            ('PROYECTO', 'Proyecto'),
            ('SUCURSAL', 'Sucursal'),
            ('AREA', 'Área'),
            ('LINEA_NEGOCIO', 'Línea de Negocio'),
            ('CLIENTE', 'Cliente'),
            ('PRODUCTO', 'Producto'),
            ('OTRO', 'Otro'),
        ],
        default='DEPARTAMENTO',
        verbose_name='Tipo de Centro'
    )
    
    # Responsable
    responsable = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='centros_costo_responsable',
        verbose_name='Responsable'
    )
    
    # Presupuesto
    presupuesto_anual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Presupuesto Anual'
    )
    presupuesto_mensual = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Presupuesto Mensual',
        help_text='{"1": 10000, "2": 12000, ...}'
    )
    
    # Control
    permite_gastos = models.BooleanField(
        default=True,
        verbose_name='Permite Gastos'
    )
    permite_ingresos = models.BooleanField(
        default=False,
        verbose_name='Permite Ingresos'
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    class Meta:
        unique_together = ['empresa', 'codigo']
        verbose_name = 'Centro de Costo'
        verbose_name_plural = 'Centros de Costo'
        ordering = ['codigo']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        """Validaciones"""
        if self.centro_padre:
            self.nivel = self.centro_padre.nivel + 1
    
    def get_presupuesto_mes(self, mes):
        """Obtiene presupuesto de un mes específico"""
        if isinstance(self.presupuesto_mensual, dict):
            return self.presupuesto_mensual.get(str(mes), 0)
        return 0
    
    def calcular_ejecutado(self, mes=None, año=None):
        """Calcula lo ejecutado vs presupuesto"""
        from apps.transacciones.models import MovimientoContable
        from django.db.models import Sum
        from datetime import datetime
        
        movimientos = MovimientoContable.objects.filter(
            centro_costo=self,
            transaccion__estado='CONTABILIZADA'
        )
        
        if año:
            movimientos = movimientos.filter(transaccion__fecha__year=año)
        if mes:
            movimientos = movimientos.filter(transaccion__fecha__month=mes)
        
        total = movimientos.aggregate(
            gastos=Sum('debe'),
            ingresos=Sum('haber')
        )
        
        return {
            'gastos': total['gastos'] or 0,
            'ingresos': total['ingresos'] or 0,
            'neto': (total['ingresos'] or 0) - (total['gastos'] or 0)
        }
```

### 3.3 Tags/Etiquetas de Proyectos (NUEVO)
**Archivo:** `backend/apps/catalogo_cuentas/models.py` (continuación)

```python
class TagProyecto(BaseModel):
    """
    Sistema de etiquetas para clasificación flexible
    NUEVO: Permite múltiples dimensiones de análisis
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='tags_proyecto'
    )
    
    nombre = models.CharField(
        max_length=50,
        verbose_name='Nombre del Tag'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    color = models.CharField(
        max_length=7,
        default='#2196F3',
        validators=[
            RegexValidator(
                regex='^#[0-9A-Fa-f]{6}$',
                message='Color debe ser formato HEX'
            )
        ],
        verbose_name='Color (HEX)'
    )
    icono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Icono (Material Icons)'
    )
    
    # Categorización
    categoria = models.CharField(
        max_length=30,
        choices=[
            ('PROYECTO', 'Proyecto'),
            ('CLIENTE', 'Cliente'),
            ('PROVEEDOR', 'Proveedor'),
            ('PRODUCTO', 'Producto'),
            ('SERVICIO', 'Servicio'),
            ('EVENTO', 'Evento'),
            ('CAMPAÑA', 'Campaña'),
            ('OTRO', 'Otro'),
        ],
        default='PROYECTO',
        verbose_name='Categoría'
    )
    
    # Jerarquía
    tag_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtags',
        verbose_name='Tag Padre'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata adicional'
    )
    
    # Presupuesto asociado
    presupuesto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Presupuesto'
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    # Analytics
    veces_usado = models.IntegerField(
        default=0,
        verbose_name='Veces Usado',
        editable=False
    )
    
    class Meta:
        unique_together = ['empresa', 'nombre', 'categoria']
        verbose_name = 'Tag de Proyecto'
        verbose_name_plural = 'Tags de Proyectos'
        ordering = ['categoria', 'nombre']
        
    def __str__(self):
        return f"[{self.categoria}] {self.nombre}"
    
    def esta_vigente(self):
        """Verifica si el tag está vigente"""
        from datetime import date
        hoy = date.today()
        
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
            
        return True
```

### 3.4 Catálogo de Códigos SAT (NUEVO)
**Archivo:** `backend/apps/catalogo_cuentas/models.py` (continuación)

```python
class CodigoAgrupadorSAT(models.Model):
    """
    Catálogo de códigos agrupadores del SAT
    NUEVO: Para cumplimiento fiscal y generación de reportes SAT
    """
    codigo = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name='Código'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Descripción'
    )
    nivel = models.IntegerField(
        verbose_name='Nivel'
    )
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVO', 'Activo'),
            ('PASIVO', 'Pasivo'),
            ('CAPITAL', 'Capital'),
            ('INGRESO', 'Ingreso'),
            ('COSTO', 'Costo'),
            ('GASTO', 'Gasto'),
            ('RESULTADO', 'Resultado'),
            ('ORDEN', 'Orden'),
        ],
        verbose_name='Tipo'
    )
    naturaleza = models.CharField(
        max_length=10,
        choices=[
            ('D', 'Deudora'),
            ('A', 'Acreedora'),
        ],
        verbose_name='Naturaleza'
    )
    
    class Meta:
        verbose_name = 'Código Agrupador SAT'
        verbose_name_plural = 'Códigos Agrupadores SAT'
        ordering = ['codigo']
        
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
```

### 3.5 Servicios de Importación/Exportación
**Archivo:** `backend/apps/catalogo_cuentas/services.py`

```python
import pandas as pd
from django.db import transaction
from .models import CuentaContable, CentroCosto, CodigoAgrupadorSAT

class ImportadorCatalogo:
    """
    Servicio para importar catálogo de cuentas desde Excel/CSV
    MEJORA: Importación masiva con validación
    """
    
    def __init__(self, empresa):
        self.empresa = empresa
        self.errores = []
        self.cuentas_creadas = 0
        
    def importar_desde_excel(self, archivo_path):
        """Importa catálogo desde archivo Excel"""
        try:
            df = pd.read_excel(archivo_path)
            return self._procesar_dataframe(df)
        except Exception as e:
            self.errores.append(f"Error al leer archivo: {str(e)}")
            return False
    
    def importar_desde_csv(self, archivo_path):
        """Importa catálogo desde archivo CSV"""
        try:
            df = pd.read_csv(archivo_path)
            return self._procesar_dataframe(df)
        except Exception as e:
            self.errores.append(f"Error al leer archivo: {str(e)}")
            return False
    
    @transaction.atomic
    def _procesar_dataframe(self, df):
        """Procesa DataFrame y crea cuentas"""
        columnas_requeridas = [
            'codigo', 'nombre', 'tipo', 'naturaleza'
        ]
        
        # Validar columnas
        for col in columnas_requeridas:
            if col not in df.columns:
                self.errores.append(f"Columna '{col}' no encontrada")
                return False
        
        # Procesar filas
        for index, row in df.iterrows():
            try:
                # Buscar cuenta padre si existe
                cuenta_padre = None
                if 'codigo_padre' in row and pd.notna(row['codigo_padre']):
                    cuenta_padre = CuentaContable.objects.filter(
                        empresa=self.empresa,
                        codigo=row['codigo_padre']
                    ).first()
                
                # Buscar código SAT si existe
                codigo_sat = ''
                if 'codigo_sat' in row and pd.notna(row['codigo_sat']):
                    codigo_sat = str(row['codigo_sat'])
                
                # Crear o actualizar cuenta
                cuenta, created = CuentaContable.objects.update_or_create(
                    empresa=self.empresa,
                    codigo=str(row['codigo']),
                    defaults={
                        'nombre': row['nombre'],
                        'tipo': row['tipo'].upper(),
                        'naturaleza': row['naturaleza'].upper(),
                        'cuenta_padre': cuenta_padre,
                        'codigo_agrupador_sat': codigo_sat,
                        'es_detalle': row.get('es_detalle', True),
                        'acepta_movimientos': row.get('acepta_movimientos', True),
                        'creado_por': self.empresa.creado_por,
                    }
                )
                
                if created:
                    self.cuentas_creadas += 1
                    
            except Exception as e:
                self.errores.append(
                    f"Error en fila {index + 2}: {str(e)}"
                )
                
        return len(self.errores) == 0
    
    def generar_plantilla(self):
        """Genera plantilla Excel para importación"""
        data = {
            'codigo': ['1000', '1100', '1110'],
            'nombre': ['ACTIVO', 'ACTIVO CIRCULANTE', 'CAJA Y BANCOS'],
            'codigo_padre': ['', '1000', '1100'],
            'tipo': ['ACTIVO', 'ACTIVO', 'ACTIVO'],
            'naturaleza': ['DEUDORA', 'DEUDORA', 'DEUDORA'],
            'codigo_sat': ['100', '100.01', '101.01'],
            'es_detalle': [False, False, True],
            'acepta_movimientos': [False, False, True],
        }
        
        df = pd.DataFrame(data)
        return df

class MapeoSATService:
    """
    Servicio para mapear cuentas con códigos SAT
    SUGERENCIA: Mapeo automático inteligente
    """
    
    @staticmethod
    def sugerir_codigo_sat(cuenta):
        """Sugiere código SAT basado en nombre y tipo de cuenta"""
        mapeos_comunes = {
            'CAJA': '101.01',
            'BANCOS': '102.01',
            'CLIENTES': '105.01',
            'INVENTARIOS': '115.01',
            'PROVEEDORES': '201.01',
            'IMPUESTOS POR PAGAR': '216.01',
            'CAPITAL SOCIAL': '301.01',
            'VENTAS': '401.01',
            'COSTO DE VENTAS': '501.01',
            'GASTOS DE VENTA': '601.01',
            'GASTOS DE ADMINISTRACION': '602.01',
        }
        
        nombre_upper = cuenta.nombre.upper()
        
        for keyword, codigo_sat in mapeos_comunes.items():
            if keyword in nombre_upper:
                return codigo_sat
                
        # Mapeo por tipo si no encuentra por nombre
        mapeos_tipo = {
            'ACTIVO': '100',
            'PASIVO': '200',
            'CAPITAL': '300',
            'INGRESO': '400',
            'COSTO': '500',
            'GASTO': '600',
        }
        
        return mapeos_tipo.get(cuenta.tipo, '')
    
    @staticmethod
    def validar_mapeo_sat(empresa):
        """Valida que todas las cuentas tengan código SAT"""
        cuentas_sin_sat = CuentaContable.objects.filter(
            empresa=empresa,
            codigo_agrupador_sat='',
            es_detalle=True
        )
        
        return {
            'total_cuentas': CuentaContable.objects.filter(
                empresa=empresa
            ).count(),
            'sin_codigo_sat': cuentas_sin_sat.count(),
            'cuentas_faltantes': list(
                cuentas_sin_sat.values('codigo', 'nombre')
            )
        }
```

### 3.6 API Views para Catálogo
**Archivo:** `backend/apps/catalogo_cuentas/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
import pandas as pd
from .models import CuentaContable, CentroCosto, TagProyecto
from .serializers import (
    CuentaContableSerializer, 
    CentroCostoSerializer,
    TagProyectoSerializer
)
from .services import ImportadorCatalogo, MapeoSATService

class CuentaContableViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de cuentas contables
    MEJORA: Incluye importación/exportación y árbol jerárquico
    """
    serializer_class = CuentaContableSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CuentaContable.objects.filter(
            empresa=self.request.empresa,
            activo=True
        ).select_related('cuenta_padre')
    
    @action(detail=False, methods=['get'])
    def arbol(self, request):
        """Retorna estructura de árbol del catálogo"""
        def construir_arbol(cuenta_padre=None):
            cuentas = CuentaContable.objects.filter(
                empresa=request.empresa,
                cuenta_padre=cuenta_padre,
                activo=True
            ).order_by('codigo')
            
            resultado = []
            for cuenta in cuentas:
                nodo = {
                    'id': cuenta.id,
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'tipo': cuenta.tipo,
                    'naturaleza': cuenta.naturaleza,
                    'es_detalle': cuenta.es_detalle,
                    'saldo_actual': float(cuenta.saldo_actual),
                    'hijos': construir_arbol(cuenta)
                }
                resultado.append(nodo)
                
            return resultado
        
        arbol = construir_arbol()
        return Response(arbol)
    
    @action(detail=False, methods=['post'])
    def importar(self, request):
        """Importa catálogo desde archivo"""
        archivo = request.FILES.get('archivo')
        tipo = request.data.get('tipo', 'excel')
        
        if not archivo:
            return Response(
                {'error': 'No se proporcionó archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        importador = ImportadorCatalogo(request.empresa)
        
        # Guardar archivo temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in archivo.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Procesar importación
        if tipo == 'excel':
            exito = importador.importar_desde_excel(tmp_path)
        else:
            exito = importador.importar_desde_csv(tmp_path)
        
        if exito:
            return Response({
                'mensaje': 'Importación exitosa',
                'cuentas_creadas': importador.cuentas_creadas
            })
        else:
            return Response(
                {'errores': importador.errores},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def exportar(self, request):
        """Exporta catálogo a Excel"""
        cuentas = self.get_queryset()
        
        data = []
        for cuenta in cuentas:
            data.append({
                'Código': cuenta.codigo,
                'Nombre': cuenta.nombre,
                'Tipo': cuenta.tipo,
                'Naturaleza': cuenta.naturaleza,
                'Código SAT': cuenta.codigo_agrupador_sat,
                'Saldo Inicial': cuenta.saldo_inicial,
                'Saldo Actual': cuenta.saldo_actual,
                'Es Detalle': 'Sí' if cuenta.es_detalle else 'No',
                'Acepta Movimientos': 'Sí' if cuenta.acepta_movimientos else 'No',
            })
        
        df = pd.DataFrame(data)
        
        # Crear respuesta Excel
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=catalogo_cuentas.xlsx'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Catálogo', index=False)
            
        return response
    
    @action(detail=False, methods=['get'])
    def validar_sat(self, request):
        """Valida mapeo con códigos SAT"""
        resultado = MapeoSATService.validar_mapeo_sat(request.empresa)
        return Response(resultado)
    
    @action(detail=True, methods=['post'])
    def sugerir_codigo_sat(self, request, pk=None):
        """Sugiere código SAT para una cuenta"""
        cuenta = self.get_object()
        codigo_sugerido = MapeoSATService.sugerir_codigo_sat(cuenta)
        
        return Response({
            'cuenta': cuenta.codigo,
            'codigo_sat_sugerido': codigo_sugerido
        })
```

## ✅ Criterios de Aceptación

### Validación de Estructura
```python
# Verificar modelos
python manage.py makemigrations catalogo_cuentas
python manage.py migrate

# Cargar códigos SAT iniciales
python manage.py loaddata codigos_sat.json
```

### Tests de Catálogo
```python
# backend/apps/catalogo_cuentas/tests/test_catalogo.py
from django.test import TestCase
from apps.catalogo_cuentas.models import CuentaContable, CentroCosto

class CatalogoTest(TestCase):
    def test_jerarquia_cuentas(self):
        """Verifica estructura jerárquica"""
        cuenta_mayor = CuentaContable.objects.create(
            codigo='1000',
            nombre='ACTIVO',
            tipo='ACTIVO',
            nivel=1
        )
        
        cuenta_sub = CuentaContable.objects.create(
            codigo='1100',
            nombre='ACTIVO CIRCULANTE',
            cuenta_padre=cuenta_mayor,
            tipo='ACTIVO'
        )
        
        self.assertEqual(cuenta_sub.nivel, 2)
        self.assertEqual(
            cuenta_sub.get_ruta_completa(),
            'ACTIVO / ACTIVO CIRCULANTE'
        )
    
    def test_centro_costo_presupuesto(self):
        """Verifica cálculo de presupuesto"""
        centro = CentroCosto.objects.create(
            codigo='CC001',
            nombre='Ventas',
            presupuesto_anual=120000,
            presupuesto_mensual={
                '1': 10000,
                '2': 10000,
                # ...
            }
        )
        
        self.assertEqual(
            centro.get_presupuesto_mes(1),
            10000
        )
```

### Prueba de Importación
```bash
# Generar plantilla
curl -X GET http://localhost:8000/api/catalogo/plantilla/

# Importar archivo
curl -X POST http://localhost:8000/api/catalogo/importar/ \
  -H "Authorization: Bearer TOKEN" \
  -F "archivo=@catalogo.xlsx" \
  -F "tipo=excel"
```

## 📊 Métricas de Éxito

- [ ] Catálogo con estructura jerárquica
- [ ] Centros de costo funcionando
- [ ] Tags de proyectos implementados
- [ ] Códigos SAT mapeados
- [ ] Importación/exportación operativa
- [ ] Tests con cobertura > 85%

## 🔄 Siguiente Etapa
[Etapa 4: Sistema de Transacciones →](etapa_4_transacciones.md)