"""
Visualization Collaboration Tool

This tool allows the clinical agent to request visualizations from the visualization agent.

Performance optimizations:
- Singleton pattern for visualization agent
- Execution time tracking
- Lazy loading of components
- Visualization store to avoid passing large base64 images to LLM
"""

import logging
import base64
import io
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import pandas as pd

from .claude_adapter import ClaudeToolAdapter
from ..visualization_agent import create_visualization_agent
from ..services.database_service import DatabaseService
from ..visualization_store import visualization_store

logger = logging.getLogger(__name__)


class VisualizationRequest(BaseModel):
    """Input schema for visualization collaboration tool."""
    visualization_type: str = Field(
        description="""Tipo de visualización. Tipos disponibles:
        
        BÁSICOS (probados):
        - timeline: Línea temporal para signos vitales
        - comparison: Comparación de múltiples métricas
        - distribution: Histograma o gráfico de pastel
        - scatter: Gráfico de dispersión
        
        AVANZADOS (disponibles):
        - heatmap: Mapa de calor para correlaciones
        - box: Box plot para distribuciones
        - violin: Violin plot para distribuciones detalladas
        - 3d_scatter: Gráfico 3D para tres variables
        - surface: Superficie 3D
        - contour: Gráfico de contorno
        
        ESPECIALIZADOS (disponibles):
        - sunburst: Gráfico jerárquico circular
        - treemap: Mapa de árbol jerárquico
        - waterfall: Gráfico de cascada
        - sankey: Diagrama de flujo
        - candlestick: Gráfico de velas
        - indicator: Indicador de métrica clave
        
        También puedes especificar cualquier tipo de Plotly en lenguaje natural."""
    )
    stay_id: Optional[int] = Field(None, description="ID de estancia para obtener datos")
    subject_id: Optional[int] = Field(None, description="ID de paciente para obtener datos")
    metrics: Optional[List[str]] = Field(
        None,
        description="Métricas a visualizar (ej: ['temperature', 'heartrate', 'resprate'])"
    )
    data_source: str = Field(
        default="vitalsign",
        description="Tabla fuente de datos: vitalsign, diagnosis, medrecon, pyxis"
    )
    title: Optional[str] = Field(None, description="Título del gráfico")
    requirements: Optional[str] = Field(
        None,
        description="Requisitos adicionales en lenguaje natural"
    )


