"""
Performance Monitor for Claude HCE Agent

This module provides comprehensive performance monitoring including:
- Response time tracking
- Token usage tracking
- Slow query detection and logging
- Performance metrics collection
"""

import logging
import time
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    model_name: Optional[str] = None
    success: bool = True
    error_type: Optional[str] = None
    query_type: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def finalize(self):
        """Calculate final metrics"""
        if self.end_time is None:
            self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'tokens_used': self.tokens_used,
            'model_name': self.model_name,
            'success': self.success,
            'error_type': self.error_type,
            'query_type': self.query_type,
            'timestamp': datetime.fromtimestamp(self.start_time).isoformat(),
            **self.additional_data
        }


class AgentPerformanceMonitor:
    """
    Monitors and tracks performance metrics for the Claude HCE Agent.
    
    This class provides:
    - Response time tracking per query
    - Token usage tracking
    - Slow query detection and logging
    - Performance statistics aggregation
    """
    
    def __init__(self):
        """Initialize performance monitor"""
        self.metrics_history: list[PerformanceMetrics] = []
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                'count': 0,
                'total_duration_ms': 0,
                'total_tokens': 0,
                'success_count': 0,
                'error_count': 0,
                'slow_query_count': 0
            }
        )
        
        # Performance thresholds from configuration
        self.simple_query_threshold_ms = 3000  # 3 seconds
        self.complex_query_threshold_ms = 8000  # 8 seconds
        self.visualization_threshold_ms = 10000  # 10 seconds
        
        logger.info("AgentPerformanceMonitor initialized")
    
    def start_tracking(self, operation: str, **kwargs) -> PerformanceMetrics:
        """
        Start tracking performance for an operation.
        
        Args:
            operation: Name of the operation being tracked
            **kwargs: Additional data to track
            
        Returns:
            PerformanceMetrics instance for this operation
        """
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            additional_data=kwargs
        )
        
        logger.debug(f"Started tracking: {operation}")
        return metrics
    
    def end_tracking(
        self,
        metrics: PerformanceMetrics,
        tokens_used: Optional[int] = None,
        model_name: Optional[str] = None,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        End tracking and record metrics.
        
        Args:
            metrics: PerformanceMetrics instance to finalize
            tokens_used: Number of tokens used
            model_name: Name of the model used
            success: Whether the operation succeeded
            error_type: Type of error if operation failed
        """
        # Finalize metrics
        metrics.finalize()
        metrics.tokens_used = tokens_used
        metrics.model_name = model_name
        metrics.success = success
        metrics.error_type = error_type
        
        # Add to history
        self.metrics_history.append(metrics)
        
        # Update operation statistics
        stats = self.operation_stats[metrics.operation]
        stats['count'] += 1
        stats['total_duration_ms'] += metrics.duration_ms
        if tokens_used:
            stats['total_tokens'] += tokens_used
        
        if success:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1
        
        # Check if query is slow
        is_slow = self._is_slow_query(metrics)
        if is_slow:
            stats['slow_query_count'] += 1
            self._log_slow_query(metrics)
        
        # Log metrics
        self._log_metrics(metrics, is_slow)
        
        logger.debug(
            f"Ended tracking: {metrics.operation} "
            f"({metrics.duration_ms:.0f}ms, {tokens_used or 0} tokens)"
        )
    
    def _is_slow_query(self, metrics: PerformanceMetrics) -> bool:
        """
        Determine if a query is slow based on thresholds.
        
        Args:
            metrics: Performance metrics to check
            
        Returns:
            True if query is slow, False otherwise
        """
        duration = metrics.duration_ms
        query_type = metrics.query_type or 'unknown'
        
        # Determine threshold based on query type
        if 'visualization' in query_type.lower():
            threshold = self.visualization_threshold_ms
        elif 'complex' in query_type.lower() or 'database' in query_type.lower():
            threshold = self.complex_query_threshold_ms
        else:
            threshold = self.simple_query_threshold_ms
        
        return duration > threshold
    
    def _log_slow_query(self, metrics: PerformanceMetrics):
        """
        Log slow query with details.
        
        Args:
            metrics: Performance metrics for the slow query
        """
        logger.warning(
            f"⚠️ SLOW QUERY DETECTED: {metrics.operation} "
            f"took {metrics.duration_ms:.0f}ms "
            f"(threshold: {self._get_threshold(metrics)}ms)"
        )
        
        # Log additional details
        if metrics.model_name:
            logger.warning(f"  Model: {metrics.model_name}")
        if metrics.tokens_used:
            logger.warning(f"  Tokens: {metrics.tokens_used}")
        if metrics.query_type:
            logger.warning(f"  Query type: {metrics.query_type}")
    
    def _get_threshold(self, metrics: PerformanceMetrics) -> int:
        """Get appropriate threshold for metrics"""
        query_type = metrics.query_type or 'unknown'
        
        if 'visualization' in query_type.lower():
            return self.visualization_threshold_ms
        elif 'complex' in query_type.lower() or 'database' in query_type.lower():
            return self.complex_query_threshold_ms
        else:
            return self.simple_query_threshold_ms
    
    def _log_metrics(self, metrics: PerformanceMetrics, is_slow: bool):
        """
        Log performance metrics.
        
        Args:
            metrics: Performance metrics to log
            is_slow: Whether this is a slow query
        """
        log_level = logging.WARNING if is_slow else logging.INFO
        
        log_message = (
            f"Performance: {metrics.operation} "
            f"| Duration: {metrics.duration_ms:.0f}ms "
            f"| Success: {metrics.success}"
        )
        
        if metrics.tokens_used:
            log_message += f" | Tokens: {metrics.tokens_used}"
        
        if metrics.model_name:
            log_message += f" | Model: {metrics.model_name}"
        
        logger.log(log_level, log_message)
    
    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Args:
            operation: Optional operation name to filter by
            
        Returns:
            Dictionary containing performance statistics
        """
        if operation:
            if operation not in self.operation_stats:
                return {'error': f'No statistics for operation: {operation}'}
            
            stats = self.operation_stats[operation].copy()
            
            # Calculate averages
            if stats['count'] > 0:
                stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['count']
                stats['avg_tokens'] = stats['total_tokens'] / stats['count'] if stats['total_tokens'] > 0 else 0
                stats['success_rate'] = (stats['success_count'] / stats['count']) * 100
                stats['slow_query_rate'] = (stats['slow_query_count'] / stats['count']) * 100
            
            return {operation: stats}
        
        # Return all statistics
        all_stats = {}
        for op, stats in self.operation_stats.items():
            op_stats = stats.copy()
            
            # Calculate averages
            if op_stats['count'] > 0:
                op_stats['avg_duration_ms'] = op_stats['total_duration_ms'] / op_stats['count']
                op_stats['avg_tokens'] = op_stats['total_tokens'] / op_stats['count'] if op_stats['total_tokens'] > 0 else 0
                op_stats['success_rate'] = (op_stats['success_count'] / op_stats['count']) * 100
                op_stats['slow_query_rate'] = (op_stats['slow_query_count'] / op_stats['count']) * 100
            
            all_stats[op] = op_stats
        
        return all_stats
    
    def get_recent_metrics(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get recent performance metrics.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            List of recent metrics as dictionaries
        """
        recent = self.metrics_history[-limit:] if len(self.metrics_history) > limit else self.metrics_history
        return [m.to_dict() for m in recent]
    
    def clear_history(self):
        """Clear metrics history"""
        self.metrics_history.clear()
        self.operation_stats.clear()
        logger.info("Performance metrics history cleared")


# Global performance monitor instance
_performance_monitor: Optional[AgentPerformanceMonitor] = None


def get_performance_monitor() -> AgentPerformanceMonitor:
    """Get global performance monitor instance (singleton)"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = AgentPerformanceMonitor()
    return _performance_monitor


def track_performance(
    operation: Optional[str] = None,
    query_type: Optional[str] = None
) -> Callable:
    """
    Decorator to track performance of a function.
    
    Args:
        operation: Optional operation name (defaults to function name)
        query_type: Optional query type for threshold determination
        
    Returns:
        Decorated function
        
    Example:
        @track_performance(operation="process_message", query_type="complex")
        def process_message(self, message: str):
            # ... implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            op_name = operation or func.__name__
            
            # Start tracking
            metrics = monitor.start_tracking(
                operation=op_name,
                query_type=query_type,
                function=func.__name__
            )
            
            success = True
            error_type = None
            result = None
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Extract metrics from result if available
                tokens_used = None
                model_name = None
                
                if isinstance(result, dict):
                    tokens_used = result.get('tokens_used')
                    model_name = result.get('model_used') or result.get('model_name')
                    success = result.get('success', True)
                
                return result
                
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
                
            finally:
                # End tracking
                tokens_used = None
                model_name = None
                
                if result and isinstance(result, dict):
                    tokens_used = result.get('tokens_used')
                    model_name = result.get('model_used') or result.get('model_name')
                
                monitor.end_tracking(
                    metrics,
                    tokens_used=tokens_used,
                    model_name=model_name,
                    success=success,
                    error_type=error_type
                )
        
        return wrapper
    return decorator


def log_performance_summary():
    """Log a summary of performance statistics"""
    monitor = get_performance_monitor()
    stats = monitor.get_statistics()
    
    if not stats:
        logger.info("No performance statistics available")
        return
    
    logger.info("=" * 60)
    logger.info("PERFORMANCE SUMMARY")
    logger.info("=" * 60)
    
    for operation, op_stats in stats.items():
        logger.info(f"\nOperation: {operation}")
        logger.info(f"  Total calls: {op_stats['count']}")
        logger.info(f"  Avg duration: {op_stats.get('avg_duration_ms', 0):.0f}ms")
        logger.info(f"  Avg tokens: {op_stats.get('avg_tokens', 0):.0f}")
        logger.info(f"  Success rate: {op_stats.get('success_rate', 0):.1f}%")
        logger.info(f"  Slow queries: {op_stats['slow_query_count']} ({op_stats.get('slow_query_rate', 0):.1f}%)")
    
    logger.info("=" * 60)
