"""
Visualization Selector - Selección automática de tipo de visualización

Este módulo analiza las características de los datos y selecciona automáticamente
el tipo de visualización más apropiado basándose en reglas claras y deterministas.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DataCharacteristics:
    """Características de un DataFrame para selección de visualización."""
    has_temporal: bool
    temporal_column: Optional[str]
    numeric_columns: List[str]
    categorical_columns: List[str]
    num_numeric: int
    num_categorical: int
    num_rows: int
    categorical_cardinality: Dict[str, int]
    
    def __str__(self) -> str:
        return (
            f"DataCharacteristics(temporal={self.has_temporal}, "
            f"numeric={self.num_numeric}, categorical={self.num_categorical}, "
            f"rows={self.num_rows})"
        )


class VisualizationSelector:
    """
    Selector automático de tipo de visualización basado en características de datos.
    
    Usa reglas claras y deterministas para garantizar que siempre se elija
    la visualización más apropiada para los datos disponibles.
    """
    
    # Umbrales para decisiones
    MAX_CATEGORIES_BAR = 20
    MAX_CATEGORIES_PIE = 8
    MIN_METRICS_HEATMAP = 3
    MAX_METRICS_TIMELINE = 5
    
    def __init__(self):
        """Inicializar el selector."""
        logger.info("VisualizationSelector initialized")
    
    def analyze_data(self, data: pd.DataFrame) -> DataCharacteristics:
        """
        Analizar características del DataFrame.
        
        Args:
            data: DataFrame a analizar
            
        Returns:
            DataCharacteristics con información del DataFrame
        """
        # Detectar columna temporal
        temporal_column = None
        has_temporal = False
        
        for col in ['charttime', 'time', 'date', 'datetime', 'timestamp']:
            if col in data.columns:
                if pd.api.types.is_datetime64_any_dtype(data[col]):
                    temporal_column = col
                    has_temporal = True
                    break
        
        # Identificar columnas numéricas y categóricas
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Excluir columna temporal de categóricas si está ahí
        if temporal_column and temporal_column in categorical_columns:
            categorical_columns.remove(temporal_column)
        
        # Calcular cardinalidad de categóricas
        categorical_cardinality = {}
        for col in categorical_columns:
            categorical_cardinality[col] = data[col].nunique()
        
        characteristics = DataCharacteristics(
            has_temporal=has_temporal,
            temporal_column=temporal_column,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            num_numeric=len(numeric_columns),
            num_categorical=len(categorical_columns),
            num_rows=len(data),
            categorical_cardinality=categorical_cardinality
        )
        
        logger.debug(f"Data analysis: {characteristics}")
        return characteristics
    
    def select_visualization_type(
        self,
        data: pd.DataFrame,
        user_preference: Optional[str] = None
    ) -> Tuple[str, Dict[str, any]]:
        """
        Seleccionar tipo de visualización automáticamente.
        
        Args:
            data: DataFrame con datos
            user_preference: Preferencia del usuario (opcional, tiene prioridad)
            
        Returns:
            Tuple de (tipo_visualización, parámetros_sugeridos)
        """
        # Si el usuario especificó un tipo, usarlo
        if user_preference:
            logger.info(f"Using user preference: {user_preference}")
            return user_preference, self._get_default_params(user_preference, data)
        
        # Analizar características de los datos
        chars = self.analyze_data(data)
        
        # Aplicar reglas de selección
        viz_type, params = self._apply_selection_rules(chars, data)
        
        logger.info(f"Selected visualization type: {viz_type}")
        logger.debug(f"Suggested parameters: {params}")
        
        return viz_type, params
    
    def _apply_selection_rules(
        self,
        chars: DataCharacteristics,
        data: pd.DataFrame
    ) -> Tuple[str, Dict[str, any]]:
        """
        Aplicar reglas de selección basadas en características.
        
        Args:
            chars: Características del DataFrame
            data: DataFrame original
            
        Returns:
            Tuple de (tipo, parámetros)
        """
        # REGLA 1: Timeline - Datos temporales con métricas numéricas
        if chars.has_temporal and chars.num_numeric > 0:
            if chars.num_numeric == 1:
                return 'timeline', {
                    'time_column': chars.temporal_column,
                    'metrics': chars.numeric_columns[:1],
                    'title': f'Evolución de {chars.numeric_columns[0]}'
                }
            elif chars.num_numeric <= self.MAX_METRICS_TIMELINE:
                return 'comparison', {
                    'time_column': chars.temporal_column,
                    'metrics': chars.numeric_columns[:self.MAX_METRICS_TIMELINE],
                    'title': 'Comparación de Métricas'
                }
            else:
                # Muchas métricas temporales -> heatmap temporal
                return 'heatmap', {
                    'time_column': chars.temporal_column,
                    'metrics': chars.numeric_columns,
                    'title': 'Mapa de Calor de Métricas'
                }
        
        # REGLA 2: Barras - Categórica + Numérica
        if chars.num_categorical > 0 and chars.num_numeric > 0:
            # Encontrar categórica con cardinalidad apropiada
            for cat_col, cardinality in chars.categorical_cardinality.items():
                if cardinality <= self.MAX_CATEGORIES_BAR:
                    return 'bar', {
                        'category_column': cat_col,
                        'metric': chars.numeric_columns[0],
                        'title': f'{chars.numeric_columns[0]} por {cat_col}'
                    }
        
        # REGLA 3: Pie chart - Categórica con baja cardinalidad
        if chars.num_categorical > 0:
            for cat_col, cardinality in chars.categorical_cardinality.items():
                if cardinality <= self.MAX_CATEGORIES_PIE:
                    return 'pie', {
                        'category_column': cat_col,
                        'title': f'Distribución de {cat_col}'
                    }
        
        # REGLA 4: Heatmap - Múltiples métricas numéricas
        if chars.num_numeric >= self.MIN_METRICS_HEATMAP:
            return 'heatmap', {
                'metrics': chars.numeric_columns,
                'title': 'Correlación de Métricas'
            }
        
        # REGLA 5: Scatter - Dos métricas numéricas
        if chars.num_numeric >= 2:
            return 'scatter', {
                'x_metric': chars.numeric_columns[0],
                'y_metric': chars.numeric_columns[1],
                'title': f'{chars.numeric_columns[1]} vs {chars.numeric_columns[0]}'
            }
        
        # REGLA 6: Histograma - Una métrica numérica
        if chars.num_numeric == 1:
            return 'histogram', {
                'metric': chars.numeric_columns[0],
                'title': f'Distribución de {chars.numeric_columns[0]}'
            }
        
        # REGLA 7: Box plot - Métrica numérica (con o sin categórica)
        if chars.num_numeric > 0:
            params = {
                'metric': chars.numeric_columns[0],
                'title': f'Estadísticas de {chars.numeric_columns[0]}'
            }
            if chars.num_categorical > 0:
                # Box plot agrupado
                cat_col = list(chars.categorical_cardinality.keys())[0]
                if chars.categorical_cardinality[cat_col] <= self.MAX_CATEGORIES_BAR:
                    params['category_column'] = cat_col
                    params['title'] = f'{chars.numeric_columns[0]} por {cat_col}'
            return 'box', params
        
        # FALLBACK: Si no hay datos apropiados, usar tabla
        logger.warning("No suitable visualization found, using table")
        return 'table', {
            'title': 'Datos'
        }
    
    def _get_default_params(
        self,
        viz_type: str,
        data: pd.DataFrame
    ) -> Dict[str, any]:
        """
        Obtener parámetros por defecto para un tipo de visualización.
        
        Args:
            viz_type: Tipo de visualización
            data: DataFrame con datos
            
        Returns:
            Dict con parámetros sugeridos
        """
        chars = self.analyze_data(data)
        
        params = {'title': f'Gráfico de {viz_type}'}
        
        if viz_type in ['timeline', 'comparison'] and chars.has_temporal:
            params['time_column'] = chars.temporal_column
            params['metrics'] = chars.numeric_columns[:3]
        
        elif viz_type == 'bar' and chars.num_categorical > 0 and chars.num_numeric > 0:
            params['category_column'] = chars.categorical_columns[0]
            params['metric'] = chars.numeric_columns[0]
        
        elif viz_type == 'scatter' and chars.num_numeric >= 2:
            params['x_metric'] = chars.numeric_columns[0]
            params['y_metric'] = chars.numeric_columns[1]
        
        elif viz_type in ['histogram', 'box'] and chars.num_numeric > 0:
            params['metric'] = chars.numeric_columns[0]
        
        elif viz_type == 'heatmap' and chars.num_numeric >= 2:
            params['metrics'] = chars.numeric_columns
        
        elif viz_type == 'pie' and chars.num_categorical > 0:
            params['category_column'] = chars.categorical_columns[0]
        
        return params
    
    def get_available_types(self, data: pd.DataFrame) -> List[str]:
        """
        Obtener lista de tipos de visualización disponibles para estos datos.
        
        Args:
            data: DataFrame con datos
            
        Returns:
            Lista de tipos de visualización aplicables
        """
        chars = self.analyze_data(data)
        available = []
        
        # Timeline/Comparison
        if chars.has_temporal and chars.num_numeric > 0:
            available.extend(['timeline', 'comparison'])
        
        # Barras
        if chars.num_categorical > 0 and chars.num_numeric > 0:
            for cardinality in chars.categorical_cardinality.values():
                if cardinality <= self.MAX_CATEGORIES_BAR:
                    available.append('bar')
                    break
        
        # Pie
        if chars.num_categorical > 0:
            for cardinality in chars.categorical_cardinality.values():
                if cardinality <= self.MAX_CATEGORIES_PIE:
                    available.append('pie')
                    break
        
        # Scatter
        if chars.num_numeric >= 2:
            available.append('scatter')
        
        # Histogram
        if chars.num_numeric >= 1:
            available.append('histogram')
        
        # Box plot
        if chars.num_numeric >= 1:
            available.append('box')
        
        # Heatmap
        if chars.num_numeric >= self.MIN_METRICS_HEATMAP:
            available.append('heatmap')
        
        # Siempre disponible
        available.append('table')
        
        return list(set(available))  # Eliminar duplicados
