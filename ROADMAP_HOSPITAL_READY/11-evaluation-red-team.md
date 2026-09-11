# 11 — Evaluación clínica, seguridad y Red Team

## Estado a 7 de septiembre de 2026 (Fase 2 - security foundation)

Leyenda: ✅ hecho · 🟡 parcial · ⏳ pendiente · — no aplica. Referencias: ADRs en `docs/decisions/`, evidencia en `docs/baseline/FASE1_BASELINE.md`.

| Área | Estado | Evidencia / nota |
|---|---|---|
| Seguridad: direct/indirect injection, encoded/obfuscated, cross-patient/cross-tenant, exfiltración y tool misuse | ✅ | `tests/security/` 78 tests offline; `Evaluation/security_payloads.py` 27 payloads live clasificados critical/high/medium (ADR 0150) |
| Seguridad: indirect injection live | 🟡 | `SEC-IND-001` manual con `--include-indirect-fixture` y documento de prueba aislado; no se ejecuta automáticamente contra producción |
| Regression gates | ✅ | `.github/workflows/security-suite.yml` ejecuta `pytest tests/security` como gate bloqueante y `pytest tests` informativo sin `.env` en PR/push a `main`; cero tolerancia a violaciones critical |
| Bulk queries no autorizadas | 🟡 | Límite ≤200 filas y agregados solo con `purpose=research`; test de volumen pendiente |
| Evaluación clínica | 🟡 | Golden set v2 (40 preguntas MIMIC-IV con `ground_truth_operation`, `scope`, `expected_tool`); 20 pendientes de validación clínica; casos de datos ausentes/contradictorios/unidades pendientes |
| Métricas | 🟡 | RAGAS (faithfulness, relevancy, precision, recall), corrección de tool, latencia P50 por categoría. Claim support, citation correctness, abstention correctness pendientes. Violaciones de autorización y fugas entre pacientes medidas en suite: 0 |
| Golden sets versionados | 🟡 | `Evaluation/golden_set_ragas.json` v2 con `metadata.data_snapshot`; por especialidad/riesgo pendiente |
| Red team multidisciplinar / casos humanos | ⏳ | |

Baseline de referencia: `docs/baseline/FASE1_BASELINE.md`. Lecciones de la evaluación live: los verificadores por palabras clave dieron falsos negativos ante rechazos legítimos; se corrigieron y se documentó la diferencia entre fallo de producto y fallo de runner.

## Contexto
El repo ya contiene RAGAS, golden sets, latencia y security tests. Esto debe evolucionar de suite de prototipo a **safety evaluation program** continuo.

## Tareas P0

### Ampliar seguridad
- direct prompt injection;
- indirect prompt injection;
- prompt extraction;
- SQL/tool injection;
- encoded/obfuscated attacks;
- data exfiltration;
- cross-patient leakage;
- cross-tenant leakage;
- unauthorized bulk queries;
- RAG poisoning;
- malicious documents;
- tool misuse;
- denial/resource exhaustion.

### Evaluación clínica
Casos específicos para:
- datos ausentes;
- datos contradictorios;
- temporal reasoning;
- active vs discontinued medication;
- historical vs current diagnosis;
- unidades (`mg`, `µg`, `mmol/L`, etc.);
- adult vs pediatric context;
- duplicate patients/encounters;
- abnormal reference ranges;
- stale/outdated guidelines;
- dosage hallucination;
- unsupported causal claims;
- appropriate abstention.

### Métricas
No limitarse a RAGAS. Medir:
- factual/claim support;
- citation correctness;
- citation completeness;
- unsupported claim rate;
- retrieval recall;
- abstention correctness;
- authorization violations (target: 0);
- patient leakage (target: 0);
- tool policy violations (target: 0);
- clinical critical error rate;
- latency P50/P95/P99.

### Golden sets
Crear conjuntos versionados por capability, especialidad y riesgo, revisados por clínicos cuando sea posible.

### Regression gates
Ningún cambio de modelo, prompt, embedding, reranker, tool o guideline debe promoverse si empeora métricas críticas por debajo de thresholds.

## Red team multidisciplinar
Incluir médicos, enfermería, farmacia, ciberseguridad, privacidad/DPO, informática clínica e ingeniería IA.

## Casos humanos
Evaluar utilidad, tiempo ahorrado, automation bias, comprensión de incertidumbre, capacidad para encontrar evidencia y alert fatigue.

## Definition of Done
CI ejecuta evaluaciones automáticas; releases tienen safety report; existe un proceso periódico de red team; las métricas críticas tienen thresholds bloqueantes y cero tolerancia para acceso no autorizado/cross-patient leakage.
