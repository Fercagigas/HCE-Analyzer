"""
Database Tool for Unified Chat System

This module provides a Claude-compatible tool for querying the MIMIC-IV clinical
database (schemas `mimiciv_hosp` and `mimiciv_icu`). It supports multiple query
types with comprehensive validation and error handling.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from services.medical_agent.tools.claude_adapter import ClaudeToolAdapter
from services.medical_agent.services.database_service import DatabaseService, DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class DatabaseToolInput(BaseModel):
    """Input schema for database tool."""
    query_type: str = Field(
        description="Type of query: patient_summary, admission_details, diagnoses, medications, labs, icu_vitals, custom"
    )
    subject_id: Optional[int] = Field(
        None,
        description="Patient identifier (required for patient_summary, medications, labs)"
    )
    hadm_id: Optional[int] = Field(
        None,
        description="Hospital admission identifier (required for admission_details; optional filter for labs/medications)"
    )
    stay_id: Optional[int] = Field(
        None,
        description="ICU stay identifier (required for icu_vitals)"
    )
    itemid: Optional[int] = Field(
        None,
        description="Chart/lab item identifier (optional filter for icu_vitals)"
    )
    icd_code: Optional[str] = Field(
        None, 
        description="ICD code for diagnosis search"
    )
    icd_title: Optional[str] = Field(
        None, 
        description="ICD title search term for diagnosis search"
    )
    table_name: Optional[str] = Field(
        None,
        description="Table name for direct table queries (patients, admissions, diagnoses_icd, labevents, prescriptions, pharmacy, emar, icustays, chartevents, ...)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, 
        description="Filters to apply to table queries (e.g., {'subject_id': 10014729})"
    )
    custom_query: Optional[str] = Field(
        None, 
        description="Custom SQL SELECT query (only for query_type='custom')"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, 
        description="Parameters for custom queries"
    )
    limit: Optional[int] = Field(
        None, 
        description="Maximum number of rows to return (default: 1000, max: 5000)"
    )


class DatabaseTool(ClaudeToolAdapter):
    """
    Database tool for querying MIMIC-IV-ED dataset.
    
    This tool provides secure, read-only access to the MIMIC-IV-ED emergency
    department database with comprehensive validation and error handling.
    """
    
    # Maximum query complexity (number of conditions)
    MAX_QUERY_CONDITIONS = 10
    
    # Maximum row limit
    MAX_ROW_LIMIT = 5000
    DEFAULT_ROW_LIMIT = 1000
    
    def __init__(self):
        """Initialize the database tool."""
        # Initialize database service
        try:
            self.db_service = DatabaseService()
            logger.info("DatabaseService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseService: {e}")
            raise
        
        # Initialize the adapter with tool metadata
        super().__init__(
            tool_name="query_mimic_database",
            tool_description="""Query the MIMIC-IV clinical database for patient data, hospital admissions, diagnoses, lab results, medications and ICU measurements.

Use this tool when the user asks about:
- Specific patients (by subject_id) or admissions (by hadm_id)
- Hospital admissions and their evolution
- Diagnoses and ICD codes
- Laboratory results
- Medications (prescriptions and eMAR)
- ICU stays and charted vital signs
- Statistical analysis of clinical data

KEY IDENTIFIERS:
- subject_id: patient (100 demo patients)
- hadm_id: hospital admission (an episode); a patient may have several
- stay_id: ICU stay (only for ICU tables)

DATABASE SCHEMAS — use ONLY these exact column names.

