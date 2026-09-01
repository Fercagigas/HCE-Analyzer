"""
MIMIC-IV Clinical Dataset Validator
Verifica que el dataset MIMIC-IV clinical demo 2.2 esté correctamente cargado en
Supabase (esquemas mimiciv_hosp y mimiciv_icu).
"""

import logging
from typing import Dict, List, Tuple, Optional
from supabase import create_client, Client
from config.settings import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MimicValidator:
    """Validador para el dataset MIMIC-IV clinical en Supabase"""

    # Esquema de cada tabla (subconjunto clínico curado cargado)
    TABLE_SCHEMA = {
        'd_icd_diagnoses': 'mimiciv_hosp',
        'd_icd_procedures': 'mimiciv_hosp',
        'd_labitems': 'mimiciv_hosp',
        'patients': 'mimiciv_hosp',
        'admissions': 'mimiciv_hosp',
        'transfers': 'mimiciv_hosp',
        'services': 'mimiciv_hosp',
        'diagnoses_icd': 'mimiciv_hosp',
        'procedures_icd': 'mimiciv_hosp',
        'labevents': 'mimiciv_hosp',
        'microbiologyevents': 'mimiciv_hosp',
        'omr': 'mimiciv_hosp',
        'prescriptions': 'mimiciv_hosp',
        'pharmacy': 'mimiciv_hosp',
        'emar': 'mimiciv_hosp',
        'd_items': 'mimiciv_icu',
        'icustays': 'mimiciv_icu',
        'chartevents': 'mimiciv_icu',
    }

    # Conteos esperados según el análisis del dataset (demo 2.2)
    EXPECTED_COUNTS = {
        'd_icd_diagnoses': 109775,
        'd_icd_procedures': 85257,
        'd_labitems': 1622,
        'patients': 100,
        'admissions': 275,
        'transfers': 1190,
        'services': 319,
        'diagnoses_icd': 4506,
        'procedures_icd': 722,
        'labevents': 107727,
        'microbiologyevents': 2899,
        'omr': 2964,
        'prescriptions': 18087,
        'pharmacy': 15306,
        'emar': 35835,
        'd_items': 4014,
        'icustays': 140,
        'chartevents': 668862,
    }

    # Estructura esperada de columnas por tabla (subconjunto representativo)
    EXPECTED_COLUMNS = {
        'patients': ['subject_id', 'gender', 'anchor_age', 'anchor_year', 'anchor_year_group', 'dod'],
        'admissions': ['subject_id', 'hadm_id', 'admittime', 'dischtime', 'admission_type', 'race', 'hospital_expire_flag'],
        'transfers': ['subject_id', 'hadm_id', 'transfer_id', 'eventtype', 'careunit', 'intime', 'outtime'],
        'diagnoses_icd': ['subject_id', 'hadm_id', 'seq_num', 'icd_code', 'icd_version'],
        'd_icd_diagnoses': ['icd_code', 'icd_version', 'long_title'],
        'labevents': ['labevent_id', 'subject_id', 'hadm_id', 'itemid', 'charttime', 'valuenum', 'valueuom'],
        'd_labitems': ['itemid', 'label', 'fluid', 'category'],
        'prescriptions': ['subject_id', 'hadm_id', 'starttime', 'drug', 'dose_val_rx', 'route'],
        'icustays': ['subject_id', 'hadm_id', 'stay_id', 'first_careunit', 'intime', 'outtime', 'los'],
        'chartevents': ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'valuenum', 'valueuom'],
        'd_items': ['itemid', 'label', 'category', 'unitname'],
    }

    def __init__(self):
        """Inicializar el validador con conexión a Supabase"""
        try:
            self.supabase: Client = create_client(
                settings.database.supabase_url,
                settings.database.supabase_key
            )
            logger.info("✅ Conexión a Supabase establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a Supabase: {e}")
            raise
    
    def _table(self, table_name: str):
        """Return a schema-qualified table query builder."""
        schema = self.TABLE_SCHEMA.get(table_name, 'mimiciv_hosp')
        return self.supabase.schema(schema).table(table_name)

    def check_table_exists(self, table_name: str) -> bool:
        """Verificar si una tabla existe en su esquema MIMIC-IV"""
        try:
            self._table(table_name).select("*").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Tabla {table_name} no existe o no es accesible: {e}")
            return False

    def get_table_count(self, table_name: str) -> Optional[int]:
        """Obtener el conteo de registros de una tabla"""
        try:
            result = self._table(table_name).select("*", count="exact").limit(1).execute()
            return result.count
        except Exception as e:
            logger.error(f"❌ Error obteniendo conteo de {table_name}: {e}")
            return None

    def get_table_columns(self, table_name: str) -> Optional[List[str]]:
        """Obtener las columnas de una tabla"""
        try:
            result = self._table(table_name).select("*").limit(1).execute()
            if result.data:
                return list(result.data[0].keys())
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo columnas de {table_name}: {e}")
            return None
    
    def validate_table_structure(self, table_name: str) -> Dict:
        """Validar la estructura de una tabla específica"""
        validation_result = {
            'table': table_name,
            'exists': False,
            'count_correct': False,
            'columns_correct': False,
            'actual_count': 0,
            'expected_count': self.EXPECTED_COUNTS.get(table_name, 0),
            'missing_columns': [],
            'extra_columns': [],
            'status': 'FAIL'
        }
        
        # Verificar existencia
        if not self.check_table_exists(table_name):
            return validation_result
        
        validation_result['exists'] = True
        
        # Verificar conteo
        actual_count = self.get_table_count(table_name)
        if actual_count is not None:
            validation_result['actual_count'] = actual_count
            validation_result['count_correct'] = actual_count == self.EXPECTED_COUNTS.get(table_name, 0)
        
        # Verificar columnas
        actual_columns = self.get_table_columns(table_name)
        if actual_columns is not None:
            expected_columns = set(self.EXPECTED_COLUMNS.get(table_name, []))
            actual_columns_set = set(actual_columns)
            
            validation_result['missing_columns'] = list(expected_columns - actual_columns_set)
            validation_result['extra_columns'] = list(actual_columns_set - expected_columns)
            validation_result['columns_correct'] = len(validation_result['missing_columns']) == 0
        
        # Determinar estado general
        if (validation_result['exists'] and 
            validation_result['count_correct'] and 
            validation_result['columns_correct']):
            validation_result['status'] = 'PASS'
        elif validation_result['exists']:
            validation_result['status'] = 'PARTIAL'
        
        return validation_result
    
    def validate_data_integrity(self) -> Dict:
        """Validar integridad de datos entre tablas relacionadas"""
        integrity_checks = {
            'subject_id_consistency': False,
            'stay_id_consistency': False,
            'primary_keys_unique': False,
            'foreign_key_integrity': False
        }
        
        try:
            # Consistencia de subject_id: toda admisión debe pertenecer a un paciente
            patients = self._table("patients").select("subject_id").execute()
            admissions = self._table("admissions").select("subject_id").execute()
            if patients.data and admissions.data:
                patient_ids = {row['subject_id'] for row in patients.data}
                adm_ids = {row['subject_id'] for row in admissions.data}
                integrity_checks['subject_id_consistency'] = adm_ids.issubset(patient_ids)

            # subject_id de patients es único (clave primaria)
            if patients.data:
                sids = [row['subject_id'] for row in patients.data]
                integrity_checks['primary_keys_unique'] = len(sids) == len(set(sids))

            # Integridad referencial: hadm_id de icustays existe en admissions
            icu = self._table("icustays").select("hadm_id").execute()
            adm_hadm = self._table("admissions").select("hadm_id").execute()
            if icu.data and adm_hadm.data:
                adm_hadm_ids = {row['hadm_id'] for row in adm_hadm.data}
                integrity_checks['stay_id_consistency'] = all(
                    row['hadm_id'] in adm_hadm_ids for row in icu.data
                )
                integrity_checks['foreign_key_integrity'] = integrity_checks['stay_id_consistency']

        except Exception as e:
            logger.error(f"❌ Error en validación de integridad: {e}")

        return integrity_checks
    
    def run_full_validation(self) -> Dict:
        """Ejecutar validación completa del dataset MIMIC-IV clinical"""
        logger.info("Iniciando validación completa del dataset MIMIC-IV clinical...")
        
        validation_results = {
            'timestamp': None,
            'overall_status': 'FAIL',
            'tables': {},
            'data_integrity': {},
            'summary': {
                'total_tables': len(self.EXPECTED_COUNTS),
                'tables_passed': 0,
                'tables_partial': 0,
                'tables_failed': 0,
                'total_records_expected': sum(self.EXPECTED_COUNTS.values()),
                'total_records_actual': 0
            }
        }
        
        # Validar cada tabla
        for table_name in self.EXPECTED_COUNTS.keys():
            logger.info(f"📊 Validando tabla: {table_name}")
            table_result = self.validate_table_structure(table_name)
            validation_results['tables'][table_name] = table_result
            
            # Actualizar resumen
            if table_result['status'] == 'PASS':
                validation_results['summary']['tables_passed'] += 1
            elif table_result['status'] == 'PARTIAL':
                validation_results['summary']['tables_partial'] += 1
            else:
                validation_results['summary']['tables_failed'] += 1
            
            validation_results['summary']['total_records_actual'] += table_result['actual_count']
        
        # Validar integridad de datos
        logger.info("🔗 Validando integridad de datos...")
        validation_results['data_integrity'] = self.validate_data_integrity()
        
        # Determinar estado general
        if validation_results['summary']['tables_failed'] == 0:
            if validation_results['summary']['tables_partial'] == 0:
                validation_results['overall_status'] = 'PASS'
            else:
                validation_results['overall_status'] = 'PARTIAL'
        
        validation_results['timestamp'] = self._get_timestamp()
        
        return validation_results
    
    def _get_timestamp(self) -> str:
        """Obtener timestamp actual"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def print_validation_report(self, results: Dict):
        """Imprimir reporte de validación formateado"""
        # En consolas Windows (cp1252) los emojis rompen la salida; forzamos UTF-8.
        try:
            import sys
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print("\n" + "="*80)
        print("REPORTE DE VALIDACION - DATASET MIMIC-IV CLINICAL")
        print("="*80)
        print(f"⏰ Timestamp: {results['timestamp']}")
        print(f"🎯 Estado General: {results['overall_status']}")
        print()
        
        # Resumen
        summary = results['summary']
        print("📊 RESUMEN:")
        print(f"   • Total de tablas: {summary['total_tables']}")
        print(f"   • ✅ Tablas correctas: {summary['tables_passed']}")
        print(f"   • ⚠️  Tablas parciales: {summary['tables_partial']}")
        print(f"   • ❌ Tablas fallidas: {summary['tables_failed']}")
        print(f"   • 📈 Registros esperados: {summary['total_records_expected']:,}")
        print(f"   • 📊 Registros actuales: {summary['total_records_actual']:,}")
        print()
        
        # Detalle por tabla
        print("📋 DETALLE POR TABLA:")
        print("-" * 80)
        for table_name, table_result in results['tables'].items():
            status_icon = "✅" if table_result['status'] == 'PASS' else "⚠️" if table_result['status'] == 'PARTIAL' else "❌"
            print(f"{status_icon} {table_name.upper()}")
            print(f"   • Existe: {'✅' if table_result['exists'] else '❌'}")
            print(f"   • Registros: {table_result['actual_count']:,} / {table_result['expected_count']:,} {'✅' if table_result['count_correct'] else '❌'}")
            print(f"   • Columnas: {'✅' if table_result['columns_correct'] else '❌'}")
            
            if table_result['missing_columns']:
                print(f"   • Columnas faltantes: {', '.join(table_result['missing_columns'])}")
            if table_result['extra_columns']:
                print(f"   • Columnas extra: {', '.join(table_result['extra_columns'])}")
            print()
        
        # Integridad de datos
        print("🔗 INTEGRIDAD DE DATOS:")
        integrity = results['data_integrity']
        for check, passed in integrity.items():
            icon = "✅" if passed else "❌"
            print(f"   {icon} {check.replace('_', ' ').title()}")
        
        print("="*80)


def main():
    """Función principal para ejecutar la validación"""
    try:
        validator = MimicValidator()
        results = validator.run_full_validation()
        validator.print_validation_report(results)
        
        # Retornar código de salida basado en el resultado
        if results['overall_status'] == 'PASS':
            return 0
        elif results['overall_status'] == 'PARTIAL':
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error(f"❌ Error durante la validación: {e}")
        return 3


if __name__ == "__main__":
    exit(main())