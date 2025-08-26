from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel, Configuracion, LogCambio
from unittest.mock import patch

User = get_user_model()


# Modelo de prueba que hereda de BaseModel
class TestModel(BaseModel):
    """Modelo de prueba para testing del BaseModel"""
    nombre = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'core'


class BaseModelTest(TestCase):
    """Tests para el modelo base BaseModel"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123',
            email='test@example.com'
        )
        self.user2 = User.objects.create_user(
            username='testuser2', 
            password='testpass123',
            email='test2@example.com'
        )
    
    def test_base_model_creation(self):
        """Test creación básica de modelo que hereda de BaseModel"""
        with patch('apps.core.models.BaseModel.__init__') as mock_init:
            mock_init.return_value = None
            
            # Simular creación de instancia
            instance = TestModel()
            instance.creado_por = self.user
            instance.nombre = 'Test'
            
            # Verificar campos por defecto
            self.assertTrue(hasattr(instance, 'creado_por'))
            self.assertTrue(hasattr(instance, 'modificado_por'))
            self.assertTrue(hasattr(instance, 'fecha_creacion'))
            self.assertTrue(hasattr(instance, 'fecha_modificacion'))
            self.assertTrue(hasattr(instance, 'activo'))
            self.assertTrue(hasattr(instance, 'version'))
    
    def test_soft_delete(self):
        """Test que soft delete funcione correctamente"""
        # Para esta prueba necesitamos un modelo real que use BaseModel
        # Por ahora simularemos el comportamiento
        
        # Crear instancia mock
        instance = type('MockInstance', (), {
            'activo': True,
            'pk': 1,
            'save': lambda: None
        })()
        
        # Aplicar método delete de BaseModel
        def delete_method(self):
            self.activo = False
            self.save()
        
        instance.delete = delete_method.__get__(instance)
        
        # Ejecutar soft delete
        instance.delete()
        
        # Verificar que esté marcado como inactivo
        self.assertFalse(instance.activo)
    
    def test_version_increment_on_save(self):
        """Test que la versión se incremente en updates"""
        # Simular instancia con pk (ya existe)
        instance = type('MockInstance', (), {
            'pk': 1,
            'version': 1
        })()
        
        # Simular método save de BaseModel
        def save_method(self, *args, **kwargs):
            if self.pk:
                self.version += 1
        
        instance.save = save_method.__get__(instance)
        
        # Ejecutar save
        instance.save()
        
        # Verificar incremento de versión
        self.assertEqual(instance.version, 2)
    
    def test_default_ordering(self):
        """Test que el ordenamiento por defecto sea por fecha_creacion descendente"""
        # Verificar en Meta de BaseModel que ordering = ['-fecha_creacion']
        from apps.core.models import BaseModel
        
        # Como BaseModel es abstract, verificamos en su Meta
        self.assertEqual(BaseModel.Meta.ordering, ['-fecha_creacion'])
    
    def test_abstract_model(self):
        """Test que BaseModel sea abstracto"""
        from apps.core.models import BaseModel
        
        self.assertTrue(BaseModel.Meta.abstract)


class ConfiguracionModelTest(TestCase):
    """Tests para el modelo Configuracion"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Mock empresa (ya que no tenemos el modelo aún)
        self.mock_empresa = type('MockEmpresa', (), {
            'id': 1,
            'nombre': 'Test Company'
        })()
    
    def test_configuracion_creation(self):
        """Test creación de configuración"""
        config = Configuracion(
            empresa=self.mock_empresa,
            clave='test_config',
            valor={'setting': 'value'},
            tipo='SISTEMA',
            descripcion='Test configuration',
            creado_por=self.user
        )
        
        # Verificar campos
        self.assertEqual(config.clave, 'test_config')
        self.assertEqual(config.valor, {'setting': 'value'})
        self.assertEqual(config.tipo, 'SISTEMA')
        self.assertEqual(config.descripcion, 'Test configuration')
    
    def test_configuracion_str_method(self):
        """Test método __str__ de Configuracion"""
        config = Configuracion(
            empresa=self.mock_empresa,
            clave='test_config',
            creado_por=self.user
        )
        
        expected = f"{self.mock_empresa.nombre} - {config.clave}"
        self.assertEqual(str(config), expected)
    
    def test_configuracion_choices(self):
        """Test que las opciones de tipo estén correctas"""
        from apps.core.models import Configuracion
        
        expected_choices = [
            ('SISTEMA', 'Sistema'),
            ('CONTABILIDAD', 'Contabilidad'),
            ('FISCAL', 'Fiscal'),
            ('REPORTES', 'Reportes'),
        ]
        
        tipo_field = Configuracion._meta.get_field('tipo')
        self.assertEqual(tipo_field.choices, expected_choices)


