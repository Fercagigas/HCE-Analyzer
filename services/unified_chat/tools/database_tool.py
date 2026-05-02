"""
Database Tool for Unified Chat System

This module provides a Claude-compatible tool for querying the MIMIC-IV-ED database.
It supports multiple query types with comprehensive validation and error handling.
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
        description="Type of query: patient_summary, vital_signs, diagnoses, medications, custom"
    )
    subject_id: Optional[int] = Field(
        None, 
        description="Patient identifier (required for patient_summary, medications)"
    )
    stay_id: Optional[int] = Field(
        None, 
        description="Stay identifier (required for vital_signs)"
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
        description="Table name for direct table queries (diagnosis, edstays, triage, vitalsign, medrecon, pyxis)"
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
            tool_description="""Query the MIMIC-IV-ED database for patient data, vital signs, diagnoses, medications, and clinical information.

Use this tool when the user asks about:
- Specific patients (by subject_id or stay_id)
- Vital signs and trends
- Diagnoses and ICD codes
- Medications and administration
- Emergency department visits
- Statistical analysis of clinical data

DATABASE SCHEMA (mimic_ed schema — use ONLY these exact column names):

TABLE: edstays
  subject_id INT, stay_id INT, hadm_id INT, intime TIMESTAMP, outtime TIMESTAMP,
  gender VARCHAR, race VARCHAR, arrival_transport VARCHAR, disposition VARCHAR

TABLE: triage
  subject_id INT, stay_id INT, temperature FLOAT, heartrate FLOAT, resprate FLOAT,
  o2sat FLOAT, sbp FLOAT, dbp FLOAT, pain VARCHAR, acuity FLOAT, chiefcomplaint TEXT

TABLE: vitalsign
  subject_id INT, stay_id INT, charttime TIMESTAMP, temperature FLOAT, heartrate FLOAT,
  resprate FLOAT, o2sat FLOAT, sbp FLOAT, dbp FLOAT, rhythm VARCHAR, pain VARCHAR

TABLE: diagnosis
  subject_id INT, stay_id INT, seq_num INT, icd_code VARCHAR, icd_title TEXT, icd_version INT

TABLE: medrecon  (habitual medications — what the patient takes at home)
  subject_id INT, stay_id INT, charttime TIMESTAMP, name VARCHAR, gsn VARCHAR,
  ndc VARCHAR, etc_rn INT, etccode VARCHAR, etcdescription TEXT

TABLE: pyxis  (medications dispensed in the ED)
  subject_id INT, stay_id INT, charttime TIMESTAMP, name VARCHAR, gsn_rn INT, gsn VARCHAR

CRITICAL: For medications always use column "name" (NOT drugname, medication, drug, med_name).
CRITICAL: For custom queries always prefix tables with schema: mimic_ed.edstays, mimic_ed.pyxis, etc.

QUERY TYPES:

1. patient_summary: Complete patient summary with demographics, stays, diagnoses, vital signs, and medications
   Required: subject_id
   Example: {"query_type": "patient_summary", "subject_id": 10014729}

2. vital_signs: Vital signs measurements for a specific stay
   Required: stay_id
   Example: {"query_type": "vital_signs", "stay_id": 37887480}

3. diagnoses: Search diagnoses by ICD code or title
   Required: icd_code OR icd_title
   Example: {"query_type": "diagnoses", "icd_code": "431"}
   Example: {"query_type": "diagnoses", "icd_title": "pneumonia"}

4. medications: Medication history for a patient
   Required: subject_id
   Example: {"query_type": "medications", "subject_id": 10014729}

5. custom: Custom SQL SELECT query — MUST use exact column names from schema above
   Required: custom_query
   Example: {"query_type": "custom", "custom_query": "SELECT name, charttime FROM mimic_ed.pyxis WHERE subject_id = 10014729 ORDER BY charttime"}
   Example: {"query_type": "custom", "custom_query": "SELECT icd_code, icd_title FROM mimic_ed.diagnosis WHERE subject_id = 10014729"}

   DATASET-WIDE QUERIES (no subject_id filter needed):
   - List all unique patients:
     {"query_type": "custom", "custom_query": "SELECT DISTINCT subject_id FROM mimic_ed.edstays ORDER BY subject_id"}
   - List unique patients with gender and race:
     {"query_type": "custom", "custom_query": "SELECT DISTINCT subject_id, gender, race FROM mimic_ed.edstays ORDER BY subject_id"}
   - Count visits per patient:
     {"query_type": "custom", "custom_query": "SELECT subject_id, COUNT(stay_id) as total_visitas FROM mimic_ed.edstays GROUP BY subject_id ORDER BY total_visitas DESC"}
   - Top 10 most frequent diagnoses:
     {"query_type": "custom", "custom_query": "SELECT icd_title, COUNT(*) as frecuencia FROM mimic_ed.diagnosis GROUP BY icd_title ORDER BY frecuencia DESC LIMIT 10"}
   - Distribution by disposition:
     {"query_type": "custom", "custom_query": "SELECT disposition, COUNT(*) as total FROM mimic_ed.edstays GROUP BY disposition ORDER BY total DESC"}

