# 11 — Evaluación clínica, seguridad y Red Team

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
