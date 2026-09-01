"""
Visualization Agent - Builds allowlisted medical data visualizations.

This agent collaborates with the Claude HCE Agent to create visualizations
through deterministic Plotly functions with validated parameters.

Performance optimizations:
- Singleton pattern for agent instance
- Deterministic Plotly function dispatch
- Execution time tracking
- Optimized preprocessing pipeline
"""

import logging
import time
from typing import Dict, Any, Optional, List
import pandas as pd
from config.settings import settings
from .code_executor import (
    MAX_METRICS,
    SUPPORTED_VISUALIZATION_TYPES,
    VISUALIZATION_TYPE_ALIASES,
    create_allowlisted_visualization,
)
from .data_preprocessor import DataPreprocessor
from .visualization_selector import VisualizationSelector

logger = logging.getLogger(__name__)

# Singleton instance for visualization agent
_visualization_agent_instance: Optional['VisualizationAgent'] = None


class VisualizationAgent:
    """
    Agent specialized in deterministic visualizations for medical data.
    
    This agent receives data and requirements from the clinical agent
    and selects an allowlisted function with validated parameters.
    
    Performance optimizations:
    - Singleton pattern via create_visualization_agent()
    - Explicit allowlist for supported visualization types
    - Execution time tracking for monitoring
    - Optimized preprocessing pipeline
    """
    
    def __init__(self):
        """Initialize the visualization agent."""
        start_time = time.perf_counter()
        
        logger.info("Initializing Visualization Agent...")
        
        # Store visualization settings for easy access
        self.viz_settings = settings.visualization
        
        # Initialize deterministic selection and preprocessing components.
        self.selector = VisualizationSelector()
        self.preprocessor = DataPreprocessor()
        
        # Performance tracking
        self._total_visualizations = 0
        self._successful_visualizations = 0
        self._total_execution_time_ms = 0.0
        self._template_usage_count = 0
        
        init_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"✅ Visualization Agent initialized with allowlisted functions "
            f"in {init_time_ms:.2f}ms"
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        avg_time = (
            self._total_execution_time_ms / self._total_visualizations
            if self._total_visualizations > 0 else 0
        )
        success_rate = (
            self._successful_visualizations / self._total_visualizations * 100
            if self._total_visualizations > 0 else 0
        )
        
        return {
            'total_visualizations': self._total_visualizations,
            'successful_visualizations': self._successful_visualizations,
            'success_rate_percent': success_rate,
            'total_execution_time_ms': self._total_execution_time_ms,
            'average_execution_time_ms': avg_time,
            'template_usage_count': self._template_usage_count,
            'allowlisted_function_usage_count': self._template_usage_count,
            'llm_usage_count': 0,
            'preprocessor_stats': self.preprocessor.get_performance_stats(),
            'template_cache_stats': {
                'templates_loaded': 0,
                'templates_available': 0,
            },
            'supported_visualization_types': sorted(SUPPORTED_VISUALIZATION_TYPES),
        }

    @staticmethod
    def _coerce_auto_selection(data: pd.DataFrame, selected_type: str) -> str:
        """Keep automatic selection inside the approved visualization allowlist."""
        normalized = selected_type.lower().strip().replace(' ', '_')
        normalized = VISUALIZATION_TYPE_ALIASES.get(normalized, normalized)
        if normalized in SUPPORTED_VISUALIZATION_TYPES:
            return normalized

        numeric_columns = [
            column for column in data.select_dtypes(include=['number']).columns
            if not column.endswith('_id') and column != 'seq_num'
        ]
        has_time = any(
            column in data.columns
            for column in ('charttime', 'time', 'date', 'datetime', 'timestamp')
        )
        if has_time and numeric_columns:
            return 'comparison' if len(numeric_columns) > 1 else 'timeline'
        if len(data.select_dtypes(include=['object', 'category', 'string']).columns):
            return 'bar'
        if numeric_columns:
            return 'histogram'
        return normalized
    
    def generate_visualization(
        self,
        data: pd.DataFrame,
        visualization_type: str,
        requirements: Optional[str] = None,
        title: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate a visualization through an allowlisted function.
        
        FLUJO SEGURO:
        1. Selector automático elige el tipo correcto (si no se especifica)
        2. El tipo se limita a la allowlist aprobada
        3. Una función determinista valida parámetros y crea la figura
        
        Args:
            data: DataFrame with medical data
            visualization_type: Type of visualization (auto-detected if 'auto')
            requirements: Additional requirements in natural language
            title: Chart title
            max_retries: Conserved for API compatibility; no LLM retries occur
            
        Returns:
            Dict with figure and metadata including execution_time_ms
        """
        start_time = time.perf_counter()
        
        self._total_visualizations += 1
        
        # PASO 1: Preprocesar datos
        logger.info("Preprocessing data before visualization...")
        preprocess_metadata = {}
        
        # Detectar si es visualización temporal
        is_temporal = 'charttime' in data.columns or visualization_type in ['timeline', 'temporal', 'trend', 'comparison']
        
        if is_temporal and 'charttime' in data.columns:
            preprocess_result = self.preprocessor.preprocess_temporal_data(
                data=data,
                time_column='charttime'
            )
            data = preprocess_result.data
            preprocess_metadata = preprocess_result.to_dict()
            logger.info(
                f"Temporal preprocessing: {preprocess_result.rows_processed}/{preprocess_result.rows_original} rows"
            )
        
        # Limpiar valores inválidos
        data = self.preprocessor.clean_invalid_values(data)
        
        # PASO 2: Selección automática de tipo de visualización
        if visualization_type == 'auto' or not visualization_type:
            logger.info("Auto-selecting visualization type based on data characteristics...")
            selected_type, suggested_params = self.selector.select_visualization_type(data)
            visualization_type = self._coerce_auto_selection(data, selected_type)
            logger.info(f"Auto-selected allowlisted type: {visualization_type}")
            
            # Usar título sugerido si no se proporcionó uno
            if not title and 'title' in suggested_params:
                title = suggested_params['title']
        
        # PASO 3: Construir mediante una función parametrizada allowlisted.
        logger.info(f"Attempting allowlisted generation for {visualization_type}...")
        template_result = self._try_template_generation(
            data=data,
            visualization_type=visualization_type,
            title=title or 'Gráfico de Datos Médicos'
        )
        
        if template_result['success']:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self._successful_visualizations += 1
            self._total_execution_time_ms += execution_time_ms
            self._template_usage_count += 1
            
            logger.info(f"✅ Visualization generated using allowlisted function in {execution_time_ms:.2f}ms")
            template_result['preprocess_metadata'] = preprocess_metadata
            template_result['execution_time_ms'] = execution_time_ms
            template_result['method'] = 'allowlisted_function'
            return template_result

        # Fail closed: no LLM fallback and no code-string execution.
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._total_execution_time_ms += execution_time_ms

        error_msg = template_result.get('error', 'Visualización no permitida')
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'figure': None,
            'retry_count': 0,
            'execution_time_ms': execution_time_ms,
            'method': 'rejected'
        }
    
    def generate_multiple_visualizations(
        self,
        data: pd.DataFrame,
        metrics: Optional[List[str]] = None,
        title_prefix: str = "Evolución de",
        include_combined: bool = True
    ) -> Dict[str, Any]:
        """
        Genera múltiples visualizaciones, una por cada métrica.
        
        NUEVO PIPELINE:
        1. Analiza los datos y detecta métricas válidas
        2. Para cada métrica, decide el mejor tipo de visualización
        3. Genera una visualización individual por métrica
        4. Opcionalmente genera una visualización combinada
        
        Args:
            data: DataFrame con datos médicos
            metrics: Lista de métricas a visualizar (None = auto-detectar)
            title_prefix: Prefijo para títulos de gráficos
            include_combined: Si incluir gráfico combinado al final
            
        Returns:
            Dict con lista de figuras y metadata
        """
        start_time = time.perf_counter()
        
        logger.info("="*60)
        logger.info("INICIANDO GENERACIÓN DE MÚLTIPLES VISUALIZACIONES")
        logger.info("="*60)
        
        results = {
            'success': True,
            'figures': [],
            'metrics_processed': [],
            'metrics_excluded': [],
            'visualization_plan': [],
            'errors': [],
            'execution_time_ms': 0
        }
        
        # PASO 1: Preprocesar datos
        logger.info("PASO 1: Preprocesando datos...")
        if 'charttime' in data.columns:
            preprocess_result = self.preprocessor.preprocess_temporal_data(
                data=data,
                time_column='charttime'
            )
            data = preprocess_result.data
            logger.info(f"  → Registros: {preprocess_result.rows_processed}/{preprocess_result.rows_original}")
        
        data = self.preprocessor.clean_invalid_values(data)
        
        # PASO 2: Detectar métricas válidas
        logger.info("PASO 2: Detectando métricas válidas...")
        if metrics is None:
            # Auto-detectar métricas numéricas
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            # Excluir columnas de ID
            metrics = [col for col in numeric_cols if not col.endswith('_id') and col != 'seq_num']
        
        # Validar métricas (excluir las que tienen muchos nulos)
        valid_metrics = []
        for metric in metrics:
            if metric not in data.columns:
                results['metrics_excluded'].append({
                    'metric': metric,
                    'reason': 'Columna no encontrada'
                })
                continue
            
            null_pct = data[metric].isna().sum() / len(data) * 100
            if null_pct > 50:
                results['metrics_excluded'].append({
                    'metric': metric,
                    'reason': f'{null_pct:.1f}% valores nulos'
                })
                logger.info(f"  ⚠️ {metric}: Excluida ({null_pct:.1f}% nulos)")
            else:
                valid_metrics.append(metric)
                logger.info(f"  ✅ {metric}: Válida ({null_pct:.1f}% nulos)")
        
        if not valid_metrics:
            results['success'] = False
            results['errors'].append('No hay métricas válidas para visualizar')
            return results
        
        # PASO 3: Crear plan de visualización
        logger.info("PASO 3: Creando plan de visualización...")
        visualization_plan = self._create_visualization_plan(data, valid_metrics)
        results['visualization_plan'] = visualization_plan
        
        for plan in visualization_plan:
            logger.info(f"  📊 {plan['metric']}: {plan['viz_type']} - {plan['reason']}")
        
        # PASO 4: Generar visualización individual por cada métrica
        logger.info("PASO 4: Generando visualizaciones individuales...")
        for plan in visualization_plan:
            metric = plan['metric']
            viz_type = plan['viz_type']
            
            logger.info(f"  → Generando {viz_type} para {metric}...")
            
            # Preparar datos para esta métrica
            metric_data = self._prepare_metric_data(data, metric)
            
            # Generar título descriptivo
            title = self._generate_metric_title(metric, title_prefix)
            
            # Generar visualización
            viz_result = self._generate_single_metric_visualization(
                data=metric_data,
                metric=metric,
                viz_type=viz_type,
                title=title
            )
            
            if viz_result['success']:
                results['figures'].append({
                    'metric': metric,
                    'figure': viz_result['figure'],
                    'viz_type': viz_result.get('visualization_type', viz_type),
                    'title': title,
                    'reason': plan['reason']
                })
                results['metrics_processed'].append(metric)
                logger.info(f"    ✅ {metric}: Generada exitosamente")
            else:
                results['errors'].append(f"{metric}: {viz_result.get('error', 'Error desconocido')}")
                logger.warning(f"    ❌ {metric}: {viz_result.get('error')}")
        
        # PASO 5: Generar visualización combinada (opcional)
        if include_combined and len(results['metrics_processed']) > 1:
            logger.info("PASO 5: Generando visualización combinada...")
            combined_result = self._generate_combined_visualization(
                data=data,
                metrics=results['metrics_processed'][:5],  # Máximo 5 métricas
                title="Comparación de Signos Vitales"
            )
            
            if combined_result['success']:
                results['figures'].append({
                    'metric': 'combined',
                    'figure': combined_result['figure'],
                    'viz_type': 'comparison',
                    'title': 'Comparación de Signos Vitales',
                    'reason': 'Vista combinada de todas las métricas'
                })
                logger.info("  ✅ Visualización combinada generada")
        
        # Calcular tiempo total
        results['execution_time_ms'] = (time.perf_counter() - start_time) * 1000
        results['success'] = len(results['figures']) > 0
        
        logger.info("="*60)
        logger.info(f"COMPLETADO: {len(results['figures'])} visualizaciones en {results['execution_time_ms']:.0f}ms")
        logger.info("="*60)
        
        return results
    
    def _create_visualization_plan(
        self,
        data: pd.DataFrame,
        metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Crea un plan de visualización decidiendo el mejor tipo para cada métrica.
        
        Args:
            data: DataFrame con datos
            metrics: Lista de métricas a visualizar
            
        Returns:
            Lista de planes con tipo de visualización y razón
        """
        plan = []
        has_temporal = 'charttime' in data.columns
        num_rows = len(data)
        
        for metric in metrics:
            viz_info = self._decide_best_visualization(data, metric, has_temporal, num_rows)
            plan.append({
                'metric': metric,
                'viz_type': viz_info['type'],
                'reason': viz_info['reason']
            })
        
        return plan
    
    def _decide_best_visualization(
        self,
        data: pd.DataFrame,
        metric: str,
        has_temporal: bool,
        num_rows: int
    ) -> Dict[str, str]:
        """
        Decide el mejor tipo de visualización para una métrica específica.
        
        Reglas de decisión:
        1. Si hay datos temporales y >3 puntos → timeline (evolución)
        2. Si hay pocos puntos (<=3) → bar o indicator
        3. Si hay muchos puntos (>20) y no temporal → histogram
        4. Si hay valores categóricos asociados → bar agrupado
        
        Args:
            data: DataFrame con datos
            metric: Nombre de la métrica
            has_temporal: Si hay columna temporal
            num_rows: Número de filas
            
        Returns:
            Dict con tipo y razón
        """
        # Obtener estadísticas de la métrica
        metric_data = data[metric].dropna()
        unique_values = metric_data.nunique()
        
        # REGLA 1: Datos temporales con suficientes puntos → Timeline
        if has_temporal and num_rows >= 3:
            return {
                'type': 'timeline',
                'reason': f'Evolución temporal ({num_rows} mediciones)'
            }
        
        # REGLA 2: Muy pocos puntos → Indicator o Bar
        if num_rows <= 2:
            return {
                'type': 'indicator',
                'reason': f'Valor único/pocos datos ({num_rows} mediciones)'
            }
        
        # REGLA 3: Pocos puntos sin temporal → Bar
        if num_rows <= 5 and not has_temporal:
            return {
                'type': 'bar',
                'reason': f'Comparación de valores ({num_rows} mediciones)'
            }
        
        # REGLA 4: Muchos puntos sin temporal → Histogram
        if num_rows > 10 and not has_temporal:
            return {
                'type': 'histogram',
                'reason': f'Distribución de valores ({num_rows} mediciones)'
            }
        
        # REGLA 5: Pocos valores únicos → Box plot
        if unique_values <= 5:
            return {
                'type': 'box',
                'reason': f'Estadísticas ({unique_values} valores únicos)'
            }
        
        # DEFAULT: Timeline si hay temporal, sino histogram
        if has_temporal:
            return {
                'type': 'timeline',
                'reason': 'Evolución temporal (default)'
            }
        else:
            return {
                'type': 'histogram',
                'reason': 'Distribución de valores (default)'
            }
    
    def _prepare_metric_data(self, data: pd.DataFrame, metric: str) -> pd.DataFrame:
        """
        Prepara los datos para una métrica específica.
        
        Args:
            data: DataFrame completo
            metric: Nombre de la métrica
            
        Returns:
            DataFrame con solo las columnas necesarias
        """
        columns = [metric]
        
        # Incluir columna temporal si existe
        if 'charttime' in data.columns:
            columns.insert(0, 'charttime')
        
        return data[columns].dropna(subset=[metric])
    
    def _generate_metric_title(self, metric: str, prefix: str) -> str:
        """
        Genera un título descriptivo para la métrica.
        
        Args:
            metric: Nombre de la métrica
            prefix: Prefijo del título
            
        Returns:
            Título formateado
        """
        # Mapeo de nombres técnicos a nombres legibles
        metric_names = {
            'heartrate': 'Frecuencia Cardíaca (lpm)',
            'resprate': 'Frecuencia Respiratoria (rpm)',
            'o2sat': 'Saturación de Oxígeno (%)',
            'sbp': 'Presión Arterial Sistólica (mmHg)',
            'dbp': 'Presión Arterial Diastólica (mmHg)',
            'temperature': 'Temperatura (°F)',
            'pain': 'Nivel de Dolor (0-10)',
            'acuity': 'Nivel de Acuidad (1-5)'
        }
        
        metric_label = metric_names.get(metric, metric.replace('_', ' ').title())
        return f"{prefix} {metric_label}"
    
    def _generate_single_metric_visualization(
        self,
        data: pd.DataFrame,
        metric: str,
        viz_type: str,
        title: str
    ) -> Dict[str, Any]:
        """
        Genera una visualización para una sola métrica.
        
        Args:
            data: DataFrame con datos de la métrica
            metric: Nombre de la métrica
            viz_type: Tipo de visualización
            title: Título del gráfico
            
        Returns:
            Dict con figura y metadata
        """
        try:
            viz_type = self._coerce_auto_selection(data, viz_type)
            result = create_allowlisted_visualization(
                visualization_type=viz_type,
                data=data,
                title=title,
                metrics=[metric],
                time_column='charttime' if 'charttime' in data.columns else None,
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_combined_visualization(
        self,
        data: pd.DataFrame,
        metrics: List[str],
        title: str
    ) -> Dict[str, Any]:
        """
        Genera una visualización combinada con múltiples métricas.
        
        Args:
            data: DataFrame con datos
            metrics: Lista de métricas a incluir
            title: Título del gráfico
            
        Returns:
            Dict con figura y metadata
        """
        try:
            result = create_allowlisted_visualization(
                visualization_type='comparison',
                data=data,
                title=title,
                metrics=metrics[:MAX_METRICS],
                time_column='charttime' if 'charttime' in data.columns else None,
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_metric_unit(self, metric: str) -> str:
        """Obtiene la unidad de medida para una métrica."""
        units = {
            'heartrate': 'lpm',
            'resprate': 'rpm',
            'o2sat': '%',
            'sbp': 'mmHg',
            'dbp': 'mmHg',
            'temperature': '°F',
            'pain': '',
            'acuity': ''
        }
        return units.get(metric, '')
    
    def _try_template_generation(
        self,
        data: pd.DataFrame,
        visualization_type: str,
        title: str
    ) -> Dict[str, Any]:
        """
        Generar visualización usando una función allowlisted.
        
        Args:
            data: DataFrame con datos
            visualization_type: Tipo de visualización
            title: Título del gráfico
            
        Returns:
            Dict con resultado de la visualización
        """
        try:
            logger.info(f"Generating allowlisted visualization for {visualization_type}...")

            numeric_columns = [
                column for column in data.select_dtypes(include=['number']).columns
                if not column.endswith('_id') and column != 'seq_num'
            ]
            metrics = numeric_columns[:MAX_METRICS]
            categorical_columns = data.select_dtypes(
                include=['object', 'category', 'string']
            ).columns.tolist()

            result = create_allowlisted_visualization(
                visualization_type=visualization_type,
                data=data,
                title=title,
                metrics=metrics or None,
                time_column='charttime' if 'charttime' in data.columns else None,
                category_column=categorical_columns[0] if categorical_columns else None,
            )
            
            if result['success']:
                logger.info("✅ Allowlisted generation successful")
                return {
                    'success': True,
                    'figure': result['figure'],
                    'visualization_type': result['visualization_type'],
                    'used_template': False,
                    'method': 'allowlisted_function',
                }
            else:
                logger.error(f"Allowlisted generation rejected: {result['error']}")
                return {
                    'success': False,
                    'error': result['error'],
                    'method': 'rejected',
                }
                
        except Exception as e:
            error_msg = f"Error en visualización allowlisted: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


# Convenience function with singleton pattern
def create_visualization_agent() -> VisualizationAgent:
    """
    Create or return the singleton visualization agent instance.
    
    Uses singleton pattern to avoid re-initializing the agent on every call.
    This improves performance by reusing deterministic preprocessing components.
    
    Returns:
        VisualizationAgent singleton instance
    """
    global _visualization_agent_instance
    
    if _visualization_agent_instance is None:
        logger.info("Creating new VisualizationAgent singleton instance")
        _visualization_agent_instance = VisualizationAgent()
    else:
        logger.debug("Reusing existing VisualizationAgent singleton instance")
    
    return _visualization_agent_instance