SCHEMA mimiciv_hosp:
  patients(subject_id INT, gender VARCHAR, anchor_age INT, anchor_year INT, anchor_year_group VARCHAR, dod DATE)
  admissions(subject_id INT, hadm_id INT, admittime TS, dischtime TS, deathtime TS, admission_type VARCHAR,
             admission_location VARCHAR, discharge_location VARCHAR, insurance VARCHAR, language VARCHAR,
             marital_status VARCHAR, race VARCHAR, hospital_expire_flag INT)
  transfers(subject_id INT, hadm_id INT, transfer_id INT, eventtype VARCHAR, careunit VARCHAR, intime TS, outtime TS)
  services(subject_id INT, hadm_id INT, transfertime TS, prev_service VARCHAR, curr_service VARCHAR)
  diagnoses_icd(subject_id INT, hadm_id INT, seq_num INT, icd_code VARCHAR, icd_version INT)
  procedures_icd(subject_id INT, hadm_id INT, seq_num INT, chartdate TS, icd_code VARCHAR, icd_version INT)
  d_icd_diagnoses(icd_code VARCHAR, icd_version INT, long_title TEXT)   -- diagnosis titles
  d_icd_procedures(icd_code VARCHAR, icd_version INT, long_title TEXT)  -- procedure titles
  labevents(labevent_id INT, subject_id INT, hadm_id INT, itemid INT, charttime TS, value TEXT, valuenum FLOAT,
            valueuom VARCHAR, ref_range_lower FLOAT, ref_range_upper FLOAT, flag VARCHAR, priority VARCHAR)
  d_labitems(itemid INT, label TEXT, fluid TEXT, category TEXT)         -- lab test names
  microbiologyevents(microevent_id INT, subject_id INT, hadm_id INT, charttime TS, spec_type_desc VARCHAR,
                     test_name VARCHAR, org_name VARCHAR, ab_name VARCHAR, interpretation VARCHAR)
  omr(subject_id INT, chartdate DATE, seq_num INT, result_name VARCHAR, result_value TEXT)  -- outpatient measurements (BMI, BP...)
  prescriptions(subject_id INT, hadm_id INT, starttime TS, stoptime TS, drug VARCHAR, gsn VARCHAR, ndc VARCHAR,
                prod_strength VARCHAR, dose_val_rx VARCHAR, dose_unit_rx VARCHAR, route VARCHAR)
  pharmacy(subject_id INT, hadm_id INT, pharmacy_id INT, starttime TS, stoptime TS, medication TEXT, status VARCHAR, route VARCHAR, frequency VARCHAR)
  emar(subject_id INT, hadm_id INT, emar_id VARCHAR, charttime TS, medication TEXT, event_txt VARCHAR)  -- administrations

SCHEMA mimiciv_icu:
  icustays(subject_id INT, hadm_id INT, stay_id INT, first_careunit VARCHAR, last_careunit VARCHAR, intime TS, outtime TS, los FLOAT)
  chartevents(subject_id INT, hadm_id INT, stay_id INT, charttime TS, itemid INT, value TEXT, valuenum FLOAT, valueuom VARCHAR)
  d_items(itemid INT, label TEXT, category VARCHAR, unitname VARCHAR)   -- chart item names (HR, BP, SpO2...)

CRITICAL:
- Diagnoses/procedures store codes only; JOIN d_icd_diagnoses / d_icd_procedures on (icd_code, icd_version) for titles.
- Labs and chartevents store itemid only; JOIN d_labitems / d_items on itemid for the measurement name.
- For custom queries ALWAYS prefix tables with schema: mimiciv_hosp.admissions, mimiciv_icu.chartevents, etc.

QUERY TYPES:

1. patient_summary: demographics, admissions, diagnoses, recent labs and medications
   Required: subject_id
   Example: {"query_type": "patient_summary", "subject_id": 10000032}

2. admission_details: one hospital admission with diagnoses, transfers and services
   Required: hadm_id
   Example: {"query_type": "admission_details", "hadm_id": 22595853}

