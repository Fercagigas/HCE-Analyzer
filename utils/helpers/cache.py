
"""
Intelligent caching system
"""
import redis
import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import pickle

class CacheManager:
    """Advanced cache management with Redis backend"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_available = True
        except:
            self.redis_available = False
            self._memory_cache = {}
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data"""
        data_str = json.dumps(data, sort_keys=True) if isinstance(data, dict) else str(data)
        hash_key = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cache value with TTL"""
        try:
            if self.redis_available:
                serialized_value = pickle.dumps(value)
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                # Fallback to memory cache
                expiry = datetime.now() + timedelta(seconds=ttl)
                self._memory_cache[key] = {
                    'value': value,
                    'expiry': expiry
                }
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            if self.redis_available:
                cached_value = self.redis_client.get(key)
                if cached_value:
                    return pickle.loads(cached_value)
            else:
                # Memory cache fallback
                if key in self._memory_cache:
                    cache_entry = self._memory_cache[key]
                    if datetime.now() < cache_entry['expiry']:
                        return cache_entry['value']
                    else:
                        del self._memory_cache[key]
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        try:
            if self.redis_available:
                return bool(self.redis_client.delete(key))
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    return True
            return False
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def cache_analysis_result(self, patient_id: str, document_hash: str, 
                            analysis_result: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache analysis result for patient document"""
        cache_key = self._generate_key("analysis", f"{patient_id}:{document_hash}")
        return self.set(cache_key, analysis_result, ttl)
    
    def get_cached_analysis(self, patient_id: str, document_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        cache_key = self._generate_key("analysis", f"{patient_id}:{document_hash}")
        return self.get(cache_key)
    
    def clear_patient_cache(self, patient_id: str) -> int:
        """Clear all cache entries for a patient"""
        pattern = f"analysis:*{patient_id}*"
        deleted_count = 0
        
        try:
            if self.redis_available:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted_count = self.redis_client.delete(*keys)
            else:
                # Memory cache cleanup
                keys_to_delete = [k for k in self._memory_cache.keys() if patient_id in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                deleted_count = len(keys_to_delete)
        except Exception as e:
            print(f"Cache clear error: {e}")
        
        return deleted_count

# Global cache instance
cache_manager = CacheManager()
