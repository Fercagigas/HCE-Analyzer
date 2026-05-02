"""
Cache utilities - re-exports from services.cache_manager for backwards compatibility.
"""
from services.cache_manager import CacheManager, cache_manager, cached, invalidate_cache_pattern, get_cache_stats

__all__ = ["CacheManager", "cache_manager", "cached", "invalidate_cache_pattern", "get_cache_stats"]
