"""
Database Service for Medical Agent

This module provides database connectivity and query execution services
for the medical conversation agent with comprehensive error handling.
"""

import logging
import re
import time
from typing import Dict, Any, Optional, List
import pandas as pd
from supabase import create_client, Client
from config.settings import settings
from services.connection_pool_manager import connection_pool_manager
import asyncio
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Exception for database connection issues."""
    pass


class QueryTimeoutError(DatabaseError):
    """Exception for query timeout issues."""
    pass


class ValidationError(DatabaseError):
    """Exception for query validation issues."""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry database operations on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ValidationError:
                    # Don't retry validation errors - they won't succeed on retry
                    raise
                except (ConnectionError, QueryTimeoutError) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        break
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Only retry certain types of errors
                    if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'server error']):
                        if attempt == max_retries:
                            logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                            break
                        
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Non-retryable error, fail immediately
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
            
            # If we get here, all retries failed
            raise DatabaseError(f"Operation failed after {max_retries} retries: {str(last_exception)}")
        
        return wrapper
    return decorator


def timeout_handler(timeout_seconds: int = 30):
    """
    Decorator to handle query timeouts.
    
    Args:
        timeout_seconds: Maximum time to wait for query completion
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # For now, we'll implement a simple timeout using the settings
                # In a production environment, you might want to use asyncio or threading
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                
                if elapsed_time > timeout_seconds:
                    logger.warning(f"Query took {elapsed_time:.2f}s, which exceeds timeout of {timeout_seconds}s")
                
                return result
                
            except Exception as e:
                if "timeout" in str(e).lower():
                    raise QueryTimeoutError(f"Query timed out after {timeout_seconds} seconds")
                raise
        
        return wrapper
    return decorator