class VisualizationCollaborationTool(ClaudeToolAdapter):
    """
    Tool for requesting visualizations from the visualization agent.
    
    This tool acts as a bridge between the clinical agent and the visualization agent.
    """
    
    def __init__(self):
        """Initialize the visualization collaboration tool."""
        start_time = time.perf_counter()
        
        # Initialize database service
        self.db_service = DatabaseService()
        
        # Initialize visualization agent (lazy loading with singleton)
        self._viz_agent = None
        
        # Initialize preprocessor for automatic data preprocessing
        from ..data_preprocessor import DataPreprocessor
        self.preprocessor = DataPreprocessor()
        
        # Performance tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._total_execution_time_ms = 0.0
        
        init_time_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"VisualizationCollaborationTool base init in {init_time_ms:.2f}ms")
        
        # Initialize the adapter
        super().__init__(
            tool_name="request_visualization",
            tool_description="""Solicita la creación de una visualización al agente de visualización.

El sistema usa GENERACIÓN DINÁMICA DE CÓDIGO para crear visualizaciones personalizadas.
Puedes solicitar CUALQUIER tipo de visualización de Plotly en lenguaje natural.

TIPOS DE VISUALIZACIÓN DISPONIBLES:

BÁSICOS (probados):
1. timeline: Línea temporal para signos vitales a lo largo del tiempo
2. comparison: Comparación de múltiples métricas (barras, líneas)
3. distribution: Distribución de diagnósticos o medicamentos (histograma, pie)
4. scatter: Gráfico de dispersión para correlaciones

AVANZADOS (disponibles):
5. heatmap: Mapa de calor para matriz de correlación
6. box: Box plot para distribuciones con cuartiles
7. violin: Violin plot para distribuciones detalladas
8. 3d_scatter: Gráfico 3D para tres variables simultáneas
9. surface: Superficie 3D para funciones de dos variables
10. contour: Gráfico de contorno con isolíneas

ESPECIALIZADOS (disponibles):
11. sunburst: Gráfico jerárquico circular
12. treemap: Mapa de árbol jerárquico
13. waterfall: Gráfico de cascada para cambios acumulativos
14. sankey: Diagrama de flujo entre categorías
15. candlestick: Gráfico de velas para rangos de valores
16. indicator: Indicador de métrica clave (KPI)

FUENTES DE DATOS:
- vitalsign: Signos vitales (temperatura, frecuencia cardíaca, presión arterial, etc.)
- diagnosis: Diagnósticos médicos
- medrecon: Reconciliación de medicamentos
- pyxis: Dispensación de medicamentos

MÉTRICAS DISPONIBLES (para vitalsign):
- temperature: Temperatura corporal
- heartrate: Frecuencia cardíaca
- resprate: Frecuencia respiratoria
- o2sat: Saturación de oxígeno
- sbp: Presión arterial sistólica
- dbp: Presión arterial diastólica

EJEMPLOS BÁSICOS:
1. Línea temporal de un paciente:
   {"visualization_type": "timeline", "stay_id": 37887480, "metrics": ["temperature", "heartrate"], "data_source": "vitalsign"}

2. Comparación de métricas de un paciente:
   {"visualization_type": "comparison", "stay_id": 37887480, "metrics": ["sbp", "dbp"], "data_source": "vitalsign"}

3. Top-N diagnósticos más frecuentes en TODO el dataset (SIN subject_id):
   {"visualization_type": "bar", "data_source": "diagnosis", "title": "10 Diagnósticos Más Frecuentes en Urgencias"}

4. Medicamentos más administrados en TODO el dataset (SIN subject_id):
   {"visualization_type": "bar", "data_source": "pyxis", "title": "Medicamentos Más Administrados en Urgencias"}

5. Distribución de disposiciones en TODO el dataset (SIN subject_id):
   {"visualization_type": "bar", "data_source": "edstays", "title": "Distribución de Disposiciones"}

IMPORTANTE:
- Para datos de UN PACIENTE específico: proporciona stay_id o subject_id
- Para estadísticas de TODO el dataset (top-N, frecuencias globales): NO incluyas subject_id ni stay_id
- El sistema puede generar CUALQUIER visualización de Plotly
- Usa "requirements" para especificar detalles adicionales en lenguaje natural""",
            args_schema=VisualizationRequest
        )
        
        logger.info("VisualizationCollaborationTool initialized")
    
    @property
    def viz_agent(self):
        """Lazy load visualization agent (uses singleton)."""
        if self._viz_agent is None:
            logger.debug("Lazy loading visualization agent singleton")
            self._viz_agent = create_visualization_agent()
        return self._viz_agent
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        avg_time = (
            self._total_execution_time_ms / self._total_requests
            if self._total_requests > 0 else 0
        )
        success_rate = (
            self._successful_requests / self._total_requests * 100
            if self._total_requests > 0 else 0
        )
        
        stats = {
            'total_requests': self._total_requests,
            'successful_requests': self._successful_requests,
            'success_rate_percent': success_rate,
            'total_execution_time_ms': self._total_execution_time_ms,
            'average_execution_time_ms': avg_time,
            'preprocessor_stats': self.preprocessor.get_performance_stats()
        }
        
        # Include viz agent stats if initialized
        if self._viz_agent is not None:
            stats['viz_agent_stats'] = self._viz_agent.get_performance_stats()
        
        return stats
    
    def execute(
        self,
        visualization_type: str,
        stay_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        metrics: Optional[List[str]] = None,
        data_source: str = "vitalsign",
        title: Optional[str] = None,
        requirements: Optional[str] = None
    ) -> str:
        """
        Request visualization from visualization agent.
        
        Performance optimizations:
        - Execution time tracking
        - Singleton visualization agent
        - Optimized preprocessing
        
        Args:
            visualization_type: Type of visualization
            stay_id: Stay identifier
            subject_id: Patient identifier
            metrics: Metrics to visualize
            data_source: Data source table
            title: Chart title
            requirements: Additional requirements
            
        Returns:
            Base64 encoded image or error message with metadata
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        
        try:
            # Validate inputs — subject_id/stay_id are optional for aggregate queries
            # (e.g. "top 10 diagnoses across all patients")
            is_aggregate = not stay_id and not subject_id

            # Fetch data from database
            logger.info(f"Fetching data from {data_source} (aggregate={is_aggregate})...")
            try:
                data = self._fetch_data(
                    data_source=data_source,
                    stay_id=stay_id,
                    subject_id=subject_id,
                    metrics=metrics
                )
            except ValueError as e:
                # Invalid data source or parameters
                return self._format_error_response(
                    "Error de validación",
                    str(e)
                )
            except ConnectionError as e:
                # Database connection error
                return self._format_error_response(
                    "Error de conexión a la base de datos",
                    "No se pudo conectar a la base de datos. Por favor, intente nuevamente."
                )
            except RuntimeError as e:
                # Unexpected error during data fetch
                return self._format_error_response(
                    "Error al obtener datos",
                    str(e)
                )
            
            # Handle empty DataFrame case
            if data is None or len(data) == 0:
                return self._format_empty_data_response(data_source, stay_id, subject_id)
            
            logger.info(f"Data fetched: {len(data)} rows")
            
            # Preprocess data automatically after fetching
            preprocess_metadata = {}
            if metrics and data_source == 'vitalsign':
                # Validate metrics before generating visualization
                validation_result = self.preprocessor.validate_metrics(data, metrics)
                
                if not validation_result.has_valid_metrics:
                    # No valid metrics available
                    return self._format_no_valid_metrics_response(
                        validation_result,
                        data
                    )
                
                # Update metrics to only valid ones
                if len(validation_result.excluded_metrics) > 0:
                    logger.info(
                        f"Excluded {len(validation_result.excluded_metrics)} metrics: "
                        f"{validation_result.excluded_metrics}"
                    )
                    metrics = validation_result.valid_metrics
                
                preprocess_metadata['metrics_validation'] = {
                    'requested': metrics + validation_result.excluded_metrics,
                    'valid': validation_result.valid_metrics,
                    'excluded': validation_result.excluded_metrics,
                    'null_percentages': validation_result.null_percentages,
                    'warnings': validation_result.warnings
                }
            
            # Request visualization from visualization agent
            try:
                # NUEVO: Decidir si generar múltiples visualizaciones o una sola
                # Si hay múltiples métricas de signos vitales, generar una por cada una
                should_generate_multiple = (
                    data_source == 'vitalsign' and 
                    metrics and 
                    len(metrics) > 1 and
                    visualization_type in ['timeline', 'auto', 'comparison']
                )
                
                if should_generate_multiple:
                    logger.info(f"Generating multiple visualizations for {len(metrics)} metrics...")
                    result = self.viz_agent.generate_multiple_visualizations(
                        data=data,
                        metrics=metrics,
                        title_prefix="Evolución de",
                        include_combined=True
                    )
                    
                    if result['success'] and result['figures']:
                        execution_time_ms = (time.perf_counter() - start_time) * 1000
                        self._successful_requests += 1
                        self._total_execution_time_ms += execution_time_ms
                        
                        response_parts = []
                        
                        # Agregar información del plan de visualización
                        if result.get('visualization_plan'):
                            response_parts.append("📊 **Plan de Visualización:**\n")
                            for plan in result['visualization_plan']:
                                response_parts.append(
                                    f"  • {plan['metric']}: {plan['viz_type']} - {plan['reason']}"
                                )
                            response_parts.append("")
                        
                        # Store figures in visualization store instead of returning base64
                        stored_viz_ids = []
                        for i, fig_info in enumerate(result['figures']):
                            metric_name = fig_info.get('metric', f'Gráfico {i+1}')
                            viz_type = fig_info.get('viz_type', 'unknown')
                            title = fig_info.get('title', metric_name)
                            
                            # Store the figure (will convert to base64 when retrieved by UI)
                            viz_id = visualization_store.store(
                                figure=fig_info['figure'],
                                title=title,
                                metric=metric_name,
                                viz_type=viz_type,
                                metadata={'data_source': data_source, 'stay_id': stay_id, 'subject_id': subject_id}
                            )
                            stored_viz_ids.append(viz_id)
                            response_parts.append(f"  ✅ {title} (ID: {viz_id})")
                        
                        # Add visualization IDs marker for UI to detect
                        response_parts.append(f"\n[VISUALIZATION_IDS:{','.join(stored_viz_ids)}]")
                        
                        # Agregar métricas excluidas si las hay
                        if result.get('metrics_excluded'):
                            response_parts.append("\n⚠️ **Métricas excluidas:**")
                            for excluded in result['metrics_excluded']:
                                response_parts.append(
                                    f"  • {excluded['metric']}: {excluded['reason']}"
                                )
                        
                        # Agregar metadata de preprocesamiento
                        if preprocess_metadata:
                            response_parts.append(self._format_metadata_message(preprocess_metadata))
                        
                        response_parts.append(f"\n⏱️ Tiempo total: {execution_time_ms:.0f}ms")
                        response_parts.append(f"📊 Visualizaciones generadas: {len(result['figures'])}")
                        
                        return '\n'.join(response_parts)
                    else:
                        # Si falla múltiples, intentar con una sola
                        logger.warning("Multiple visualization failed, falling back to single...")
                
                # Generar visualización única (comportamiento original)
                result = self.viz_agent.generate_visualization(
                    data=data,
                    visualization_type=visualization_type,
                    requirements=requirements,
                    title=title
                )
            except Exception as viz_error:
                # Catch visualization generation errors and continue flow
                logger.error(f"Visualization generation exception: {viz_error}", exc_info=True)
                return self._format_error_response(
                    "Error al generar la visualización",
                    f"Ocurrió un error durante la generación: {str(viz_error)}"
                )
            
            if not result['success']:
                error_msg = f"Error generando visualización: {result.get('error', 'Error desconocido')}"
                logger.error(error_msg)
                # Continue flow by returning formatted error instead of raising
                return self._format_error_response(
                    "No se pudo generar la visualización",
                    result.get('error', 'Error desconocido')
                )
            
            # Store figure in visualization store instead of returning base64 directly
            # This prevents the "prompt too long" error
            figure = result['figure']
            
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self._successful_requests += 1
            self._total_execution_time_ms += execution_time_ms
            
            logger.info(f"✅ Visualization generated successfully in {execution_time_ms:.2f}ms")
            
            # Store the figure in visualization store
            viz_id = visualization_store.store(
                figure=figure,
                title=title or f"Visualización {visualization_type}",
                metric=metrics[0] if metrics else visualization_type,
                viz_type=visualization_type,
                metadata={'data_source': data_source, 'stay_id': stay_id, 'subject_id': subject_id}
            )
            
            # Build response with visualization ID marker
            response_parts = []
            response_parts.append(f"✅ Visualización generada exitosamente (ID: {viz_id})")
            
            # Add visualization IDs marker for UI to detect
            response_parts.append(f"\n[VISUALIZATION_IDS:{viz_id}]")
            
            # Add preprocessing metadata if available
            if preprocess_metadata:
                response_parts.append(self._format_metadata_message(preprocess_metadata))
            
            # Add visualization metadata from result
            if 'preprocess_metadata' in result and result['preprocess_metadata']:
                response_parts.append(
                    self._format_preprocess_metadata(result['preprocess_metadata'])
                )
            
            # Add performance info
            response_parts.append(f"\n⏱️ Tiempo de ejecución: {execution_time_ms:.0f}ms")
            
            return '\n\n'.join(response_parts)
                
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self._total_execution_time_ms += execution_time_ms
            
            error_msg = f"Error en colaboración de visualización: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._format_error_response(error_msg, str(e))
    
    def _fetch_data(
        self,
        data_source: str,
        stay_id: Optional[int],
        subject_id: Optional[int],
        metrics: Optional[List[str]]
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data from database with improved error handling.
        
        Args:
            data_source: Data source table
            stay_id: Stay identifier
            subject_id: Patient identifier
            metrics: Metrics to fetch
            
        Returns:
            DataFrame with data or None if error
            
        Raises:
            ValueError: If data_source is invalid
            ConnectionError: If database connection fails
        """
        try:
            # Validate data source
            valid_sources = ['vitalsign', 'diagnosis', 'medrecon', 'pyxis', 'triage', 'edstays']
            if data_source not in valid_sources:
                logger.error(f"Invalid data source: {data_source}")
                raise ValueError(
                    f"Fuente de datos inválida: '{data_source}'. "
                    f"Fuentes válidas: {', '.join(valid_sources)}"
                )
            
            # Build filter
            filters = {}
            if stay_id:
                filters['stay_id'] = stay_id
            if subject_id:
                filters['subject_id'] = subject_id

            # --- Aggregate queries (no patient filter) ---
            # For aggregate visualizations (e.g. top-N diagnoses across all patients)
            # we build a pre-aggregated DataFrame directly instead of fetching raw rows.
            if not filters:
                logger.info(f"No patient filter — building aggregate DataFrame for {data_source}")
                return self._fetch_aggregate_data(data_source, metrics)
            
            # Fetch data
            logger.info(f"Fetching from {data_source} with filters: {filters}")
            data = self.db_service.get_table_data(data_source, filters)
            
            if data is None or len(data) == 0:
                logger.warning(f"No data found in {data_source} for filters: {filters}")
                return None
            
            logger.info(f"Fetched {len(data)} rows from {data_source}")
            
            # Filter metrics if specified
            if metrics and data_source == 'vitalsign':
                # Keep only specified metrics plus identifiers and time
                keep_cols = ['subject_id', 'stay_id', 'charttime'] + metrics
                available_cols = [col for col in keep_cols if col in data.columns]
                
                # Log missing columns
                missing_cols = [col for col in keep_cols if col not in data.columns]
                if missing_cols:
                    logger.warning(f"Requested columns not found: {missing_cols}")
                
                data = data[available_cols]
                logger.info(f"Filtered to {len(available_cols)} columns")
            
            return data
            
        except ValueError as e:
            # Re-raise validation errors
            logger.error(f"Validation error: {e}")
            raise
        except ConnectionError as e:
            # Database connection errors
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise ConnectionError(f"Error de conexión a la base de datos: {str(e)}")
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error fetching data: {e}", exc_info=True)
            raise RuntimeError(f"Error inesperado al obtener datos: {str(e)}")

    def _fetch_aggregate_data(
        self,
        data_source: str,
        metrics: Optional[List[str]],
        top_n: int = 10,
    ) -> Optional[pd.DataFrame]:
        """
        Build a pre-aggregated DataFrame for dataset-wide visualizations.

        Returns a DataFrame with two columns ready for a bar chart:
          - 'categoria': the label (icd_title, name, disposition, …)
          - 'frecuencia': the count

        Args:
            data_source: Table name ('diagnosis', 'pyxis', 'medrecon', 'edstays', …)
            metrics: Ignored for aggregate queries (kept for API consistency)
            top_n: How many top rows to return (default 10)

        Returns:
            DataFrame with columns ['categoria', 'frecuencia'] or None on error
        """
        try:
            if data_source == 'diagnosis':
                raw = self.db_service.get_table_data('diagnosis', {})
                if raw is None or len(raw) == 0:
                    return None
                agg = (
                    raw.groupby('icd_title')
                    .size()
                    .reset_index(name='frecuencia')
                    .sort_values('frecuencia', ascending=False)
                    .head(top_n)
                    .rename(columns={'icd_title': 'categoria'})
                )
                return agg

            elif data_source == 'pyxis':
                raw = self.db_service.get_table_data('pyxis', {})
                if raw is None or len(raw) == 0:
                    return None
                agg = (
                    raw.groupby('name')
                    .size()
                    .reset_index(name='frecuencia')
                    .sort_values('frecuencia', ascending=False)
                    .head(top_n)
                    .rename(columns={'name': 'categoria'})
                )
                return agg

            elif data_source == 'medrecon':
                raw = self.db_service.get_table_data('medrecon', {})
                if raw is None or len(raw) == 0:
                    return None
                agg = (
                    raw.groupby('name')
                    .size()
                    .reset_index(name='frecuencia')
                    .sort_values('frecuencia', ascending=False)
                    .head(top_n)
                    .rename(columns={'name': 'categoria'})
                )
                return agg

            elif data_source == 'edstays':
                raw = self.db_service.get_table_data('edstays', {})
                if raw is None or len(raw) == 0:
                    return None
                group_col = 'disposition'
                agg = (
                    raw.groupby(group_col)
                    .size()
                    .reset_index(name='frecuencia')
                    .sort_values('frecuencia', ascending=False)
                    .head(top_n)
                    .rename(columns={group_col: 'categoria'})
                )
                return agg

            else:
                # For other sources just return raw data (no aggregation)
                return self.db_service.get_table_data(data_source, {})

        except Exception as e:
            logger.error(f"Error building aggregate data for {data_source}: {e}")
            return None
    
    def _figure_to_base64(self, figure) -> Optional[str]:
        """Convert Plotly figure to base64 encoded PNG."""
        try:
            # Convert figure to image bytes
            img_bytes = figure.to_image(format='png', width=1200, height=600)
            
            # Encode to base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            return img_base64
            
        except Exception as e:
            logger.error(f"Error converting figure to base64: {e}")
            return None
    
    def _format_empty_data_response(
        self,
        data_source: str,
        stay_id: Optional[int],
        subject_id: Optional[int]
    ) -> str:
        """
        Format response for empty data case.
        
        Args:
            data_source: Data source table
            stay_id: Stay identifier
            subject_id: Patient identifier
            
        Returns:
            Formatted error message
        """
        identifier = f"stay_id={stay_id}" if stay_id else f"subject_id={subject_id}"
        return (
            f"❌ **No se encontraron datos**\n\n"
            f"No hay datos disponibles en la tabla '{data_source}' para {identifier}.\n\n"
            f"**Sugerencias:**\n"
            f"- Verifica que el identificador sea correcto\n"
            f"- Intenta con otra tabla de datos (vitalsign, diagnosis, medrecon, pyxis)\n"
            f"- Consulta primero los datos disponibles para este paciente"
        )
    
    def _format_no_valid_metrics_response(
        self,
        validation_result,
        data: pd.DataFrame
    ) -> str:
        """
        Format response when no valid metrics are available.
        
        Args:
            validation_result: MetricsValidation result
            data: Original DataFrame
            
        Returns:
            Formatted error message with available metrics
        """
        # Get available numeric columns
        available_metrics = data.select_dtypes(include=['number']).columns.tolist()
        # Remove identifiers
        available_metrics = [m for m in available_metrics if m not in ['subject_id', 'stay_id']]
        
        message_parts = [
            "❌ **No hay métricas válidas disponibles**\n",
            f"Las métricas solicitadas tienen demasiados valores nulos (>50%).\n"
        ]
        
        if validation_result.excluded_metrics:
            message_parts.append("\n**Métricas excluidas:**")
            for metric in validation_result.excluded_metrics:
                null_pct = validation_result.null_percentages.get(metric, 0) * 100
                message_parts.append(f"- {metric}: {null_pct:.1f}% valores nulos")
        
        if available_metrics:
            message_parts.append("\n**Métricas disponibles:**")
            for metric in available_metrics:
                null_count = data[metric].isna().sum()
                total_count = len(data)
                null_pct = (null_count / total_count * 100) if total_count > 0 else 0
                message_parts.append(f"- {metric}: {null_pct:.1f}% valores nulos")
        
        return '\n'.join(message_parts)
    
    def _format_error_response(
        self,
        error_msg: str,
        error_detail: Optional[str]
    ) -> str:
        """
        Format error response with details.
        
        Args:
            error_msg: Main error message
            error_detail: Detailed error information
            
        Returns:
            Formatted error message
        """
        message_parts = [
            f"❌ **Error en visualización**\n",
            f"{error_msg}\n"
        ]
        
        if error_detail and error_detail != error_msg:
            message_parts.append(f"\n**Detalles del error:**\n{error_detail}")
        
        message_parts.append(
            "\n**Sugerencias:**\n"
            "- Verifica que los datos sean correctos\n"
            "- Intenta con un tipo de visualización diferente\n"
            "- Simplifica los requisitos de la visualización"
        )
        
        return '\n'.join(message_parts)
    
    def _format_metadata_message(self, metadata: Dict[str, Any]) -> str:
        """
        Format metadata message for response.
        
        Includes:
        - Métricas disponibles vs solicitadas
        - Métricas excluidas y razones
        - Porcentajes de valores nulos
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Formatted metadata message
        """
        message_parts = ["\n📊 **Información de procesamiento:**\n"]
        
        if 'metrics_validation' in metadata:
            mv = metadata['metrics_validation']
            
            # Show requested vs available metrics
            if mv.get('requested') and mv.get('valid'):
                requested_count = len(mv['requested'])
                valid_count = len(mv['valid'])
                message_parts.append(
                    f"📋 Métricas solicitadas: {requested_count}, disponibles: {valid_count}"
                )
            
            # Show excluded metrics with reasons
            if mv.get('excluded'):
                message_parts.append(
                    f"\n⚠️ **Métricas excluidas ({len(mv['excluded'])}):**"
                )
                for metric in mv['excluded']:
                    null_pct = mv.get('null_percentages', {}).get(metric, 0) * 100
                    message_parts.append(
                        f"   - {metric}: {null_pct:.1f}% valores nulos (umbral: 50%)"
                    )
            
            # Show valid metrics with quality info
            if mv.get('valid'):
                message_parts.append(
                    f"\n✅ **Métricas incluidas ({len(mv['valid'])}):**"
                )
                for metric in mv['valid']:
                    null_pct = mv.get('null_percentages', {}).get(metric, 0) * 100
                    message_parts.append(
                        f"   - {metric}: {null_pct:.1f}% valores nulos"
                    )
            
            # Show warnings if any
            if mv.get('warnings'):
                message_parts.append("\n⚠️ **Advertencias:**")
                for warning in mv['warnings']:
                    message_parts.append(f"   - {warning}")
        
        return '\n'.join(message_parts)
    
    def _format_preprocess_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Format preprocessing metadata from visualization agent.
        
        Includes:
        - Registros procesados vs originales
        - Registros excluidos y razones (duplicados, outliers)
        - Advertencias del preprocesamiento
        
        Args:
            metadata: Preprocessing metadata
            
        Returns:
            Formatted metadata message
        """
        message_parts = []
        
        # Always show processing summary if we have the data
        if 'rows_original' in metadata and 'rows_processed' in metadata:
            rows_original = metadata['rows_original']
            rows_processed = metadata['rows_processed']
            rows_removed = metadata.get('rows_removed', 0)
            
            message_parts.append(
                f"\n🔧 **Preprocesamiento de datos:**"
            )
            message_parts.append(
                f"   Registros originales: {rows_original}"
            )
            message_parts.append(
                f"   Registros procesados: {rows_processed}"
            )
            
            if rows_removed > 0:
                message_parts.append(
                    f"   Registros excluidos: {rows_removed}"
                )
                
                # Breakdown of exclusions
                exclusion_reasons = []
                
                if metadata.get('duplicates_removed', 0) > 0:
                    exclusion_reasons.append(
                        f"      • {metadata['duplicates_removed']} duplicados temporales"
                    )
                
                if exclusion_reasons:
                    message_parts.append("\n   **Razones de exclusión:**")
                    message_parts.extend(exclusion_reasons)
        
        # Show outliers information
        if metadata.get('outliers_detected', 0) > 0:
            message_parts.append(
                f"\n⚠️ **Outliers detectados:** {metadata['outliers_detected']}"
            )
            message_parts.append(
                "   (Los outliers están marcados en la gráfica pero no se eliminan)"
            )
        
        # Show excluded metrics
        if metadata.get('metrics_excluded'):
            message_parts.append(
                f"\n⚠️ **Métricas excluidas:** {', '.join(metadata['metrics_excluded'])}"
            )
        
        # Show temporal gaps information
        if metadata.get('has_large_gaps'):
            message_parts.append(
                "\n📅 **Gaps temporales detectados:** >24 horas entre mediciones"
            )
            message_parts.append(
                "   (Se usa visualización con marcadores para mayor claridad)"
            )
        
        # Show warnings
        if metadata.get('warnings'):
            message_parts.append("\n⚠️ **Advertencias del preprocesamiento:**")
            for warning in metadata['warnings']:
                message_parts.append(f"   - {warning}")
        
        return '\n'.join(message_parts) if message_parts else ""
    
    def format_output(self, output_data: Any) -> str:
        """Format output for Claude."""
        return str(output_data)


# Convenience function
def create_visualization_collaboration_tool() -> VisualizationCollaborationTool:
    """Create a visualization collaboration tool instance."""
    return VisualizationCollaborationTool()
