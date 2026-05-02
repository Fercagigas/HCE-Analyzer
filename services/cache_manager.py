"""
Cache management service for ChatHCE
Provides memory-based caching with TTL support, statistics, and monitoring capabilities.
"""
import time
import threading
import hashlib
import pickle
import gc
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, asdict
import logging
import structlog
from functools import wraps

from config.settings import settings


@dataclass
class CacheEntry:
    """Data class for cache entries"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    cache_type: str = "memory"
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of the cached value in bytes"""
        try:
            return len(pickle.dumps(self.value))
        except Exception:
            # Fallback for non-serializable objects
            return len(str(self.value).encode('utf-8'))
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Get the age of the cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Data class for cache statistics"""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    expired_count: int = 0
    cleanup_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.hit_count + self.miss_count
        return self.hit_count / total_requests if total_requests > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate
    
    @property
    def total_size_mb(self) -> float:
        """Get total cache size in MB"""
        return self.total_size_bytes / 1024 / 1024


class CacheManager:
    """
    Memory-based cache manager with TTL support, statistics, and monitoring.
    
    Features:
    - TTL-based expiration
    - LRU eviction when size limits are reached
    - Cache statistics and monitoring
    - Thread-safe operations
    - Multiple cache types support
    - Automatic cleanup of expired entries
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        # Store reference to settings for dynamic checking
        self._settings_ref = settings
        
        # Cache storage - using OrderedDict for LRU behavior
        self._caches: Dict[str, OrderedDict] = {
            "memory": OrderedDict(),
            "llm_responses": OrderedDict(),
            "embeddings": OrderedDict(),
            "query_results": OrderedDict(),
            "ui_data": OrderedDict()
        }
        
        # Cache statistics per cache type
        self._stats: Dict[str, CacheStats] = {
            cache_type: CacheStats() for cache_type in self._caches.keys()
        }
        
        # Thread safety
        self._locks: Dict[str, threading.RLock] = {
            cache_type: threading.RLock() for cache_type in self._caches.keys()
        }
        
        # Global lock for cross-cache operations
        self._global_lock = threading.RLock()
        
        # Cleanup tracking
        self._last_cleanup = datetime.now()
        self._cleanup_running = False
        
        # Size tracking
        self._max_size_bytes = self._settings_ref.performance.max_cache_size_mb * 1024 * 1024
        
        self.logger.info("CacheManager initialized", 
                        cache_enabled=self._settings_ref.performance.cache_enabled,
                        max_size_mb=self._settings_ref.performance.max_cache_size_mb,
                        ttl_seconds=self._settings_ref.performance.cache_ttl_seconds)
    
    @property
    def settings(self):
        """Dynamic access to current settings"""
        return self._settings_ref.performance
    
    def get(self, key: str, cache_type: str = "memory") -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache to use
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.settings.cache_enabled:
            return None
        
        if cache_type not in self._caches:
            self.logger.warning("Invalid cache type", cache_type=cache_type)
            return None
        
        with self._locks[cache_type]:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            if key not in cache:
                stats.miss_count += 1
                self.logger.debug("Cache miss", key=key, cache_type=cache_type)
                return None
            
            entry = cache[key]
            
            # Check if expired
            if entry.is_expired:
                del cache[key]
                stats.expired_count += 1
                stats.miss_count += 1
                self.logger.debug("Cache entry expired", key=key, cache_type=cache_type)
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            stats.hit_count += 1
            
            # Move to end for LRU (most recently used)
            cache.move_to_end(key)
            
            self.logger.debug("Cache hit", key=key, cache_type=cache_type, 
                            access_count=entry.access_count)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = None, cache_type: str = "memory") -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            cache_type: Type of cache to use
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.settings.cache_enabled:
            return False
        
        if cache_type not in self._caches:
            self.logger.warning("Invalid cache type", cache_type=cache_type)
            return False
        
        if ttl is None:
            ttl = self.settings.cache_ttl_seconds
        
        # Create cache entry
        now = datetime.now()
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            cache_type=cache_type
        )
        
        with self._locks[cache_type]:
            cache = self._caches[cache_type]
            stats = self._stats[cache_type]
            
            # Check if we need to evict entries due to size limits
            self._evict_if_needed(cache_type, entry.size_bytes)
            
            # Add/update entry
            if key in cache:
                # Update existing entry
                old_entry = cache[key]
                stats.total_size_bytes -= old_entry.size_bytes
            else:
                stats.total_entries += 1
            
            cache[key] = entry
            stats.total_size_bytes += entry.size_bytes
            
            # Move to end for LRU
            cache.move_to_end(key)
            
            self.logger.debug("Cache set", key=key, cache_type=cache_type, 
                            ttl=ttl, size_bytes=entry.size_bytes)
            
            return True
    
    def invalidate(self, pattern: str, cache_type: str = "all") -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match keys (supports wildcards with *)
            cache_type: Cache type to invalidate ("all" for all caches)
            
        Returns:
            Number of entries invalidated
        """
        if not self.settings.cache_enabled:
            return 0
        
        invalidated_count = 0
        
        if cache_type == "all":
            cache_types = list(self._caches.keys())
        else:
            cache_types = [cache_type] if cache_type in self._caches else []
        
        for ct in cache_types:
            with self._locks[ct]:
                cache = self._caches[ct]
                stats = self._stats[ct]
                
                keys_to_remove = []
                
                # Simple pattern matching (supports * wildcard)
                if "*" in pattern:
                    pattern_parts = pattern.split("*")
                    for key in cache.keys():
                        if self._matches_pattern(key, pattern_parts):
                            keys_to_remove.append(key)
                else:
                    # Exact match
                    if pattern in cache:
                        keys_to_remove.append(pattern)
                
                # Remove matched keys
                for key in keys_to_remove:
                    entry = cache[key]
                    stats.total_size_bytes -= entry.size_bytes
                    stats.total_entries -= 1
                    del cache[key]
                    invalidated_count += 1
        
        if invalidated_count > 0:
            self.logger.info("Cache invalidated", pattern=pattern, 
                           cache_type=cache_type, count=invalidated_count)
        
        return invalidated_count
    
    def get_cache_stats(self, cache_type: str = "all") -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            cache_type: Cache type to get stats for ("all" for all caches)
            
        Returns:
            Dictionary containing cache statistics
        """
        if cache_type == "all":
            # Aggregate stats across all cache types
            total_stats = CacheStats()
            cache_details = {}
            
            for ct in self._caches.keys():
                with self._locks[ct]:
                    stats = self._stats[ct]
                    stats_dict = asdict(stats)
                    # Add computed properties
                    stats_dict["hit_rate"] = stats.hit_rate
                    stats_dict["miss_rate"] = stats.miss_rate
                    stats_dict["total_size_mb"] = stats.total_size_mb
                    cache_details[ct] = stats_dict
                    
                    # Aggregate totals
                    total_stats.total_entries += stats.total_entries
                    total_stats.total_size_bytes += stats.total_size_bytes
                    total_stats.hit_count += stats.hit_count
                    total_stats.miss_count += stats.miss_count
                    total_stats.eviction_count += stats.eviction_count
                    total_stats.expired_count += stats.expired_count
                    total_stats.cleanup_count += stats.cleanup_count
            
            total_stats_dict = asdict(total_stats)
            total_stats_dict["hit_rate"] = total_stats.hit_rate
            total_stats_dict["miss_rate"] = total_stats.miss_rate
            total_stats_dict["total_size_mb"] = total_stats.total_size_mb
            
            return {
                "total": total_stats_dict,
                "by_cache_type": cache_details,
                "cache_enabled": self.settings.cache_enabled,
                "max_size_mb": self.settings.max_cache_size_mb,
                "ttl_seconds": self.settings.cache_ttl_seconds,
                "last_cleanup": self._last_cleanup.isoformat()
            }
        
        elif cache_type in self._caches:
            with self._locks[cache_type]:
                stats = self._stats[cache_type]
                stats_dict = asdict(stats)
                # Add computed properties
                stats_dict["hit_rate"] = stats.hit_rate
                stats_dict["miss_rate"] = stats.miss_rate
                stats_dict["total_size_mb"] = stats.total_size_mb
                
                return {
                    "cache_type": cache_type,
                    "stats": stats_dict,
                    "cache_enabled": self.settings.cache_enabled
                }
        
        else:
            return {"error": f"Invalid cache type: {cache_type}"}
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries across all cache types.
        
        Returns:
            Number of entries cleaned up
        """
        if not self.settings.cache_enabled or self._cleanup_running:
            return 0
        
        self._cleanup_running = True
        cleanup_count = 0
        
        try:
            now = datetime.now()
            
            for cache_type in self._caches.keys():
                with self._locks[cache_type]:
                    cache = self._caches[cache_type]
                    stats = self._stats[cache_type]
                    
                    expired_keys = []
                    
                    for key, entry in cache.items():
                        if entry.is_expired:
                            expired_keys.append(key)
                    
                    # Remove expired entries
                    for key in expired_keys:
                        entry = cache[key]
                        stats.total_size_bytes -= entry.size_bytes
                        stats.total_entries -= 1
                        stats.cleanup_count += 1
                        del cache[key]
                        cleanup_count += 1
            
            self._last_cleanup = now
            
            if cleanup_count > 0:
                self.logger.info("Cache cleanup completed", 
                               expired_entries=cleanup_count)
                
                # Force garbage collection after cleanup
                gc.collect()
        
        finally:
            self._cleanup_running = False
        
        return cleanup_count
    
    def clear_cache(self, cache_type: str = "all") -> int:
        """
        Clear all entries from specified cache type(s).
        
        Args:
            cache_type: Cache type to clear ("all" for all caches)
            
        Returns:
            Number of entries cleared
        """
        cleared_count = 0
        
        if cache_type == "all":
            cache_types = list(self._caches.keys())
        else:
            cache_types = [cache_type] if cache_type in self._caches else []
        
        for ct in cache_types:
            with self._locks[ct]:
                cache = self._caches[ct]
                stats = self._stats[ct]
                
                cleared_count += len(cache)
                cache.clear()
                
                # Reset stats
                stats.total_entries = 0
                stats.total_size_bytes = 0
        
        if cleared_count > 0:
            self.logger.info("Cache cleared", cache_type=cache_type, 
                           entries_cleared=cleared_count)
            gc.collect()
        
        return cleared_count
    
    def generate_cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        # Create a string representation of all arguments
        key_parts = []
        
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(str(hash(str(arg))))
        
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}={value}")
            else:
                key_parts.append(f"{key}={hash(str(value))}")
        
        key_string = "|".join(key_parts)
        
        # Generate hash for consistent key length
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _evict_if_needed(self, cache_type: str, new_entry_size: int) -> None:
        """
        Evict entries if cache size limit would be exceeded.
        
        Args:
            cache_type: Cache type to check
            new_entry_size: Size of the new entry to be added
        """
        cache = self._caches[cache_type]
        stats = self._stats[cache_type]
        
        # Calculate size per cache type (distribute total limit)
        max_size_per_cache = self._max_size_bytes // len(self._caches)
        
        while (stats.total_size_bytes + new_entry_size > max_size_per_cache and 
               len(cache) > 0):
            # Remove least recently used entry (first in OrderedDict)
            key, entry = cache.popitem(last=False)
            stats.total_size_bytes -= entry.size_bytes
            stats.total_entries -= 1
            stats.eviction_count += 1
            
            self.logger.debug("Cache entry evicted", key=key, cache_type=cache_type,
                            size_bytes=entry.size_bytes)
    
    def _matches_pattern(self, key: str, pattern_parts: List[str]) -> bool:
        """
        Check if a key matches a wildcard pattern.
        
        Args:
            key: Key to check
            pattern_parts: Pattern parts split by *
            
        Returns:
            True if key matches pattern
        """
        if not pattern_parts:
            return True
        
        if len(pattern_parts) == 1:
            return pattern_parts[0] in key
        
        # Check if key starts with first part and ends with last part
        if not key.startswith(pattern_parts[0]):
            return False
        
        if not key.endswith(pattern_parts[-1]):
            return False
        
        # Check middle parts
        current_pos = len(pattern_parts[0])
        for part in pattern_parts[1:-1]:
            pos = key.find(part, current_pos)
            if pos == -1:
                return False
            current_pos = pos + len(part)
        
        return True


# Global cache manager instance
cache_manager = CacheManager()


def cached(ttl: int = None, cache_type: str = "memory", key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        cache_type: Type of cache to use
        key_prefix: Prefix for cache keys
        
    Usage:
        @cached(ttl=300, cache_type="llm_responses")
        def expensive_function(arg1, arg2):
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not settings.performance.cache_enabled:
                return func(*args, **kwargs)
            
            # Generate cache key
            key_parts = [key_prefix, func.__name__] if key_prefix else [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            
            cache_key = cache_manager.generate_cache_key(*key_parts)
            
            # Try to get from cache
            result = cache_manager.get(cache_key, cache_type)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, cache_type)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str, cache_type: str = "all"):
    """
    Utility function to invalidate cache entries matching a pattern.
    
    Args:
        pattern: Pattern to match
        cache_type: Cache type to invalidate
    """
    return cache_manager.invalidate(pattern, cache_type)


def get_cache_stats():
    """
    Utility function to get cache statistics.
    
    Returns:
        Cache statistics dictionary
    """
    return cache_manager.get_cache_stats()