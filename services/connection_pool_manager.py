"""
Connection Pool Manager Service for ChatHCE

This service provides connection pooling for database and API connections
to optimize performance and resource utilization.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Queue, Empty, Full
from contextlib import contextmanager
import httpx
from supabase import create_client, Client
from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for connection pool monitoring"""
    pool_name: str
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    max_connections: int = 0
    connection_errors: int = 0
    average_response_time_ms: float = 0.0
    total_requests: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PooledConnection:
    """Wrapper for pooled connections with metadata"""
    connection: Any
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    is_healthy: bool = True
    connection_id: str = ""
    
    def mark_used(self):
        """Mark connection as used"""
        self.last_used = datetime.now()
        self.use_count += 1


class ConnectionPool:
    """Generic connection pool implementation"""
    
    def __init__(self, name: str, max_size: int, min_size: int = 1, 
                 max_idle_time: int = 300, health_check_interval: int = 60):
        self.name = name
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        
        self._pool: Queue = Queue(maxsize=max_size)
        self._active_connections: Dict[str, PooledConnection] = {}
        self._stats = ConnectionStats(pool_name=name, max_connections=max_size)
        self._lock = threading.RLock()
        self._last_health_check = time.time()
        self._connection_factory = None
        self._health_checker = None
        
        logger.info(f"Initialized connection pool '{name}' with max_size={max_size}, min_size={min_size}")
    
    def set_connection_factory(self, factory_func):
        """Set the function to create new connections"""
        self._connection_factory = factory_func
    
    def set_health_checker(self, health_func):
        """Set the function to check connection health"""
        self._health_checker = health_func
    
    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection"""
        if not self._connection_factory:
            raise RuntimeError(f"No connection factory set for pool '{self.name}'")
        
        try:
            connection = self._connection_factory()
            pooled_conn = PooledConnection(
                connection=connection,
                created_at=datetime.now(),
                last_used=datetime.now(),
                connection_id=f"{self.name}_{int(time.time() * 1000)}"
            )
            
            with self._lock:
                self._stats.total_connections += 1
            
            logger.debug(f"Created new connection {pooled_conn.connection_id} for pool '{self.name}'")
            return pooled_conn
            
        except Exception as e:
            with self._lock:
                self._stats.connection_errors += 1
            logger.error(f"Failed to create connection for pool '{self.name}': {e}")
            raise
    
    def _is_connection_healthy(self, pooled_conn: PooledConnection) -> bool:
        """Check if a connection is healthy"""
        try:
            # Check if connection is too old
            if (datetime.now() - pooled_conn.created_at).total_seconds() > self.max_idle_time:
                return False
            
            # Use custom health checker if available
            if self._health_checker:
                return self._health_checker(pooled_conn.connection)
            
            # Default: assume healthy if not too old
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed for connection {pooled_conn.connection_id}: {e}")
            return False
    
    def _cleanup_idle_connections(self):
        """Remove idle and unhealthy connections"""
        current_time = time.time()
        
        # Only run cleanup periodically
        if current_time - self._last_health_check < self.health_check_interval:
            return
        
        with self._lock:
            self._last_health_check = current_time
            
            # Check connections in pool
            temp_connections = []
            while not self._pool.empty():
                try:
                    pooled_conn = self._pool.get_nowait()
                    if self._is_connection_healthy(pooled_conn):
                        temp_connections.append(pooled_conn)
                    else:
                        logger.debug(f"Removing unhealthy connection {pooled_conn.connection_id}")
                        self._stats.total_connections -= 1
                except Empty:
                    break
            
            # Put healthy connections back
            for conn in temp_connections:
                try:
                    self._pool.put_nowait(conn)
                except Full:
                    # Pool is full, close excess connections
                    logger.debug(f"Pool full, closing excess connection {conn.connection_id}")
                    self._stats.total_connections -= 1
    
    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """Get a connection from the pool with context manager"""
        pooled_conn = None
        start_time = time.time()
        
        try:
            # Try to get existing connection from pool
            try:
                pooled_conn = self._pool.get(timeout=timeout)
                
                # Verify connection is still healthy
                if not self._is_connection_healthy(pooled_conn):
                    logger.debug(f"Connection {pooled_conn.connection_id} is unhealthy, creating new one")
                    pooled_conn = self._create_connection()
                    
            except Empty:
                # No connections available, create new one if under limit
                with self._lock:
                    if self._stats.total_connections < self.max_size:
                        pooled_conn = self._create_connection()
                    else:
                        raise RuntimeError(f"Connection pool '{self.name}' exhausted")
            
            # Mark connection as active
            with self._lock:
                self._active_connections[pooled_conn.connection_id] = pooled_conn
                self._stats.active_connections = len(self._active_connections)
                self._stats.idle_connections = self._pool.qsize()
                self._stats.total_requests += 1
            
            pooled_conn.mark_used()
            
            # Yield the actual connection
            yield pooled_conn.connection
            
        except Exception as e:
            with self._lock:
                self._stats.connection_errors += 1
            logger.error(f"Error getting connection from pool '{self.name}': {e}")
            raise
            
        finally:
            # Return connection to pool
            if pooled_conn:
                try:
                    # Calculate response time
                    response_time = (time.time() - start_time) * 1000
                    
                    with self._lock:
                        # Update average response time
                        if self._stats.total_requests > 0:
                            self._stats.average_response_time_ms = (
                                (self._stats.average_response_time_ms * (self._stats.total_requests - 1) + response_time) 
                                / self._stats.total_requests
                            )
                        
                        # Remove from active connections
                        if pooled_conn.connection_id in self._active_connections:
                            del self._active_connections[pooled_conn.connection_id]
                        
                        self._stats.active_connections = len(self._active_connections)
                        self._stats.last_updated = datetime.now()
                    
                    # Return to pool if healthy and pool not full
                    if self._is_connection_healthy(pooled_conn):
                        try:
                            self._pool.put_nowait(pooled_conn)
                            with self._lock:
                                self._stats.idle_connections = self._pool.qsize()
                        except Full:
                            # Pool is full, close connection
                            logger.debug(f"Pool full, closing connection {pooled_conn.connection_id}")
                            with self._lock:
                                self._stats.total_connections -= 1
                    else:
                        # Connection is unhealthy, don't return to pool
                        with self._lock:
                            self._stats.total_connections -= 1
                            
                except Exception as e:
                    logger.error(f"Error returning connection to pool '{self.name}': {e}")
            
            # Periodic cleanup
            self._cleanup_idle_connections()
    
    def get_stats(self) -> ConnectionStats:
        """Get current pool statistics"""
        with self._lock:
            self._stats.idle_connections = self._pool.qsize()
            self._stats.active_connections = len(self._active_connections)
            return self._stats
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            # Close active connections
            for pooled_conn in self._active_connections.values():
                try:
                    if hasattr(pooled_conn.connection, 'close'):
                        pooled_conn.connection.close()
                except Exception as e:
                    logger.warning(f"Error closing active connection: {e}")
            
            # Close pooled connections
            while not self._pool.empty():
                try:
                    pooled_conn = self._pool.get_nowait()
                    if hasattr(pooled_conn.connection, 'close'):
                        pooled_conn.connection.close()
                except Exception as e:
                    logger.warning(f"Error closing pooled connection: {e}")
            
            self._active_connections.clear()
            self._stats.total_connections = 0
            self._stats.active_connections = 0
            self._stats.idle_connections = 0
            
        logger.info(f"Closed all connections for pool '{self.name}'")


class ConnectionPoolManager:
    """
    Connection Pool Manager for database and API connections
    
    Manages multiple connection pools for different services and provides
    optimized connection reuse, health monitoring, and performance tracking.
    """
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.RLock()
        self._initialized = False
        
        # Initialize pools based on settings
        self._initialize_pools()
        
        logger.info("ConnectionPoolManager initialized successfully")
    
    def _initialize_pools(self):
        """Initialize connection pools based on configuration"""
        try:
            # Database connection pool
            self._create_database_pool()
            
            # API connection pools
            self._create_api_pools()
            
            self._initialized = True
            logger.info("All connection pools initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}")
            raise
    
    def _create_database_pool(self):
        """Create database connection pool for Supabase"""
        pool_name = "supabase_db"
        max_size = settings.performance.db_pool_size
        max_overflow = settings.performance.db_pool_max_overflow
        
        db_pool = ConnectionPool(
            name=pool_name,
            max_size=max_size + max_overflow,
            min_size=min(2, max_size),
            max_idle_time=300,  # 5 minutes
            health_check_interval=60  # 1 minute
        )
        
        # Set connection factory
        def create_supabase_connection():
            return create_client(
                settings.database.supabase_url,
                settings.database.supabase_key
            )
        
        # Set health checker
        def check_supabase_health(client: Client) -> bool:
            try:
                # Simple health check query - use .schema() for mimic_ed schema
                result = client.schema('mimic_ed').table('edstays').select('stay_id').limit(1).execute()
                return hasattr(result, 'data')
            except Exception:
                return False
        
        db_pool.set_connection_factory(create_supabase_connection)
        db_pool.set_health_checker(check_supabase_health)
        
        with self._lock:
            self._pools[pool_name] = db_pool
        
        logger.info(f"Created database pool '{pool_name}' with max_size={max_size + max_overflow}")
    
    def _create_api_pools(self):
        """Create API connection pools for external services"""
        # Anthropic API pool
        if settings.ai.anthropic_api_key:
            self._create_anthropic_api_pool()
        
        # HuggingFace API pool
        if settings.ai.huggingface_api_token:
            self._create_huggingface_api_pool()
    
    def _create_anthropic_api_pool(self):
        """Create connection pool for Anthropic API"""
        pool_name = "anthropic_api"
        max_size = settings.performance.api_pool_size
        
        api_pool = ConnectionPool(
            name=pool_name,
            max_size=max_size,
            min_size=1,
            max_idle_time=600,  # 10 minutes
            health_check_interval=120  # 2 minutes
        )
        
        # Set connection factory
        def create_anthropic_client():
            return httpx.Client(
                base_url="https://api.anthropic.com",
                headers={
                    "x-api-key": settings.ai.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                timeout=settings.performance.connection_timeout_seconds
            )
        
        # Set health checker
        def check_anthropic_health(client: httpx.Client) -> bool:
            try:
                # Simple connectivity check - POST to messages with minimal payload
                # A 401/400 response still confirms the endpoint is reachable
                response = client.post(
                    "/v1/messages",
                    json={"model": "claude-haiku-4-5-20251001", "messages": [], "max_tokens": 1},
                    timeout=5.0
                )
                # Any response (including 400/401) means the API is reachable
                return response.status_code in [200, 400, 401, 403, 429]
            except Exception:
                return False
        
        api_pool.set_connection_factory(create_anthropic_client)
        api_pool.set_health_checker(check_anthropic_health)
        
        with self._lock:
            self._pools[pool_name] = api_pool
        
        logger.info(f"Created Anthropic API pool '{pool_name}' with max_size={max_size}")
    
    def _create_huggingface_api_pool(self):
        """Create connection pool for HuggingFace API"""
        pool_name = "huggingface_api"
        max_size = min(settings.performance.api_pool_size, 3)  # HF has stricter limits
        
        api_pool = ConnectionPool(
            name=pool_name,
            max_size=max_size,
            min_size=1,
            max_idle_time=900,  # 15 minutes
            health_check_interval=180  # 3 minutes
        )
        
        # Set connection factory
        def create_hf_client():
            return httpx.Client(
                base_url="https://api-inference.huggingface.co",
                headers={
                    "Authorization": f"Bearer {settings.ai.huggingface_api_token}",
                    "Content-Type": "application/json"
                },
                timeout=settings.performance.connection_timeout_seconds
            )
        
        # Set health checker
        def check_hf_health(client: httpx.Client) -> bool:
            try:
                # Simple health check - just verify we can connect
                response = client.get("/", timeout=5.0)
                return response.status_code in [200, 404]  # 404 is OK for root endpoint
            except Exception:
                return False
        
        api_pool.set_connection_factory(create_hf_client)
        api_pool.set_health_checker(check_hf_health)
        
        with self._lock:
            self._pools[pool_name] = api_pool
        
        logger.info(f"Created HuggingFace API pool '{pool_name}' with max_size={max_size}")
    
    def get_db_connection(self, timeout: float = 30.0):
        """
        Get a database connection from the pool
        
        Args:
            timeout: Maximum time to wait for a connection
            
        Returns:
            Context manager yielding a Supabase client
        """
        if not self._initialized:
            raise RuntimeError("ConnectionPoolManager not initialized")
        
        pool_name = "supabase_db"
        if pool_name not in self._pools:
            raise RuntimeError(f"Database pool '{pool_name}' not found")
        
        return self._pools[pool_name].get_connection(timeout=timeout)
    
    def get_api_client(self, service: str, timeout: float = 30.0):
        """
        Get an API client from the pool
        
        Args:
            service: Service name ('anthropic', 'huggingface')
            timeout: Maximum time to wait for a connection
            
        Returns:
            Context manager yielding an HTTP client
        """
        if not self._initialized:
            raise RuntimeError("ConnectionPoolManager not initialized")
        
        pool_name = f"{service}_api"
        if pool_name not in self._pools:
            raise RuntimeError(f"API pool '{pool_name}' not found")
        
        return self._pools[pool_name].get_connection(timeout=timeout)
    
    def get_pool_stats(self, pool_name: Optional[str] = None) -> Union[Dict[str, ConnectionStats], ConnectionStats]:
        """
        Get connection pool statistics
        
        Args:
            pool_name: Specific pool name, or None for all pools
            
        Returns:
            Pool statistics
        """
        with self._lock:
            if pool_name:
                if pool_name not in self._pools:
                    raise ValueError(f"Pool '{pool_name}' not found")
                return self._pools[pool_name].get_stats()
            else:
                return {name: pool.get_stats() for name, pool in self._pools.items()}
    
    def optimize_pool_size(self, pool_name: Optional[str] = None):
        """
        Optimize pool sizes based on usage patterns
        
        Args:
            pool_name: Specific pool to optimize, or None for all pools
        """
        pools_to_optimize = [pool_name] if pool_name else list(self._pools.keys())
        
        for name in pools_to_optimize:
            if name not in self._pools:
                continue
                
            pool = self._pools[name]
            stats = pool.get_stats()
            
            # Simple optimization logic
            if stats.average_response_time_ms > 1000 and stats.active_connections >= stats.max_connections * 0.8:
                logger.info(f"Pool '{name}' may benefit from increased size (avg response: {stats.average_response_time_ms:.2f}ms)")
            
            if stats.connection_errors > stats.total_requests * 0.1:
                logger.warning(f"Pool '{name}' has high error rate: {stats.connection_errors}/{stats.total_requests}")
    
    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all pools
        
        Returns:
            Health status for each pool
        """
        health_status = {}
        
        with self._lock:
            for name, pool in self._pools.items():
                stats = pool.get_stats()
                
                # Determine health status
                is_healthy = True
                issues = []
                
                if stats.connection_errors > stats.total_requests * 0.2:
                    is_healthy = False
                    issues.append("High error rate")
                
                if stats.average_response_time_ms > 5000:
                    is_healthy = False
                    issues.append("High response time")
                
                if stats.total_connections == 0:
                    is_healthy = False
                    issues.append("No connections available")
                
                health_status[name] = {
                    'healthy': is_healthy,
                    'issues': issues,
                    'stats': stats,
                    'last_check': datetime.now().isoformat()
                }
        
        return health_status
    
    def close_all_pools(self):
        """Close all connection pools"""
        with self._lock:
            for name, pool in self._pools.items():
                try:
                    pool.close_all()
                    logger.info(f"Closed pool '{name}'")
                except Exception as e:
                    logger.error(f"Error closing pool '{name}': {e}")
            
            self._pools.clear()
            self._initialized = False
        
        logger.info("All connection pools closed")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.close_all_pools()
        except Exception:
            pass


# Global connection pool manager instance
connection_pool_manager = ConnectionPoolManager()