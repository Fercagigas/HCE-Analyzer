# Mejoras al Sistema RAG — Análisis y Cambios Implementados

## Contexto

Durante la evaluación con RAGAS se detectó que el sistema RAG obtenía métricas
cercanas a cero en Context Precision y Context Recall a pesar de tener los
documentos clínicos correctamente indexados en Supabase pgvector. Este documento
describe el diagnóstico, los cambios aplicados y la evolución de las métricas.

---

## Línea Base — Resultados Antes de las Mejoras

Evaluación del **2026-04-27** (documentos indexados, sin mejoras de prompt):

| Métrica | Golden Set DB | Golden Set RAG | Umbral |
|---------|:---:|:---:|:---:|
| Faithfulness | 0.7883 | 0.7883 | 0.85 |
| Answer Relevancy | 0.0956 | 0.0000 | 0.80 |
| Context Precision | 0.0111 | 0.0167 | 0.75 |
| Context Recall | 0.0667 | 0.0333 | 0.70 |

Los scores de Context Precision y Context Recall prácticamente en cero indicaban
que el agente **no estaba invocando `search_clinical_documents`** para las preguntas
del golden set RAG, respondiendo desde su conocimiento general sin recuperar
fragmentos de los documentos indexados.

---

## Diagnóstico de Causas Raíz

### Causa 1 — Desalineación del system prompt con los documentos indexados

El system prompt del agente (`services/unified_chat/unified_agent.py`,
método `_create_system_prompt`) definía cuándo usar `search_clinical_documents`
con esta lista:

```
- Protocolos de urgencias y emergencias
- Guías de tratamiento de urgencias
- Información sobre medicamentos de urgencias
- Mejores prácticas en urgencias
- Procedimientos de triaje
```

Los documentos indexados son sobre **UCI y Medicina Intensiva**, no sobre urgencias:
- Manual del Residente de Medicina Intensiva (Hospital Virgen del Rocío)
- Estándares y Recomendaciones para UCI (Ministerio de Sanidad)
- El Libro de la UCI — Paul L. Marino, 3ª Edición

El agente no reconocía que debía buscar en los documentos para preguntas como
"¿Cuántas camas tiene la UCI?" o "¿Cuál es la ratio médico-paciente en nivel III?".

### Causa 2 — Límite de tokens del system prompt demasiado bajo

El `PromptManager` se inicializaba con `max_tokens=4000`. El prompt completo
(schema de BD + directivas + tool descriptions) alcanzaba 7726 tokens, por lo que
se truncaba a 4000 — eliminando parte del schema y las directivas de selección
de herramientas.

```
WARNING: Prompt exceeds token limit (7726 tokens). Truncating to fit 4000 tokens.
```

### Causa 3 — Contexto truncado a 600 caracteres en el RAG tool

En `services/unified_chat/tools/rag_tool.py`, el método `format_output` truncaba
el contenido de cada documento a 600 caracteres antes de pasarlo al LLM:

```python
if len(content) > 600:
    content = content[:600] + "..."
```

Los fragmentos de los documentos (parent chunks de ~3000 chars) quedaban cortados,
impidiendo que el LLM encontrara datos específicos como "9 mEq/min" o "58.1%".

### Causa 4 — `top_k=5` insuficiente para fragmentos específicos

El RAG tool usaba `top_k=5` por defecto. Con query augmentation (múltiples queries
por pregunta) y reranking, 5 resultados finales eran insuficientes para cubrir
fragmentos muy específicos dispersos en documentos de cientos de páginas.

### Causa 5 — `fetch_k` bajo en el reranker

`ImprovedRAGService.search()` usaba `fetch_k = top_k * 3` como candidatos para
el reranker. Con `top_k=5` solo se evaluaban 15 candidatos antes del reranking,
reduciendo la probabilidad de recuperar fragmentos relevantes.

### Causa 6 — Contexto RAG no llegaba a RAGAS

`_extract_tool_result` en `unified_agent.py` truncaba el `raw_output` del RAG
tool a 1000 caracteres:

```python
result['raw_output'] = observation[:1000]
```