IMPORTANT:
- Always provide required parameters for each query type
- Patient IDs (subject_id) and stay IDs (stay_id) must be positive integers
- Custom queries are validated for security (no INSERT, UPDATE, DELETE, DROP, etc.)
- Results are limited to prevent performance issues
- All responses are formatted for clinical interpretation""",
            args_schema=DatabaseToolInput
        )
        
        logger.info("DatabaseTool initialized successfully")
    
    def execute(
        self,
        query_type: str,
        subject_id: Optional[int] = None,
        stay_id: Optional[int] = None,
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
                
            elif query_type == "vital_signs":
                return self._execute_vital_signs(stay_id)
                
            elif query_type == "diagnoses":
                return self._execute_diagnoses(icd_code, icd_title, subject_id, stay_id, filters, limit)
                
            elif query_type == "medications":
                return self._execute_medications(subject_id, stay_id, limit)
                
            elif query_type == "custom":
                return self._execute_custom(custom_query, params, limit)
                
            else:
                return {
                    'success': False,
                    'error': f"Tipo de consulta no reconocido: '{query_type}'. Tipos válidos: patient_summary, vital_signs, diagnoses, medications, custom",
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
    
    def _execute_vital_signs(self, stay_id: Optional[int]) -> Dict[str, Any]:
        """
        Execute vital signs query.
        
        Args:
            stay_id: Stay identifier
            
        Returns:
            Dict with vital signs data
        """
        # Validate required parameters
        if not stay_id:
            raise ValidationError("stay_id es requerido para vital_signs")
        
        if not isinstance(stay_id, int) or stay_id <= 0:
            raise ValidationError(f"stay_id debe ser un entero positivo, recibido: {stay_id}")
        
        # Execute query
        logger.info(f"Fetching vital signs for stay_id={stay_id}")
        result = self.db_service.get_vital_signs(stay_id)
        
        return {
            'success': True,
            'data': result,
            'query_type': 'vital_signs',
            'parameters': {'stay_id': stay_id},
            'count': len(result) if isinstance(result, list) else 0
        }
    
    def _execute_diagnoses(
        self,
        icd_code: Optional[str],
        icd_title: Optional[str],
        subject_id: Optional[int],
        stay_id: Optional[int],
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
        if not icd_code and not icd_title and not subject_id and not stay_id and not filters:
            raise ValidationError(
                "Se requiere al menos un criterio de búsqueda: icd_code, icd_title, subject_id, stay_id, o filters"
            )
        
        # Use search_diagnoses if ICD code or title provided
        if icd_code or icd_title:
            logger.info(f"Searching diagnoses: icd_code={icd_code}, icd_title={icd_title}")
            result = self.db_service.search_diagnoses(icd_code=icd_code, icd_title=icd_title)
        else:
            # Use table query with filters
            query_filters = filters or {}
            if subject_id:
                query_filters['subject_id'] = subject_id
            if stay_id:
                query_filters['stay_id'] = stay_id
            
            logger.info(f"Querying diagnosis table with filters: {query_filters}")
            result_df = self.db_service.get_table_data(
                'diagnosis',
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
                'stay_id': stay_id
            },
            'count': len(result) if isinstance(result, list) else 0
        }
    
    def _execute_medications(
        self,
        subject_id: Optional[int],
        stay_id: Optional[int],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """
        Execute medications query.
        
        Args:
            subject_id: Patient identifier
            stay_id: Optional stay identifier
            limit: Row limit
            
        Returns:
            Dict with medication data
        """
        # Validate required parameters
        if not subject_id and not stay_id:
            raise ValidationError("subject_id o stay_id es requerido para medications")
        
        # Execute query based on available parameters
        if subject_id:
            if not isinstance(subject_id, int) or subject_id <= 0:
                raise ValidationError(f"subject_id debe ser un entero positivo, recibido: {subject_id}")
            
            logger.info(f"Fetching medication history for subject_id={subject_id}")
            result = self.db_service.get_medication_history(subject_id)
            
            # Apply limit if specified
            if limit and isinstance(result, list):
                validated_limit = self._get_validated_limit(limit)
                result = result[:validated_limit]
        else:
            # Query by stay_id using table data
            if not isinstance(stay_id, int) or stay_id <= 0:
                raise ValidationError(f"stay_id debe ser un entero positivo, recibido: {stay_id}")
            
            logger.info(f"Fetching medications for stay_id={stay_id}")
            result_df = self.db_service.get_table_data(
                'medrecon',
                filters={'stay_id': stay_id},
                limit=self._get_validated_limit(limit)
            )
            result = result_df.to_dict('records') if not result_df.empty else []
        
        return {
            'success': True,
            'data': result,
            'query_type': 'medications',
            'parameters': {'subject_id': subject_id, 'stay_id': stay_id},
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
        # Map of incorrect column names → correct column name + table context
        WRONG_COLUMNS: Dict[str, str] = {
            'DRUGNAME':       'name (en pyxis o medrecon)',
            'DRUG_NAME':      'name (en pyxis o medrecon)',
            'MEDICATION':     'name (en pyxis o medrecon)',
            'MEDICATION_NAME':'name (en pyxis o medrecon)',
            'MED_NAME':       'name (en pyxis o medrecon)',
            'DRUG':           'name (en pyxis o medrecon)',
            'MEDICINE':       'name (en pyxis o medrecon)',
            'AGE':            'no existe columna age; calcula desde intime si es necesario',
            'DOB':            'no existe columna dob en MIMIC-IV-ED',
            'BIRTH_DATE':     'no existe columna birth_date en MIMIC-IV-ED',
            'DEATH_DATE':     'no existe columna death_date en MIMIC-IV-ED',
            'PATIENT_ID':     'subject_id (en edstays, triage, vitalsign, diagnosis, medrecon, pyxis)',
            'VISIT_ID':       'stay_id',
            'ENCOUNTER_ID':   'stay_id',
            'ADMISSION_ID':   'hadm_id (en edstays)',
            'DIAGNOSIS_CODE': 'icd_code (en diagnosis)',
            'DIAGNOSIS_NAME': 'icd_title (en diagnosis)',
            'VITAL_SIGNS':    'tabla vitalsign (columnas: heartrate, sbp, dbp, o2sat, temperature, resprate)',
            'HEART_RATE':     'heartrate (en vitalsign o triage)',
            'BLOOD_PRESSURE': 'sbp y dbp (en vitalsign o triage)',
            'OXYGEN_SAT':     'o2sat (en vitalsign o triage)',
            'RESP_RATE':      'resprate (en vitalsign o triage)',
            'CHIEF_COMPLAINT':'chiefcomplaint (en triage)',
            'COMPLAINT':      'chiefcomplaint (en triage)',
            'ARRIVAL_MODE':   'arrival_transport (en edstays)',
            'TRANSPORT':      'arrival_transport (en edstays)',
            'DISCHARGE':      'disposition (en edstays)',
            'DISCHARGE_DISPOSITION': 'disposition (en edstays)',
        }

        for wrong_col, correction in WRONG_COLUMNS.items():
            # Match as a word boundary to avoid false positives inside longer names
            if re.search(r'\b' + wrong_col + r'\b', query_upper):
                raise ValidationError(
                    f"Columna '{wrong_col.lower()}' no existe en MIMIC-IV-ED. "
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
        
        # Verify only allowed tables are referenced
        allowed_tables = {
            'EDSTAYS', 'TRIAGE', 'VITALSIGN', 'DIAGNOSIS',
            'MEDRECON', 'PYXIS'
        }
        table_pattern = r'(?:FROM|JOIN)\s+(?:mimic_ed\.)?(\w+)'
        tables_found = re.findall(table_pattern, query_upper)
        for table in tables_found:
            if table not in allowed_tables:
                raise ValidationError(
                    f"Tabla '{table}' no permitida. "
                    f"Solo se permiten tablas MIMIC-IV-ED: {', '.join(sorted(allowed_tables))}."
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