class DatabaseService:
    """
    Database service for MIMIC-IV-ED data access.
    
    Provides secure, read-only access to medical data with proper
    connection management and query validation.
    """
    
    # Allowed tables for security (table names only, schema is set via .schema() method)
    ALLOWED_TABLES = {
        'diagnosis', 'edstays', 'triage', 'vitalsign', 'medrecon', 'pyxis'
    }
    
    # Schema name for MIMIC-IV-ED tables (exposed in Supabase API settings)
    SCHEMA_NAME = 'mimic_ed'
    
    # Dangerous SQL keywords to prevent
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
        'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'UNION', 'DECLARE', 'CURSOR',
        'COPY', 'VACUUM', 'ANALYZE', 'COMMENT', 'SECURITY', 'OWNER',
    }
    
    def __init__(self):
        """Initialize database service with connection pooling."""
        self.supabase: Optional[Client] = None
        self._connection_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
        self._use_connection_pool = True
        
        try:
            # Test connection pool availability
            if self._use_connection_pool:
                try:
                    with connection_pool_manager.get_db_connection() as conn:
                        # Test the pooled connection - use .schema() for mimic_ed schema
                        conn.schema('mimic_ed').table('edstays').select('stay_id').limit(1).execute()
                    logger.info("Database service initialized with connection pooling")
                except Exception as pool_error:
                    logger.warning(f"Connection pool not available, falling back to direct connection: {pool_error}")
                    self._use_connection_pool = False
                    self._initialize_connection()
            else:
                self._initialize_connection()
        except Exception as e:
            logger.error(f"Failed to initialize database service: {e}")
            raise ConnectionError(f"Unable to establish database connection: {str(e)}")
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def _initialize_connection(self):
        """Initialize Supabase connection with retry logic."""
        try:
            self.supabase = create_client(
                settings.database.supabase_url,
                settings.database.supabase_key
            )
            
            # Test connection with a simple query
            self._test_connection()
            self._connection_healthy = True
            self._last_health_check = time.time()
            
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            self._connection_healthy = False
            logger.error(f"Failed to initialize database connection: {e}")
            raise ConnectionError(f"Database initialization failed: {str(e)}")
    
    def _test_connection(self):
        """Test database connection health."""
        try:
            # Simple query to test connection - use .schema() for mimic_ed schema
            result = self.supabase.schema('mimic_ed').table('edstays').select('stay_id').limit(1).execute()
            if not hasattr(result, 'data'):
                raise ConnectionError("Invalid response from database")
            return True
        except Exception as e:
            raise ConnectionError(f"Connection test failed: {str(e)}")
    
    def _get_connection(self):
        """Get a database connection, either from pool or direct connection."""
        if self._use_connection_pool:
            return connection_pool_manager.get_db_connection()
        else:
            # Fallback to direct connection
            self._ensure_connection_healthy()
            return self._direct_connection_context()
    
    def _direct_connection_context(self):
        """Context manager for direct connection (fallback)."""
        from contextlib import contextmanager
        
        @contextmanager
        def connection_context():
            yield self.supabase
        
        return connection_context()
    
    def _ensure_connection_healthy(self):
        """Ensure database connection is healthy, reconnect if needed."""
        if self._use_connection_pool:
            # Connection health is managed by the pool
            return
            
        current_time = time.time()
        
        # Check if we need to verify connection health
        if (current_time - self._last_health_check) > self._health_check_interval or not self._connection_healthy:
            try:
                self._test_connection()
                self._connection_healthy = True
                self._last_health_check = current_time
            except Exception as e:
                logger.warning(f"Connection health check failed: {e}")
                self._connection_healthy = False
                
                # Try to reconnect
                try:
                    self._initialize_connection()
                except Exception as reconnect_error:
                    raise ConnectionError(f"Failed to reconnect to database: {str(reconnect_error)}")
    
    def _get_user_friendly_error(self, error: Exception, operation: str = "database operation") -> str:
        """
        Convert technical database errors to user-friendly messages.
        
        Args:
            error: The original exception
            operation: Description of the operation that failed
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        if "connection" in error_str or "network" in error_str:
            return f"Unable to connect to the medical database. Please check your internet connection and try again."
        
        elif "timeout" in error_str:
            return f"The database query is taking longer than expected. Please try a more specific search or try again later."
        
        elif "permission" in error_str or "unauthorized" in error_str:
            return f"You don't have permission to access this medical data. Please contact your administrator."
        
        elif "not found" in error_str or "does not exist" in error_str:
            return f"The requested medical record was not found in the database."
        
        elif "invalid" in error_str or "syntax" in error_str:
            return f"There was an issue with your search request. Please try rephrasing your question."
        
        elif "rate limit" in error_str or "too many requests" in error_str:
            return f"Too many requests have been made. Please wait a moment and try again."
        
        elif "server error" in error_str or "internal error" in error_str:
            return f"The medical database is experiencing technical difficulties. Please try again in a few minutes."
        
        else:
            return f"An unexpected error occurred while accessing medical data. Please try again or contact support if the problem persists."
    
    def _validate_query(self, query: str) -> bool:
        """
        Validate SQL query for security with defense-in-depth.
        
        Args:
            query: SQL query string
            
        Returns:
            True if query is safe, False otherwise
        """
        if not query or not query.strip():
            logger.warning("Empty query rejected")
            return False
        
        # Limit query length
        if len(query) > 2000:
            logger.warning("Query exceeds maximum length of 2000 characters")
            return False
        
        query_upper = query.upper().strip()
        
        # Must start with SELECT
        if not query_upper.startswith('SELECT'):
            logger.warning("Query does not start with SELECT")
            return False
        
        # Check for dangerous keywords using word boundaries
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                logger.warning(f"Dangerous keyword '{keyword}' found in query")
                return False
        
        # Block semicolons, comments, and multi-statement attacks
        if ';' in query or '--' in query or '/*' in query:
            logger.warning("Query contains forbidden characters (;, --, /*)")
            return False
        
        # Block system table access
        if re.search(r'\b(?:PG_|INFORMATION_SCHEMA)\b', query_upper):
            logger.warning("Query attempts to access system tables")
            return False
        
        # Block dangerous PostgreSQL functions
        dangerous_functions = [
            'PG_SLEEP', 'PG_READ_FILE', 'PG_WRITE_FILE',
            'DBLINK', 'LO_IMPORT', 'LO_EXPORT',
            'CURRENT_SETTING', 'SET_CONFIG',
        ]
        for func in dangerous_functions:
            if func in query_upper:
                logger.warning(f"Dangerous function '{func}' found in query")
                return False
        
        # Check that only allowed tables are referenced
        table_pattern = r'(?:FROM|JOIN)\s+(?:mimic_ed\.)?(\w+)'
        tables_in_query = re.findall(table_pattern, query_upper)
        
        for table in tables_in_query:
            if table.lower() not in self.ALLOWED_TABLES:
                logger.warning(f"Unauthorized table '{table}' in query")
                return False
        
        return True
    
    def _sanitize_params(self, params: Optional[Dict]) -> Dict:
        """
        Sanitize query parameters.
        
        Args:
            params: Query parameters
            
        Returns:
            Sanitized parameters
        """
        if not params:
            return {}
        
        sanitized = {}
        for key, value in params.items():
            # Only allow alphanumeric keys
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                logger.warning(f"Invalid parameter key: {key}")
                continue
            
            # Convert values to safe types
            if isinstance(value, (int, float, str, bool)):
                sanitized[key] = value
            else:
                logger.warning(f"Invalid parameter type for {key}: {type(value)}")
        
        return sanitized
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Query results as pandas DataFrame
            
        Raises:
            ValueError: If query is invalid or unsafe
            Exception: If query execution fails
        """
        # Validate query
        if not self._validate_query(query):
            raise ValueError("Query validation failed - unsafe or unauthorized query")
        
        # Sanitize parameters
        safe_params = self._sanitize_params(params)
        
        try:
            # For Supabase, we'll use the table-based API instead of raw SQL
            # This is more secure and follows Supabase best practices
            logger.info(f"Executing query with {len(safe_params)} parameters")
            
            # Note: This is a simplified implementation
            # In practice, we'd need to parse the query and convert to Supabase API calls
            # For now, we'll implement specific methods for common queries
            raise NotImplementedError("Direct SQL execution not implemented. Use specific query methods.")
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_table_data(self, table_name: str, filters: Optional[Dict] = None, 
                      columns: Optional[List[str]] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Get data from a specific table with optional filters.
        
        Args:
            table_name: Name of the table
            filters: Optional filters to apply
            columns: Optional list of columns to select
            limit: Maximum number of rows to return
            
        Returns:
            Query results as pandas DataFrame
            
        Raises:
            ValidationError: If table name or parameters are invalid
            DatabaseError: If query execution fails
        """
        try:
            # Validate inputs
            if table_name not in self.ALLOWED_TABLES:
                raise ValidationError(f"Access to table '{table_name}' is not permitted. Available tables: {', '.join(self.ALLOWED_TABLES)}")
            
            if limit > settings.medical_agent.max_result_rows:
                limit = settings.medical_agent.max_result_rows
                logger.info(f"Limiting results to {limit} rows for performance")
            
            # Get connection from pool or direct
            with self._get_connection() as supabase_client:
                # Build query with mimic_ed schema using .schema() method
                query = supabase_client.schema('mimic_ed').table(table_name)
                
                # Select columns
                if columns:
                    # Validate column names
                    safe_columns = [col for col in columns if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col)]
                    if len(safe_columns) != len(columns):
                        invalid_columns = set(columns) - set(safe_columns)
                        raise ValidationError(f"Invalid column names: {', '.join(invalid_columns)}")
                    query = query.select(','.join(safe_columns))
                else:
                    query = query.select('*')
                
                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                            raise ValidationError(f"Invalid filter column name: {key}")
                        query = query.eq(key, value)
                
                # Execute query with limit
                start_time = time.time()
                result = query.limit(limit).execute()
                execution_time = time.time() - start_time
                
                # Log performance metrics
                if execution_time > 5.0:
                    logger.warning(f"Slow query detected: {table_name} took {execution_time:.2f}s")
                
                # Convert to DataFrame
                if result.data:
                    df = pd.DataFrame(result.data)
                    logger.info(f"Retrieved {len(df)} rows from {table_name} in {execution_time:.2f}s")
                    return df
                else:
                    logger.info(f"No data found in {table_name} with given filters")
                    return pd.DataFrame()
                
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            error_msg = self._get_user_friendly_error(e, f"retrieving data from {table_name}")
            logger.error(f"Failed to get data from {table_name}: {e}")
            raise DatabaseError(error_msg) from e
    
    @retry_on_failure(max_retries=2, delay=1.0, backoff=2.0)
    @timeout_handler(timeout_seconds=45)
    def get_patient_summary(self, subject_id: int) -> Dict[str, Any]:
        """
        Get comprehensive patient summary from multiple tables.
        
        Args:
            subject_id: Patient identifier
            
        Returns:
            Patient summary data with formatted medical information
            
        Raises:
            ValidationError: If subject_id is invalid
            DatabaseError: If data retrieval fails
        """
        try:
            # Validate input
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"Invalid patient ID: {subject_id}. Patient ID must be a positive integer.")
            
            # Connection health is managed by get_table_data method
            logger.info(f"Generating patient summary for subject_id: {subject_id}")
            summary = {
                'subject_id': subject_id,
                'demographics': {},
                'stays': [],
                'diagnoses': [],
                'vital_signs_summary': {},
                'medications': [],
                'summary_stats': {
                    'total_stays': 0,
                    'total_diagnoses': 0,
                    'total_medications': 0,
                    'last_visit': None
                }
            }
            
            # Get patient stays with comprehensive error handling
            try:
                stays_df = self.get_table_data('edstays', {'subject_id': subject_id})
                if not stays_df.empty:
                    # Format stay data
                    formatted_stays = []
                    for _, stay in stays_df.iterrows():
                        formatted_stay = {
                            'stay_id': stay.get('stay_id'),
                            'admission_time': stay.get('intime'),
                            'discharge_time': stay.get('outtime'),
                            'arrival_method': stay.get('arrival_transport'),
                            'disposition': stay.get('disposition'),
                            'hadm_id': stay.get('hadm_id')
                        }
                        formatted_stays.append(formatted_stay)
                    
                    summary['stays'] = formatted_stays
                    summary['summary_stats']['total_stays'] = len(formatted_stays)
                    
                    # Get demographics from first stay
                    first_stay = stays_df.iloc[0]
                    summary['demographics'] = {
                        'gender': first_stay.get('gender', 'Unknown'),
                        'race': first_stay.get('race', 'Unknown')
                    }
                    
                    # Find most recent visit
                    if 'intime' in stays_df.columns:
                        latest_visit = stays_df['intime'].max()
                        summary['summary_stats']['last_visit'] = latest_visit
                        
            except DatabaseError as e:
                logger.warning(f"Database error retrieving stays for patient {subject_id}: {e}")
                summary['stays'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append(f"Could not retrieve hospital stays: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error retrieving stays for patient {subject_id}: {e}")
                summary['stays'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append("Could not retrieve hospital stays due to a technical issue")
            
            # Get diagnoses with formatting
            try:
                diagnoses_df = self.get_table_data('diagnosis', {'subject_id': subject_id})
                if not diagnoses_df.empty:
                    # Format diagnosis data
                    formatted_diagnoses = []
                    for _, diagnosis in diagnoses_df.iterrows():
                        formatted_diagnosis = {
                            'icd_code': diagnosis.get('icd_code'),
                            'icd_version': diagnosis.get('icd_version'),
                            'description': diagnosis.get('icd_title'),
                            'sequence': diagnosis.get('seq_num'),
                            'stay_id': diagnosis.get('stay_id')
                        }
                        formatted_diagnoses.append(formatted_diagnosis)
                    
                    summary['diagnoses'] = formatted_diagnoses
                    summary['summary_stats']['total_diagnoses'] = len(formatted_diagnoses)
                    
            except DatabaseError as e:
                logger.warning(f"Database error retrieving diagnoses for patient {subject_id}: {e}")
                summary['diagnoses'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append(f"Could not retrieve diagnoses: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error retrieving diagnoses for patient {subject_id}: {e}")
                summary['diagnoses'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append("Could not retrieve diagnoses due to a technical issue")
            
            # Get vital signs summary with medical formatting
            try:
                vitals_df = self.get_table_data('vitalsign', {'subject_id': subject_id})
                if not vitals_df.empty:
                    # Get most recent vital signs
                    vitals_df['charttime'] = pd.to_datetime(vitals_df['charttime'], errors='coerce')
                    latest_vitals = vitals_df.sort_values('charttime').tail(1)
                    
                    if not latest_vitals.empty:
                        vital_record = latest_vitals.iloc[0]
                        summary['vital_signs_summary'] = {
                            'measurement_time': str(vital_record.get('charttime')),
                            'temperature': self._format_temperature(vital_record.get('temperature')),
                            'heart_rate': self._format_heart_rate(vital_record.get('heartrate')),
                            'respiratory_rate': self._format_respiratory_rate(vital_record.get('resprate')),
                            'oxygen_saturation': self._format_oxygen_sat(vital_record.get('o2sat')),
                            'blood_pressure': self._format_blood_pressure(
                                vital_record.get('sbp'), vital_record.get('dbp')
                            ),
                            'pain_score': vital_record.get('pain'),
                            'rhythm': vital_record.get('rhythm')
                        }
                        
            except DatabaseError as e:
                logger.warning(f"Database error retrieving vital signs for patient {subject_id}: {e}")
                summary['vital_signs_summary'] = {}
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append(f"Could not retrieve vital signs: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error retrieving vital signs for patient {subject_id}: {e}")
                summary['vital_signs_summary'] = {}
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append("Could not retrieve vital signs due to a technical issue")
            
            # Get medications with formatting
            try:
                medications = self.get_medication_history(subject_id)
                summary['medications'] = medications[:10]  # Limit to recent 10
                summary['summary_stats']['total_medications'] = len(medications)
                
            except DatabaseError as e:
                logger.warning(f"Database error retrieving medications for patient {subject_id}: {e}")
                summary['medications'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append(f"Could not retrieve medications: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error retrieving medications for patient {subject_id}: {e}")
                summary['medications'] = []
                summary['errors'] = summary.get('errors', [])
                summary['errors'].append("Could not retrieve medications due to a technical issue")
            
            logger.info(f"Generated comprehensive summary for patient {subject_id}")
            return summary
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except DatabaseError as e:
            logger.error(f"Database error getting patient summary for {subject_id}: {e}")
            raise DatabaseError(f"Unable to retrieve complete patient summary: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting patient summary for {subject_id}: {e}")
            error_msg = self._get_user_friendly_error(e, "retrieving patient summary")
            raise DatabaseError(error_msg) from e
    
    @retry_on_failure(max_retries=2, delay=1.0, backoff=2.0)
    @timeout_handler(timeout_seconds=45)
    def get_stay_details(self, stay_id: int) -> Dict[str, Any]:
        """
        Get emergency department stay details with comprehensive medical formatting.
        
        Args:
            stay_id: Stay identifier
            
        Returns:
            Stay details data with formatted medical information
            
        Raises:
            ValidationError: If stay_id is invalid
            DatabaseError: If data retrieval fails
        """
        try:
            # Validate input
            if not isinstance(stay_id, int) or stay_id <= 0:
                raise ValidationError(f"Invalid stay ID: {stay_id}. Stay ID must be a positive integer.")
            
            # Connection health is managed by get_table_data method
            logger.info(f"Generating stay details for stay_id: {stay_id}")
            details = {
                'stay_id': stay_id,
                'stay_info': {},
                'triage': {},
                'diagnoses': [],
                'vital_signs': [],
                'medications': [],
                'stay_summary': {
                    'duration_hours': None,
                    'total_diagnoses': 0,
                    'total_vitals': 0,
                    'total_medications': 0,
                    'chief_complaint': None,
                    'acuity_level': None
                }
            }
            
            # Get stay information with error handling
            try:
                stay_df = self.get_table_data('edstays', {'stay_id': stay_id})
                if not stay_df.empty:
                    stay_record = stay_df.iloc[0]
                    details['stay_info'] = {
                        'subject_id': stay_record.get('subject_id'),
                        'hadm_id': stay_record.get('hadm_id'),
                        'admission_time': stay_record.get('intime'),
                        'discharge_time': stay_record.get('outtime'),
                        'patient_demographics': {
                            'gender': stay_record.get('gender'),
                            'race': stay_record.get('race')
                        },
                        'arrival_method': stay_record.get('arrival_transport'),
                        'disposition': stay_record.get('disposition')
                    }
                    
                    # Calculate stay duration
                    try:
                        intime = pd.to_datetime(stay_record.get('intime'))
                        outtime = pd.to_datetime(stay_record.get('outtime'))
                        duration = outtime - intime
                        details['stay_summary']['duration_hours'] = round(duration.total_seconds() / 3600, 2)
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"Error retrieving stay info for {stay_id}: {e}")
            
            # Get triage information with medical formatting
            try:
                triage_df = self.get_table_data('triage', {'stay_id': stay_id})
                if not triage_df.empty:
                    triage_record = triage_df.iloc[0]
                    details['triage'] = {
                        'chief_complaint': triage_record.get('chiefcomplaint'),
                        'acuity_level': triage_record.get('acuity'),
                        'initial_vitals': {
                            'temperature': self._format_temperature(triage_record.get('temperature')),
                            'heart_rate': self._format_heart_rate(triage_record.get('heartrate')),
                            'respiratory_rate': self._format_respiratory_rate(triage_record.get('resprate')),
                            'oxygen_saturation': self._format_oxygen_sat(triage_record.get('o2sat')),
                            'blood_pressure': self._format_blood_pressure(
                                triage_record.get('sbp'), triage_record.get('dbp')
                            ),
                            'pain_score': triage_record.get('pain')
                        }
                    }
                    
                    # Update summary
                    details['stay_summary']['chief_complaint'] = triage_record.get('chiefcomplaint')
                    details['stay_summary']['acuity_level'] = triage_record.get('acuity')
                    
            except Exception as e:
                logger.warning(f"Error retrieving triage info for {stay_id}: {e}")
            
            # Get diagnoses with medical formatting
            try:
                diagnoses_df = self.get_table_data('diagnosis', {'stay_id': stay_id})
                if not diagnoses_df.empty:
                    formatted_diagnoses = []
                    for _, diagnosis in diagnoses_df.iterrows():
                        formatted_diagnosis = {
                            'sequence': diagnosis.get('seq_num'),
                            'icd_code': diagnosis.get('icd_code'),
                            'icd_version': f"ICD-{diagnosis.get('icd_version')}",
                            'description': diagnosis.get('icd_title'),
                            'is_primary': diagnosis.get('seq_num') == 1
                        }
                        formatted_diagnoses.append(formatted_diagnosis)
                    
                    # Sort by sequence number
                    formatted_diagnoses.sort(key=lambda x: x.get('sequence', 999))
                    details['diagnoses'] = formatted_diagnoses
                    details['stay_summary']['total_diagnoses'] = len(formatted_diagnoses)
                    
            except Exception as e:
                logger.warning(f"Error retrieving diagnoses for {stay_id}: {e}")
            
            # Get vital signs with timeline formatting
            try:
                vitals_df = self.get_table_data('vitalsign', {'stay_id': stay_id})
                if not vitals_df.empty:
                    # Sort by charttime
                    vitals_df['charttime'] = pd.to_datetime(vitals_df['charttime'], errors='coerce')
                    vitals_df = vitals_df.sort_values('charttime')
                    
                    formatted_vitals = []
                    for _, vital in vitals_df.iterrows():
                        formatted_vital = {
                            'measurement_time': str(vital.get('charttime')),
                            'temperature': self._format_temperature(vital.get('temperature')),
                            'heart_rate': self._format_heart_rate(vital.get('heartrate')),
                            'respiratory_rate': self._format_respiratory_rate(vital.get('resprate')),
                            'oxygen_saturation': self._format_oxygen_sat(vital.get('o2sat')),
                            'blood_pressure': self._format_blood_pressure(
                                vital.get('sbp'), vital.get('dbp')
                            ),
                            'pain_score': vital.get('pain'),
                            'rhythm': vital.get('rhythm')
                        }
                        formatted_vitals.append(formatted_vital)
                    
                    details['vital_signs'] = formatted_vitals
                    details['stay_summary']['total_vitals'] = len(formatted_vitals)
                    
            except Exception as e:
                logger.warning(f"Error retrieving vital signs for {stay_id}: {e}")
            
            # Get medications with comprehensive formatting
            try:
                # Get from both medrecon and pyxis
                medrecon_df = self.get_table_data('medrecon', {'stay_id': stay_id})
                pyxis_df = self.get_table_data('pyxis', {'stay_id': stay_id})
                
                formatted_medications = []
                
                # Process medrecon data
                if not medrecon_df.empty:
                    for _, med in medrecon_df.iterrows():
                        formatted_med = {
                            'source': 'Medication Reconciliation',
                            'time': med.get('charttime'),
                            'medication_name': med.get('name'),
                            'gsn': med.get('gsn'),
                            'ndc': med.get('ndc'),
                            'category': med.get('etcdescription'),
                            'category_code': med.get('etccode')
                        }
                        formatted_medications.append(formatted_med)
                
                # Process pyxis data
                if not pyxis_df.empty:
                    for _, med in pyxis_df.iterrows():
                        formatted_med = {
                            'source': 'Pyxis Dispensing',
                            'time': med.get('charttime'),
                            'medication_name': med.get('name'),
                            'gsn': med.get('gsn'),
                            'med_rn': med.get('med_rn')
                        }
                        formatted_medications.append(formatted_med)
                
                # Sort by time
                formatted_medications.sort(key=lambda x: x.get('time', ''), reverse=True)
                details['medications'] = formatted_medications
                details['stay_summary']['total_medications'] = len(formatted_medications)
                
            except Exception as e:
                logger.warning(f"Error retrieving medications for {stay_id}: {e}")
            
            logger.info(f"Generated comprehensive details for stay {stay_id}")
            return details
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except DatabaseError as e:
            logger.error(f"Database error getting stay details for {stay_id}: {e}")
            raise DatabaseError(f"Unable to retrieve complete stay details: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting stay details for {stay_id}: {e}")
            error_msg = self._get_user_friendly_error(e, "retrieving stay details")
            raise DatabaseError(error_msg) from e
    
    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def search_diagnoses(self, icd_code: Optional[str] = None, 
                        icd_title: Optional[str] = None) -> List[Dict]:
        """
        Search diagnoses by ICD code or title.
        
        Args:
            icd_code: Optional ICD code to search for
            icd_title: Optional ICD title to search for (partial match)
            
        Returns:
            List of matching diagnoses
            
        Raises:
            ValidationError: If search parameters are invalid
            DatabaseError: If search fails
        """
        try:
            # Validate inputs
            if not icd_code and not icd_title:
                raise ValidationError("At least one search parameter (ICD code or title) must be provided")
            
            if icd_code and not re.match(r'^[A-Z0-9.]+$', icd_code):
                raise ValidationError(f"Invalid ICD code format: {icd_code}")
            
            # Ensure connection is healthy
            self._ensure_connection_healthy()
            filters = {}
            
            if icd_code:
                filters['icd_code'] = icd_code
            
            diagnoses_df = self.get_table_data('diagnosis', filters)
            
            # If searching by title, filter after retrieval (Supabase doesn't support LIKE in basic API)
            if icd_title and not diagnoses_df.empty:
                diagnoses_df = diagnoses_df[
                    diagnoses_df['icd_title'].str.contains(icd_title, case=False, na=False)
                ]
            
            result = diagnoses_df.to_dict('records') if not diagnoses_df.empty else []
            logger.info(f"Found {len(result)} matching diagnoses")
            return result
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except DatabaseError as e:
            logger.error(f"Database error searching diagnoses: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching diagnoses: {e}")
            error_msg = self._get_user_friendly_error(e, "searching diagnoses")
            raise DatabaseError(error_msg) from e
    
    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_vital_signs(self, stay_id: int) -> List[Dict]:
        """
        Get vital signs for a specific stay.
        
        Args:
            stay_id: Stay identifier
            
        Returns:
            List of vital sign measurements
            
        Raises:
            ValidationError: If stay_id is invalid
            DatabaseError: If data retrieval fails
        """
        try:
            # Validate input
            if not isinstance(stay_id, int) or stay_id <= 0:
                raise ValidationError(f"Invalid stay ID: {stay_id}. Stay ID must be a positive integer.")
            
            # Ensure connection is healthy
            self._ensure_connection_healthy()
            vitals_df = self.get_table_data('vitalsign', {'stay_id': stay_id})
            
            if not vitals_df.empty:
                # Sort by charttime
                vitals_df['charttime'] = pd.to_datetime(vitals_df['charttime'])
                vitals_df = vitals_df.sort_values('charttime')
                result = vitals_df.to_dict('records')
            else:
                result = []
            
            logger.info(f"Retrieved {len(result)} vital sign measurements for stay {stay_id}")
            return result
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except DatabaseError as e:
            logger.error(f"Database error getting vital signs for stay {stay_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting vital signs for stay {stay_id}: {e}")
            error_msg = self._get_user_friendly_error(e, "retrieving vital signs")
            raise DatabaseError(error_msg) from e
    
    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_medication_history(self, subject_id: int) -> List[Dict]:
        """
        Get medication history for a patient.
        
        Args:
            subject_id: Patient identifier
            
        Returns:
            List of medication records
            
        Raises:
            ValidationError: If subject_id is invalid
            DatabaseError: If data retrieval fails
        """
        try:
            # Validate input
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"Invalid patient ID: {subject_id}. Patient ID must be a positive integer.")
            
            # Ensure connection is healthy
            self._ensure_connection_healthy()
            # Get from both medrecon and pyxis tables
            medrecon_df = self.get_table_data('medrecon', {'subject_id': subject_id})
            pyxis_df = self.get_table_data('pyxis', {'subject_id': subject_id})
            
            medications = []
            
            if not medrecon_df.empty:
                medrecon_records = medrecon_df.to_dict('records')
                for record in medrecon_records:
                    record['source'] = 'medrecon'
                medications.extend(medrecon_records)
            
            if not pyxis_df.empty:
                pyxis_records = pyxis_df.to_dict('records')
                for record in pyxis_records:
                    record['source'] = 'pyxis'
                medications.extend(pyxis_records)
            
            # Sort by charttime if available
            if medications:
                medications.sort(key=lambda x: x.get('charttime', ''), reverse=True)
            
            logger.info(f"Retrieved {len(medications)} medication records for patient {subject_id}")
            return medications
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except DatabaseError as e:
            logger.error(f"Database error getting medication history for patient {subject_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting medication history for patient {subject_id}: {e}")
            error_msg = self._get_user_friendly_error(e, "retrieving medication history")
            raise DatabaseError(error_msg) from e
    
    def _format_temperature(self, temp: Optional[float]) -> Dict[str, Any]:
        """Format temperature with medical context."""
        if temp is None or pd.isna(temp):
            return {'value': None, 'unit': '°F', 'status': 'Not recorded'}
        
        # Assume Fahrenheit (MIMIC-IV-ED standard)
        status = 'Normal'
        if temp < 97.0:
            status = 'Hypothermia'
        elif temp > 100.4:
            status = 'Fever'
        elif temp > 99.0:
            status = 'Low-grade fever'
        
        return {
            'value': round(temp, 1),
            'unit': '°F',
            'status': status,
            'celsius': round((temp - 32) * 5/9, 1)
        }
    
    def _format_heart_rate(self, hr: Optional[float]) -> Dict[str, Any]:
        """Format heart rate with medical context."""
        if hr is None or pd.isna(hr):
            return {'value': None, 'unit': 'bpm', 'status': 'Not recorded'}
        
        status = 'Normal'
        if hr < 60:
            status = 'Bradycardia'
        elif hr > 100:
            status = 'Tachycardia'
        
        return {
            'value': int(hr),
            'unit': 'bpm',
            'status': status
        }
    
    def _format_respiratory_rate(self, rr: Optional[float]) -> Dict[str, Any]:
        """Format respiratory rate with medical context."""
        if rr is None or pd.isna(rr):
            return {'value': None, 'unit': 'breaths/min', 'status': 'Not recorded'}
        
        status = 'Normal'
        if rr < 12:
            status = 'Bradypnea'
        elif rr > 20:
            status = 'Tachypnea'
        
        return {
            'value': int(rr),
            'unit': 'breaths/min',
            'status': status
        }
    
    def _format_oxygen_sat(self, o2sat: Optional[float]) -> Dict[str, Any]:
        """Format oxygen saturation with medical context."""
        if o2sat is None or pd.isna(o2sat):
            return {'value': None, 'unit': '%', 'status': 'Not recorded'}
        
        status = 'Normal'
        if o2sat < 90:
            status = 'Severe hypoxemia'
        elif o2sat < 95:
            status = 'Mild hypoxemia'
        
        return {
            'value': int(o2sat),
            'unit': '%',
            'status': status
        }
    
    def _format_blood_pressure(self, sbp: Optional[float], dbp: Optional[float]) -> Dict[str, Any]:
        """Format blood pressure with medical context."""
        if (sbp is None or pd.isna(sbp)) and (dbp is None or pd.isna(dbp)):
            return {'systolic': None, 'diastolic': None, 'status': 'Not recorded'}
        
        # Handle partial readings
        sys_val = int(sbp) if sbp is not None and not pd.isna(sbp) else None
        dia_val = int(dbp) if dbp is not None and not pd.isna(dbp) else None
        
        # Determine status based on available values
        status = 'Normal'
        if sys_val is not None and dia_val is not None:
            if sys_val >= 180 or dia_val >= 120:
                status = 'Hypertensive crisis'
            elif sys_val >= 140 or dia_val >= 90:
                status = 'Hypertension'
            elif sys_val < 90 or dia_val < 60:
                status = 'Hypotension'
        elif sys_val is not None:
            if sys_val >= 180:
                status = 'Hypertensive crisis (systolic)'
            elif sys_val >= 140:
                status = 'Hypertension (systolic)'
            elif sys_val < 90:
                status = 'Hypotension (systolic)'
        
        return {
            'systolic': sys_val,
            'diastolic': dia_val,
            'reading': f"{sys_val or '?'}/{dia_val or '?'}",
            'status': status
        }
    
    def get_medications_by_stay(self, stay_id: int) -> List[Dict]:
        """
        Get medications for a specific stay.
        
        Args:
            stay_id: Stay identifier
            
        Returns:
            List of medication records for the stay
        """
        try:
            # Get from both medrecon and pyxis tables
            medrecon_df = self.get_table_data('medrecon', {'stay_id': stay_id})
            pyxis_df = self.get_table_data('pyxis', {'stay_id': stay_id})
            
            medications = []
            
            if not medrecon_df.empty:
                medrecon_records = medrecon_df.to_dict('records')
                for record in medrecon_records:
                    record['source'] = 'medrecon'
                medications.extend(medrecon_records)
            
            if not pyxis_df.empty:
                pyxis_records = pyxis_df.to_dict('records')
                for record in pyxis_records:
                    record['source'] = 'pyxis'
                medications.extend(pyxis_records)
            
            # Sort by charttime if available
            if medications:
                medications.sort(key=lambda x: x.get('charttime', ''), reverse=True)
            
            logger.info(f"Retrieved {len(medications)} medication records for stay {stay_id}")
            return medications
            
        except Exception as e:
            logger.error(f"Failed to get medications for stay {stay_id}: {e}")
            raise
    
    def get_patient_diagnoses(self, subject_id: int) -> List[Dict]:
        """
        Get all diagnoses for a patient.
        
        Args:
            subject_id: Patient identifier
            
        Returns:
            List of diagnosis records for the patient
        """
        try:
            diagnosis_df = self.get_table_data('diagnosis', {'subject_id': subject_id})
            
            if diagnosis_df.empty:
                logger.info(f"No diagnoses found for patient {subject_id}")
                return []
            
            diagnoses = diagnosis_df.to_dict('records')
            
            # Sort by sequence number if available
            diagnoses.sort(key=lambda x: x.get('seq_num', 0))
            
            logger.info(f"Retrieved {len(diagnoses)} diagnoses for patient {subject_id}")
            return diagnoses
            
        except Exception as e:
            logger.error(f"Failed to get diagnoses for patient {subject_id}: {e}")
            raise
    
    def get_stay_diagnoses(self, stay_id: int) -> List[Dict]:
        """
        Get diagnoses for a specific stay.
        
        Args:
            stay_id: Stay identifier
            
        Returns:
            List of diagnosis records for the stay
        """
        try:
            diagnosis_df = self.get_table_data('diagnosis', {'stay_id': stay_id})
            
            if diagnosis_df.empty:
                logger.info(f"No diagnoses found for stay {stay_id}")
                return []
            
            diagnoses = diagnosis_df.to_dict('records')
            
            # Sort by sequence number if available
            diagnoses.sort(key=lambda x: x.get('seq_num', 0))
            
            logger.info(f"Retrieved {len(diagnoses)} diagnoses for stay {stay_id}")
            return diagnoses
            
        except Exception as e:
            logger.error(f"Failed to get diagnoses for stay {stay_id}: {e}")
            raise
    
    @retry_on_failure(max_retries=2, delay=0.5)
    def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query (SELECT only for security).
        
        Args:
            query: SQL SELECT query string
            params: Optional query parameters (not used with Supabase RPC)
            
        Returns:
            List of result dictionaries
            
        Raises:
            ValidationError: If query is invalid or unsafe
            DatabaseError: If query execution fails
        """
        try:
            # Sanitize query: remove trailing semicolons (Supabase RPC doesn't accept them)
            query = query.strip()
            while query.endswith(';'):
                query = query[:-1].strip()
            
            # Validate query is SELECT only
            query_upper = query.upper()
            if not query_upper.startswith('SELECT'):
                raise ValidationError("Only SELECT queries are allowed")
            
            # Check for dangerous keywords
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    raise ValidationError(f"Query contains forbidden keyword: {keyword}")
            
            logger.info(f"Executing custom query: {query[:200]}...")
            
            # Get connection (either from pool or direct)
            with self._get_connection() as supabase_client:
                # Use Supabase RPC to execute raw SQL
                # Note: This requires a stored procedure in Supabase
                result = supabase_client.rpc('execute_readonly_query', {'query_text': query}).execute()
                
                if hasattr(result, 'data') and result.data:
                    logger.info(f"Custom query returned {len(result.data)} rows")
                    return result.data
                else:
                    logger.info("Custom query returned no results")
                    return []
                
        except ValidationError:
            raise
        except Exception as e:
            error_msg = f"Custom query execution failed: {str(e)}"
            logger.error(error_msg)
            
            # If RPC doesn't exist, provide helpful error
            if 'function' in str(e).lower() and 'does not exist' in str(e).lower():
                raise DatabaseError(
                    "Custom SQL queries require a stored procedure in Supabase. "
                    "Please use specific query methods (patient_summary, stay_details, etc.) instead."
                )
            
            raise DatabaseError(error_msg)