`extract_contexts` en `run_ragas_eval.py` intentaba parsear los bloques
`--- Documento N: ---` del `raw_observation`, pero ese campo no existía en
`tool_results` — solo existía `raw_output` truncado. RAGAS recibía contexto
vacío o muy corto, lo que producía scores de Context Precision/Recall cercanos
a cero aunque el agente hubiera recuperado documentos correctamente.

---

## Cambios Implementados

### 1. System prompt — directivas de selección de herramienta

**Archivo:** `services/unified_chat/unified_agent.py`

Se reescribió la sección "Cuándo usar `search_clinical_documents`" para:
- Incluir explícitamente UCI, cuidados críticos y medicina intensiva
- Listar los documentos reales indexados en el sistema
- Cambiar "considera usar" por "SIEMPRE invoca"
- Añadir 8 ejemplos concretos de preguntas que deben usar la herramienta
- Añadir advertencia explícita de fallo si no se invoca

```python
# Antes
## Cuándo usar search_clinical_documents:
- Protocolos de urgencias y emergencias
- Guías de tratamiento de urgencias
...

# Después
## Cuándo usar search_clinical_documents:
**REGLA FUNDAMENTAL**: Si la pregunta NO contiene un subject_id o stay_id
específico de paciente, SIEMPRE invoca search_clinical_documents antes de
responder desde tu conocimiento general.
...
**DOCUMENTOS INDEXADOS EN EL SISTEMA**:
- Manual del Residente de Medicina Intensiva (Hospital Virgen del Rocío)
- Estándares y Recomendaciones para UCI (Ministerio de Sanidad)
- El Libro de la UCI - Paul L. Marino, 3ª Edición
```

### 2. Descripción del RAG tool

**Archivo:** `services/unified_chat/tools/rag_tool.py`

Se actualizó `tool_description` para reflejar los documentos reales indexados
y los casos de uso de UCI/Medicina Intensiva, alineándola con el system prompt.

### 3. Límite de tokens del PromptManager

**Archivo:** `services/unified_chat/unified_agent.py`

```python
# Antes
self.prompt_manager = PromptManager(max_tokens=4000, ...)

# Después
self.prompt_manager = PromptManager(max_tokens=8000, ...)
```

Esto elimina el truncado del prompt (7726 tokens < 8000) y garantiza que el
agente recibe el schema completo y todas las directivas.

### 4. Truncado de contenido en format_output

**Archivo:** `services/unified_chat/tools/rag_tool.py`

```python
# Antes
if len(content) > 600:
    content = content[:600] + "..."

# Después
if len(content) > 1500:
    content = content[:1500] + "..."
```

Los parent chunks (~3000 chars) ahora se pasan al LLM con suficiente contexto
para encontrar datos específicos.

### 5. top_k por defecto aumentado

**Archivo:** `services/unified_chat/tools/rag_tool.py`

```python
# Antes
k = top_k or 5

# Después
k = top_k or 8
```

Más resultados finales mejoran la cobertura de fragmentos específicos.

### 6. fetch_k del reranker aumentado

**Archivo:** `services/rag/improved_rag_service.py`

```python
# Antes
fetch_k = top_k * 3 if rerank else top_k

# Después
fetch_k = top_k * 4 if rerank else top_k
```

Con `top_k=8` y `fetch_k=32`, el reranker evalúa 32 candidatos antes de
seleccionar los 8 mejores — mayor probabilidad de recuperar fragmentos relevantes.

### 7. Preservación del raw_observation en tool_results

**Archivo:** `services/unified_chat/unified_agent.py`

```python
# Antes
result['raw_output'] = observation[:1000]

# Después
result['raw_output'] = observation          # texto completo
result['raw_observation'] = observation     # campo adicional para extract_contexts
```

### 8. extract_contexts mejorado en el evaluador

**Archivo:** `Evaluation/run_ragas_eval.py`

Se añadió lógica para parsear directamente los bloques `--- Documento N: ---`
del `raw_observation` cuando el tool es `search_clinical_documents`:

```python
if "search_clinical_documents" in str(tool_name):
    raw = tr.get("raw_observation") or tr.get("result") or ...
    if isinstance(raw, str) and "--- Documento" in raw:
        for match in doc_pattern.finditer(raw):
            doc_text = match.group(1).strip()
            if doc_text and len(doc_text) > 20:
                contexts.append(doc_text)
```

