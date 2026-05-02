# Implementation Plan - Visualization System Improvement

## Task Overview

Este plan implementa las mejoras al sistema de visualización médica, integrándose con el código existente sin crear duplicación y asegurando integración automática con el chat unificado.

## Implementation Tasks

- [x] 1. Configurar Claude Sonnet 4.5 para visualización
  - Añadir configuración específica en settings.py
  - Crear variables de entorno necesarias
  - Verificar que llm_manager.py puede usar Sonnet 4.5
  - _Requirements: 3.1_

- [x] 2. Crear módulo DataPreprocessor
- [x] 2.1 Implementar clase DataPreprocessor base
  - Crear archivo data_preprocessor.py
  - Implementar __init__ con configuración
  - Definir modelos de datos (PreprocessResult, MetricsValidation)
  - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2_

- [x] 2.2 Implementar preprocesamiento temporal
  - Implementar preprocess_temporal_data()
  - Ordenar datos por charttime
  - Eliminar duplicados temporales
  - Convertir charttime a datetime
  - Preservar integridad de columnas
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [ ]* 2.3 Escribir property test para preprocesamiento temporal
  - **Property 1: Preprocesamiento temporal completo**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.5**

- [x] 2.4 Implementar detección de outliers
  - Implementar detect_outliers() con método IQR
  - Marcar outliers sin eliminarlos
  - Añadir columna 'is_outlier' al DataFrame
  - _Requirements: 4.3_

- [ ]* 2.5 Escribir property test para detección de outliers
  - **Property 6: Detección no destructiva de outliers**
  - **Validates: Requirements 4.3, 4.4**

- [x] 2.6 Implementar validación de métricas
  - Implementar validate_metrics()
  - Calcular porcentaje de nulos por columna
  - Excluir métricas con >50% nulos
  - Reemplazar inf/NaN con None
  - _Requirements: 4.1, 4.2, 4.5_

- [ ]* 2.7 Escribir property test para validación de métricas
  - **Property 5: Validación y filtrado de métricas**
  - **Validates: Requirements 4.1, 4.2, 4.5**

- [x] 3. Crear módulo VisualizationTemplates
- [x] 3.1 Implementar clase VisualizationTemplates
  - Crear archivo visualization_templates.py
  - Implementar __init__ con cache de plantillas
  - Implementar get_template()
  - _Requirements: 8.1, 8.2_

- [x] 3.2 Crear plantillas para tipos comunes
  - Crear plantilla para timeline
  - Crear plantilla para comparison
  - Crear plantilla para distribution
  - Crear plantilla para scatter
  - _Requirements: 8.3_

- [x] 3.3 Implementar personalización de plantillas
  - Implementar customize_template()
  - Reemplazar placeholders con datos reales
  - Usar LLM solo para adaptaciones específicas
  - _Requirements: 8.4_

- [ ]* 3.4 Escribir property test para uso de plantillas
  - **Property 9: Uso inteligente de plantillas**
  - **Validates: Requirements 8.1, 8.2, 8.4**

- [x] 3.5 Implementar validación de plantillas
  - Implementar validate_template()
  - Probar con al menos 3 conjuntos de datos
  - _Requirements: 8.5_

- [-] 4. Mejorar validación de código en code_executor.py
- [x] 4.1 Implementar ImprovedCodeValidator
  - Crear clase ImprovedCodeValidator heredando de CodeValidator
  - Implementar validate_code() mejorado
  - Implementar check_column_usage()
  - Implementar check_plotly_methods()
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ]* 4.2 Escribir property test para validación de código
  - **Property 8: Validación completa de código**
  - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 5. Actualizar VisualizationAgent
- [x] 5.1 Integrar nuevos componentes
  - Añadir self.preprocessor = DataPreprocessor()
  - Añadir self.templates = VisualizationTemplates()
  - Añadir self.validator = ImprovedCodeValidator()
  - Modificar __init__ para usar Sonnet 4.5
  - _Requirements: 3.1, 9.2_

- [x] 5.2 Implementar lógica de reintentos
  - Modificar generate_visualization() para incluir reintentos
  - Implementar prompt simplificado para reintentos
  - Capturar errores y solicitar corrección al LLM
  - _Requirements: 2.1, 2.2_

- [ ]* 5.3 Escribir property test para reintentos
  - **Property 2: Reintentos con corrección automática**
  - **Validates: Requirements 2.1, 2.2**

- [x] 5.4 Implementar fallback a plantillas
  - Usar plantilla de respaldo después de 3 fallos
  - Registrar error en logs
  - _Requirements: 2.4, 2.5_

- [x] 5.5 Integrar preprocesamiento en flujo
  - Llamar a preprocessor antes de generar código
  - Usar datos preprocesados para generación
  - Incluir metadata de preprocesamiento en resultado
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 5.6 Mejorar prompts de generación
  - Actualizar _create_code_generation_prompt()
  - Incluir ejemplos de código limpio
  - Especificar nombres en español
  - Especificar template='plotly_white'
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [ ]* 5.7 Escribir property test para calidad de código
  - **Property 4: Calidad de código generado**
  - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

- [x] 5.7 Implementar detección de gaps temporales
  - Detectar gaps >24 horas en datos temporales
  - Usar mode='lines+markers' cuando hay gaps grandes
  - _Requirements: 1.4_

