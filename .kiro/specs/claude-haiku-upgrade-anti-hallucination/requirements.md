# Requirements Document

## Introduction

Este documento especifica los requisitos para actualizar el sistema de Chat Unificado de ChatHCE, migrando de Claude Haiku 3.5 a Claude Haiku 4.5 e implementando mejoras significativas para minimizar alucinaciones. El objetivo es que el modelo sea plenamente consciente de su contexto operativo, sus capacidades y limitaciones, y que proporcione respuestas fundamentadas exclusivamente en datos reales del dataset MIMIC-IV-ED.

## Glossary

- **ChatHCE**: Sistema de análisis clínico inteligente especializado en datos del Servicio de Urgencias
- **Claude Haiku 4.5**: Versión actualizada del modelo de lenguaje de Anthropic (claude-haiku-4-5-20251001)
- **MIMIC-IV-ED**: Dataset de demostración de datos médicos del Servicio de Urgencias (Emergency Department)
- **Alucinación**: Generación de información falsa o inventada que no está respaldada por datos reales
- **Grounding**: Técnica para anclar las respuestas del modelo a datos y contexto verificables
- **System Prompt**: Instrucciones iniciales que definen el comportamiento y contexto del modelo
- **UnifiedChatAgent**: Agente principal del sistema que orquesta las herramientas de consulta
- **Anti-hallucination**: Conjunto de técnicas y directivas para prevenir la generación de información falsa

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to upgrade the LLM model to Claude Haiku 4.5, so that the system benefits from improved capabilities and performance.

#### Acceptance Criteria

1. WHEN the UnifiedChatAgent initializes THEN the system SHALL use the model identifier "claude-haiku-4-5-20251001" as the primary model
2. WHEN the ClaudeAgentSettings loads configuration THEN the system SHALL set primary_model to "claude-haiku-4-5-20251001"
3. WHEN the LLM manager creates a new instance THEN the system SHALL configure the model with the updated version string
4. WHEN a fallback occurs THEN the system SHALL maintain the existing fallback chain with secondary and tertiary models

### Requirement 2

**User Story:** As a medical professional, I want the AI assistant to be fully aware of its operational context, so that it provides contextually appropriate responses.

#### Acceptance Criteria

1. WHEN the system prompt initializes THEN the system SHALL include a clear identity statement identifying itself as "ChatHCE - Asistente de Análisis Clínico de Urgencias"
2. WHEN the system prompt initializes THEN the system SHALL describe its primary purpose as analyzing emergency department data from MIMIC-IV-ED
3. WHEN the system prompt initializes THEN the system SHALL enumerate its available tools (database queries, RAG search, visualizations)
4. WHEN the system prompt initializes THEN the system SHALL specify that it operates exclusively with the MIMIC-IV-ED demo dataset containing 222 unique patients
5. WHEN the system prompt initializes THEN the system SHALL declare its response language as Spanish with appropriate medical terminology

### Requirement 3

**User Story:** As a medical professional, I want the AI assistant to never fabricate medical data, so that I can trust the information provided.

#### Acceptance Criteria

1. WHEN the model generates a response about patient data THEN the system SHALL only include information retrieved from the MIMIC-IV-ED database
2. WHEN the model cannot find requested information THEN the system SHALL explicitly state that the data is not available in the dataset
3. WHEN the model provides numerical values THEN the system SHALL cite the source table and query used to obtain the data
4. WHEN the model is asked about data outside MIMIC-IV-ED scope THEN the system SHALL clearly indicate that such data does not exist in the available dataset
5. WHEN the model provides clinical interpretations THEN the system SHALL distinguish between data-based observations and general medical knowledge

### Requirement 4

**User Story:** As a medical professional, I want the AI assistant to acknowledge uncertainty, so that I understand the reliability of the information provided.

#### Acceptance Criteria

1. WHEN the model encounters incomplete or null data THEN the system SHALL explicitly mention the data gaps in its response
2. WHEN the model makes inferences THEN the system SHALL clearly label them as interpretations rather than facts
3. WHEN the model is asked about information it cannot verify THEN the system SHALL respond with "No tengo información suficiente para responder esta pregunta"
4. WHEN the model provides statistical analysis THEN the system SHALL include sample sizes and data quality indicators
5. WHEN the model references clinical guidelines THEN the system SHALL distinguish between RAG-retrieved guidelines and general knowledge

### Requirement 5

**User Story:** As a developer, I want the anti-hallucination directives to be maintainable and configurable, so that they can be updated without code changes.

#### Acceptance Criteria

1. WHEN the PromptManager generates the system prompt THEN the system SHALL include a dedicated anti-hallucination section
2. WHEN the anti-hallucination directives are defined THEN the system SHALL organize them in a structured format within the prompt
3. WHEN the system prompt is generated THEN the system SHALL include explicit prohibitions against inventing patient IDs, medical values, or diagnoses
4. WHEN the system prompt is generated THEN the system SHALL include instructions for handling queries about non-existent data
5. WHEN the system prompt is cached THEN the system SHALL include the anti-hallucination directives in the cached version
