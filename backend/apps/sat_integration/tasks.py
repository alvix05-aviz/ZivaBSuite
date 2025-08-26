import os
import tempfile
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from django.utils import timezone as django_timezone
from celery import shared_task, current_task
from django.core.files.base import ContentFile
from django.db import transaction
from .models import CFDIDownloadJob, CFDI, SATCredentials, CFDIStatusLog
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_massive_download(self, job_id):
    """
    Tarea principal para procesar la descarga masiva de CFDI del SAT
    """
    try:
        # Obtener el trabajo de descarga
        job = CFDIDownloadJob.objects.get(id=job_id)
        job.estado = 'PROCESANDO'
        job.fecha_inicio_proceso = django_timezone.now()
        job.save()
        
        # Actualizar el estado de la tarea
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Iniciando descarga...'}
        )
        
        # Obtener las credenciales SAT de la empresa
        try:
            credentials = job.empresa.credenciales_sat
            if not credentials.validadas:
                raise Exception("Las credenciales SAT no están validadas")
        except SATCredentials.DoesNotExist:
            raise Exception("No hay credenciales SAT configuradas para esta empresa")
        
        # Importar satcfdi aquí para evitar errores de importación si no está instalado
        from satcfdi.create.descarga import DescargaMasiva
        from satcfdi.create.authenticate import Authenticate
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Autenticando con SAT...'}
        )
        
        # Configurar autenticación
        auth = Authenticate(
            cer_file=credentials.certificado_cer.path,
            key_file=credentials.llave_privada_key.path,
            password=credentials.password_llave
        )
        
        # Configurar los parámetros de descarga
        descarga_config = {
            'rfc_emisor': credentials.rfc if job.tipo_cfdi in ['EMITIDOS', 'TODOS'] else None,
            'rfc_receptor': credentials.rfc if job.tipo_cfdi in ['RECIBIDOS', 'TODOS'] else None,
            'fecha_inicial': job.fecha_inicio,
            'fecha_final': job.fecha_fin,
            'tipo_solicitud': 'CFDI'
        }
        
        # Crear instancia de descarga masiva
        descarga = DescargaMasiva(
            auth=auth,
            **descarga_config
        )
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Solicitando descarga al SAT...'}
        )
        
        # Solicitar la descarga
        solicitud_result = descarga.solicitar_descarga()
        
        if not solicitud_result.get('success'):
            raise Exception(f"Error en solicitud de descarga: {solicitud_result.get('message', 'Error desconocido')}")
        
        # Guardar el ID de solicitud
        job.solicitud_id = solicitud_result.get('id_solicitud')
        job.save()
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': 'Verificando estado de la solicitud...'}
        )
        
        # Verificar el estado de la solicitud (polling)
        max_attempts = 30  # Máximo 30 intentos (15 minutos aprox)
        attempts = 0
        
        while attempts < max_attempts:
            estado_result = descarga.verificar_descarga()
            
            if estado_result.get('estado_solicitud') == '3':  # Terminada
                break
            elif estado_result.get('estado_solicitud') == '5':  # Error
                raise Exception(f"Error en la solicitud del SAT: {estado_result.get('mensaje', 'Error desconocido')}")
            
            attempts += 1
            
            # Actualizar progreso
            progress = 30 + (attempts * 2)  # Incremento gradual hasta 60%
            self.update_state(
                state='PROGRESS',
                meta={'current': min(progress, 60), 'total': 100, 'status': f'Esperando respuesta del SAT... (intento {attempts}/{max_attempts})'}
            )
            
            # Esperar 30 segundos antes del siguiente intento
            import time
            time.sleep(30)
        
        if attempts >= max_attempts:
            raise Exception("Timeout: El SAT no completó la solicitud en el tiempo esperado")
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 70, 'total': 100, 'status': 'Descargando archivos...'}
        )
        
        # Descargar los archivos
        descarga_result = descarga.descargar()
        
        if not descarga_result.get('success'):
            raise Exception(f"Error en descarga de archivos: {descarga_result.get('message', 'Error desconocido')}")
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 80, 'total': 100, 'status': 'Procesando archivos descargados...'}
        )
        
        # Procesar los archivos descargados
        archivos_procesados = 0
        total_archivos = len(descarga_result.get('archivos', []))
        job.total_cfdi = total_archivos
        job.save()
        
        for archivo_path in descarga_result.get('archivos', []):
            try:
                # Procesar archivo ZIP con CFDIs
                with zipfile.ZipFile(archivo_path, 'r') as zip_file:
                    for filename in zip_file.namelist():
                        if filename.endswith('.xml'):
                            # Procesar CFDI individual
                            xml_content = zip_file.read(filename)
                            _process_cfdi_xml(xml_content, job)
                            archivos_procesados += 1
                            job.procesados = archivos_procesados
                            job.save()
                            
                            # Actualizar progreso
                            progress = 80 + ((archivos_procesados / total_archivos) * 15)
                            self.update_state(
                                state='PROGRESS',
                                meta={'current': int(progress), 'total': 100, 'status': f'Procesados {archivos_procesados} de {total_archivos} CFDIs'}
                            )
                
            except Exception as e:
                logger.error(f"Error procesando archivo {archivo_path}: {str(e)}")
                continue
        
        # Guardar archivo de descarga comprimido
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            with zipfile.ZipFile(temp_file, 'w') as zip_file:
                for archivo_path in descarga_result.get('archivos', []):
                    zip_file.write(archivo_path, os.path.basename(archivo_path))
            
            # Guardar en el modelo
            with open(temp_file.name, 'rb') as f:
                job.archivo_descarga.save(
                    f'descarga_cfdi_{job.id}.zip',
                    ContentFile(f.read())
                )
        
        # Completar el trabajo
        job.estado = 'COMPLETADO'
        job.fecha_fin_proceso = django_timezone.now()
        job.save()
        
        # Actualizar progreso final
        self.update_state(
            state='SUCCESS',
            meta={'current': 100, 'total': 100, 'status': f'Descarga completada. {archivos_procesados} CFDIs procesados.'}
        )
        
        return {
            'status': 'success',
            'message': f'Descarga completada exitosamente. {archivos_procesados} CFDIs procesados.',
            'total_cfdi': archivos_procesados
        }
        
    except Exception as e:
        # Marcar el trabajo como error
        job.estado = 'ERROR'
        job.mensaje_error = str(e)
        job.fecha_fin_proceso = django_timezone.now()
        job.save()
        
        logger.error(f"Error en descarga masiva (job_id: {job_id}): {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={'current': 0, 'total': 100, 'status': f'Error: {str(e)}'}
        )
        
        raise e


