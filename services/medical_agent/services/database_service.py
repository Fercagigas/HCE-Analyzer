"""
Database Service for Medical Agent (MIMIC-IV clinical demo 2.2)

Provides secure, read-only access to the MIMIC-IV clinical database
(schemas `mimiciv_hosp` and `mimiciv_icu`) for the medical conversation agent,
with connection management, query validation and clinical formatting helpers.

Data model note:
    This service was migrated from MIMIC-IV-ED (schema `mimic_ed`, ED stays) to
    the full MIMIC-IV clinical demo. The episode key is now the hospital
    admission `hadm_id` (table `admissions`), not the ED `stay_id`. ICU stays are
    identified by `stay_id` in `mimiciv_icu.icustays`.
"""

import logging
import re
import time
from typing import Dict, Any, Optional, List
import pandas as pd
from supabase import create_client, Client
from config.settings import settings
from services.connection_pool_manager import connection_pool_manager
from functools import wraps

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
    """Decorator to retry database operations on transient failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ValidationError:
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
                    if any(k in error_str for k in ['connection', 'timeout', 'network', 'server error']):
                        if attempt == max_retries:
                            logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                            break
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
            raise DatabaseError(f"Operation failed after {max_retries} retries: {str(last_exception)}")
        return wrapper
    return decorator


def timeout_handler(timeout_seconds: int = 30):
    """Decorator to log slow queries and normalise timeout errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
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
    Read-only data access for the MIMIC-IV clinical demo.

    Table names are mapped to their schema internally; callers never provide a
    schema name. Writes are never performed by this service.
    """

    # Table -> schema mapping (single source of truth for the adapter).
    TABLE_SCHEMA: Dict[str, str] = {
        # hosp
        'patients': 'mimiciv_hosp',
        'admissions': 'mimiciv_hosp',
        'transfers': 'mimiciv_hosp',
        'services': 'mimiciv_hosp',
        'diagnoses_icd': 'mimiciv_hosp',
        'procedures_icd': 'mimiciv_hosp',
        'd_icd_diagnoses': 'mimiciv_hosp',
        'd_icd_procedures': 'mimiciv_hosp',
        'labevents': 'mimiciv_hosp',
        'd_labitems': 'mimiciv_hosp',
        'microbiologyevents': 'mimiciv_hosp',
        'omr': 'mimiciv_hosp',
        'prescriptions': 'mimiciv_hosp',
        'pharmacy': 'mimiciv_hosp',
        'emar': 'mimiciv_hosp',
        # icu
        'icustays': 'mimiciv_icu',
        'chartevents': 'mimiciv_icu',
        'd_items': 'mimiciv_icu',
    }

    ALLOWED_TABLES = set(TABLE_SCHEMA.keys())

    # Schemas that may appear (prefixed) in custom SQL. Kept in sync with settings.
    ALLOWED_SCHEMAS = {'mimiciv_hosp', 'mimiciv_icu'}

    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
        'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'UNION', 'DECLARE', 'CURSOR',
        'COPY', 'VACUUM', 'ANALYZE', 'COMMENT', 'SECURITY', 'OWNER',
    }

    # A stable, cheap table for health checks.
    _HEALTH_TABLE = 'patients'
    _HEALTH_SCHEMA = 'mimiciv_hosp'

    def __init__(self):
        """Initialize database service with connection pooling."""
        self.supabase: Optional[Client] = None
        self._connection_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 300
        self._use_connection_pool = True

        try:
            if self._use_connection_pool:
                try:
                    with connection_pool_manager.get_db_connection() as conn:
                        conn.schema(self._HEALTH_SCHEMA).table(self._HEALTH_TABLE).select('subject_id').limit(1).execute()
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
            result = self.supabase.schema(self._HEALTH_SCHEMA).table(self._HEALTH_TABLE).select('subject_id').limit(1).execute()
            if not hasattr(result, 'data'):
                raise ConnectionError("Invalid response from database")
            return True
        except Exception as e:
            raise ConnectionError(f"Connection test failed: {str(e)}")

    def _schema_for(self, table_name: str) -> str:
        """Return the schema that owns a table, or raise if not allowlisted."""
        schema = self.TABLE_SCHEMA.get(table_name)
        if schema is None:
            raise ValidationError(
                f"Access to table '{table_name}' is not permitted. "
                f"Available tables: {', '.join(sorted(self.ALLOWED_TABLES))}"
            )
        return schema

    def _get_connection(self):
        """Get a database connection, either from pool or direct connection."""
        if self._use_connection_pool:
            return connection_pool_manager.get_db_connection()
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
            return
        current_time = time.time()
        if (current_time - self._last_health_check) > self._health_check_interval or not self._connection_healthy:
            try:
                self._test_connection()
                self._connection_healthy = True
                self._last_health_check = current_time
            except Exception as e:
                logger.warning(f"Connection health check failed: {e}")
                self._connection_healthy = False
                try:
                    self._initialize_connection()
                except Exception as reconnect_error:
                    raise ConnectionError(f"Failed to reconnect to database: {str(reconnect_error)}")

    def _get_user_friendly_error(self, error: Exception, operation: str = "database operation") -> str:
        """Convert technical database errors to user-friendly messages."""
        error_str = str(error).lower()
        if "connection" in error_str or "network" in error_str:
            return "Unable to connect to the medical database. Please check your internet connection and try again."
        elif "timeout" in error_str:
            return "The database query is taking longer than expected. Please try a more specific search or try again later."
        elif "permission" in error_str or "unauthorized" in error_str:
            return "You don't have permission to access this medical data. Please contact your administrator."
        elif "not found" in error_str or "does not exist" in error_str:
            return "The requested medical record was not found in the database."
        elif "invalid" in error_str or "syntax" in error_str:
            return "There was an issue with your search request. Please try rephrasing your question."
        elif "rate limit" in error_str or "too many requests" in error_str:
            return "Too many requests have been made. Please wait a moment and try again."
        elif "server error" in error_str or "internal error" in error_str:
            return "The medical database is experiencing technical difficulties. Please try again in a few minutes."
        else:
            return "An unexpected error occurred while accessing medical data. Please try again or contact support if the problem persists."

    def _validate_query(self, query: str) -> bool:
        """Validate SQL query for security with defense-in-depth."""
        if not query or not query.strip():
            logger.warning("Empty query rejected")
            return False
        if len(query) > 2000:
            logger.warning("Query exceeds maximum length of 2000 characters")
            return False

        query_upper = query.upper().strip()
        if not query_upper.startswith('SELECT'):
            logger.warning("Query does not start with SELECT")
            return False

        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                logger.warning(f"Dangerous keyword '{keyword}' found in query")
                return False

        if ';' in query or '--' in query or '/*' in query:
            logger.warning("Query contains forbidden characters (;, --, /*)")
            return False

        if re.search(r'\b(?:PG_|INFORMATION_SCHEMA)\b', query_upper):
            logger.warning("Query attempts to access system tables")
            return False

        dangerous_functions = [
            'PG_SLEEP', 'PG_READ_FILE', 'PG_WRITE_FILE',
            'DBLINK', 'LO_IMPORT', 'LO_EXPORT',
            'CURRENT_SETTING', 'SET_CONFIG',
        ]
        for func in dangerous_functions:
            if func in query_upper:
                logger.warning(f"Dangerous function '{func}' found in query")
                return False

        # Only allowlisted tables may be referenced, with or without schema prefix.
        table_pattern = r'(?:FROM|JOIN)\s+(?:(MIMICIV_HOSP|MIMICIV_ICU)\.)?(\w+)'
        for _schema, table in re.findall(table_pattern, query_upper):
            if table.lower() not in self.ALLOWED_TABLES:
                logger.warning(f"Unauthorized table '{table}' in query")
                return False

        return True

    def _sanitize_params(self, params: Optional[Dict]) -> Dict:
        """Sanitize query parameters."""
        if not params:
            return {}
        sanitized = {}
        for key, value in params.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                logger.warning(f"Invalid parameter key: {key}")
                continue
            if isinstance(value, (int, float, str, bool)):
                sanitized[key] = value
            else:
                logger.warning(f"Invalid parameter type for {key}: {type(value)}")
        return sanitized

    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Deprecated raw SQL path. Use specific methods or execute_custom_query."""
        if not self._validate_query(query):
            raise ValueError("Query validation failed - unsafe or unauthorized query")
        raise NotImplementedError("Direct SQL execution not implemented. Use specific query methods.")

    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_table_data(self, table_name: str, filters: Optional[Dict] = None,
                       columns: Optional[List[str]] = None, limit: int = 1000) -> pd.DataFrame:
        """Get data from an allowlisted table with optional filters."""
        try:
            schema = self._schema_for(table_name)

            if limit > settings.medical_agent.max_result_rows:
                limit = settings.medical_agent.max_result_rows
                logger.info(f"Limiting results to {limit} rows for performance")

            with self._get_connection() as supabase_client:
                query = supabase_client.schema(schema).table(table_name)

                if columns:
                    safe_columns = [col for col in columns if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col)]
                    if len(safe_columns) != len(columns):
                        invalid_columns = set(columns) - set(safe_columns)
                        raise ValidationError(f"Invalid column names: {', '.join(invalid_columns)}")
                    query = query.select(','.join(safe_columns))
                else:
                    query = query.select('*')

                if filters:
                    for key, value in filters.items():
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                            raise ValidationError(f"Invalid filter column name: {key}")
                        query = query.eq(key, value)

                start_time = time.time()
                result = query.limit(limit).execute()
                execution_time = time.time() - start_time

                if execution_time > 5.0:
                    logger.warning(f"Slow query detected: {table_name} took {execution_time:.2f}s")

                if result.data:
                    df = pd.DataFrame(result.data)
                    logger.info(f"Retrieved {len(df)} rows from {table_name} in {execution_time:.2f}s")
                    return df
                logger.info(f"No data found in {table_name} with given filters")
                return pd.DataFrame()

        except ValidationError:
            raise
        except Exception as e:
            error_msg = self._get_user_friendly_error(e, f"retrieving data from {table_name}")
            logger.error(f"Failed to get data from {table_name}: {e}")
            raise DatabaseError(error_msg) from e

    # ------------------------------------------------------------------
    # Clinical convenience operations (MIMIC-IV hosp/icu model)
    # ------------------------------------------------------------------

    @retry_on_failure(max_retries=2, delay=1.0, backoff=2.0)
    @timeout_handler(timeout_seconds=45)
    def get_patient_summary(self, subject_id: int) -> Dict[str, Any]:
        """Comprehensive patient summary across demographics, admissions,
        diagnoses, labs and medications."""
        try:
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"Invalid patient ID: {subject_id}. Patient ID must be a positive integer.")

            logger.info(f"Generating patient summary for subject_id: {subject_id}")
            summary: Dict[str, Any] = {
                'subject_id': subject_id,
                'demographics': {},
                'admissions': [],
                'diagnoses': [],
                'recent_labs': [],
                'medications': [],
                'summary_stats': {
                    'total_admissions': 0,
                    'total_diagnoses': 0,
                    'total_medications': 0,
                    'last_admission': None,
                },
            }

            # Demographics from patients
            try:
                pat_df = self.get_table_data('patients', {'subject_id': subject_id})
                if not pat_df.empty:
                    p = pat_df.iloc[0]
                    summary['demographics'] = {
                        'gender': p.get('gender', 'Unknown'),
                        'anchor_age': p.get('anchor_age'),
                        'anchor_year_group': p.get('anchor_year_group'),
                        'deceased': bool(p.get('dod')),
                    }
            except DatabaseError as e:
                logger.warning(f"Demographics error for patient {subject_id}: {e}")

            # Admissions
            try:
                adm_df = self.get_table_data('admissions', {'subject_id': subject_id})
                if not adm_df.empty:
                    formatted = []
                    for _, a in adm_df.iterrows():
                        formatted.append({
                            'hadm_id': a.get('hadm_id'),
                            'admittime': a.get('admittime'),
                            'dischtime': a.get('dischtime'),
                            'admission_type': a.get('admission_type'),
                            'admission_location': a.get('admission_location'),
                            'discharge_location': a.get('discharge_location'),
                            'race': a.get('race'),
                            'hospital_expire_flag': a.get('hospital_expire_flag'),
                        })
                    summary['admissions'] = formatted
                    summary['summary_stats']['total_admissions'] = len(formatted)
                    if 'admittime' in adm_df.columns:
                        summary['summary_stats']['last_admission'] = adm_df['admittime'].max()
                    if not summary['demographics'].get('race') and not adm_df.empty:
                        summary['demographics']['race'] = adm_df.iloc[0].get('race')
            except DatabaseError as e:
                logger.warning(f"Admissions error for patient {subject_id}: {e}")
                summary.setdefault('errors', []).append(f"Could not retrieve admissions: {str(e)}")

            # Diagnoses (with human-readable titles)
            try:
                diagnoses = self.get_patient_diagnoses(subject_id)
                summary['diagnoses'] = diagnoses
                summary['summary_stats']['total_diagnoses'] = len(diagnoses)
            except DatabaseError as e:
                logger.warning(f"Diagnoses error for patient {subject_id}: {e}")
                summary.setdefault('errors', []).append(f"Could not retrieve diagnoses: {str(e)}")

            # Recent labs
            try:
                labs_df = self.get_table_data('labevents', {'subject_id': subject_id}, limit=200)
                if not labs_df.empty and 'charttime' in labs_df.columns:
                    labs_df['charttime'] = pd.to_datetime(labs_df['charttime'], errors='coerce')
                    labs_df = labs_df.sort_values('charttime').tail(20)
                    summary['recent_labs'] = labs_df.to_dict('records')
            except DatabaseError as e:
                logger.warning(f"Labs error for patient {subject_id}: {e}")

            # Medications
            try:
                medications = self.get_medication_history(subject_id)
                summary['medications'] = medications[:10]
                summary['summary_stats']['total_medications'] = len(medications)
            except DatabaseError as e:
                logger.warning(f"Medication error for patient {subject_id}: {e}")
                summary.setdefault('errors', []).append(f"Could not retrieve medications: {str(e)}")

            logger.info(f"Generated comprehensive summary for patient {subject_id}")
            return summary

        except ValidationError:
            raise
        except DatabaseError as e:
            logger.error(f"Database error getting patient summary for {subject_id}: {e}")
            raise DatabaseError(f"Unable to retrieve complete patient summary: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting patient summary for {subject_id}: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "retrieving patient summary")) from e

    @retry_on_failure(max_retries=2, delay=1.0, backoff=2.0)
    @timeout_handler(timeout_seconds=45)
    def get_admission_details(self, hadm_id: int) -> Dict[str, Any]:
        """Hospital admission details: admission info, diagnoses, transfers, labs."""
        try:
            if not isinstance(hadm_id, int) or hadm_id <= 0:
                raise ValidationError(f"Invalid admission ID: {hadm_id}. hadm_id must be a positive integer.")

            logger.info(f"Generating admission details for hadm_id: {hadm_id}")
            details: Dict[str, Any] = {
                'hadm_id': hadm_id,
                'admission_info': {},
                'diagnoses': [],
                'transfers': [],
                'services': [],
            }

            adm_df = self.get_table_data('admissions', {'hadm_id': hadm_id})
            if not adm_df.empty:
                details['admission_info'] = adm_df.iloc[0].to_dict()

            diag_df = self.get_table_data('diagnoses_icd', {'hadm_id': hadm_id})
            if not diag_df.empty:
                details['diagnoses'] = self._enrich_diagnoses(diag_df.to_dict('records'))

            trans_df = self.get_table_data('transfers', {'hadm_id': hadm_id})
            if not trans_df.empty:
                details['transfers'] = trans_df.to_dict('records')

            svc_df = self.get_table_data('services', {'hadm_id': hadm_id})
            if not svc_df.empty:
                details['services'] = svc_df.to_dict('records')

            return details

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting admission details for {hadm_id}: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "retrieving admission details")) from e

    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def search_diagnoses(self, icd_code: Optional[str] = None,
                         icd_title: Optional[str] = None) -> List[Dict]:
        """Search the ICD diagnosis dictionary by code or (partial) title."""
        try:
            if not icd_code and not icd_title:
                raise ValidationError("At least one search parameter (ICD code or title) must be provided")
            if icd_code and not re.match(r'^[A-Za-z0-9.]+$', icd_code):
                raise ValidationError(f"Invalid ICD code format: {icd_code}")

            self._ensure_connection_healthy()
            filters = {}
            if icd_code:
                filters['icd_code'] = icd_code

            dict_df = self.get_table_data('d_icd_diagnoses', filters)
            if icd_title and not dict_df.empty and 'long_title' in dict_df.columns:
                dict_df = dict_df[dict_df['long_title'].str.contains(icd_title, case=False, na=False)]

            result = dict_df.to_dict('records') if not dict_df.empty else []
            logger.info(f"Found {len(result)} matching diagnoses")
            return result
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching diagnoses: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "searching diagnoses")) from e

    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_icu_chartevents(self, stay_id: int, itemid: Optional[int] = None) -> List[Dict]:
        """ICU charted measurements (vital signs and monitored values) for an ICU stay."""
        try:
            if not isinstance(stay_id, int) or stay_id <= 0:
                raise ValidationError(f"Invalid ICU stay ID: {stay_id}. stay_id must be a positive integer.")

            self._ensure_connection_healthy()
            filters = {'stay_id': stay_id}
            if itemid is not None:
                filters['itemid'] = itemid

            ce_df = self.get_table_data('chartevents', filters)
            if not ce_df.empty and 'charttime' in ce_df.columns:
                ce_df['charttime'] = pd.to_datetime(ce_df['charttime'], errors='coerce')
                ce_df = ce_df.sort_values('charttime')
                result = ce_df.to_dict('records')
            else:
                result = []
            logger.info(f"Retrieved {len(result)} chartevents for ICU stay {stay_id}")
            return result
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting chartevents for ICU stay {stay_id}: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "retrieving ICU chartevents")) from e

    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_lab_results(self, subject_id: int, hadm_id: Optional[int] = None) -> List[Dict]:
        """Laboratory results for a patient, optionally scoped to one admission."""
        try:
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"Invalid patient ID: {subject_id}. subject_id must be a positive integer.")

            self._ensure_connection_healthy()
            filters = {'subject_id': subject_id}
            if hadm_id is not None:
                filters['hadm_id'] = hadm_id

            labs_df = self.get_table_data('labevents', filters)
            if not labs_df.empty and 'charttime' in labs_df.columns:
                labs_df['charttime'] = pd.to_datetime(labs_df['charttime'], errors='coerce')
                labs_df = labs_df.sort_values('charttime')
                result = labs_df.to_dict('records')
            else:
                result = []
            logger.info(f"Retrieved {len(result)} lab results for patient {subject_id}")
            return result
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting lab results for patient {subject_id}: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "retrieving lab results")) from e

    @retry_on_failure(max_retries=2, delay=0.5, backoff=2.0)
    @timeout_handler(timeout_seconds=30)
    def get_medication_history(self, subject_id: int) -> List[Dict]:
        """Medication history for a patient from prescriptions and eMAR."""
        try:
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"Invalid patient ID: {subject_id}. subject_id must be a positive integer.")

            self._ensure_connection_healthy()
            rx_df = self.get_table_data('prescriptions', {'subject_id': subject_id})
            emar_df = self.get_table_data('emar', {'subject_id': subject_id})

            medications: List[Dict] = []
            if not rx_df.empty:
                for record in rx_df.to_dict('records'):
                    record['source'] = 'prescriptions'
                    record.setdefault('medication', record.get('drug'))
                    medications.append(record)
            if not emar_df.empty:
                for record in emar_df.to_dict('records'):
                    record['source'] = 'emar'
                    medications.append(record)

            if medications:
                medications.sort(key=lambda x: str(x.get('starttime') or x.get('charttime') or ''), reverse=True)

            logger.info(f"Retrieved {len(medications)} medication records for patient {subject_id}")
            return medications
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting medication history for patient {subject_id}: {e}")
            raise DatabaseError(self._get_user_friendly_error(e, "retrieving medication history")) from e

    def get_medications_by_admission(self, hadm_id: int) -> List[Dict]:
        """Medications for a specific hospital admission (prescriptions + eMAR)."""
        try:
            rx_df = self.get_table_data('prescriptions', {'hadm_id': hadm_id})
            emar_df = self.get_table_data('emar', {'hadm_id': hadm_id})
            medications: List[Dict] = []
            if not rx_df.empty:
                for record in rx_df.to_dict('records'):
                    record['source'] = 'prescriptions'
                    record.setdefault('medication', record.get('drug'))
                    medications.append(record)
            if not emar_df.empty:
                for record in emar_df.to_dict('records'):
                    record['source'] = 'emar'
                    medications.append(record)
            if medications:
                medications.sort(key=lambda x: str(x.get('starttime') or x.get('charttime') or ''), reverse=True)
            logger.info(f"Retrieved {len(medications)} medication records for admission {hadm_id}")
            return medications
        except Exception as e:
            logger.error(f"Failed to get medications for admission {hadm_id}: {e}")
            raise

    def _enrich_diagnoses(self, diagnoses: List[Dict]) -> List[Dict]:
        """Attach long_title from the ICD dictionary to raw diagnosis rows."""
        if not diagnoses:
            return []
        try:
            codes = {(d.get('icd_code'), d.get('icd_version')) for d in diagnoses if d.get('icd_code')}
            titles: Dict[tuple, str] = {}
            for code, version in codes:
                dict_df = self.get_table_data(
                    'd_icd_diagnoses', {'icd_code': code, 'icd_version': version}, limit=1
                )
                if not dict_df.empty:
                    titles[(code, version)] = dict_df.iloc[0].get('long_title')
            for d in diagnoses:
                d['long_title'] = titles.get((d.get('icd_code'), d.get('icd_version')))
        except Exception as e:
            logger.warning(f"Could not enrich diagnoses with titles: {e}")
        return diagnoses

    def get_patient_diagnoses(self, subject_id: int) -> List[Dict]:
        """All diagnoses for a patient, enriched with ICD titles."""
        try:
            diag_df = self.get_table_data('diagnoses_icd', {'subject_id': subject_id})
            if diag_df.empty:
                logger.info(f"No diagnoses found for patient {subject_id}")
                return []
            diagnoses = diag_df.to_dict('records')
            diagnoses.sort(key=lambda x: (x.get('hadm_id') or 0, x.get('seq_num') or 0))
            return self._enrich_diagnoses(diagnoses)
        except Exception as e:
            logger.error(f"Failed to get diagnoses for patient {subject_id}: {e}")
            raise

    def get_admission_diagnoses(self, hadm_id: int) -> List[Dict]:
        """Diagnoses for a specific hospital admission, enriched with ICD titles."""
        try:
            diag_df = self.get_table_data('diagnoses_icd', {'hadm_id': hadm_id})
            if diag_df.empty:
                logger.info(f"No diagnoses found for admission {hadm_id}")
                return []
            diagnoses = diag_df.to_dict('records')
            diagnoses.sort(key=lambda x: x.get('seq_num') or 0)
            return self._enrich_diagnoses(diagnoses)
        except Exception as e:
            logger.error(f"Failed to get diagnoses for admission {hadm_id}: {e}")
            raise

    # --- Clinical formatting helpers (unit-aware, dataset agnostic) ---

    def _format_temperature(self, temp: Optional[float]) -> Dict[str, Any]:
        if temp is None or pd.isna(temp):
            return {'value': None, 'unit': '°C', 'status': 'Not recorded'}
        status = 'Normal'
        if temp < 35.0:
            status = 'Hypothermia'
        elif temp > 38.0:
            status = 'Fever'
        elif temp > 37.5:
            status = 'Low-grade fever'
        return {'value': round(temp, 1), 'unit': '°C', 'status': status}

    def _format_heart_rate(self, hr: Optional[float]) -> Dict[str, Any]:
        if hr is None or pd.isna(hr):
            return {'value': None, 'unit': 'bpm', 'status': 'Not recorded'}
        status = 'Normal'
        if hr < 60:
            status = 'Bradycardia'
        elif hr > 100:
            status = 'Tachycardia'
        return {'value': int(hr), 'unit': 'bpm', 'status': status}

    def _format_respiratory_rate(self, rr: Optional[float]) -> Dict[str, Any]:
        if rr is None or pd.isna(rr):
            return {'value': None, 'unit': 'breaths/min', 'status': 'Not recorded'}
        status = 'Normal'
        if rr < 12:
            status = 'Bradypnea'
        elif rr > 20:
            status = 'Tachypnea'
        return {'value': int(rr), 'unit': 'breaths/min', 'status': status}

    def _format_oxygen_sat(self, o2sat: Optional[float]) -> Dict[str, Any]:
        if o2sat is None or pd.isna(o2sat):
            return {'value': None, 'unit': '%', 'status': 'Not recorded'}
        status = 'Normal'
        if o2sat < 90:
            status = 'Severe hypoxemia'
        elif o2sat < 95:
            status = 'Mild hypoxemia'
        return {'value': int(o2sat), 'unit': '%', 'status': status}

    def _format_blood_pressure(self, sbp: Optional[float], dbp: Optional[float]) -> Dict[str, Any]:
        if (sbp is None or pd.isna(sbp)) and (dbp is None or pd.isna(dbp)):
            return {'systolic': None, 'diastolic': None, 'status': 'Not recorded'}
        sys_val = int(sbp) if sbp is not None and not pd.isna(sbp) else None
        dia_val = int(dbp) if dbp is not None and not pd.isna(dbp) else None
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
            'status': status,
        }

    @retry_on_failure(max_retries=2, delay=0.5)
    def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a custom read-only SQL query through the Supabase RPC."""
        try:
            query = query.strip()
            while query.endswith(';'):
                query = query[:-1].strip()

            query_upper = query.upper()
            if not query_upper.startswith('SELECT'):
                raise ValidationError("Only SELECT queries are allowed")

            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
            for keyword in dangerous_keywords:
                if re.search(r'\b' + keyword + r'\b', query_upper):
                    raise ValidationError(f"Query contains forbidden keyword: {keyword}")

            logger.info(f"Executing custom query: {query[:200]}...")

            with self._get_connection() as supabase_client:
                result = supabase_client.rpc('execute_readonly_query', {'query_text': query}).execute()
                if hasattr(result, 'data') and result.data:
                    logger.info(f"Custom query returned {len(result.data)} rows")
                    return result.data
                logger.info("Custom query returned no results")
                return []
        except ValidationError:
            raise
        except Exception as e:
            error_msg = f"Custom query execution failed: {str(e)}"
            logger.error(error_msg)
            if 'function' in str(e).lower() and 'does not exist' in str(e).lower():
                raise DatabaseError(
                    "Custom SQL queries require a stored procedure in Supabase. "
                    "Please use specific query methods instead."
                )
            raise DatabaseError(error_msg)
