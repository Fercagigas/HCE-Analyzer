# ChatHCE - Documentación

Capa de inteligencia clínica con IA y RAG sobre MIMIC-IV Clinical Demo 2.2 (hospitalario + UCI). Fase 1 (Foundation) completada el 2 de septiembre de 2026.

---

## 🚀 Inicio rápido

- **Estado del proyecto** → [ESTADO_ACTUAL.md](ESTADO_ACTUAL.md) (empezar aquí) | roadmap con estado → [../ROADMAP_HOSPITAL_READY/README.md](../ROADMAP_HOSPITAL_READY/README.md)
- **Producto / dirección** → [product/INTENDED_PURPOSE.md](product/INTENDED_PURPOSE.md) | [product/COMPETITIVE_POSITIONING.md](product/COMPETITIVE_POSITIONING.md)
- **Usuarios** → [../README.md](../README.md) (instalación, ejecución, uso) | [UNIFIED_CHAT_COMPLETE_GUIDE.md](UNIFIED_CHAT_COMPLETE_GUIDE.md)
- **Desarrolladores** → [UNIFIED_CHAT_ARCHITECTURE.md](UNIFIED_CHAT_ARCHITECTURE.md) | [UNIFIED_CHAT_TOOL_CREATION.md](UNIFIED_CHAT_TOOL_CREATION.md) | [architecture/INVENTORY.md](architecture/INVENTORY.md) | [../tests/README.md](../tests/README.md)
- **Administradores** → [CONFIGURACION_SUPABASE_VERIFICADA.md](CONFIGURACION_SUPABASE_VERIFICADA.md) | [../db/README.md](../db/README.md) | [RAG_VECTORIZATION_VERIFICATION.md](RAG_VECTORIZATION_VERIFICATION.md)
- **Seguridad** → [security/THREAT_MODEL.md](security/THREAT_MODEL.md) | [security/SUPABASE_VERIFICATION_CHECKLIST.md](security/SUPABASE_VERIFICATION_CHECKLIST.md) | [decisions/](decisions/)
- **Evaluación** → [baseline/FASE1_BASELINE.md](baseline/FASE1_BASELINE.md)

---

Ver **[INDEX.md](INDEX.md)** para el índice completo organizado por tema y audiencia.
El backlog de transformación hospitalaria vive fuera de `docs/`, en **`ROADMAP_HOSPITAL_READY/`**, con el estado de cada documento.

## 📁 Estructura

```
docs/
├── INDEX.md                              # Índice de documentación
├── README.md                             # Este archivo
├── ESTADO_ACTUAL.md                      # Fase, arquitectura, verificación y pendientes
├── APRENDIZAJES_FASE1.md                 # Clase magistral: decisiones, razones y lecciones de Fase 1
│
├── UNIFIED_CHAT_ARCHITECTURE.md          # Arquitectura del chat (core chathce/, gateway, tools, canales)
├── UNIFIED_CHAT_TOOL_CREATION.md         # Crear herramientas (ToolContract + handler)
├── VISUALIZATION_SYSTEM.md               # Visualización con plantillas parametrizadas
├── PROMPT_ENGINEERING_GUIDE.md           # System prompt: plantilla, tools generadas, invariantes
├── LLM_PROVIDER_MAPPING.md               # Port LLMProvider, adapter Anthropic, fallback
├── UNIFIED_CHAT_COMPLETE_GUIDE.md        # Guía de usuario (histórica en lo técnico)
├── CONVERSATION_MEMORY_IMPLEMENTATION.md # Memoria conversacional del agente anterior (histórico)
│
├── MIMIC_IV_DATA_DICTIONARY.md           # Diccionario de datos (18 tablas)
├── MIGRACION_MIMIC_IV.md                 # Migración MIMIC-IV-ED → MIMIC-IV Demo 2.2 (histórico)
├── DATABASE_SCHEMA_UPDATE.md             # Esquema public.*, RLS y autenticación
├── CONFIGURACION_SUPABASE_VERIFICADA.md  # Esquemas, RPC vigentes/a eliminar, claves por función
│
├── RAG_VECTORIZATION_VERIFICATION.md     # Sistema RAG (embeddings, híbrido, reranking)
├── RAG_MEJORAS_METRICAS.md               # Mejoras y métricas del RAG (histórico)
├── EVALUACION_SISTEMA.md                 # Evaluación del sistema (histórico)
│
├── product/                              # Intended purpose, alcance, riesgo y posicionamiento
│   ├── INTENDED_PURPOSE.md
│   ├── OUT_OF_SCOPE.md
│   ├── CLINICAL_USE_CASES.md
│   ├── RISK_CAPABILITY_MATRIX.md
│   └── COMPETITIVE_POSITIONING.md
│
├── decisions/                            # ADRs
│   ├── 0001-chathce-capa-ia-clinica-no-hce.md
│   ├── 0010-desacoplar-core-de-runtime-y-proveedores.md
│   ├── 0020-baseline-reproducible-tests-evaluation.md
│   ├── 0030-metodologia-y-alcance-threat-model-inicial.md
│   ├── 0040-visualizaciones-parametrizadas-sin-ejecucion-de-codigo.md
│   ├── 0050-acceso-datos-clinicos-allowlisted-y-agregados-server-side.md
│   ├── 0060-cerrar-superficie-web-xsrf-cors.md
│   ├── 0070-verificacion-operativa-de-supabase-y-despliegue.md
│   ├── 0080-model-gateway-sdk-anthropic-y-retiro-de-langchain.md
│   ├── 0090-request-context-scope-estricto-contratos-y-evidence.md
│   ├── 0100-autenticacion-api-jwt-supabase-y-sesion-streamlit-revalidada.md
│   ├── 0110-layout-chathce-composition-root-y-adapters-de-presentacion.md
│   └── 0120-estrategia-de-tests-por-capas-y-baseline-fase-1.md
│
├── security/                             # Threat model (con estado tras Fase 1) y checklist Supabase
│   ├── THREAT_MODEL.md
│   └── SUPABASE_VERIFICATION_CHECKLIST.md
│
├── architecture/                         # Inventario y acoplamiento tras Fase 1
│   ├── INVENTORY.md
│   └── COUPLING_MAP.md
│
└── baseline/                             # Baselines reproducibles por fase
    ├── FASE0_BASELINE.md
    ├── FASE1_WP0_BASELINE.md
    ├── FASE1_BASELINE.md
    └── raw/                              # Salidas crudas de tests y evaluación
```

Fuera de `docs/`: `ROADMAP_HOSPITAL_READY/` (backlog con estado), `db/README.md` (migraciones), `tests/README.md` (tests), `.env.example` (configuración).
