# ChatHCE - Índice de Documentación

**Última actualización**: 2 de septiembre de 2026 (cierre de Fase 1)

---

## 🧭 Estado del proyecto

- **[ESTADO_ACTUAL.md](ESTADO_ACTUAL.md)** - En qué punto estamos: fase, arquitectura, verificación de cierre de Fase 1, acciones pendientes del propietario (empezar aquí)
- **[APRENDIZAJES_FASE1.md](APRENDIZAJES_FASE1.md)** - Clase magistral de la Fase 1: qué se tuvo en cuenta, qué se construyó y por qué, lecciones de evaluación y de proceso
- **[../ROADMAP_HOSPITAL_READY/README.md](../ROADMAP_HOSPITAL_READY/README.md)** - Roadmap hospital-ready con estado por documento; fases en `15-implementation-phases.md`

---

## 🎯 Producto y posicionamiento

- **[product/INTENDED_PURPOSE.md](product/INTENDED_PURPOSE.md)** - Intended purpose aprobado de la versión 1 (usuarios, tareas, contexto de uso, gobernanza)
- **[product/OUT_OF_SCOPE.md](product/OUT_OF_SCOPE.md)** - Límites explícitos: lo que ChatHCE no hace
- **[product/CLINICAL_USE_CASES.md](product/CLINICAL_USE_CASES.md)** - Casos de uso clínicos previstos
- **[product/RISK_CAPABILITY_MATRIX.md](product/RISK_CAPABILITY_MATRIX.md)** - Clasificación de capabilities por riesgo y controles asociados
- **[product/COMPETITIVE_POSITIONING.md](product/COMPETITIVE_POSITIONING.md)** - Análisis competitivo tras ChatGPT Health + Epic (sep 2026): ejes de diferenciación y opciones abiertas

---

## 🏗️ Arquitectura del sistema (Fase 1)

- **[UNIFIED_CHAT_ARCHITECTURE.md](UNIFIED_CHAT_ARCHITECTURE.md)** - Arquitectura del chat: `RequestContext`, `ChatService`, `ModelGateway`, `ToolRegistry`, `ScopeGuard`, 12 tools, `ChatResponse`, canales Streamlit y FastAPI
- **[architecture/INVENTORY.md](architecture/INVENTORY.md)** - Inventario tras Fase 1: módulos, datos, secretos, dependencias, superficie expuesta al modelo
- **[architecture/COUPLING_MAP.md](architecture/COUPLING_MAP.md)** - Acoplamientos cerrados en Fase 1 y los que permanecen
- **[VISUALIZATION_SYSTEM.md](VISUALIZATION_SYSTEM.md)** - Visualizaciones con plantillas parametrizadas (sin código generado), tool `create_visualization`
- **[../db/README.md](../db/README.md)** - Migraciones SQL versionadas (RPC de agregados, retirada de SQL libre) y claves por función
- **[../tests/README.md](../tests/README.md)** - Estructura de tests por capas, fakes, fixtures MIMIC y cómo ejecutarlos

---

## 📋 Decisiones (ADRs)

- **[decisions/0001](decisions/0001-chathce-capa-ia-clinica-no-hce.md)** - ChatHCE es una capa de IA clínica, no una HCE (decisión fundacional)
- **[decisions/0010](decisions/0010-desacoplar-core-de-runtime-y-proveedores.md)** - Desacoplar core de runtime y proveedores
- **[decisions/0020](decisions/0020-baseline-reproducible-tests-evaluation.md)** - Baseline reproducible de tests y evaluación
- **[decisions/0030](decisions/0030-metodologia-y-alcance-threat-model-inicial.md)** - Metodología y alcance del threat model inicial
- **[decisions/0040](decisions/0040-visualizaciones-parametrizadas-sin-ejecucion-de-codigo.md)** - Visualizaciones parametrizadas sin ejecución de código
- **[decisions/0050](decisions/0050-acceso-datos-clinicos-allowlisted-y-agregados-server-side.md)** - Acceso a datos clínicos MIMIC por operaciones allowlisted y agregados server-side (sin SQL libre)
- **[decisions/0060](decisions/0060-cerrar-superficie-web-xsrf-cors.md)** - Cerrar superficie web: XSRF, CORS y bind localhost
- **[decisions/0070](decisions/0070-verificacion-operativa-de-supabase-y-despliegue.md)** - Verificación operativa de Supabase y despliegue
- **[decisions/0080](decisions/0080-model-gateway-sdk-anthropic-y-retiro-de-langchain.md)** - Model Gateway sobre SDK `anthropic` y retiro de LangChain del bucle agéntico
- **[decisions/0090](decisions/0090-request-context-scope-estricto-contratos-y-evidence.md)** - `RequestContext`, scope estricto de paciente, contratos de tools y schemas Evidence/Claim
- **[decisions/0100](decisions/0100-autenticacion-api-jwt-supabase-y-sesion-streamlit-revalidada.md)** - Autenticación de la API por JWT de Supabase y sesión Streamlit revalidada; claves por función
- **[decisions/0110](decisions/0110-layout-chathce-composition-root-y-adapters-de-presentacion.md)** - Layout del paquete `chathce`, composition root y adapters de presentación
- **[decisions/0120](decisions/0120-estrategia-de-tests-por-capas-y-baseline-fase-1.md)** - Estrategia de tests por capas y baseline de Fase 1

---

## 🔒 Seguridad