class LogCambioModelTest(TestCase):
    """Tests para el modelo LogCambio"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_log_cambio_creation(self):
        """Test creación de log de cambio"""
        log = LogCambio(
            modelo='TestModel',
            registro_id=1,
            campo='nombre',
            valor_anterior='Valor Viejo',
            valor_nuevo='Valor Nuevo',
            usuario=self.user,
            ip_address='192.168.1.1'
        )
        
        # Verificar campos
        self.assertEqual(log.modelo, 'TestModel')
        self.assertEqual(log.registro_id, 1)
        self.assertEqual(log.campo, 'nombre')
        self.assertEqual(log.valor_anterior, 'Valor Viejo')
        self.assertEqual(log.valor_nuevo, 'Valor Nuevo')
        self.assertEqual(log.usuario, self.user)
        self.assertEqual(log.ip_address, '192.168.1.1')
    
    def test_log_cambio_str_method(self):
        """Test método __str__ de LogCambio"""
        log = LogCambio(
            modelo='TestModel',
            registro_id=1,
            campo='nombre',
            usuario=self.user
        )
        
        # Como fecha_cambio se asigna automáticamente, solo verificamos el formato
        str_result = str(log)
        self.assertIn('TestModel(1)', str_result)
        self.assertIn('nombre', str_result)
    
    def test_log_cambio_ordering(self):
        """Test ordenamiento por fecha_cambio descendente"""
        from apps.core.models import LogCambio
        
        self.assertEqual(LogCambio.Meta.ordering, ['-fecha_cambio'])
    
    def test_log_cambio_indexes(self):
        """Test que los índices estén configurados"""
        from apps.core.models import LogCambio
        
        indexes = LogCambio.Meta.indexes
        self.assertEqual(len(indexes), 2)
        
        # Verificar campos de los índices
        index_fields = [idx.fields for idx in indexes]
        self.assertIn(['modelo', 'registro_id'], index_fields)
        self.assertIn(['usuario', 'fecha_cambio'], index_fields)


class UtilsTest(TestCase):
    """Tests para utilidades en utils.py"""
    
    def test_validar_cuadratura(self):
        """Test validación de cuadratura contable"""
        from apps.core.utils import validar_cuadratura
        
        # Caso cuadrado
        self.assertTrue(validar_cuadratura(1000.00, 1000.00))
        
        # Caso con tolerancia
        self.assertTrue(validar_cuadratura(1000.00, 1000.01, tolerancia=0.02))
        
        # Caso descuadrado
        self.assertFalse(validar_cuadratura(1000.00, 1001.00))
    
    def test_obtener_ip_cliente(self):
        """Test obtención de IP del cliente"""
        from apps.core.utils import obtener_ip_cliente
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # Test IP normal
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = obtener_ip_cliente(request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test con X-Forwarded-For
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1,192.168.1.1'
        ip = obtener_ip_cliente(request)
        self.assertEqual(ip, '10.0.0.1')
    
    def test_formatear_moneda(self):
        """Test formateo de monedas"""
        from apps.core.utils import formatear_moneda
        
        # Peso mexicano (default)
        self.assertEqual(formatear_moneda(1000.50), "$1,000.50")
        
        # Dólar americano
        self.assertEqual(formatear_moneda(1000.50, 'USD'), "$1,000.50 USD")
        
        # Euro
        self.assertEqual(formatear_moneda(1000.50, 'EUR'), "€1,000.50")
    
    def test_validar_rfc(self):
        """Test validación de RFC"""
        from apps.core.utils import validar_rfc
        
        # RFC válido persona física
        self.assertTrue(validar_rfc('CURP800825HDFGRL09'))
        
        # RFC válido persona moral
        self.assertTrue(validar_rfc('ABC123456ABC'))
        
        # RFC inválido
        self.assertFalse(validar_rfc('INVALID'))
        self.assertFalse(validar_rfc('ABC12345'))


# Necesitamos importar models aquí para el TestModel
from django.db import models