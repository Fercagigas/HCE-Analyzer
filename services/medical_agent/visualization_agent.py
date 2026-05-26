"""
Visualization Agent - Generates Python code for medical data visualizations

This agent collaborates with the Claude HCE Agent to create visualizations
by generating and executing Python code using Plotly.

Performance optimizations:
- Singleton pattern for agent instance
- Template caching via VisualizationTemplates
- Execution time tracking
- Optimized preprocessing pipeline
"""

import logging
import time
from typing import Dict, Any, Optional, List
import pandas as pd
from langchain_anthropic import ChatAnthropic

from config.settings import settings
from .code_executor import execute_visualization_code, ImprovedCodeValidator
from .llm_manager import ClaudeLLMManager
from .prompt_manager import PromptManager
from .data_preprocessor import DataPreprocessor
from .visualization_selector import VisualizationSelector
from .visualization_templates import create_visualization_templates

logger = logging.getLogger(__name__)

# Singleton instance for visualization agent
_visualization_agent_instance: Optional['VisualizationAgent'] = None


class VisualizationAgent:
    """
    Agent specialized in generating visualization code for medical data.
    
    This agent receives data and requirements from the clinical agent
    and generates Python code to create appropriate visualizations.
    
    Performance optimizations:
    - Singleton pattern via create_visualization_agent()
    - Template caching for common visualization types
    - Execution time tracking for monitoring
    - Optimized preprocessing pipeline
    """
    
    def __init__(self):
        """Initialize the visualization agent."""
        start_time = time.perf_counter()
        
        logger.info("Initializing Visualization Agent...")
        
        # Store visualization settings for easy access
        self.viz_settings = settings.visualization
        
        # Initialize new components (using singleton for templates)
        self.selector = VisualizationSelector()  # NUEVO: Selector automático
        self.preprocessor = DataPreprocessor()
        self.templates = create_visualization_templates()  # Uses singleton with lazy loading
        self.validator = ImprovedCodeValidator()
        
        # Initialize LLM only for fallback cases (lazy initialization)
        self._llm = None
        self._prompt_manager = None
        
        # Performance tracking
        self._total_visualizations = 0
        self._successful_visualizations = 0
        self._total_execution_time_ms = 0.0
        self._template_usage_count = 0
        self._llm_usage_count = 0
        
        init_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"✅ Visualization Agent initialized with template-first approach "
            f"(LLM lazy-loaded) in {init_time_ms:.2f}ms"
        )
    
    @property
    def llm(self):
        """Lazy initialization of LLM (only when needed)."""
        if self._llm is None:
            logger.info("Lazy-loading Claude Sonnet 4.5 for visualization...")
            self._llm = ChatAnthropic(
                model=self.viz_settings.model_name,
                anthropic_api_key=settings.claude_agent.anthropic_api_key,
                max_tokens=self.viz_settings.max_tokens,
                temperature=self.viz_settings.temperature,
                timeout=self.viz_settings.timeout_seconds
            )
            logger.info(f"Claude Sonnet 4.5 loaded: {self.viz_settings.model_name}")
        return self._llm
    
    @property
    def prompt_manager(self):
        """Lazy initialization of prompt manager (only when needed)."""
        if self._prompt_manager is None:
            logger.info("Lazy-loading prompt manager...")
            self._prompt_manager = PromptManager(
                max_tokens=self.viz_settings.max_tokens,
                anthropic_api_key=settings.claude_agent.anthropic_api_key
            )
        return self._prompt_manager
    
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
            'llm_usage_count': self._llm_usage_count,
            'preprocessor_stats': self.preprocessor.get_performance_stats(),
            'template_cache_stats': self.templates.get_cache_stats()
        }
    
    def _initialize_sonnet_45(self) -> ChatAnthropic:
        """Inicializar Claude Sonnet 4.5 específicamente."""
        logger.info("Initializing Claude Sonnet 4.5 for visualization...")
        
        llm = ChatAnthropic(
            model=self.viz_settings.model_name,
            anthropic_api_key=settings.claude_agent.anthropic_api_key,
            max_tokens=self.viz_settings.max_tokens,
            temperature=self.viz_settings.temperature,
            timeout=self.viz_settings.timeout_seconds
        )
        
        logger.info(f"Claude Sonnet 4.5 initialized: {self.viz_settings.model_name}")
        return llm
    
    def generate_visualization(
        self,
        data: pd.DataFrame,
        visualization_type: str,
        requirements: Optional[str] = None,
        title: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate visualization code and execute it.
        
        NUEVO FLUJO SIMPLIFICADO:
        1. Selector automático elige el tipo correcto (si no se especifica)
        2. Template se carga y personaliza
        3. Se ejecuta el código
        4. LLM solo como último recurso si falla
        
        Args:
            data: DataFrame with medical data
            visualization_type: Type of visualization (auto-detected if 'auto')
            requirements: Additional requirements in natural language
            title: Chart title
            max_retries: Maximum number of retry attempts (default: 2)
            
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
            visualization_type, suggested_params = self.selector.select_visualization_type(data)
            logger.info(f"Auto-selected: {visualization_type}")
            
            # Usar título sugerido si no se proporcionó uno
            if not title and 'title' in suggested_params:
                title = suggested_params['title']
        
        # PASO 3: Intentar con template primero (FLUJO PRINCIPAL)
        logger.info(f"Attempting template-based generation for {visualization_type}...")
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
            
            logger.info(f"✅ Visualization generated using template in {execution_time_ms:.2f}ms")
            template_result['preprocess_metadata'] = preprocess_metadata
            template_result['execution_time_ms'] = execution_time_ms
            template_result['method'] = 'template'
            return template_result
        
        # PASO 4: Si el template falla, intentar con LLM (FALLBACK)
        logger.warning("Template generation failed, falling back to LLM generation...")
        
        retry_count = 0
        last_error = template_result.get('error', 'Template generation failed')
        
        while retry_count < max_retries:
            try:
                logger.info(f"LLM generation attempt {retry_count + 1}/{max_retries}...")
                
                # Crear prompt simplificado
                prompt = self._create_simplified_retry_prompt(
                    data=data,
                    visualization_type=visualization_type,
                    title=title or 'Gráfico de Datos Médicos',
                    previous_error=last_error if retry_count > 0 else None
                )
                
                # Generar código con LLM (lazy-loaded)
                response = self.llm.invoke(prompt)
                code = self._extract_code_from_response(response.content)
                
                if not code:
                    last_error = 'No se pudo generar código de visualización'
                    retry_count += 1
                    continue
                
                logger.debug(f"Generated code:\n{code}")
                
                # Ejecutar código
                result = execute_visualization_code(
                    code=code,
                    data={'data': data}
                )
                
                if result['success']:
                    execution_time_ms = (time.perf_counter() - start_time) * 1000
                    self._successful_visualizations += 1
                    self._total_execution_time_ms += execution_time_ms
                    self._llm_usage_count += 1
                    
                    logger.info(f"✅ Visualization generated using LLM in {execution_time_ms:.2f}ms")
                    return {
                        'success': True,
                        'figure': result['figure'],
                        'code': code,
                        'visualization_type': visualization_type,
                        'retry_count': retry_count,
                        'preprocess_metadata': preprocess_metadata,
                        'execution_time_ms': execution_time_ms,
                        'method': 'llm'
                    }
                else:
                    last_error = result['error']
                    retry_count += 1
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"LLM generation error: {last_error}")
                retry_count += 1
        
        # Todo falló
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._total_execution_time_ms += execution_time_ms
        
        error_msg = f"Error generando visualización después de template y {max_retries} intentos LLM: {last_error}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'figure': None,
            'retry_count': retry_count,
            'execution_time_ms': execution_time_ms,
            'method': 'failed'
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
                    'viz_type': viz_type,
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
            # Obtener template
            template = self.templates.get_template(viz_type)
            
            if not template:
                # Fallback a timeline
                template = self.templates.get_template('timeline')
                viz_type = 'timeline'
            
            # Preparar información
            data_info = {
                'time_column': 'charttime' if 'charttime' in data.columns else data.columns[0],
                'categorical_columns': [],
                'unit': self._get_metric_unit(metric)
            }
            
            # Personalizar template
            customized_code = self.templates.customize_template(
                template=template,
                data_info=data_info,
                title=title,
                metrics=[metric]
            )
            
            # Ejecutar
            result = execute_visualization_code(
                code=customized_code,
                data={'data': data}
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
            # Usar template de comparison
            template = self.templates.get_template('comparison')
            
            if not template:
                return {'success': False, 'error': 'Template comparison no disponible'}
            
            data_info = {
                'time_column': 'charttime' if 'charttime' in data.columns else data.columns[0],
                'categorical_columns': [],
                'unit': ''
            }
            
            customized_code = self.templates.customize_template(
                template=template,
                data_info=data_info,
                title=title,
                metrics=metrics[:2]  # Template comparison usa 2 métricas
            )
            
            result = execute_visualization_code(
                code=customized_code,
                data={'data': data}
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
        Generar visualización usando template (FLUJO PRINCIPAL).
        
        Args:
            data: DataFrame con datos
            visualization_type: Tipo de visualización
            title: Título del gráfico
            
        Returns:
            Dict con resultado de la visualización
        """
        try:
            logger.info(f"Generating visualization using template for {visualization_type}...")
            
            # Obtener template (lazy loading)
            template = self.templates.get_template(visualization_type)
            
            if not template:
                logger.warning(f"No template found for {visualization_type}")
                return {
                    'success': False,
                    'error': f'No hay template disponible para {visualization_type}'
                }
            
            # Preparar información de datos
            data_info = {
                'time_column': 'charttime' if 'charttime' in data.columns else data.columns[0],
                'categorical_columns': data.select_dtypes(include=['object']).columns.tolist(),
                'unit': ''  # Puede ser expandido en el futuro
            }
            
            # Obtener métricas numéricas
            numeric_columns = data.select_dtypes(include=['number']).columns.tolist()
            metrics = numeric_columns[:3] if numeric_columns else []
            
            if not metrics and visualization_type not in ['table', 'pie', 'sunburst']:
                return {
                    'success': False,
                    'error': 'No hay métricas numéricas disponibles para visualización'
                }
            
            # Personalizar template
            customized_code = self.templates.customize_template(
                template=template,
                data_info=data_info,
                title=title,
                metrics=metrics
            )
            
            logger.debug(f"Customized template code:\n{customized_code}")
            
            # Ejecutar código de template
            result = execute_visualization_code(
                code=customized_code,
                data={'data': data}
            )
            
            if result['success']:
                logger.info("✅ Template generation successful")
                return {
                    'success': True,
                    'figure': result['figure'],
                    'code': customized_code,
                    'visualization_type': visualization_type,
                    'used_template': True
                }
            else:
                logger.error(f"Template execution failed: {result['error']}")
                return {
                    'success': False,
                    'error': f"Template execution failed: {result['error']}"
                }
                
        except Exception as e:
            error_msg = f"Error en template generation: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _create_simplified_retry_prompt(
        self,
        data: pd.DataFrame,
        visualization_type: str,
        title: str,
        previous_error: Optional[str]
    ) -> str:
        """
        Crear prompt simplificado para LLM (solo usado como fallback).
        
        Args:
            data: DataFrame con datos
            visualization_type: Tipo de visualización
            title: Título del gráfico
            previous_error: Error del intento anterior
            
        Returns:
            Prompt simplificado
        """
        data_info = self._get_data_info(data)
        
        error_context = f"\nEl intento anterior falló con este error:\n{previous_error}\n" if previous_error else ""
        
        prompt = f"""Genera código Python SIMPLE usando Plotly para crear una visualización de tipo {visualization_type}.

{error_context}
DATOS DISPONIBLES:
{data_info}

TÍTULO: {title}

REGLAS:
1. Los datos están en la variable 'data' (pandas DataFrame)
2. Usa plotly.graph_objects (go)
3. La figura final DEBE estar en la variable 'fig'
4. Usa template='plotly_white'
5. Código SIMPLE y DIRECTO
6. Verifica que las columnas existen

GENERA SOLO EL CÓDIGO PYTHON, sin explicaciones."""
        
        return prompt
    
    def _get_data_info(self, data: pd.DataFrame) -> str:
        """Get formatted information about the DataFrame."""
        info_parts = []
        
        # Shape
        info_parts.append(f"Dimensiones: {data.shape[0]} filas × {data.shape[1]} columnas")
        
        # Columns
        info_parts.append(f"\nColumnas disponibles:")
        for col in data.columns:
            dtype = data[col].dtype
            non_null = data[col].notna().sum()
            info_parts.append(f"  - {col} ({dtype}): {non_null} valores no nulos")
        
        # Sample data
        if len(data) > 0:
            info_parts.append(f"\nPrimeras filas:")
            info_parts.append(data.head(3).to_string())
        
        return '\n'.join(info_parts)
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract Python code from LLM response."""
        # Look for code blocks
        if '```python' in response:
            # Extract code between ```python and ```
            start = response.find('```python') + len('```python')
            end = response.find('```', start)
            if end != -1:
                code = response[start:end].strip()
                return code
        
        elif '```' in response:
            # Extract code between ``` and ```
            start = response.find('```') + len('```')
            end = response.find('```', start)
            if end != -1:
                code = response[start:end].strip()
                return code
        
        # If no code blocks, assume entire response is code
        # (but this is risky, so we'll be cautious)
        if 'import' in response and 'fig' in response:
            return response.strip()
        
        return None


# Convenience function with singleton pattern
def create_visualization_agent() -> VisualizationAgent:
    """
    Create or return the singleton visualization agent instance.
    
    Uses singleton pattern to avoid re-initializing the agent on every call.
    This improves performance by reusing the LLM connection and cached templates.
    
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