Esto garantiza que RAGAS recibe el texto real de los documentos recuperados,
no solo metadatos o strings truncados.

---

## Resultados Después de las Mejoras

Evaluación del **2026-04-28**:

### Golden Set DB (40 preguntas sobre MIMIC-IV-ED)

| Métrica | Antes (27-abr) | Después (28-abr) | Δ | Umbral |
|---------|:---:|:---:|:---:|:---:|
| Faithfulness | 0.7995 | 0.7357 | -0.064 | 0.85 |
| Answer Relevancy | 0.5011 | 0.5944 | **+0.093** | 0.80 |
| Context Precision | 0.7417 | 0.6021 | -0.140 | 0.75 |
| Context Recall | 0.7917 | **0.8458** | **+0.054** | 0.70 ✅ |

### Golden Set RAG (30 preguntas sobre guías clínicas UCI)

| Métrica | Sin docs (27-abr) | Con docs sin mejoras (27-abr) | Con mejoras (28-abr) | Umbral |
|---------|:---:|:---:|:---:|:---:|
| Faithfulness | 0.7170 | 0.7883 | 0.5708 | 0.85 |
| Answer Relevancy | 0.0000 | 0.0956 | 0.4348 | 0.80 |
| Context Precision | 0.0167 | 0.0111 | **0.4501** | 0.75 |
| Context Recall | 0.0333 | 0.0667 | **0.4694** | 0.70 |

La mejora más significativa es en el golden set RAG: Context Precision pasó de
0.011 a **0.450** (+4000%) y Context Recall de 0.033 a **0.469** (+1300%),
confirmando que el agente ahora invoca `search_clinical_documents` y recupera
contexto real de los documentos.

---

## Análisis de Métricas Pendientes

### Faithfulness (RAG: 0.57, umbral 0.85)

Las respuestas incluyen interpretaciones clínicas del LLM que van más allá del
texto recuperado. El modelo añade contexto de su conocimiento general aunque
los documentos no lo contengan explícitamente. Posibles mejoras:
- Reforzar directivas anti-alucinación específicas para respuestas RAG
- Añadir instrucción explícita: "responde SOLO con lo que aparece en los fragmentos"

### Answer Relevancy (RAG: 0.43, umbral 0.80)

Las respuestas son largas y añaden contexto no solicitado. El agente tiende a
elaborar más de lo necesario. Posibles mejoras:
- Directiva de concisión específica para respuestas RAG
- Limitar la longitud de respuesta cuando la pregunta es directa

### Context Precision (RAG: 0.45, umbral 0.75)

Solo el 45% del contexto recuperado es directamente relevante para la pregunta.
El sistema recupera fragmentos relacionados pero no siempre los más precisos.
Posibles mejoras:
- Ajustar el modelo de reranking para el dominio médico en español
- Aumentar el peso de la búsqueda léxica (tsvector) para términos técnicos exactos

### Context Recall (RAG: 0.47, umbral 0.70)

El sistema recupera menos de la mitad de la información necesaria para responder.
Los fragmentos específicos (datos numéricos exactos) no siempre están en los
top-8 resultados. Posibles mejoras:
- Aumentar `top_k` a 10-12 para preguntas de tipo `directa`
- Mejorar el chunking para preservar mejor los datos numéricos en contexto

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `services/unified_chat/unified_agent.py` | System prompt, max_tokens=8000, raw_observation |
| `services/unified_chat/tools/rag_tool.py` | tool_description, top_k=8, truncado 1500 chars |
| `services/rag/improved_rag_service.py` | fetch_k = top_k * 4 |
| `Evaluation/run_ragas_eval.py` | extract_contexts con parseo de raw_observation |

---

## Referencias

- Golden sets: `Evaluation/golden_set_ragas.json`, `Evaluation/golden_set_ragas_rag.json`
- Resultados evaluación: `Evaluation/results/`
- Documentación de evaluación: `docs/EVALUACION_SISTEMA.md`
- Servicio RAG: `services/rag/improved_rag_service.py`
- RAG Tool: `services/unified_chat/tools/rag_tool.py`
