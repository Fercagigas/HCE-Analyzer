# Implementation Plan - Claude Haiku 4.5 Upgrade with Anti-Hallucination

## Task Overview

Este plan implementa la actualización del sistema de Chat Unificado a Claude Haiku 4.5 con mejoras anti-alucinación, asegurando que el modelo sea consciente de su contexto y proporcione respuestas fundamentadas en datos reales.

## Implementation Tasks

- [x] 1. Actualizar configuración del modelo a Claude Haiku 4.5
- [x] 1.1 Modificar ClaudeAgentSettings en settings.py
  - Cambiar primary_model de "claude-3-5-haiku-latest" a "claude-haiku-4-5-20251001"
  - Cambiar primary_model_version a "claude-haiku-4-5-20251001"
  - Verificar que los valores por defecto son correctos
  - _Requirements: 1.1, 1.2_

- [x] 1.2 Actualizar llm_manager.py
  - Modificar _get_model_chain() para usar el nuevo modelo
  - Verificar que el fallback chain se mantiene
  - Añadir logging para confirmar modelo usado
  - _Requirements: 1.3, 1.4_

- [x] 1.3 Verificar inicialización del modelo
  - Ejecutar test de conexión con el nuevo modelo
  - Verificar que la API key funciona con Haiku 4.5
  - Confirmar que el modelo responde correctamente
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implementar contexto del sistema en el system prompt
- [x] 2.1 Crear sección de identidad del sistema
  - Añadir identificación como "ChatHCE - Asistente de Análisis Clínico de Urgencias"
  - Describir propósito principal del sistema
  - Especificar especialización en datos de urgencias
  - _Requirements: 2.1, 2.2_

- [x] 2.2 Añadir contexto operativo del dataset
  - Describir MIMIC-IV-ED como dataset de demostración
  - Especificar que contiene 222 pacientes únicos
  - Listar tablas disponibles (edstays, triage, vitalsign, diagnosis, medrecon, pyxis)
  - _Requirements: 2.4_

- [x] 2.3 Documentar herramientas disponibles
  - Describir query_mimic_database y sus capacidades
  - Describir search_clinical_documents y su propósito
  - Describir request_visualization y tipos de gráficas
  - _Requirements: 2.3_

- [x] 2.4 Especificar idioma y terminología
  - Indicar que las respuestas deben ser en español
  - Especificar uso de terminología médica apropiada
  - _Requirements: 2.5_

- [x] 3. Implementar directivas anti-alucinación
- [x] 3.1 Crear sección de prohibiciones absolutas
  - Prohibir inventar subject_id, stay_id, hadm_id
  - Prohibir fabricar valores de signos vitales
  - Prohibir inventar diagnósticos o códigos ICD
  - Prohibir crear medicamentos o dosis ficticias
  - Prohibir generar fechas o timestamps falsos
  - _Requirements: 3.1, 3.4, 5.3_

- [x] 3.2 Implementar manejo de datos faltantes
  - Definir respuesta para datos no encontrados
  - Definir respuesta para valores nulos
  - Definir respuesta para pacientes inexistentes
  - _Requirements: 3.2, 4.1_

- [x] 3.3 Implementar citación de fuentes
  - Requerir mención de herramienta usada
  - Requerir mención de tabla de origen
  - Requerir citación de documentos RAG
  - _Requirements: 3.3, 4.5_

- [x] 3.4 Implementar reconocimiento de incertidumbre
  - Definir frases para datos verificados
  - Definir frases para interpretaciones
  - Definir frases para inferencias
  - _Requirements: 3.5, 4.2, 4.3_

- [x] 3.5 Documentar limitaciones del dataset
  - Especificar que es dataset de demostración
  - Indicar que solo contiene datos de urgencias
  - Clarificar que no hay acceso a datos externos
  - _Requirements: 3.4, 4.4_

- [x] 4. Integrar directivas en el system prompt
- [x] 4.1 Modificar _create_system_prompt() en unified_agent.py
  - Añadir sección de identidad al inicio
  - Añadir contexto operativo después de identidad
  - Añadir directivas anti-alucinación antes de guías de herramientas
  - Mantener guías de selección de herramientas existentes
  - _Requirements: 5.1, 5.2_

- [x] 4.2 Actualizar PromptManager si es necesario
  - Añadir método get_anti_hallucination_directives()
  - Añadir método get_system_context()
  - Integrar con get_system_prompt()
  - _Requirements: 5.2, 5.5_

- [x] 4.3 Verificar estructura del prompt
  - Confirmar que todas las secciones están presentes
  - Verificar orden correcto de secciones
  - Validar que no hay conflictos con prompts existentes
  - _Requirements: 5.1, 5.2_

