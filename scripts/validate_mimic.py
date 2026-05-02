#!/usr/bin/env python3
"""
Script para validar el dataset MIMIC-IV-ED en Supabase
Uso: python scripts/validate_mimic.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validators.mimic_validator import MimicValidator

def main():
    """Ejecutar validación del dataset MIMIC-IV-ED"""
    print("🏥 Validador del Dataset MIMIC-IV-ED")
    print("=" * 50)
    
    try:
        # Crear instancia del validador
        validator = MimicValidator()
        
        # Ejecutar validación completa
        results = validator.run_full_validation()
        
        # Mostrar reporte
        validator.print_validation_report(results)
        
        # Mostrar recomendaciones basadas en el resultado
        if results['overall_status'] == 'PASS':
            print("🎉 ¡Dataset MIMIC-IV-ED validado correctamente!")
            print("✅ Todas las tablas están cargadas y estructuradas correctamente.")
        elif results['overall_status'] == 'PARTIAL':
            print("⚠️  Dataset MIMIC-IV-ED parcialmente válido")
            print("💡 Revisa los detalles arriba para ver qué necesita corrección.")
        else:
            print("❌ Dataset MIMIC-IV-ED tiene problemas significativos")
            print("🔧 Revisa la configuración de Supabase y la carga de datos.")
        
        return 0 if results['overall_status'] == 'PASS' else 1
        
    except Exception as e:
        print(f"💥 Error durante la validación: {e}")
        print("🔍 Verifica tu configuración de Supabase en .env")
        return 2

if __name__ == "__main__":
    exit(main())