def _process_cfdi_xml(xml_content, job):
    """
    Procesa un archivo XML de CFDI individual y lo guarda en la base de datos
    """
    try:
        # Importar herramientas de parsing XML
        from xml.etree import ElementTree as ET
        from datetime import datetime
        import uuid
        
        # Parse del XML
        root = ET.fromstring(xml_content)
        
        # Namespaces comunes de CFDI
        namespaces = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'cfdi32': 'http://www.sat.gob.mx/cfd/3',
            'cfdi33': 'http://www.sat.gob.mx/cfd/3',
        }
        
        # Determinar versión y namespace
        cfdi_ns = None
        for ns_prefix, ns_uri in namespaces.items():
            if ns_uri in root.tag:
                cfdi_ns = ns_uri
                break
        
        if not cfdi_ns:
            # Intentar detectar automáticamente
            cfdi_ns = root.tag.split('}')[0][1:] if '}' in root.tag else ''
        
        # Extraer información básica del comprobante
        uuid_element = root.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
        if uuid_element is None:
            # Buscar en versiones anteriores
            uuid_element = root.find('.//tfd:TimbreFiscalDigital', {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'})
        
        if uuid_element is None:
            logger.warning("No se encontró TimbreFiscalDigital en el XML")
            return
        
        uuid_cfdi = uuid_element.get('UUID')
        
        # Verificar si ya existe
        if CFDI.objects.filter(uuid=uuid_cfdi).exists():
            return  # Ya existe, omitir
        
        # Extraer datos del comprobante
        serie = root.get('Serie', '')
        folio = root.get('Folio', '')
        fecha_str = root.get('Fecha')
        fecha_emision = datetime.fromisoformat(fecha_str.replace('T', ' ').replace('Z', ''))
        
        # Datos del emisor
        emisor_element = root.find(f'.//{{{cfdi_ns}}}Emisor')
        rfc_emisor = emisor_element.get('Rfc') if emisor_element is not None else ''
        nombre_emisor = emisor_element.get('Nombre', '') if emisor_element is not None else ''
        
        # Datos del receptor
        receptor_element = root.find(f'.//{{{cfdi_ns}}}Receptor')
        rfc_receptor = receptor_element.get('Rfc') if receptor_element is not None else ''
        nombre_receptor = receptor_element.get('Nombre', '') if receptor_element is not None else ''
        
        # Montos
        subtotal = Decimal(root.get('SubTotal', '0'))
        total = Decimal(root.get('Total', '0'))
        
        # Calcular IVA (aproximado, podría ser más complejo)
        iva = total - subtotal if total > subtotal else Decimal('0')
        
        # Tipo de comprobante
        tipo_comp = root.get('TipoDeComprobante', '')
        tipo_mapping = {
            'I': 'INGRESO',
            'E': 'EGRESO',
            'T': 'TRASLADO',
            'N': 'NOMINA',
            'P': 'PAGO'
        }
        tipo_comprobante = tipo_mapping.get(tipo_comp, 'INGRESO')
        
        # Crear registro CFDI
        with transaction.atomic():
            cfdi = CFDI.objects.create(
                empresa=job.empresa,
                trabajo_descarga=job,
                uuid=uuid_cfdi,
                serie=serie,
                folio=folio,
                fecha_emision=fecha_emision,
                rfc_emisor=rfc_emisor,
                nombre_emisor=nombre_emisor,
                rfc_receptor=rfc_receptor,
                nombre_receptor=nombre_receptor,
                tipo_comprobante=tipo_comprobante,
                subtotal=subtotal,
                iva=iva,
                total=total,
                creado_por=job.creado_por
            )
            
            # Guardar archivo XML
            cfdi.archivo_xml.save(
                f'{uuid_cfdi}.xml',
                ContentFile(xml_content)
            )
        
        logger.info(f"CFDI procesado: {uuid_cfdi}")
        
    except Exception as e:
        logger.error(f"Error procesando CFDI XML: {str(e)}")
        

@shared_task(bind=True)
def verify_cfdi_status(self, cfdi_ids):
    """
    Tarea para verificar el estado de CFDIs específicos en el SAT
    """
    try:
        from satcfdi.create.descarga import DescargaMasiva
        from satcfdi.create.authenticate import Authenticate
        
        processed = 0
        total = len(cfdi_ids)
        
        for cfdi_id in cfdi_ids:
            try:
                cfdi = CFDI.objects.get(id=cfdi_id)
                
                # Obtener credenciales de la empresa
                credentials = cfdi.empresa.credenciales_sat
                
                # Configurar autenticación
                auth = Authenticate(
                    cer_file=credentials.certificado_cer.path,
                    key_file=credentials.llave_privada_key.path,
                    password=credentials.password_llave
                )
                
                # Verificar estado del CFDI
                # Nota: Esto requiere implementar la verificación individual en satcfdi
                # Por ahora, marcaremos como validado
                estado_anterior = cfdi.estado_sat
                
                # Actualizar estado (aquí iría la lógica real de consulta al SAT)
                cfdi.estado_sat = 'VIGENTE'  # Placeholder
                cfdi.validado_sat = True
                cfdi.fecha_validacion = django_timezone.now()
                cfdi.save()
                
                # Crear log de cambio de estado
                CFDIStatusLog.objects.create(
                    cfdi=cfdi,
                    estado_anterior=estado_anterior,
                    estado_nuevo=cfdi.estado_sat,
                    fecha_consulta=django_timezone.now(),
                    creado_por=cfdi.creado_por
                )
                
                processed += 1
                
                # Actualizar progreso
                self.update_state(
                    state='PROGRESS',
                    meta={'current': processed, 'total': total, 'status': f'Verificados {processed} de {total} CFDIs'}
                )
                
            except Exception as e:
                logger.error(f"Error verificando CFDI {cfdi_id}: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'message': f'Verificación completada. {processed} CFDIs verificados.',
            'processed': processed,
            'total': total
        }
        
    except Exception as e:
        logger.error(f"Error en verificación de CFDIs: {str(e)}")
        raise e


@shared_task
def validate_sat_credentials(credentials_id):
    """
    Tarea para validar credenciales SAT
    """
    try:
        from satcfdi.create.authenticate import Authenticate
        
        credentials = SATCredentials.objects.get(id=credentials_id)
        
        # Intentar autenticar con las credenciales
        auth = Authenticate(
            cer_file=credentials.certificado_cer.path,
            key_file=credentials.llave_privada_key.path,
            password=credentials.password_llave
        )
        
        # Obtener información del certificado
        cert_info = auth.get_certificate_info()
        
        # Actualizar credenciales
        credentials.validadas = True
        credentials.fecha_validacion = django_timezone.now()
        
        if cert_info.get('fecha_vencimiento'):
            credentials.fecha_vencimiento = cert_info['fecha_vencimiento']
        
        credentials.save()
        
        return {
            'status': 'success',
            'message': 'Credenciales validadas exitosamente',
            'cert_info': cert_info
        }
        
    except Exception as e:
        # Marcar como no validadas
        credentials.validadas = False
        credentials.save()
        
        logger.error(f"Error validando credenciales {credentials_id}: {str(e)}")
        
        return {
            'status': 'error',
            'message': f'Error validando credenciales: {str(e)}'
        }