- [x] 5. Escribir tests unitarios
- [x] 5.1 Test de versión del modelo
  - Verificar que se usa claude-haiku-4-5-20251001
  - Verificar configuración en settings
  - Verificar inicialización en llm_manager
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5.2 Test de identidad del sistema
  - Verificar que el prompt contiene "ChatHCE"
  - Verificar que menciona "Asistente de Análisis Clínico de Urgencias"
  - _Requirements: 2.1, 2.2_

- [x] 5.3 Test de contexto operativo
  - Verificar que menciona MIMIC-IV-ED
  - Verificar que menciona 222 pacientes
  - Verificar que lista las tablas disponibles
  - _Requirements: 2.4_

- [x] 5.4 Test de directivas anti-alucinación
  - Verificar que contiene prohibiciones
  - Verificar que contiene manejo de datos faltantes
  - Verificar que contiene citación de fuentes
  - _Requirements: 3.1, 3.2, 3.3, 5.3_

- [x] 5.5 Test de fallback chain
  - Verificar que el fallback funciona si Haiku 4.5 falla
  - Verificar que los modelos secundarios están configurados
  - _Requirements: 1.4_

- [x] 6. Escribir tests de integración
- [x] 6.1 Test de respuesta con datos reales
  - Consultar paciente existente
  - Verificar que la respuesta cita la fuente
  - Verificar que no hay datos inventados
  - _Requirements: 3.1, 3.3_

- [x] 6.2 Test de manejo de datos faltantes
  - Consultar paciente inexistente
  - Verificar que indica que no existe
  - Verificar que no inventa datos
  - _Requirements: 3.2, 4.1_

- [x] 6.3 Test de reconocimiento de incertidumbre
  - Solicitar interpretación de datos
  - Verificar que distingue datos de interpretaciones
  - Verificar uso de frases apropiadas
  - _Requirements: 3.5, 4.2, 4.3_

- [x] 6.4 Test de citación de fuentes RAG
  - Consultar información de documentos clínicos
  - Verificar que cita el documento fuente
  - Verificar que distingue de datos de base de datos
  - _Requirements: 4.5_

- [x] 7. Checkpoint - Verificar tests
  - Ejecutar todos los tests unitarios
  - Ejecutar todos los tests de integración
  - Verificar que no hay regresiones
  - Documentar cualquier problema encontrado

- [x] 8. Actualizar documentación
- [x] 8.1 Actualizar README.md
  - Documentar nuevo modelo usado
  - Actualizar requisitos si es necesario
  - _Requirements: N/A_

- [x] 8.2 Actualizar UNIFIED_CHAT_ARCHITECTURE.md
  - Documentar cambio de modelo
  - Documentar directivas anti-alucinación
  - Actualizar diagrama de flujo si es necesario
  - _Requirements: N/A_

- [x] 8.3 Actualizar steering rules
  - Actualizar unified-chat-system.md con nuevo modelo
  - Añadir información sobre anti-alucinación
  - _Requirements: N/A_

- [x] 9. Pruebas manuales de validación
- [x] 9.1 Probar consultas de pacientes
  - Consultar datos de paciente existente
  - Verificar respuesta fundamentada
  - Verificar citación de fuentes

- [x] 9.2 Probar consultas de datos inexistentes
  - Consultar paciente que no existe
  - Verificar que indica que no existe
  - Verificar que no inventa datos

- [x] 9.3 Probar consultas de interpretación
  - Solicitar análisis de tendencias
  - Verificar distinción datos/interpretación
  - Verificar uso de frases apropiadas

- [x] 9.4 Probar consultas RAG
  - Consultar guías clínicas
  - Verificar citación de documentos
  - Verificar que no inventa guías

- [x] 10. Final Checkpoint - Verificación completa
  - Ejecutar todos los tests (unit + integration)
  - Verificar que el modelo responde correctamente
  - Verificar que no hay alucinaciones en pruebas manuales
  - Confirmar que la documentación está actualizada
  - Preguntar al usuario si hay problemas

## Notes

### Consideraciones de Implementación
- El cambio de modelo es principalmente de configuración
- El system prompt mejorado es el cambio más significativo
- Mantener compatibilidad con el código existente
- No modificar las herramientas (database_tool, rag_tool, visualization_tool)

### Riesgos
- El modelo Haiku 4.5 podría tener comportamiento diferente
- El system prompt más largo aumenta tokens de entrada
- Posibles cambios en la API de Anthropic

### Métricas de Éxito
- 0 alucinaciones en pruebas manuales
- Todos los tests pasan
- Tiempo de respuesta similar al anterior
- Respuestas siempre citan fuentes cuando usan herramientas
