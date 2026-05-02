"""
Data Preprocessor for Medical Visualizations

This module provides data preprocessing functionality for medical data
before visualization, including temporal ordering, outlier detection,
and metrics validation.

Performance optimizations:
- Vectorized pandas operations for speed
- Caching of validation results
- Optimized datetime conversions
- Execution time tracking
"""

import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class PreprocessResult:
    """Resultado del preprocesamiento de datos."""
    data: pd.DataFrame
    rows_original: int
    rows_processed: int
    rows_removed: int
    duplicates_removed: int
    outliers_detected: int
    metrics_excluded: List[str]
    warnings: List[str]
    execution_time_ms: float = 0.0  # Performance tracking
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logging."""
        return {
            'rows_original': self.rows_original,
            'rows_processed': self.rows_processed,
            'rows_removed': self.rows_removed,
            'duplicates_removed': self.duplicates_removed,
            'outliers_detected': self.outliers_detected,
            'metrics_excluded': self.metrics_excluded,
            'warnings': self.warnings,
            'execution_time_ms': self.execution_time_ms
        }


@dataclass
class MetricsValidation:
    """Resultado de validación de métricas."""
    valid_metrics: List[str]
    excluded_metrics: List[str]
    null_percentages: Dict[str, float]
    warnings: List[str]
    execution_time_ms: float = 0.0  # Performance tracking
    
    @property
    def has_valid_metrics(self) -> bool:
        """Verificar si hay métricas válidas."""
        return len(self.valid_metrics) > 0


class DataPreprocessor:
    """
    Preprocesador de datos para visualizaciones médicas.
    
    Responsabilidades:
    - Ordenar datos temporales
    - Eliminar duplicados
    - Detectar outliers
    - Validar métricas
    - Limpiar valores inválidos
    
    Performance optimizations:
    - Vectorized pandas operations
    - Caching of validation results for repeated calls
    - Optimized datetime conversions
    - Execution time tracking for monitoring
    """
    
    def __init__(self, null_threshold: float = 0.5):
        """
        Inicializar el preprocesador.
        
        Args:
            null_threshold: Umbral de valores nulos para excluir métricas (0.5 = 50%)
        """
        self.null_threshold = null_threshold
        
        # Performance tracking
        self._total_preprocess_calls = 0
        self._total_preprocess_time_ms = 0.0
        self._validation_cache: Dict[str, MetricsValidation] = {}
        
        logger.info(f"DataPreprocessor initialized with null_threshold={null_threshold}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        avg_time = (
            self._total_preprocess_time_ms / self._total_preprocess_calls
            if self._total_preprocess_calls > 0 else 0
        )
        
        return {
            'total_preprocess_calls': self._total_preprocess_calls,
            'total_preprocess_time_ms': self._total_preprocess_time_ms,
            'average_preprocess_time_ms': avg_time,
            'validation_cache_size': len(self._validation_cache)
        }
    
    def clear_validation_cache(self) -> None:
        """Clear the validation cache."""
        self._validation_cache.clear()
        logger.debug("Validation cache cleared")
    
    def preprocess_temporal_data(
        self,
        data: pd.DataFrame,
        time_column: str = 'charttime',
        metrics: Optional[List[str]] = None
    ) -> PreprocessResult:
        """
        Preprocesar datos temporales para visualización.
        
        Optimized with:
        - Vectorized pandas operations
        - Efficient datetime conversion
        - Performance tracking
        
        Args:
            data: DataFrame con datos médicos
            time_column: Nombre de la columna temporal
            metrics: Lista de métricas a procesar
            
        Returns:
            PreprocessResult con datos limpios y metadata
        """
        start_time = time.perf_counter()
        
        logger.info(f"Preprocessing temporal data with {len(data)} rows")
        
        # Guardar estado original
        rows_original = len(data)
        warnings = []
        
        # Copiar datos para no modificar el original
        # Use copy(deep=False) for better performance when we'll modify columns anyway
        processed_data = data.copy()
        
        # Verificar que existe la columna temporal
        if time_column not in processed_data.columns:
            warnings.append(f"Columna temporal '{time_column}' no encontrada")
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            return PreprocessResult(
                data=processed_data,
                rows_original=rows_original,
                rows_processed=len(processed_data),
                rows_removed=0,
                duplicates_removed=0,
                outliers_detected=0,
                metrics_excluded=[],
                warnings=warnings,
                execution_time_ms=execution_time_ms
            )
        
        # Convertir charttime a datetime si no lo está (optimized)
        if not pd.api.types.is_datetime64_any_dtype(processed_data[time_column]):
            try:
                # Use infer_datetime_format for faster parsing
                processed_data[time_column] = pd.to_datetime(
                    processed_data[time_column],
                    infer_datetime_format=True,
                    errors='coerce'
                )
                logger.info(f"Converted {time_column} to datetime")
            except Exception as e:
                warnings.append(f"No se pudo convertir {time_column} a datetime: {str(e)}")
        
        # Ordenar por tiempo (in-place for better performance)
        processed_data.sort_values(by=time_column, inplace=True)
        logger.debug(f"Data sorted by {time_column}")
        
        # Eliminar duplicados temporales (optimized)
        duplicates_before = len(processed_data)
        
        if metrics:
            # Si se especifican métricas, eliminar duplicados basados en tiempo + métricas
            subset_cols = [time_column] + [m for m in metrics if m in processed_data.columns]
            processed_data.drop_duplicates(subset=subset_cols, keep='first', inplace=True)
        else:
            # Si no se especifican métricas, eliminar duplicados basados solo en tiempo
            processed_data.drop_duplicates(subset=[time_column], keep='first', inplace=True)
        
        duplicates_removed = duplicates_before - len(processed_data)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate temporal records")
        
        # Calcular estadísticas finales
        rows_processed = len(processed_data)
        rows_removed = rows_original - rows_processed
        
        # Track performance
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._total_preprocess_calls += 1
        self._total_preprocess_time_ms += execution_time_ms
        
        result = PreprocessResult(
            data=processed_data,
            rows_original=rows_original,
            rows_processed=rows_processed,
            rows_removed=rows_removed,
            duplicates_removed=duplicates_removed,
            outliers_detected=0,  # Se detectarán en otro método
            metrics_excluded=[],
            warnings=warnings,
            execution_time_ms=execution_time_ms
        )
        
        logger.info(
            f"Temporal preprocessing complete: {rows_processed}/{rows_original} rows retained "
            f"in {execution_time_ms:.2f}ms"
        )
        return result
    
    def detect_outliers(
        self,
        data: pd.DataFrame,
        columns: List[str],
        method: str = 'iqr'
    ) -> pd.DataFrame:
        """
        Detectar outliers en métricas numéricas.
        
        Optimized with:
        - Vectorized operations for all columns at once
        - Efficient boolean mask operations
        - Performance tracking
        
        Args:
            data: DataFrame con datos
            columns: Columnas a analizar
            method: Método de detección ('iqr', 'zscore')
            
        Returns:
            DataFrame con columna 'is_outlier' añadida
        """
        start_time = time.perf_counter()
        
        logger.info(f"Detecting outliers in {len(columns)} columns using {method} method")
        
        # Copiar datos para no modificar el original
        result_data = data.copy()
        
        # Inicializar columna de outliers
        result_data['is_outlier'] = False
        
        # Filtrar solo columnas que existen y son numéricas
        valid_columns = [
            col for col in columns 
            if col in result_data.columns and pd.api.types.is_numeric_dtype(result_data[col])
        ]
        
        if not valid_columns:
            logger.warning("No valid numeric columns found for outlier detection")
            return result_data
        
        # Combined outlier mask for all columns (vectorized)
        combined_outlier_mask = pd.Series(False, index=result_data.index)
        
        if method == 'iqr':
            # Método IQR (Interquartile Range) - Vectorized
            for col in valid_columns:
                # Calcular Q1, Q3 e IQR
                Q1 = result_data[col].quantile(0.25)
                Q3 = result_data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                # Definir límites
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Marcar outliers (sin eliminarlos) - vectorized
                outliers_mask = (result_data[col] < lower_bound) | (result_data[col] > upper_bound)
                combined_outlier_mask |= outliers_mask
                
                outliers_count = outliers_mask.sum()
                if outliers_count > 0:
                    logger.debug(f"Detected {outliers_count} outliers in column '{col}'")
        
        elif method == 'zscore':
            # Método Z-score - Vectorized
            for col in valid_columns:
                # Calcular z-scores
                mean = result_data[col].mean()
                std = result_data[col].std()
                
                if std > 0:  # Evitar división por cero
                    z_scores = np.abs((result_data[col] - mean) / std)
                    
                    # Marcar outliers (z-score > 3)
                    outliers_mask = z_scores > 3
                    combined_outlier_mask |= outliers_mask
                    
                    outliers_count = outliers_mask.sum()
                    if outliers_count > 0:
                        logger.debug(f"Detected {outliers_count} outliers in column '{col}'")
        
        else:
            logger.warning(f"Unknown outlier detection method: {method}, using 'iqr'")
            return self.detect_outliers(data, columns, method='iqr')
        
        # Apply combined mask at once (more efficient)
        result_data.loc[combined_outlier_mask, 'is_outlier'] = True
        
        total_outliers = combined_outlier_mask.sum()
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"Total outliers detected: {total_outliers} in {execution_time_ms:.2f}ms")
        
        return result_data
    
    def validate_metrics(
        self,
        data: pd.DataFrame,
        requested_metrics: List[str]
    ) -> MetricsValidation:
        """
        Validar disponibilidad y calidad de métricas.
        
        Optimized with:
        - Caching of validation results
        - Vectorized null percentage calculation
        - Performance tracking
        
        Args:
            data: DataFrame con datos
            requested_metrics: Métricas solicitadas
            
        Returns:
            MetricsValidation con métricas válidas y excluidas
        """
        start_time = time.perf_counter()
        
        # Create cache key based on data shape and metrics
        cache_key = self._create_validation_cache_key(data, requested_metrics)
        
        # Check cache
        if cache_key in self._validation_cache:
            logger.debug(f"Validation cache HIT for metrics: {requested_metrics}")
            return self._validation_cache[cache_key]
        
        logger.info(f"Validating {len(requested_metrics)} requested metrics")
        
        valid_metrics = []
        excluded_metrics = []
        null_percentages = {}
        warnings = []
        
        total_count = len(data)
        
        # Vectorized null percentage calculation for all columns at once
        if total_count > 0:
            all_null_counts = data[
                [m for m in requested_metrics if m in data.columns]
            ].isna().sum()
        
        for metric in requested_metrics:
            # Verificar que la métrica existe en el DataFrame
            if metric not in data.columns:
                excluded_metrics.append(metric)
                warnings.append(f"Métrica '{metric}' no encontrada en los datos")
                continue
            
            # Use pre-calculated null counts
            null_count = all_null_counts.get(metric, 0) if total_count > 0 else 0
            null_percentage = null_count / total_count if total_count > 0 else 1.0
            
            null_percentages[metric] = null_percentage
            
            # Excluir métricas con más del umbral de nulos
            if null_percentage > self.null_threshold:
                excluded_metrics.append(metric)
                warnings.append(
                    f"Métrica '{metric}' excluida: {null_percentage*100:.1f}% valores nulos "
                    f"(umbral: {self.null_threshold*100:.1f}%)"
                )
                logger.debug(f"Metric '{metric}' excluded due to high null percentage: {null_percentage*100:.1f}%")
            else:
                # Reemplazar inf y NaN con None para Plotly
                if pd.api.types.is_numeric_dtype(data[metric]):
                    # Contar infinitos (vectorized)
                    inf_count = np.isinf(data[metric]).sum()
                    if inf_count > 0:
                        warnings.append(f"Métrica '{metric}': {inf_count} valores infinitos reemplazados con None")
                
                valid_metrics.append(metric)
                logger.debug(f"Metric '{metric}' validated: {null_percentage*100:.1f}% nulls")
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        result = MetricsValidation(
            valid_metrics=valid_metrics,
            excluded_metrics=excluded_metrics,
            null_percentages=null_percentages,
            warnings=warnings,
            execution_time_ms=execution_time_ms
        )
        
        # Cache the result (limit cache size to 50 entries)
        if len(self._validation_cache) < 50:
            self._validation_cache[cache_key] = result
        
        logger.info(
            f"Metrics validation complete: {len(valid_metrics)} valid, "
            f"{len(excluded_metrics)} excluded in {execution_time_ms:.2f}ms"
        )
        
        return result
    
    def _create_validation_cache_key(
        self,
        data: pd.DataFrame,
        metrics: List[str]
    ) -> str:
        """Create a cache key for validation caching."""
        # Use data shape and column hash as part of key
        data_hash = hash((len(data), tuple(data.columns.tolist())))
        metrics_hash = hash(tuple(sorted(metrics)))
        return f"{data_hash}:{metrics_hash}"
    
    def clean_invalid_values(
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Limpiar valores inválidos (inf, NaN) reemplazándolos con None.
        
        Args:
            data: DataFrame con datos
            columns: Columnas a limpiar (None = todas las numéricas)
            
        Returns:
            DataFrame con valores limpios
        """
        result_data = data.copy()
        
        # Si no se especifican columnas, usar todas las numéricas
        if columns is None:
            columns = result_data.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col in result_data.columns and pd.api.types.is_numeric_dtype(result_data[col]):
                # Reemplazar inf con NaN
                result_data[col] = result_data[col].replace([np.inf, -np.inf], np.nan)
                
                # Contar valores reemplazados
                nan_count = result_data[col].isna().sum()
                if nan_count > 0:
                    logger.debug(f"Column '{col}': {nan_count} invalid values cleaned")
        
        return result_data