3. diagnoses: search the ICD dictionary by code or title (or list a patient's diagnoses via subject_id/hadm_id filters)
   Required: icd_code OR icd_title (or subject_id/hadm_id)
   Example: {"query_type": "diagnoses", "icd_title": "sepsis"}

4. medications: medication history for a patient (prescriptions + eMAR)
   Required: subject_id (optional hadm_id to scope to one admission)
   Example: {"query_type": "medications", "subject_id": 10000032}

5. labs: laboratory results for a patient
   Required: subject_id (optional hadm_id)
   Example: {"query_type": "labs", "subject_id": 10000032}

6. icu_vitals: ICU charted measurements for an ICU stay
   Required: stay_id (optional itemid)
   Example: {"query_type": "icu_vitals", "stay_id": 30057454}

7. custom: Custom SQL SELECT query — MUST use exact schema-qualified table names
   Required: custom_query
   Example: {"query_type": "custom", "custom_query": "SELECT DISTINCT subject_id FROM mimiciv_hosp.patients ORDER BY subject_id"}
   Example: {"query_type": "custom", "custom_query": "SELECT d.long_title, COUNT(*) AS n FROM mimiciv_hosp.diagnoses_icd x JOIN mimiciv_hosp.d_icd_diagnoses d ON d.icd_code = x.icd_code AND d.icd_version = x.icd_version GROUP BY d.long_title ORDER BY n DESC LIMIT 10"}
   Example: {"query_type": "custom", "custom_query": "SELECT l.charttime, di.label, l.valuenum, l.valueuom FROM mimiciv_hosp.labevents l JOIN mimiciv_hosp.d_labitems di ON di.itemid = l.itemid WHERE l.subject_id = 10000032 ORDER BY l.charttime"}

IMPORTANT:
- Always provide required parameters for each query type
- subject_id / hadm_id / stay_id must be positive integers
- Custom queries are validated for security (SELECT-only, no writes)
- Results are limited to prevent performance issues
- All responses are formatted for clinical interpretation""",
            args_schema=DatabaseToolInput
        )
        
        logger.info("DatabaseTool initialized successfully")
    
    def execute(
        self,
        query_type: str,
        subject_id: Optional[int] = None,
        hadm_id: Optional[int] = None,
        stay_id: Optional[int] = None,
        itemid: Optional[int] = None,
        icd_code: Optional[str] = None,
        icd_title: Optional[str] = None,
        table_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        custom_query: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute database query with routing logic.
        
        Args:
            query_type: Type of query to execute
            subject_id: Patient identifier
            stay_id: Stay identifier
            icd_code: ICD code for diagnosis search
            icd_title: ICD title search term
            table_name: Table name for direct queries
            filters: Filters for table queries
            custom_query: Custom SQL query
            params: Parameters for custom queries
            limit: Row limit
            
        Returns:
            Dict with success status, data, and metadata
        """
        try:
            logger.info(f"Executing database query: type={query_type}")
            
            # Validate and execute based on query type
            if query_type == "patient_summary":
                return self._execute_patient_summary(subject_id)

            elif query_type == "admission_details":
                return self._execute_admission_details(hadm_id)

            elif query_type == "diagnoses":
                return self._execute_diagnoses(icd_code, icd_title, subject_id, hadm_id, filters, limit)

            elif query_type == "medications":
                return self._execute_medications(subject_id, hadm_id, limit)

            elif query_type == "labs":
                return self._execute_labs(subject_id, hadm_id, limit)

            elif query_type == "icu_vitals":
                return self._execute_icu_vitals(stay_id, itemid)

            elif query_type == "custom":
                return self._execute_custom(custom_query, params, limit)

            else:
                return {
                    'success': False,
                    'error': f"Tipo de consulta no reconocido: '{query_type}'. Tipos válidos: patient_summary, admission_details, diagnoses, medications, labs, icu_vitals, custom",
                    'data': None
                }
                
        except ValidationError as e:
            logger.warning(f"Validation error in database query: {e}")
            return {
                'success': False,
                'error': f"Error de validación: {str(e)}",
                'data': None
            }
        except DatabaseError as e:
            logger.error(f"Database error in query execution: {e}")
            return {
                'success': False,
                'error': f"Error de base de datos: {str(e)}",
                'data': None
            }
        except Exception as e:
            logger.error(f"Unexpected error in database query: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'data': None
            }
    
    def _execute_patient_summary(self, subject_id: Optional[int]) -> Dict[str, Any]:
        """
        Execute patient summary query.
        
        Args:
            subject_id: Patient identifier
            
        Returns:
            Dict with patient summary data
        """
        # Validate required parameters
        if not subject_id:
            raise ValidationError("subject_id es requerido para patient_summary")
        
        if not isinstance(subject_id, int) or subject_id <= 0:
            raise ValidationError(f"subject_id debe ser un entero positivo, recibido: {subject_id}")
        
        # Execute query
        logger.info(f"Fetching patient summary for subject_id={subject_id}")
        result = self.db_service.get_patient_summary(subject_id)
        
        return {
            'success': True,
            'data': result,
            'query_type': 'patient_summary',
            'parameters': {'subject_id': subject_id}
        }
    
    def _execute_admission_details(self, hadm_id: Optional[int]) -> Dict[str, Any]:
        """Execute hospital admission details query."""
        if not hadm_id:
            raise ValidationError("hadm_id es requerido para admission_details")
        if not isinstance(hadm_id, int) or hadm_id <= 0:
            raise ValidationError(f"hadm_id debe ser un entero positivo, recibido: {hadm_id}")

        logger.info(f"Fetching admission details for hadm_id={hadm_id}")
        result = self.db_service.get_admission_details(hadm_id)
        return {
            'success': True,
            'data': result,
            'query_type': 'admission_details',
            'parameters': {'hadm_id': hadm_id}
        }

    def _execute_icu_vitals(self, stay_id: Optional[int], itemid: Optional[int]) -> Dict[str, Any]:
        """Execute ICU chartevents (vital signs) query for an ICU stay."""
        if not stay_id:
            raise ValidationError("stay_id es requerido para icu_vitals")
        if not isinstance(stay_id, int) or stay_id <= 0:
            raise ValidationError(f"stay_id debe ser un entero positivo, recibido: {stay_id}")

        logger.info(f"Fetching ICU chartevents for stay_id={stay_id}, itemid={itemid}")
        result = self.db_service.get_icu_chartevents(stay_id, itemid)
        return {
            'success': True,
            'data': result,
            'query_type': 'icu_vitals',
            'parameters': {'stay_id': stay_id, 'itemid': itemid},
            'count': len(result) if isinstance(result, list) else 0
        }

    def _execute_labs(self, subject_id: Optional[int], hadm_id: Optional[int], limit: Optional[int]) -> Dict[str, Any]:
        """Execute laboratory results query for a patient."""
        if not subject_id:
            raise ValidationError("subject_id es requerido para labs")
        if not isinstance(subject_id, int) or subject_id <= 0:
            raise ValidationError(f"subject_id debe ser un entero positivo, recibido: {subject_id}")

        logger.info(f"Fetching labs for subject_id={subject_id}, hadm_id={hadm_id}")
        result = self.db_service.get_lab_results(subject_id, hadm_id)
        if limit and isinstance(result, list):
            result = result[:self._get_validated_limit(limit)]
        return {
            'success': True,
            'data': result,
            'query_type': 'labs',
            'parameters': {'subject_id': subject_id, 'hadm_id': hadm_id},
            'count': len(result) if isinstance(result, list) else 0
        }

    def _execute_diagnoses(
        self,
        icd_code: Optional[str],
        icd_title: Optional[str],
        subject_id: Optional[int],
        hadm_id: Optional[int],
        filters: Optional[Dict],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """
        Execute diagnoses query.
        
        Args:
            icd_code: ICD code to search
            icd_title: ICD title to search
            subject_id: Optional patient filter
            stay_id: Optional stay filter
            filters: Optional additional filters
            limit: Row limit
            
        Returns:
            Dict with diagnosis data
        """
        # Validate that at least one search criterion is provided
        if not icd_code and not icd_title and not subject_id and not hadm_id and not filters:
            raise ValidationError(
                "Se requiere al menos un criterio de búsqueda: icd_code, icd_title, subject_id, hadm_id, o filters"
            )

        # Use dictionary search if ICD code or title provided
        if icd_code or icd_title:
            logger.info(f"Searching diagnoses dictionary: icd_code={icd_code}, icd_title={icd_title}")
            result = self.db_service.search_diagnoses(icd_code=icd_code, icd_title=icd_title)
        elif hadm_id:
            logger.info(f"Fetching diagnoses for admission hadm_id={hadm_id}")
            result = self.db_service.get_admission_diagnoses(hadm_id)
        elif subject_id:
            logger.info(f"Fetching diagnoses for patient subject_id={subject_id}")
            result = self.db_service.get_patient_diagnoses(subject_id)
        else:
            query_filters = filters or {}
            logger.info(f"Querying diagnoses_icd with filters: {query_filters}")
            result_df = self.db_service.get_table_data(
                'diagnoses_icd',
                filters=query_filters,
                limit=self._get_validated_limit(limit)
            )
            result = result_df.to_dict('records') if not result_df.empty else []

        return {
            'success': True,
            'data': result,
            'query_type': 'diagnoses',
            'parameters': {
                'icd_code': icd_code,
                'icd_title': icd_title,
                'subject_id': subject_id,
                'hadm_id': hadm_id
            },
            'count': len(result) if isinstance(result, list) else 0
        }

    def _execute_medications(
        self,
        subject_id: Optional[int],
        hadm_id: Optional[int],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """Execute medications query (prescriptions + eMAR)."""
        if not subject_id and not hadm_id:
            raise ValidationError("subject_id o hadm_id es requerido para medications")

        if hadm_id:
            if not isinstance(hadm_id, int) or hadm_id <= 0:
                raise ValidationError(f"hadm_id debe ser un entero positivo, recibido: {hadm_id}")
            logger.info(f"Fetching medications for hadm_id={hadm_id}")
            result = self.db_service.get_medications_by_admission(hadm_id)
        else:
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"subject_id debe ser un entero positivo, recibido: {subject_id}")
            logger.info(f"Fetching medication history for subject_id={subject_id}")
            result = self.db_service.get_medication_history(subject_id)

        if limit and isinstance(result, list):
            result = result[:self._get_validated_limit(limit)]

        return {
            'success': True,
            'data': result,
            'query_type': 'medications',
            'parameters': {'subject_id': subject_id, 'hadm_id': hadm_id},
            'count': len(result) if isinstance(result, list) else 0
        }
    
    def _execute_custom(
        self,
        custom_query: Optional[str],
        params: Optional[Dict],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """
        Execute custom SQL query with safety validation.
        
        Args:
            custom_query: SQL query string
            params: Query parameters
            limit: Row limit
            
        Returns:
            Dict with query results
        """
        # Validate required parameters
        if not custom_query:
            raise ValidationError("custom_query es requerido para consultas personalizadas")
        
        if not isinstance(custom_query, str):
            raise ValidationError("custom_query debe ser una cadena de texto")
        
        # Additional safety validation
        self._validate_custom_query(custom_query)
        
        # Execute query
        logger.info(f"Executing custom query: {custom_query[:100]}...")
        result = self.db_service.execute_custom_query(custom_query, params or {})
        
        # Apply limit if specified
        if limit and isinstance(result, list):
            validated_limit = self._get_validated_limit(limit)
            result = result[:validated_limit]
        
        return {
            'success': True,
            'data': result,
            'query_type': 'custom',
            'parameters': {'query': custom_query[:100] + '...' if len(custom_query) > 100 else custom_query},
            'count': len(result) if isinstance(result, list) else 0
        }
    
    TAUTOLOGY_PATTERNS = [
        r'\bOR\s+1\s*=\s*1\b',                    # OR 1=1
        r"\bOR\s+'[^']*'\s*=\s*'[^']*'\b",        # OR 'a'='a', OR 'x'='x'
        r'\bOR\s+"[^"]*"\s*=\s*"[^"]*"\b',        # OR "a"="a"
        r'\bOR\s+TRUE\b',                          # OR TRUE/true
        r'\bOR\s+1\b',                             # OR 1 (bare truthy)
        r'\bOR\s*\(\s*1\s*=\s*1\s*\)',             # OR (1=1)
        r'\bOR\s+\d+\s*=\s*\d+\b',                # OR 2=2, OR 0=0
        r'\bOR\s+\d+\s*<>\s*0\b',                  # OR 1<>0
        r'\bOR\s+NOT\s+0\b',                       # OR NOT 0
        r'--\s',                                    # SQL comment injection
        r'/\*.*?\*/',                               # Block comment injection
    ]

    def _detect_tautology(self, query: str) -> bool:
        """Detect SQL tautology patterns in WHERE clause."""
        query_upper = query.upper()
        for pattern in self.TAUTOLOGY_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return True
        return False

    def _validate_custom_query(self, query: str) -> None:
        """
        Validate custom query for safety with defense-in-depth.
        Also checks for known incorrect column names and suggests corrections.

        Args:
            query: SQL query string

        Raises:
            ValidationError: If query is unsafe or uses non-existent columns
        """
        if self._detect_tautology(query):
            raise ValidationError(
                "Consulta contiene patrón de tautología SQL no permitido (ej: OR 1=1). "
                "Este patrón puede ser usado para inyección SQL."
            )

        if not query or not query.strip():
            raise ValidationError("La consulta no puede estar vacía.")

        # Limit query length to prevent DoS
        if len(query) > 2000:
            raise ValidationError(
                "La consulta excede el límite de 2000 caracteres."
            )

        query_upper = query.upper().strip()

        # Must be a SELECT query
        if not query_upper.startswith('SELECT'):
            raise ValidationError(
                "Solo se permiten consultas SELECT. No se permiten INSERT, UPDATE, DELETE, DROP, etc."
            )

        # Block dangerous DDL/DML keywords anywhere in query
        blocked_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
            'TRUNCATE', 'GRANT', 'REVOKE', 'COPY', 'VACUUM', 'ANALYZE',
            'COMMENT', 'SECURITY', 'OWNER', 'SET ROLE', 'RESET ROLE',
        ]
        for keyword in blocked_keywords:
            # Use word boundary check to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, query_upper):
                raise ValidationError(
                    f"Operación '{keyword}' no permitida. Solo se permiten consultas SELECT."
                )

        # Check for dangerous patterns (injection, file access, multi-statement)
        dangerous_patterns = [
            r'\bINTO\s+OUTFILE\b',
            r'\bLOAD_FILE\b',
            r'\bINTO\s+DUMPFILE\b',
            r'\bEXEC\b',
            r'\bEXECUTE\b',
            r'\bSYSTEM\b',
            r'\bSHELL\b',
            r'\bPG_SLEEP\b',
            r'\bPG_READ_FILE\b',
            r'\bPG_WRITE_FILE\b',
            r'\bDBLINK\b',
            r'\bCOPY\s+TO\b',
            r'\bCOPY\s+FROM\b',
            r'\bLO_IMPORT\b',
            r'\bLO_EXPORT\b',
            r'\bCURRENT_SETTING\b',
            r'\bSET\s+SESSION\b',
            r'\bSET\s+LOCAL\b',
            r';',  # Block ALL semicolons (no multi-statement)
            r'--',  # Block SQL comments
            r'/\*',  # Block block comments
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                raise ValidationError(
                    "Consulta contiene patrón no permitido. "
                    "Las consultas deben ser SELECT simples sin comentarios ni múltiples sentencias."
                )

        # Block subqueries that could modify data
        if re.search(r'\(\s*SELECT.*FROM\s+(?:pg_|information_schema)', query_upper):
            raise ValidationError(
                "No se permiten consultas a tablas del sistema."
            )

        # --- Column name validation ---
        # Map of incorrect column names → correct column name + table context (MIMIC-IV)
        WRONG_COLUMNS: Dict[str, str] = {
            'DRUGNAME':        'drug (en prescriptions) o medication (en pharmacy/emar)',
            'DRUG_NAME':       'drug (en prescriptions) o medication (en pharmacy/emar)',
            'MED_NAME':        'drug (en prescriptions) o medication (en pharmacy/emar)',
            'MEDICINE':        'drug (en prescriptions) o medication (en pharmacy/emar)',
            'AGE':             'anchor_age (en patients)',
            'DOB':             'no existe fecha de nacimiento; usa anchor_age/anchor_year (en patients)',
            'BIRTH_DATE':      'no existe; usa anchor_age/anchor_year (en patients)',
            'DEATH_DATE':      'dod (en patients) o deathtime (en admissions)',
            'PATIENT_ID':      'subject_id',
            'VISIT_ID':        'hadm_id (admisión hospitalaria) o stay_id (estancia ICU)',
            'ENCOUNTER_ID':    'hadm_id (admisión hospitalaria)',
            'ADMISSION_ID':    'hadm_id (en admissions)',
            'DIAGNOSIS_CODE':  'icd_code (en diagnoses_icd)',
            'DIAGNOSIS_NAME':  'long_title (en d_icd_diagnoses)',
            'ICD_TITLE':       'long_title (en d_icd_diagnoses / d_icd_procedures)',
            'LAB_NAME':        'label (en d_labitems)',
            'ITEM_NAME':       'label (en d_labitems o d_items)',
            'CHIEF_COMPLAINT': 'no existe en MIMIC-IV clinical (era de MIMIC-IV-ED)',
            'ACUITY':          'no existe en MIMIC-IV clinical (era de triage en MIMIC-IV-ED)',
            'DISPOSITION':     'discharge_location (en admissions)',
        }

        for wrong_col, correction in WRONG_COLUMNS.items():
            # Match as a word boundary to avoid false positives inside longer names
            if re.search(r'\b' + wrong_col + r'\b', query_upper):
                raise ValidationError(
                    f"Columna '{wrong_col.lower()}' no existe en MIMIC-IV. "
                    f"Usa en su lugar: {correction}. "
                    f"Consulta el schema completo en la descripción de la herramienta."
                )

        # Check query complexity (number of conditions)
        condition_count = (
            query_upper.count(' WHERE ') + 
            query_upper.count(' AND ') + 
            query_upper.count(' OR ')
        )
        if condition_count > self.MAX_QUERY_CONDITIONS:
            raise ValidationError(
                f"Consulta demasiado compleja. Máximo {self.MAX_QUERY_CONDITIONS} condiciones permitidas."
            )
        
        # Verify only allowed tables are referenced (MIMIC-IV hosp/icu)
        allowed_tables = {t.upper() for t in self.db_service.ALLOWED_TABLES}
        table_pattern = r'(?:FROM|JOIN)\s+(?:(?:MIMICIV_HOSP|MIMICIV_ICU)\.)?(\w+)'
        tables_found = re.findall(table_pattern, query_upper)
        for table in tables_found:
            if table not in allowed_tables:
                raise ValidationError(
                    f"Tabla '{table}' no permitida. "
                    f"Solo se permiten tablas MIMIC-IV: {', '.join(sorted(t.lower() for t in allowed_tables))}."
                )

        logger.debug("Custom query validation passed")
    
    def _get_validated_limit(self, limit: Optional[int]) -> int:
        """
        Validate and return row limit.
        
        Args:
            limit: Requested limit
            
        Returns:
            Validated limit value
        """
        if limit is None:
            return self.DEFAULT_ROW_LIMIT
        
        if not isinstance(limit, int) or limit <= 0:
            logger.warning(f"Invalid limit value: {limit}, using default")
            return self.DEFAULT_ROW_LIMIT
        
        if limit > self.MAX_ROW_LIMIT:
            logger.warning(f"Limit {limit} exceeds maximum, capping at {self.MAX_ROW_LIMIT}")
            return self.MAX_ROW_LIMIT
        
        return limit
    
    def format_output(self, output_data: Any) -> str:
        """
        Format output for Claude consumption.
        
        Args:
            output_data: Output from tool execution
            
        Returns:
            Formatted output string
        """
        if isinstance(output_data, dict):
            if not output_data.get('success', False):
                # Format error response
                return f"❌ Error: {output_data.get('error', 'Unknown error')}"
            
            # Format successful response
            data = output_data.get('data')
            query_type = output_data.get('query_type', 'unknown')
            count = output_data.get('count', 0)
            
            lines = [f"✅ Consulta exitosa: {query_type}"]
            
            if count > 0:
                lines.append(f"📊 Registros encontrados: {count}")
            
            # Format data based on type
            if isinstance(data, dict):
                lines.append("\n📋 Datos:")
                lines.append(self._format_dict_data(data))
            elif isinstance(data, list):
                lines.append("\n📋 Datos:")
                lines.append(self._format_list_data(data))
            else:
                lines.append(f"\n📋 Datos: {data}")
            
            return "\n".join(lines)
        
        return str(output_data)
    
    def _format_dict_data(self, data: Dict, indent: int = 0) -> str:
        """Format dictionary data for display."""
        lines = []
        indent_str = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}{key}:")
                lines.append(self._format_dict_data(value, indent + 1))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                lines.append(f"{indent_str}{key}: ({len(value)} items)")
                for i, item in enumerate(value[:3], 1):  # Show first 3 items
                    lines.append(f"{indent_str}  {i}.")
                    lines.append(self._format_dict_data(item, indent + 2))
                if len(value) > 3:
                    lines.append(f"{indent_str}  ... y {len(value) - 3} más")
            elif isinstance(value, list):
                lines.append(f"{indent_str}{key}: {value}")
            else:
                lines.append(f"{indent_str}{key}: {value}")
        
        return "\n".join(lines)
    
    def _format_list_data(self, data: List, max_items: int = 10) -> str:
        """Format list data for display."""
        if not data:
            return "  No hay datos disponibles"
        
        lines = []
        for i, item in enumerate(data[:max_items], 1):
            if isinstance(item, dict):
                lines.append(f"  {i}.")
                lines.append(self._format_dict_data(item, indent=2))
            else:
                lines.append(f"  {i}. {item}")
        
        if len(data) > max_items:
            lines.append(f"  ... y {len(data) - max_items} registros más")
        
        return "\n".join(lines)


# Convenience function to create the tool
def create_database_tool() -> DatabaseTool:
    """
    Create a database tool instance.
    
    Returns:
        DatabaseTool instance
    """
    return DatabaseTool()