- [ ]* 5.8 Escribir property test para generación garantizada
  - **Property 3: Generación garantizada con datos válidos**
  - **Validates: Requirements 2.3**

- [x] 6. Actualizar VisualizationCollaborationTool
- [x] 6.1 Integrar preprocesamiento automático
  - Llamar a preprocessor después de obtener datos
  - Validar métricas antes de generar visualización
  - Manejar caso de DataFrame vacío
  - _Requirements: 7.1, 7.2_

- [x] 6.2 Mejorar manejo de errores
  - Capturar errores específicos
  - Incluir error en mensaje de respuesta
  - Continuar flujo en caso de fallo
  - _Requirements: 7.3, 10.5_

- [ ]* 6.3 Escribir property test para feedback detallado
  - **Property 10: Feedback detallado y transparente**
  - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**

- [x] 6.4 Añadir metadata en respuestas
  - Incluir información de preprocesamiento
  - Incluir registros excluidos y razones
  - Incluir métricas disponibles vs solicitadas
  - _Requirements: 7.4, 7.5_

- [x] 7. Implementar configuración visual consistente
- [x] 7.1 Definir paleta de colores médicos
  - Añadir paleta en settings.py
  - Usar paleta en prompts de generación
  - _Requirements: 5.1_

- [x] 7.2 Mejorar configuración de ejes y tooltips
  - Especificar títulos en español en prompts
  - Especificar formato de fecha para ejes temporales
  - Especificar hover tooltips con métricas y unidades
  - Especificar hovermode='x unified' para temporales
  - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [ ]* 7.3 Escribir property test para configuración visual
  - **Property 7: Configuración visual consistente**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 8. Integrar con Chat Unificado
- [x] 8.1 Implementar detección automática de visualizaciones
  - Modificar unified_agent.py para detectar consultas temporales
  - Detectar consultas con múltiples métricas numéricas
  - Invocar automáticamente herramienta de visualización
  - _Requirements: 10.1, 10.2_

- [ ]* 8.2 Escribir property test para integración automática
  - **Property 12: Integración automática con chat unificado**
  - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 8.3 Mejorar presentación de visualizaciones
  - Incluir visualizaciones en respuesta del chat
  - Organizar múltiples visualizaciones coherentemente
  - _Requirements: 10.3, 10.4_

- [x] 8.4 Implementar manejo graceful de errores
  - Continuar con respuesta textual si falla visualización
  - No interrumpir flujo conversacional
  - _Requirements: 10.5_

- [ ]* 8.5 Escribir property test para manejo de errores en chat
  - **Property 13: Manejo graceful de errores en chat**
  - **Validates: Requirements 10.5**

- [x] 9. Verificar compatibilidad con interfaces existentes
- [x] 9.1 Verificar interfaces públicas
  - Verificar que generate_visualization() mantiene firma
  - Verificar que execute() en tool mantiene firma
  - Verificar que visualization_handler funciona sin cambios
  - _Requirements: 9.4_

- [ ]* 9.2 Escribir property test para compatibilidad
  - **Property 11: Compatibilidad de interfaces públicas**
  - **Validates: Requirements 9.4**

- [x] 10. Checkpoint - Asegurar que todos los tests pasan
  - Ejecutar suite completa de unit tests
  - Ejecutar suite completa de property tests
  - Verificar que no hay regresiones
  - Asegurar que todos los tests pasan, preguntar al usuario si surgen problemas

- [ ] 11. Pruebas de integración end-to-end
- [ ]* 11.1 Escribir test e2e para timeline
  - Crear datos de prueba temporales
  - Generar visualización completa
  - Verificar figura válida y metadata

- [ ]* 11.2 Escribir test e2e con preprocesamiento
  - Crear datos desordenados con duplicados
  - Verificar que se preprocesan correctamente
  - Verificar visualización resultante

- [ ]* 11.3 Escribir test e2e con reintentos
  - Simular fallos en generación
  - Verificar reintentos y fallback
  - Verificar logging de errores

- [ ]* 11.4 Escribir test e2e de integración con chat
  - Simular consulta temporal desde chat
  - Verificar invocación automática
  - Verificar inclusión en respuesta

- [x] 12. Optimización y ajustes finales
- [x] 12.1 Optimizar performance
  - Implementar cache de plantillas
  - Optimizar operaciones de preprocesamiento
  - Verificar tiempos de ejecución
  - _Target: <5000ms end-to-end_

- [x] 12.2 Ajustar configuración
  - Ajustar max_retries si es necesario
  - Ajustar timeouts basado en pruebas
  - Ajustar paleta de colores si es necesario

- [ ] 13. Documentación
- [ ]* 13.1 Actualizar documentación existente
  - Actualizar VISUALIZATION_AGENT_ARCHITECTURE.md
  - Actualizar UNIFIED_CHAT_ARCHITECTURE.md
  - Actualizar README.md

- [ ]* 13.2 Crear nueva documentación
  - Crear VISUALIZATION_TEMPLATES_GUIDE.md
  - Crear DATA_PREPROCESSING_GUIDE.md

- [x] 14. Final Checkpoint - Verificación completa
  - Ejecutar todos los tests (unit + property + integration)
  - Verificar performance cumple targets
  - Verificar documentación completa
  - Asegurar que todo funciona correctamente, preguntar al usuario si surgen problemas
