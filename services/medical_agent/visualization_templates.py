"""
Visualization Templates for Medical Data

This module provides pre-defined code templates for common visualization types,
improving consistency and speed of generation while reducing LLM calls.

Performance optimizations:
- LRU cache for template retrieval
- Singleton pattern for template manager
- Pre-compiled templates at initialization
"""

import logging
import time
from typing import Dict, Any, Optional, List
from functools import lru_cache
import pandas as pd

logger = logging.getLogger(__name__)

# Singleton instance for template manager
_template_manager_instance: Optional['VisualizationTemplates'] = None


class VisualizationTemplates:
    """
    Gestiona plantillas de código para visualizaciones comunes.
    
    Responsabilidades:
    - Proporcionar plantillas predefinidas para tipos comunes
    - Personalizar plantillas con parámetros específicos
    - Validar plantillas con datos de prueba
    - Cachear plantillas para acceso rápido
    
    Performance optimizations:
    - Lazy loading: Templates are loaded only when needed
    - LRU cache for loaded templates
    - Singleton pattern via create_visualization_templates()
    """
    
    # Mapeo de tipos a métodos de creación (sin cargar los templates)
    TEMPLATE_CREATORS = {
        'timeline': '_create_timeline_template',
        'comparison': '_create_comparison_template',
        'bar': '_create_bar_template',
        'scatter': '_create_scatter_template',
        'histogram': '_create_histogram_template',
        'box': '_create_box_template',
        'violin': '_create_violin_template',
        'heatmap': '_create_heatmap_template',
        'pie': '_create_pie_template',
        'sunburst': '_create_sunburst_template',
        'table': '_create_table_template',
        'indicator': '_create_indicator_template',
    }
    
    def __init__(self):
        """Inicializar el gestor de plantillas con lazy loading."""
        start_time = time.perf_counter()
        
        # Cache para templates ya cargados (lazy loading)
        self._template_cache: Dict[str, str] = {}
        self._customization_cache: Dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Alias para compatibilidad
        self.TEMPLATE_CREATORS['distribution'] = '_create_histogram_template'
        
        init_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"VisualizationTemplates initialized with {len(self.TEMPLATE_CREATORS)} available templates "
            f"(lazy loading enabled) in {init_time_ms:.2f}ms"
        )
    
    def get_template(self, visualization_type: str) -> Optional[str]:
        """
        Obtener plantilla de código para tipo de visualización.
        
        Uses lazy loading: templates are only created when first requested.
        
        Args:
            visualization_type: Tipo de visualización
            
        Returns:
            Código de plantilla o None si no existe
        """
        # Normalizar el tipo (lowercase, sin espacios)
        normalized_type = visualization_type.lower().strip().replace(' ', '_')
        
        # Verificar si ya está en cache
        if normalized_type in self._template_cache:
            self._cache_hits += 1
            logger.debug(f"Template cache HIT for type: {visualization_type}")
            return self._template_cache[normalized_type]
        
        # Si no está en cache, intentar cargarlo (lazy loading)
        if normalized_type in self.TEMPLATE_CREATORS:
            self._cache_misses += 1
            logger.debug(f"Template cache MISS for type: {visualization_type}, loading now...")
            
            # Obtener el método creador
            creator_method_name = self.TEMPLATE_CREATORS[normalized_type]
            creator_method = getattr(self, creator_method_name)
            
            # Crear y cachear el template
            template = creator_method()
            self._template_cache[normalized_type] = template
            
            logger.debug(f"Template loaded and cached for type: {visualization_type}")
            return template
        
        # Template no existe
        self._cache_misses += 1
        logger.warning(f"Template not found for type: {visualization_type}")
        return None
    
    def get_available_types(self) -> List[str]:
        """
        Obtener lista de tipos de visualización disponibles.
        
        Returns:
            Lista de tipos disponibles (sin cargar los templates)
        """
        return list(self.TEMPLATE_CREATORS.keys())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dict with cache hit/miss statistics
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'total_requests': total,
            'hit_rate_percent': hit_rate,
            'templates_loaded': len(self._template_cache),
            'templates_available': len(self.TEMPLATE_CREATORS),
            'customization_cache_size': len(self._customization_cache)
        }
    
    def customize_template(
        self,
        template: str,
        data_info: Dict[str, Any],
        title: str,
        metrics: List[str]
    ) -> str:
        """
        Personalizar plantilla con parámetros específicos.
        
        Uses caching for repeated customizations with same parameters.
        
        Args:
            template: Código de plantilla base
            data_info: Información sobre los datos (columnas, tipos, etc.)
            title: Título del gráfico
            metrics: Métricas a visualizar
            
        Returns:
            Código personalizado listo para ejecutar
        """
        start_time = time.perf_counter()
        
        # Create cache key from parameters
        cache_key = self._create_customization_cache_key(
            template[:100],  # Use first 100 chars of template as part of key
            data_info.get('time_column', 'charttime'),
            title,
            tuple(metrics) if metrics else ()
        )
        
        # Check customization cache
        if cache_key in self._customization_cache:
            logger.debug(f"Customization cache HIT for title='{title}'")
            return self._customization_cache[cache_key]
        
        logger.debug(f"Customizing template with title='{title}', metrics={metrics}")
        
        # Reemplazar placeholders básicos
        customized = template
        
        # Reemplazar título
        customized = customized.replace('{{TITLE}}', title)
        
        # Reemplazar columna temporal si existe
        time_column = data_info.get('time_column', 'charttime')
        customized = customized.replace('{{TIME_COLUMN}}', time_column)
        
        # Reemplazar métricas
        if metrics and len(metrics) > 0:
            # Primera métrica
            customized = customized.replace('{{METRIC_1}}', metrics[0])
            customized = customized.replace('{{METRIC_1_LABEL}}', metrics[0].replace('_', ' ').title())
            
            # Segunda métrica si existe
            if len(metrics) > 1:
                customized = customized.replace('{{METRIC_2}}', metrics[1])
                customized = customized.replace('{{METRIC_2_LABEL}}', metrics[1].replace('_', ' ').title())
            
            # Tercera métrica si existe
            if len(metrics) > 2:
                customized = customized.replace('{{METRIC_3}}', metrics[2])
                customized = customized.replace('{{METRIC_3_LABEL}}', metrics[2].replace('_', ' ').title())
        
        # Reemplazar columnas categóricas si existen
        categorical_columns = data_info.get('categorical_columns', [])
        if categorical_columns:
            customized = customized.replace('{{CATEGORY_COLUMN}}', categorical_columns[0])
        
        # Reemplazar unidades si existen
        unit = data_info.get('unit', '')
        customized = customized.replace('{{UNIT}}', unit)
        
        # Cache the customized template (limit cache size to 100 entries)
        if len(self._customization_cache) < 100:
            self._customization_cache[cache_key] = customized
        
        customization_time_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Template customization complete in {customization_time_ms:.2f}ms")
        
        return customized
    
    def _create_customization_cache_key(
        self,
        template_prefix: str,
        time_column: str,
        title: str,
        metrics: tuple
    ) -> str:
        """Create a cache key for customization caching."""
        return f"{hash(template_prefix)}:{time_column}:{title}:{metrics}"
    
    def clear_customization_cache(self) -> None:
        """Clear the customization cache."""
        self._customization_cache.clear()
        logger.debug("Customization cache cleared")
    
    def validate_template(
        self,
        template: str,
        test_data: List[pd.DataFrame]
    ) -> bool:
        """
        Validar que plantilla funciona con datos de prueba.
        
        Args:
            template: Código de plantilla
            test_data: Lista de DataFrames de prueba
            
        Returns:
            True si funciona con todos los datos de prueba
        """
        logger.info(f"Validating template with {len(test_data)} test datasets")
        
        # Importar el ejecutor de código
        from .code_executor import execute_visualization_code
        
        for i, data in enumerate(test_data):
            try:
                # Intentar ejecutar el código con estos datos
                result = execute_visualization_code(
                    code=template,
                    data={'data': data}
                )
                
                if not result['success']:
                    logger.warning(f"Template validation failed on dataset {i+1}: {result.get('error')}")
                    return False
                
                # Verificar que se generó una figura
                if result.get('figure') is None:
                    logger.warning(f"Template validation failed on dataset {i+1}: No figure generated")
                    return False
                
                logger.debug(f"Template validated successfully on dataset {i+1}")
                
            except Exception as e:
                logger.warning(f"Template validation failed on dataset {i+1}: {str(e)}")
                return False
        
        logger.info("Template validation successful on all test datasets")
        return True
    
    # Template creation methods
    
    def _create_timeline_template(self) -> str:
        """Crear plantilla para gráfico de línea temporal."""
        return """import plotly.graph_objects as go
import pandas as pd

# Asegurar que la columna temporal es datetime
if not pd.api.types.is_datetime64_any_dtype(data['{{TIME_COLUMN}}']):
    data['{{TIME_COLUMN}}'] = pd.to_datetime(data['{{TIME_COLUMN}}'])

# Crear figura
fig = go.Figure()

# Agregar traza para la métrica
fig.add_trace(go.Scatter(
    x=data['{{TIME_COLUMN}}'],
    y=data['{{METRIC_1}}'],
    mode='lines+markers',
    name='{{METRIC_1_LABEL}}',
    line=dict(color='#2E86AB', width=2),
    marker=dict(size=6),
    hovertemplate='<b>%{y:.2f}</b><br>%{x}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    xaxis_title='Tiempo',
    yaxis_title='{{METRIC_1_LABEL}}',
    hovermode='x unified',
    template='plotly_white',
    showlegend=True,
    height=600,
    xaxis=dict(
        showgrid=True,
        gridcolor='lightgray'
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='lightgray'
    )
)
"""
    
    def _create_comparison_template(self) -> str:
        """Crear plantilla para comparación de múltiples métricas."""
        return """import plotly.graph_objects as go
import pandas as pd

# Paleta de colores médicos
colors = ['#2E86AB', '#06A77D', '#F77F00', '#8338EC', '#3A86FF']

# Crear figura
fig = go.Figure()

# Agregar trazas para cada métrica
metrics = ['{{METRIC_1}}', '{{METRIC_2}}']
labels = ['{{METRIC_1_LABEL}}', '{{METRIC_2_LABEL}}']

for i, (metric, label) in enumerate(zip(metrics, labels)):
    if metric in data.columns:
        fig.add_trace(go.Scatter(
            x=data['{{TIME_COLUMN}}'] if '{{TIME_COLUMN}}' in data.columns else data.index,
            y=data[metric],
            mode='lines+markers',
            name=label,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{label}: %{{y:.2f}}</b><br>%{{x}}<extra></extra>'
        ))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    xaxis_title='Tiempo',
    yaxis_title='Valor',
    hovermode='x unified',
    template='plotly_white',
    showlegend=True,
    height=600,
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=1
    )
)
"""
    
    def _create_histogram_template(self) -> str:
        """Crear plantilla para histograma/distribución."""
        return """import plotly.graph_objects as go

# Crear figura
fig = go.Figure()

# Agregar histograma
fig.add_trace(go.Histogram(
    x=data['{{METRIC_1}}'],
    name='{{METRIC_1_LABEL}}',
    marker=dict(
        color='#2E86AB',
        line=dict(color='white', width=1)
    ),
    hovertemplate='<b>Rango: %{x}</b><br>Frecuencia: %{y}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    xaxis_title='{{METRIC_1_LABEL}}',
    yaxis_title='Frecuencia',
    template='plotly_white',
    showlegend=False,
    height=600,
    bargap=0.1
)
"""
    
    def _create_scatter_template(self) -> str:
        """Crear plantilla para gráfico de dispersión."""
        return """import plotly.graph_objects as go

# Crear figura
fig = go.Figure()

# Agregar scatter plot
fig.add_trace(go.Scatter(
    x=data['{{METRIC_1}}'],
    y=data['{{METRIC_2}}'],
    mode='markers',
    marker=dict(
        size=8,
        color='#2E86AB',
        opacity=0.6,
        line=dict(width=1, color='white')
    ),
    hovertemplate='<b>{{METRIC_1_LABEL}}: %{x:.2f}</b><br>{{METRIC_2_LABEL}}: %{y:.2f}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    xaxis_title='{{METRIC_1_LABEL}}',
    yaxis_title='{{METRIC_2_LABEL}}',
    template='plotly_white',
    showlegend=False,
    height=600,
    xaxis=dict(showgrid=True, gridcolor='lightgray'),
    yaxis=dict(showgrid=True, gridcolor='lightgray')
)
"""
    
    def _create_bar_template(self) -> str:
        """Crear plantilla para gráfico de barras."""
        return """import plotly.graph_objects as go
import pandas as pd

# Detectar columnas automáticamente
# Si el DataFrame ya viene pre-agregado (columnas 'categoria' y 'frecuencia'), usarlas directamente.
# Si no, intentar con las columnas configuradas.
if 'categoria' in data.columns and 'frecuencia' in data.columns:
    x_col = 'categoria'
    y_col = 'frecuencia'
    y_label = 'Frecuencia'
else:
    x_col = '{{CATEGORY_COLUMN}}'
    y_col = '{{METRIC_1}}'
    y_label = '{{METRIC_1_LABEL}}'

# Ordenar de mayor a menor para mejor legibilidad
plot_data = data[[x_col, y_col]].dropna().sort_values(y_col, ascending=False)

# Crear figura
fig = go.Figure()

# Agregar barras
fig.add_trace(go.Bar(
    x=plot_data[x_col],
    y=plot_data[y_col],
    marker=dict(
        color='#2E86AB',
        line=dict(color='white', width=1)
    ),
    hovertemplate='<b>%{x}</b><br>' + y_label + ': %{y}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    xaxis_title=x_col.replace('_', ' ').title(),
    yaxis_title=y_label,
    template='plotly_white',
    showlegend=False,
    height=600,
    xaxis=dict(tickangle=-45)
)
"""
    
    def _create_box_template(self) -> str:
        """Crear plantilla para box plot."""
        return """import plotly.graph_objects as go

# Crear figura
fig = go.Figure()

# Agregar box plot
fig.add_trace(go.Box(
    y=data['{{METRIC_1}}'],
    name='{{METRIC_1_LABEL}}',
    marker=dict(color='#2E86AB'),
    boxmean='sd',  # Mostrar media y desviación estándar
    hovertemplate='<b>{{METRIC_1_LABEL}}</b><br>Valor: %{y:.2f}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    yaxis_title='{{METRIC_1_LABEL}}',
    template='plotly_white',
    showlegend=False,
    height=600
)
"""
    
    def _create_violin_template(self) -> str:
        """Crear plantilla para violin plot."""
        return """import plotly.graph_objects as go

# Crear figura
fig = go.Figure()

# Agregar violin plot
fig.add_trace(go.Violin(
    y=data['{{METRIC_1}}'],
    name='{{METRIC_1_LABEL}}',
    marker=dict(color='#2E86AB'),
    box_visible=True,
    meanline_visible=True,
    hovertemplate='<b>{{METRIC_1_LABEL}}</b><br>Valor: %{y:.2f}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    yaxis_title='{{METRIC_1_LABEL}}',
    template='plotly_white',
    showlegend=False,
    height=600
)
"""
    
    def _create_heatmap_template(self) -> str:
        """Crear plantilla para heatmap."""
        return """import plotly.graph_objects as go
import pandas as pd

# Calcular matriz de correlación
numeric_cols = [col for col in data.columns if pd.api.types.is_numeric_dtype(data[col])]
corr_matrix = data[numeric_cols].corr()

# Crear figura
fig = go.Figure()

# Agregar heatmap
fig.add_trace(go.Heatmap(
    z=corr_matrix.values,
    x=corr_matrix.columns,
    y=corr_matrix.columns,
    colorscale='RdBu',
    zmid=0,
    text=corr_matrix.values,
    texttemplate='%{text:.2f}',
    textfont=dict(size=10),
    hovertemplate='<b>%{x} vs %{y}</b><br>Correlación: %{z:.3f}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    template='plotly_white',
    height=600,
    xaxis=dict(tickangle=-45)
)
"""
    
    def _create_pie_template(self) -> str:
        """Crear plantilla para gráfico de pastel."""
        return """import plotly.graph_objects as go

# Contar frecuencias
value_counts = data['{{CATEGORY_COLUMN}}'].value_counts()

# Crear figura
fig = go.Figure()

# Agregar pie chart
fig.add_trace(go.Pie(
    labels=value_counts.index,
    values=value_counts.values,
    marker=dict(
        colors=['#2E86AB', '#06A77D', '#F77F00', '#8338EC', '#3A86FF', '#FF006E', '#FFBE0B', '#FB5607']
    ),
    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    template='plotly_white',
    height=600,
    showlegend=True
)
"""
    
    def _create_sunburst_template(self) -> str:
        """Crear plantilla para sunburst (jerárquico)."""
        return """import plotly.graph_objects as go

# Contar frecuencias
value_counts = data['{{CATEGORY_COLUMN}}'].value_counts()

# Crear figura
fig = go.Figure()

# Agregar sunburst
fig.add_trace(go.Sunburst(
    labels=['Total'] + value_counts.index.tolist(),
    parents=[''] + ['Total'] * len(value_counts),
    values=[value_counts.sum()] + value_counts.values.tolist(),
    marker=dict(
        colors=['#2E86AB', '#06A77D', '#F77F00', '#8338EC', '#3A86FF', '#FF006E', '#FFBE0B', '#FB5607']
    ),
    hovertemplate='<b>%{label}</b><br>Cantidad: %{value}<extra></extra>'
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    template='plotly_white',
    height=600
)
"""
    
    def _create_table_template(self) -> str:
        """Crear plantilla para tabla."""
        return """import plotly.graph_objects as go

# Crear figura
fig = go.Figure()

# Agregar tabla
fig.add_trace(go.Table(
    header=dict(
        values=list(data.columns),
        fill_color='#2E86AB',
        font=dict(color='white', size=12),
        align='left'
    ),
    cells=dict(
        values=[data[col] for col in data.columns],
        fill_color='white',
        align='left',
        font=dict(size=11)
    )
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    template='plotly_white',
    height=600
)
"""
    
    def _create_indicator_template(self) -> str:
        """Crear plantilla para indicador KPI."""
        return """import plotly.graph_objects as go

# Calcular valor principal
value = data['{{METRIC_1}}'].mean()

# Crear figura
fig = go.Figure()

# Agregar indicador
fig.add_trace(go.Indicator(
    mode='number+delta',
    value=value,
    title=dict(text='{{METRIC_1_LABEL}}'),
    delta=dict(reference=data['{{METRIC_1}}'].median()),
    number=dict(suffix=' {{UNIT}}')
))

# Configurar layout
fig.update_layout(
    title='{{TITLE}}',
    template='plotly_white',
    height=400
)
"""


# Convenience function with singleton pattern
def create_visualization_templates() -> VisualizationTemplates:
    """
    Crear o retornar la instancia singleton del gestor de plantillas.
    
    Uses singleton pattern to avoid re-initializing templates on every call.
    This improves performance by reusing the pre-compiled templates.
    
    Returns:
        VisualizationTemplates singleton instance
    """
    global _template_manager_instance
    
    if _template_manager_instance is None:
        logger.info("Creating new VisualizationTemplates singleton instance")
        _template_manager_instance = VisualizationTemplates()
    else:
        logger.debug("Reusing existing VisualizationTemplates singleton instance")
    
    return _template_manager_instance


def get_template_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics from the template manager singleton.
    
    Returns:
        Dict with cache statistics or empty dict if not initialized
    """
    global _template_manager_instance
    
    if _template_manager_instance is not None:
        return _template_manager_instance.get_cache_stats()
    
    return {'status': 'not_initialized'}
