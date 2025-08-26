from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Q, F
from django.http import HttpResponse
from decimal import Decimal
from datetime import datetime, date
from apps.transacciones.models import TransaccionContable, MovimientoContable
from apps.catalogo_cuentas.models import CuentaContable
from apps.empresas.models import Empresa


class ReporteViewSet(viewsets.ViewSet):
    """ViewSet para generar reportes contables MVP"""
    permission_classes = [IsAuthenticated]
    
    def get_empresa(self):
        """Obtener empresa actual del usuario"""
        if hasattr(self.request, 'empresa') and self.request.empresa:
            return self.request.empresa
        
        empresa_id = self.request.session.get('empresa_id')
        if empresa_id:
            try:
                return Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        from apps.empresas.models import UsuarioEmpresa
        acceso = UsuarioEmpresa.objects.filter(
            usuario=self.request.user,
            activo=True
        ).first()
        return acceso.empresa if acceso else None
    
    @action(detail=False, methods=['get'])
    def balanza_comprobacion(self, request):
        """Genera la balanza de comprobación"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener fecha de corte
        fecha_corte = request.query_params.get('fecha', date.today())
        if isinstance(fecha_corte, str):
            fecha_corte = datetime.strptime(fecha_corte, '%Y-%m-%d').date()
        
        # Obtener formato de descarga
        formato = request.query_params.get('formato', 'json')
        
        # Obtener todas las cuentas con movimientos
        cuentas_con_movimientos = MovimientoContable.objects.filter(
            transaccion__empresa=empresa,
            transaccion__estado='CONTABILIZADA',
            transaccion__fecha__lte=fecha_corte,
            activo=True
        ).values('cuenta').distinct()
        
        balanza = []
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        
        for cuenta_dict in cuentas_con_movimientos:
            cuenta = CuentaContable.objects.get(id=cuenta_dict['cuenta'])
            
            # Calcular saldos
            movimientos = MovimientoContable.objects.filter(
                cuenta=cuenta,
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__lte=fecha_corte,
                activo=True
            )
            
            suma_debe = movimientos.aggregate(Sum('debe'))['debe__sum'] or Decimal('0.00')
            suma_haber = movimientos.aggregate(Sum('haber'))['haber__sum'] or Decimal('0.00')
            
            # Determinar saldo según naturaleza
            if cuenta.naturaleza == 'DEUDORA':
                saldo = suma_debe - suma_haber
                saldo_debe = saldo if saldo > 0 else Decimal('0.00')
                saldo_haber = abs(saldo) if saldo < 0 else Decimal('0.00')
            else:
                saldo = suma_haber - suma_debe
                saldo_haber = saldo if saldo > 0 else Decimal('0.00')
                saldo_debe = abs(saldo) if saldo < 0 else Decimal('0.00')
            
            total_debe += saldo_debe
            total_haber += saldo_haber
            
            balanza.append({
                'cuenta_codigo': cuenta.codigo,
                'cuenta_nombre': cuenta.nombre,
                'tipo': cuenta.tipo,
                'cargos': suma_debe,
                'abonos': suma_haber,
                'saldo_deudor': saldo_debe,
                'saldo_acreedor': saldo_haber
            })
        
        # Ordenar por código de cuenta
        balanza.sort(key=lambda x: x['cuenta_codigo'])
        
        data = {
            'fecha_corte': fecha_corte,
            'empresa': empresa.nombre,
            'cuentas': balanza,
            'totales': {
                'total_deudor': total_debe,
                'total_acreedor': total_haber,
                'balanceado': total_debe == total_haber
            }
        }
        
        # Generar descarga según formato
        if formato == 'pdf':
            return self._generar_pdf_balanza(data)
        elif formato == 'excel':
            return self._generar_excel_balanza(data)
        elif formato == 'csv':
            return self._generar_csv_balanza(data)
        else:
            return Response(data)
    
    @action(detail=False, methods=['get'])
    def estado_resultados(self, request):
        """Genera el estado de resultados"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener período
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin', date.today())
        
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if not fecha_inicio:
            fecha_inicio = date(fecha_fin.year, 1, 1)  # Inicio del año
        elif isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        # Filtro base para movimientos del período
        filtro_base = Q(
            transaccion__empresa=empresa,
            transaccion__estado='CONTABILIZADA',
            transaccion__fecha__gte=fecha_inicio,
            transaccion__fecha__lte=fecha_fin,
            activo=True
        )
        
        # Calcular ingresos
        ingresos = MovimientoContable.objects.filter(
            filtro_base,
            cuenta__tipo='INGRESO'
        ).aggregate(
            total=Sum('haber') - Sum('debe')
        )['total'] or Decimal('0.00')
        
        # Calcular costos
        costos = MovimientoContable.objects.filter(
            filtro_base,
            cuenta__tipo='COSTO'
        ).aggregate(
            total=Sum('debe') - Sum('haber')
        )['total'] or Decimal('0.00')
        
        # Calcular gastos
        gastos = MovimientoContable.objects.filter(
            filtro_base,
            cuenta__tipo='GASTO'
        ).aggregate(
            total=Sum('debe') - Sum('haber')
        )['total'] or Decimal('0.00')
        
        # Calcular utilidad
        utilidad_bruta = ingresos - costos
        utilidad_operativa = utilidad_bruta - gastos
        utilidad_neta = utilidad_operativa  # En MVP no consideramos impuestos
        
        # Detalle por cuenta
        detalle_ingresos = self._obtener_detalle_cuentas(empresa, 'INGRESO', fecha_inicio, fecha_fin)
        detalle_costos = self._obtener_detalle_cuentas(empresa, 'COSTO', fecha_inicio, fecha_fin)
        detalle_gastos = self._obtener_detalle_cuentas(empresa, 'GASTO', fecha_inicio, fecha_fin)
        
        return Response({
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'empresa': empresa.nombre,
            'resumen': {
                'ingresos': ingresos,
                'costos': costos,
                'utilidad_bruta': utilidad_bruta,
                'gastos': gastos,
                'utilidad_operativa': utilidad_operativa,
                'utilidad_neta': utilidad_neta
            },
            'detalle': {
                'ingresos': detalle_ingresos,
                'costos': detalle_costos,
                'gastos': detalle_gastos
            }
        })
    
    def _obtener_detalle_cuentas(self, empresa, tipo_cuenta, fecha_inicio, fecha_fin):
        """Obtiene el detalle de movimientos por tipo de cuenta"""
        cuentas = CuentaContable.objects.filter(
            empresa=empresa,
            tipo=tipo_cuenta,
            activo=True
        )
        
        detalle = []
        for cuenta in cuentas:
            movimientos = MovimientoContable.objects.filter(
                cuenta=cuenta,
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__gte=fecha_inicio,
                transaccion__fecha__lte=fecha_fin,
                activo=True
            )
            
            if tipo_cuenta in ['COSTO', 'GASTO']:
                saldo = movimientos.aggregate(
                    total=Sum('debe') - Sum('haber')
                )['total'] or Decimal('0.00')
            else:  # INGRESO
                saldo = movimientos.aggregate(
                    total=Sum('haber') - Sum('debe')
                )['total'] or Decimal('0.00')
            
            if saldo != 0:
                detalle.append({
                    'cuenta_codigo': cuenta.codigo,
                    'cuenta_nombre': cuenta.nombre,
                    'saldo': saldo
                })
        
        return detalle
    
    @action(detail=False, methods=['get'])
    def balance_general(self, request):
        """Genera el balance general (Estado de Situación Financiera)"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Fecha de corte
        fecha_corte = request.query_params.get('fecha', date.today())
        if isinstance(fecha_corte, str):
            fecha_corte = datetime.strptime(fecha_corte, '%Y-%m-%d').date()
        
        # Obtener saldos por tipo
        activos = self._calcular_saldo_tipo(empresa, 'ACTIVO', fecha_corte)
        pasivos = self._calcular_saldo_tipo(empresa, 'PASIVO', fecha_corte)
        capital = self._calcular_saldo_tipo(empresa, 'CAPITAL', fecha_corte)
        
        # Calcular resultado del ejercicio
        ingresos = self._calcular_saldo_tipo(empresa, 'INGRESO', fecha_corte)
        costos = self._calcular_saldo_tipo(empresa, 'COSTO', fecha_corte)
        gastos = self._calcular_saldo_tipo(empresa, 'GASTO', fecha_corte)
        resultado_ejercicio = ingresos['total'] - costos['total'] - gastos['total']
        
        # Total capital contable
        total_capital = capital['total'] + resultado_ejercicio
        
        # Verificación de balance
        total_activos = activos['total']
        total_pasivos_capital = pasivos['total'] + total_capital
        
        return Response({
            'fecha_corte': fecha_corte,
            'empresa': empresa.nombre,
            'activos': activos,
            'pasivos': pasivos,
            'capital': {
                'detalle': capital['detalle'],
                'capital_social': capital['total'],
                'resultado_ejercicio': resultado_ejercicio,
                'total': total_capital
            },
            'verificacion': {
                'total_activos': total_activos,
                'total_pasivos_capital': total_pasivos_capital,
                'balanceado': abs(total_activos - total_pasivos_capital) < Decimal('0.01')
            }
        })
    
    def _calcular_saldo_tipo(self, empresa, tipo, fecha_corte):
        """Calcula el saldo total por tipo de cuenta"""
        cuentas = CuentaContable.objects.filter(
            empresa=empresa,
            tipo=tipo,
            activo=True
        )
        
        detalle = []
        total = Decimal('0.00')
        
        for cuenta in cuentas:
            movimientos = MovimientoContable.objects.filter(
                cuenta=cuenta,
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__lte=fecha_corte,
                activo=True
            )
            
            suma_debe = movimientos.aggregate(Sum('debe'))['debe__sum'] or Decimal('0.00')
            suma_haber = movimientos.aggregate(Sum('haber'))['haber__sum'] or Decimal('0.00')
            
            # Calcular saldo según naturaleza
            if cuenta.naturaleza == 'DEUDORA':
                saldo = suma_debe - suma_haber
            else:
                saldo = suma_haber - suma_debe
            
            if saldo != 0:
                detalle.append({
                    'cuenta_codigo': cuenta.codigo,
                    'cuenta_nombre': cuenta.nombre,
                    'saldo': saldo
                })
                total += saldo
        
        return {
            'detalle': detalle,
            'total': total
        }
    
    @action(detail=False, methods=['get'])
    def libro_diario(self, request):
        """Genera el libro diario de transacciones"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener período
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin', date.today())
        
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if not fecha_inicio:
            fecha_inicio = date(fecha_fin.year, fecha_fin.month, 1)  # Inicio del mes
        elif isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        # Obtener transacciones del período
        transacciones = TransaccionContable.objects.filter(
            empresa=empresa,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
            activo=True
        ).defer('tipo_personalizado').order_by('fecha', 'folio').prefetch_related('movimientos__cuenta')
        
        libro = []
        for trans in transacciones:
            movimientos = []
            for mov in trans.movimientos.filter(activo=True):
                movimientos.append({
                    'cuenta_codigo': mov.cuenta.codigo,
                    'cuenta_nombre': mov.cuenta.nombre,
                    'concepto': mov.concepto or trans.concepto,
                    'debe': mov.debe,
                    'haber': mov.haber
                })
            
            libro.append({
                'fecha': trans.fecha,
                'folio': trans.folio,
                'tipo': trans.tipo,
                'concepto': trans.concepto,
                'estado': trans.estado,
                'movimientos': movimientos,
                'total_debe': trans.total_debe,
                'total_haber': trans.total_haber
            })
        
        return Response({
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'empresa': empresa.nombre,
            'transacciones': libro,
            'resumen': {
                'total_transacciones': len(libro),
                'por_estado': {
                    estado: len([t for t in libro if t['estado'] == estado])
                    for estado in ['BORRADOR', 'VALIDADA', 'CONTABILIZADA', 'CANCELADA']
                }
            }
        })

    @action(detail=False, methods=['get'])
    def libro_mayor(self, request):
        """Genera el libro mayor por cuenta"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener período
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin', date.today())
        cuenta_id = request.query_params.get('cuenta_id')
        
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if not fecha_inicio:
            fecha_inicio = date(fecha_fin.year, fecha_fin.month, 1)  # Inicio del mes
        elif isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        # Filtro base
        filtro_base = Q(
            transaccion__empresa=empresa,
            transaccion__estado='CONTABILIZADA',
            transaccion__fecha__gte=fecha_inicio,
            transaccion__fecha__lte=fecha_fin,
            activo=True
        )
        
        # Si se especifica una cuenta específica
        if cuenta_id and cuenta_id != 'todas':
            try:
                cuenta = CuentaContable.objects.get(id=cuenta_id, empresa=empresa)
                cuentas_analizar = [cuenta]
            except CuentaContable.DoesNotExist:
                return Response({'error': 'Cuenta no encontrada'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            # Obtener todas las cuentas con movimientos
            cuentas_con_movimientos = MovimientoContable.objects.filter(
                filtro_base
            ).values('cuenta').distinct()
            
            cuentas_analizar = CuentaContable.objects.filter(
                id__in=[c['cuenta'] for c in cuentas_con_movimientos],
                empresa=empresa,
                activo=True
            ).order_by('codigo')
        
        libro_mayor = []
        
        for cuenta in cuentas_analizar:
            # Saldo inicial (movimientos anteriores a la fecha de inicio)
            movimientos_anteriores = MovimientoContable.objects.filter(
                cuenta=cuenta,
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__lt=fecha_inicio,
                activo=True
            )
            
            suma_debe_anterior = movimientos_anteriores.aggregate(Sum('debe'))['debe__sum'] or Decimal('0.00')
            suma_haber_anterior = movimientos_anteriores.aggregate(Sum('haber'))['haber__sum'] or Decimal('0.00')
            
            if cuenta.naturaleza == 'DEUDORA':
                saldo_inicial = suma_debe_anterior - suma_haber_anterior
            else:
                saldo_inicial = suma_haber_anterior - suma_debe_anterior
            
            # Movimientos del período
            movimientos_periodo = MovimientoContable.objects.filter(
                filtro_base,
                cuenta=cuenta
            ).select_related('transaccion').order_by('transaccion__fecha', 'transaccion__folio')
            
            movimientos_detalle = []
            saldo_acumulado = saldo_inicial
            
            for mov in movimientos_periodo:
                # Calcular el efecto en el saldo
                if cuenta.naturaleza == 'DEUDORA':
                    efecto = mov.debe - mov.haber
                else:
                    efecto = mov.haber - mov.debe
                
                saldo_acumulado += efecto
                
                movimientos_detalle.append({
                    'fecha': mov.transaccion.fecha,
                    'folio': mov.transaccion.folio,
                    'concepto': mov.concepto or mov.transaccion.concepto,
                    'debe': mov.debe,
                    'haber': mov.haber,
                    'saldo': saldo_acumulado
                })
            
            # Totales del período
            suma_debe_periodo = movimientos_periodo.aggregate(Sum('debe'))['debe__sum'] or Decimal('0.00')
            suma_haber_periodo = movimientos_periodo.aggregate(Sum('haber'))['haber__sum'] or Decimal('0.00')
            
            libro_mayor.append({
                'cuenta': {
                    'id': cuenta.id,
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'tipo': cuenta.tipo,
                    'naturaleza': cuenta.naturaleza
                },
                'saldo_inicial': saldo_inicial,
                'movimientos': movimientos_detalle,
                'totales_periodo': {
                    'debe': suma_debe_periodo,
                    'haber': suma_haber_periodo
                },
                'saldo_final': saldo_acumulado
            })
        
        # Obtener lista de cuentas disponibles para el selector
        todas_las_cuentas = CuentaContable.objects.filter(
            empresa=empresa,
            activo=True
        ).order_by('codigo').values('id', 'codigo', 'nombre')
        
        return Response({
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'empresa': empresa.nombre,
            'cuenta_seleccionada': cuenta_id,
            'cuentas_disponibles': list(todas_las_cuentas),
            'libro_mayor': libro_mayor,
            'resumen': {
                'total_cuentas': len(libro_mayor),
                'total_movimientos': sum(len(cuenta['movimientos']) for cuenta in libro_mayor)
            }
        })

    @action(detail=False, methods=['get'])
    def flujo_efectivo(self, request):
        """Genera el flujo de efectivo"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener período
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin', date.today())
        
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if not fecha_inicio:
            fecha_inicio = date(fecha_fin.year, fecha_fin.month, 1)  # Inicio del mes
        elif isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        
        # Filtro base para movimientos del período
        filtro_base = Q(
            transaccion__empresa=empresa,
            transaccion__estado='CONTABILIZADA',
            transaccion__fecha__gte=fecha_inicio,
            transaccion__fecha__lte=fecha_fin,
            activo=True
        )
        
        # Obtener cuentas de efectivo (normalmente Caja y Bancos)
        # En un sistema completo esto sería configurable, para MVP usamos tipos estándar
        cuentas_efectivo = CuentaContable.objects.filter(
            empresa=empresa,
            codigo__startswith='1.1',  # Asumiendo estructura estándar: 1.1.x para efectivo
            activo=True
        )
        
        if not cuentas_efectivo.exists():
            # Fallback: buscar cualquier cuenta que contenga "caja" o "banco"
            cuentas_efectivo = CuentaContable.objects.filter(
                empresa=empresa,
                nombre__icontains='caja',
                activo=True
            ) | CuentaContable.objects.filter(
                empresa=empresa,
                nombre__icontains='banco',
                activo=True
            )
        
        # Saldo inicial de efectivo
        saldo_inicial_total = Decimal('0.00')
        detalle_inicial = []
        
        for cuenta in cuentas_efectivo:
            movimientos_anteriores = MovimientoContable.objects.filter(
                cuenta=cuenta,
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__lt=fecha_inicio,
                activo=True
            )
            
            suma_debe = movimientos_anteriores.aggregate(Sum('debe'))['debe__sum'] or Decimal('0.00')
            suma_haber = movimientos_anteriores.aggregate(Sum('haber'))['haber__sum'] or Decimal('0.00')
            
            # Para cuentas de efectivo (activos), el saldo es debe - haber
            saldo_inicial = suma_debe - suma_haber
            saldo_inicial_total += saldo_inicial
            
            if saldo_inicial != 0:
                detalle_inicial.append({
                    'cuenta_codigo': cuenta.codigo,
                    'cuenta_nombre': cuenta.nombre,
                    'saldo_inicial': saldo_inicial
                })
        
        # Movimientos de efectivo del período
        movimientos_efectivo = MovimientoContable.objects.filter(
            filtro_base,
            cuenta__in=cuentas_efectivo
        ).select_related('transaccion', 'cuenta').order_by('transaccion__fecha', 'transaccion__folio')
        
        # Clasificar movimientos
        entradas = []
        salidas = []
        total_entradas = Decimal('0.00')
        total_salidas = Decimal('0.00')
        
        for mov in movimientos_efectivo:
            movimiento_detalle = {
                'fecha': mov.transaccion.fecha,
                'folio': mov.transaccion.folio,
                'cuenta_efectivo': f"{mov.cuenta.codigo} - {mov.cuenta.nombre}",
                'concepto': mov.concepto or mov.transaccion.concepto,
                'tipo_transaccion': mov.transaccion.tipo,
                'monto': mov.debe if mov.debe > 0 else mov.haber
            }
            
            if mov.debe > 0:  # Entrada de efectivo
                entradas.append(movimiento_detalle)
                total_entradas += mov.debe
            else:  # Salida de efectivo
                salidas.append(movimiento_detalle)
                total_salidas += mov.haber
        
        # Saldo final
        flujo_neto = total_entradas - total_salidas
        saldo_final = saldo_inicial_total + flujo_neto
        
        # Clasificación por tipo de transacción
        flujo_por_tipo = {}
        for mov in movimientos_efectivo:
            tipo = mov.transaccion.tipo
            if tipo not in flujo_por_tipo:
                flujo_por_tipo[tipo] = {'entradas': Decimal('0.00'), 'salidas': Decimal('0.00')}
            
            if mov.debe > 0:
                flujo_por_tipo[tipo]['entradas'] += mov.debe
            else:
                flujo_por_tipo[tipo]['salidas'] += mov.haber
        
        return Response({
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'empresa': empresa.nombre,
            'cuentas_efectivo': [
                {'id': c.id, 'codigo': c.codigo, 'nombre': c.nombre} 
                for c in cuentas_efectivo
            ],
            'saldo_inicial': {
                'total': saldo_inicial_total,
                'detalle': detalle_inicial
            },
            'movimientos': {
                'entradas': entradas,
                'salidas': salidas
            },
            'resumen': {
                'saldo_inicial': saldo_inicial_total,
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'flujo_neto': flujo_neto,
                'saldo_final': saldo_final
            },
            'por_tipo_transaccion': flujo_por_tipo,
            'estadisticas': {
                'total_movimientos': len(movimientos_efectivo),
                'promedio_entradas': total_entradas / len(entradas) if entradas else Decimal('0.00'),
                'promedio_salidas': total_salidas / len(salidas) if salidas else Decimal('0.00')
            }
        })

    @action(detail=False, methods=['get'], url_path='charts/ingresos-gastos')
    def chart_ingresos_gastos(self, request):
        """Genera datos para gráfico de ingresos vs gastos por mes"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener últimos 6 meses
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        fecha_actual = date.today()
        meses = []
        ingresos_data = []
        gastos_data = []
        
        for i in range(5, -1, -1):  # Últimos 6 meses
            fecha_mes = fecha_actual - relativedelta(months=i)
            inicio_mes = date(fecha_mes.year, fecha_mes.month, 1)
            
            # Calcular último día del mes
            if fecha_mes.month == 12:
                fin_mes = date(fecha_mes.year + 1, 1, 1) - timedelta(days=1)
            else:
                fin_mes = date(fecha_mes.year, fecha_mes.month + 1, 1) - timedelta(days=1)
            
            # Si es el mes actual, usar fecha actual como límite
            if fecha_mes.month == fecha_actual.month and fecha_mes.year == fecha_actual.year:
                fin_mes = fecha_actual
            
            # Filtro para el mes
            filtro_mes = Q(
                transaccion__empresa=empresa,
                transaccion__estado='CONTABILIZADA',
                transaccion__fecha__gte=inicio_mes,
                transaccion__fecha__lte=fin_mes,
                activo=True
            )
            
            # Calcular ingresos del mes
            ingresos_mes = MovimientoContable.objects.filter(
                filtro_mes,
                cuenta__tipo='INGRESO'
            ).aggregate(
                total=Sum('haber') - Sum('debe')
            )['total'] or Decimal('0.00')
            
            # Calcular gastos del mes (incluye costos y gastos)
            gastos_mes = MovimientoContable.objects.filter(
                filtro_mes,
                cuenta__tipo__in=['GASTO', 'COSTO']
            ).aggregate(
                total=Sum('debe') - Sum('haber')
            )['total'] or Decimal('0.00')
            
            # Agregar a las listas
            meses.append(fecha_mes.strftime('%b %Y'))
            ingresos_data.append(float(ingresos_mes))
            gastos_data.append(float(gastos_mes))
        
        return Response({
            'labels': meses,
            'ingresos': ingresos_data,
            'gastos': gastos_data,
            'empresa': empresa.nombre
        })
    
    @action(detail=False, methods=['get'], url_path='charts/balance-cuentas')
    def chart_balance_cuentas(self, request):
        """Genera datos para gráfico de balance por tipo de cuenta"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Fecha de corte
        fecha_corte = date.today()
        
        # Calcular saldos por tipo
        tipos_cuenta = ['ACTIVO', 'PASIVO', 'CAPITAL', 'INGRESO', 'GASTO']
        labels = []
        values = []
        
        for tipo in tipos_cuenta:
            saldo_tipo = self._calcular_saldo_tipo(empresa, tipo, fecha_corte)
            if saldo_tipo['total'] > 0:
                labels.append(tipo.capitalize())
                values.append(float(saldo_tipo['total']))
        
        return Response({
            'labels': labels,
            'values': values,
            'empresa': empresa.nombre,
            'fecha_corte': fecha_corte
        })
    
    # Métodos para generar archivos de descarga
    def _generar_pdf_balanza(self, data):
        """Genera PDF de balanza de comprobación"""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle',
                                    parent=styles['Heading1'],
                                    fontSize=16,
                                    spaceAfter=30,
                                    alignment=1)  # Centrado
        
        # Contenido
        elements = []
        
        # Título
        elements.append(Paragraph(f"BALANZA DE COMPROBACIÓN", title_style))
        elements.append(Paragraph(f"{data['empresa']}", styles['Heading2']))
        elements.append(Paragraph(f"Al {data['fecha_corte'].strftime('%d de %B de %Y')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Tabla de cuentas
        table_data = [['Código', 'Cuenta', 'Tipo', 'Cargos', 'Abonos', 'Saldo Deudor', 'Saldo Acreedor']]
        
        for cuenta in data['cuentas']:
            table_data.append([
                cuenta['cuenta_codigo'],
                cuenta['cuenta_nombre'][:30],  # Truncar nombre largo
                cuenta['tipo'],
                f"${float(cuenta['cargos']):,.2f}",
                f"${float(cuenta['abonos']):,.2f}",
                f"${float(cuenta['saldo_deudor']):,.2f}",
                f"${float(cuenta['saldo_acreedor']):,.2f}"
            ])
        
        # Totales
        table_data.append([
            '', 'TOTALES', '',
            f"${float(data['totales']['total_deudor']):,.2f}",
            f"${float(data['totales']['total_acreedor']):,.2f}",
            f"${float(data['totales']['total_deudor']):,.2f}",
            f"${float(data['totales']['total_acreedor']):,.2f}"
        ])
        
        # Crear tabla
        table = Table(table_data, colWidths=[0.8*inch, 2*inch, 0.8*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),  # Alinear números a la derecha
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Balance status
        if data['totales']['balanceado']:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("✅ La balanza está correctamente balanceada", styles['Normal']))
        
        # Construir PDF
        doc.build(elements)
        
        # Preparar respuesta
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="balanza_comprobacion_{data["fecha_corte"]}.pdf"'
        return response
    
    def _generar_excel_balanza(self, data):
        """Genera Excel de balanza de comprobación"""
        import xlsxwriter
        from io import BytesIO
        
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet('Balanza de Comprobación')
        
        # Formatos
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        money_format = workbook.add_format({'num_format': '$#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'num_format': '$#,##0.00', 'border': 1})
        
        # Título
        worksheet.merge_range('A1:G1', 'BALANZA DE COMPROBACIÓN', title_format)
        worksheet.merge_range('A2:G2', data['empresa'], title_format)
        worksheet.merge_range('A3:G3', f"Al {data['fecha_corte'].strftime('%d de %B de %Y')}", title_format)
        
        # Headers
        headers = ['Código', 'Cuenta', 'Tipo', 'Cargos', 'Abonos', 'Saldo Deudor', 'Saldo Acreedor']
        for col, header in enumerate(headers):
            worksheet.write(4, col, header, header_format)
        
        # Datos
        row = 5
        for cuenta in data['cuentas']:
            worksheet.write(row, 0, cuenta['cuenta_codigo'], text_format)
            worksheet.write(row, 1, cuenta['cuenta_nombre'], text_format)
            worksheet.write(row, 2, cuenta['tipo'], text_format)
            worksheet.write(row, 3, float(cuenta['cargos']), money_format)
            worksheet.write(row, 4, float(cuenta['abonos']), money_format)
            worksheet.write(row, 5, float(cuenta['saldo_deudor']), money_format)
            worksheet.write(row, 6, float(cuenta['saldo_acreedor']), money_format)
            row += 1
        
        # Totales
        worksheet.write(row, 0, '', text_format)
        worksheet.write(row, 1, 'TOTALES', total_format)
        worksheet.write(row, 2, '', text_format)
        worksheet.write(row, 3, float(data['totales']['total_deudor']), total_format)
        worksheet.write(row, 4, float(data['totales']['total_acreedor']), total_format)
        worksheet.write(row, 5, float(data['totales']['total_deudor']), total_format)
        worksheet.write(row, 6, float(data['totales']['total_acreedor']), total_format)
        
        # Ajustar anchos de columna
        worksheet.set_column('A:A', 12)  # Código
        worksheet.set_column('B:B', 30)  # Cuenta
        worksheet.set_column('C:C', 10)  # Tipo
        worksheet.set_column('D:G', 15)  # Montos
        
        workbook.close()
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="balanza_comprobacion_{data["fecha_corte"]}.xlsx"'
        return response
    
    def _generar_csv_balanza(self, data):
        """Genera CSV de balanza de comprobación"""
        import csv
        from io import StringIO
        
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Headers
        writer.writerow(['Código', 'Cuenta', 'Tipo', 'Cargos', 'Abonos', 'Saldo Deudor', 'Saldo Acreedor'])
        
        # Datos
        for cuenta in data['cuentas']:
            writer.writerow([
                cuenta['cuenta_codigo'],
                cuenta['cuenta_nombre'],
                cuenta['tipo'],
                float(cuenta['cargos']),
                float(cuenta['abonos']),
                float(cuenta['saldo_deudor']),
                float(cuenta['saldo_acreedor'])
            ])
        
        # Totales
        writer.writerow([
            '',
            'TOTALES',
            '',
            float(data['totales']['total_deudor']),
            float(data['totales']['total_acreedor']),
            float(data['totales']['total_deudor']),
            float(data['totales']['total_acreedor'])
        ])
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="balanza_comprobacion_{data["fecha_corte"]}.csv"'
        return response


@api_view(['GET'])
@permission_classes([AllowAny])
def reportes_root(request):
    """Página de navegación del módulo de reportes"""
    if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        html_content = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Reportes Contables - ZivaBSuite</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                h1 { color: #2c3e50; }
                .report { margin: 20px 0; padding: 20px; background: #f1f2f6; border-radius: 5px; }
                .report h3 { color: #34495e; margin-top: 0; }
                .report p { color: #555; }
                .url { color: #3498db; font-family: monospace; }
                .back-link { margin-bottom: 20px; }
                .back-link a { color: #7f8c8d; text-decoration: none; }
                .feature { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .params { background: #fff3cd; padding: 10px; border-radius: 3px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="back-link"><a href="/">← Volver al inicio</a> | <a href="/api/">API Root</a></div>
                <h1>📊 Reportes Contables</h1>
                
                <div class="feature">
                    <strong>✨ Reportes MVP disponibles:</strong>
                    <ul>
                        <li>Balanza de Comprobación</li>
                        <li>Estado de Resultados</li>
                        <li>Balance General</li>
                        <li>Libro Diario</li>
                    </ul>
                </div>
                
                <div class="report">
                    <h3>📋 Balanza de Comprobación</h3>
                    <div class="url">GET /api/reportes/reportes/balanza_comprobacion/</div>
                    <p>Muestra los saldos de todas las cuentas con movimientos</p>
                    <div class="params">
                        <strong>Parámetros:</strong> <code>?fecha=2024-08-24</code> (fecha de corte)
                    </div>
                </div>
                
                <div class="report">
                    <h3>💰 Estado de Resultados</h3>
                    <div class="url">GET /api/reportes/reportes/estado_resultados/</div>
                    <p>Ingresos, costos y gastos del período</p>
                    <div class="params">
                        <strong>Parámetros:</strong> 
                        <code>?fecha_inicio=2024-01-01&fecha_fin=2024-08-24</code>
                    </div>
                </div>
                
                <div class="report">
                    <h3>🏦 Balance General</h3>
                    <div class="url">GET /api/reportes/reportes/balance_general/</div>
                    <p>Estado de situación financiera (Activos, Pasivos, Capital)</p>
                    <div class="params">
                        <strong>Parámetros:</strong> <code>?fecha=2024-08-24</code> (fecha de corte)
                    </div>
                </div>
                
                <div class="report">
                    <h3>📖 Libro Diario</h3>
                    <div class="url">GET /api/reportes/reportes/libro_diario/</div>
                    <p>Detalle de todas las transacciones del período</p>
                    <div class="params">
                        <strong>Parámetros:</strong> 
                        <code>?fecha_inicio=2024-08-01&fecha_fin=2024-08-31</code>
                    </div>
                </div>
                
                <h2>🔑 Autenticación</h2>
                <p><code>Authorization: Token 1e0b0f1c08f1359f4c76e55c2fcba894976aeba7</code></p>
                
                <h2>📥 Formatos de Exportación</h2>
                <p><em>En desarrollo: Excel, PDF, CSV</em></p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)
    
    # Para requests JSON
    return Response({
        'message': 'Reportes Contables API',
        'version': '5.0.0-MVP',
        'endpoints': {
            'balanza_comprobacion': request.build_absolute_uri('/api/reportes/reportes/balanza_comprobacion/'),
            'estado_resultados': request.build_absolute_uri('/api/reportes/reportes/estado_resultados/'),
            'balance_general': request.build_absolute_uri('/api/reportes/reportes/balance_general/'),
            'libro_diario': request.build_absolute_uri('/api/reportes/reportes/libro_diario/'),
        },
        'features': [
            'Reportes dinámicos',
            'Filtros por fecha',
            'Verificación de balance',
            'Detalle por cuenta'
        ]
    })