- **[security/THREAT_MODEL.md](security/THREAT_MODEL.md)** - Threat model (baseline Fase 0 + sección «Estado tras Fase 1» con el estado de cada riesgo)
- **[security/SUPABASE_VERIFICATION_CHECKLIST.md](security/SUPABASE_VERIFICATION_CHECKLIST.md)** - Checklist de verificación operativa de Supabase, con la nota de Fase 1 (RPC a eliminar, RPC nuevas, claves por función)

---

## 📊 Evaluación y baselines

- **[baseline/FASE1_BASELINE.md](baseline/FASE1_BASELINE.md)** - Baseline de cierre de Fase 1: suite, cobertura, evaluación live por módulo, Definition of Done
- **[baseline/FASE1_WP0_BASELINE.md](baseline/FASE1_WP0_BASELINE.md)** - Baseline intermedio tras el saneamiento de configuración (WP0)
- **[baseline/FASE0_BASELINE.md](baseline/FASE0_BASELINE.md)** - Baseline de la Fase 0
- **[baseline/raw/](baseline/raw/)** - Salidas crudas de tests y evaluación por fase
- **[EVALUACION_SISTEMA.md](EVALUACION_SISTEMA.md)** - Evaluación del sistema (histórico)
- **[RAG_MEJORAS_METRICAS.md](RAG_MEJORAS_METRICAS.md)** - Mejoras y métricas del sistema RAG (histórico)

---

## 🔧 Guías técnicas

- **[UNIFIED_CHAT_TOOL_CREATION.md](UNIFIED_CHAT_TOOL_CREATION.md)** - Crear una tool: `ToolContract`, handler, registro en el composition root, tests
- **[PROMPT_ENGINEERING_GUIDE.md](PROMPT_ENGINEERING_GUIDE.md)** - Plantilla del system prompt, sección de tools generada, invariantes verificados por tests
- **[LLM_PROVIDER_MAPPING.md](LLM_PROVIDER_MAPPING.md)** - Port `LLMProvider`, adapter Anthropic, cadena de fallback, cómo añadir otro proveedor
- **[CONVERSATION_MEMORY_IMPLEMENTATION.md](CONVERSATION_MEMORY_IMPLEMENTATION.md)** - Memoria conversacional del agente anterior (histórico; ver banner)

---

## 🗄️ Base de datos MIMIC-IV

- **[MIMIC_IV_DATA_DICTIONARY.md](MIMIC_IV_DATA_DICTIONARY.md)** - Diccionario de datos completo: 18 tablas, columnas, tipos y claves (referencia canónica del esquema)
- **[MIGRACION_MIMIC_IV.md](MIGRACION_MIMIC_IV.md)** - Migración de MIMIC-IV-ED a MIMIC-IV Clinical Demo 2.2 (histórico; ver banner)

---

## ⚙️ Configuración

- **[CONFIGURACION_SUPABASE_VERIFICADA.md](CONFIGURACION_SUPABASE_VERIFICADA.md)** - Esquemas, conteos, funciones RPC vigentes y a eliminar, patrón de acceso del provider, claves por función
- **[DATABASE_SCHEMA_UPDATE.md](DATABASE_SCHEMA_UPDATE.md)** - Esquema `public.*`, RLS, triggers y autenticación (ver banner)
- **[RAG_VECTORIZATION_VERIFICATION.md](RAG_VECTORIZATION_VERIFICATION.md)** - Sistema RAG: embeddings, búsqueda híbrida, reranking (vigente)
- **[../.env.example](../.env.example)** - Variables de entorno: credenciales, `CLINICAL_*`, `LLM_*`, `API_*`, `AUDIT_*`

---

## 📚 Guías de usuario

- **[UNIFIED_CHAT_COMPLETE_GUIDE.md](UNIFIED_CHAT_COMPLETE_GUIDE.md)** - Guía consolidada de uso (histórica en lo técnico; los ejemplos siguen sirviendo con el paciente activo seleccionado)
- **[../README.md](../README.md)** - Instalación, ejecución (Streamlit y API), uso de la interfaz, endpoints

---

## 🗂️ Por audiencia

| Audiencia | Documentos |
|-----------|-----------|
| Producto / dirección | ESTADO_ACTUAL, INTENDED_PURPOSE, OUT_OF_SCOPE, CLINICAL_USE_CASES, RISK_CAPABILITY_MATRIX, COMPETITIVE_POSITIONING, ROADMAP_HOSPITAL_READY |
| Usuarios | README raíz, UNIFIED_CHAT_COMPLETE_GUIDE |
| Desarrolladores | UNIFIED_CHAT_ARCHITECTURE, architecture/, UNIFIED_CHAT_TOOL_CREATION, PROMPT_ENGINEERING_GUIDE, LLM_PROVIDER_MAPPING, VISUALIZATION_SYSTEM, tests/README, decisions/ |
| Administradores | CONFIGURACION_SUPABASE_VERIFICADA, db/README, DATABASE_SCHEMA_UPDATE, RAG_VECTORIZATION_VERIFICATION, .env.example |
| Seguridad / DPO | THREAT_MODEL, SUPABASE_VERIFICATION_CHECKLIST, RISK_CAPABILITY_MATRIX, decisions/0050, 0090, 0100 |
| Auditoría / evaluación | baseline/FASE1_BASELINE, baseline/raw, decisions/0120, Evaluation/ |

---

> El backlog de transformación hospitalaria (15 documentos, fases 0-9) vive fuera de `docs/`, en **`ROADMAP_HOSPITAL_READY/`**. Cada documento incluye su estado a 2 de septiembre de 2026.
