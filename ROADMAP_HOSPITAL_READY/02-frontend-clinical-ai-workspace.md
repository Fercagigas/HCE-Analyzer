# 02 — Frontend: Clinical AI Workspace

## Decisión

Retirar Streamlit del producto clínico final. Mantenerlo opcionalmente para investigación/evaluación interna.

Stack propuesto:
- React;
- TypeScript;
- Vite;
- React Router;
- TanStack Query;
- Radix UI o primitives equivalentes;
- Tailwind con design tokens clínicos;
- SSE/streaming para respuestas IA.

## Principio

**No copiar una HCE.** Oracle/Epic siguen siendo el system of record. ChatHCE muestra únicamente interfaces donde la IA aporta valor.

## Tareas

### P0.1 — Crear aplicación React independiente
Crear `/frontend` y eliminar dependencias entre presentación y lógica Python.

### P0.2 — Tres modos con el mismo frontend
1. SMART embedded app;
2. side panel contextual;
3. standalone workspace.

### P0.3 — Patient Context Header
Siempre visible: paciente, edad, identificador/alias, encounter y alertas esenciales. Cambio de paciente extremadamente evidente.

### P0.4 — Navegación AI-first
Vistas principales:
- Ask;
- What Matters Now;
- Since Last Review;
- AI Timeline;
- Insights;
- Investigate;
- Workspace/Evidence.

No recrear menús completos de Labs/Orders/etc. salvo cuando sean necesarios como evidencia de una tarea IA.

### P0.5 — Chat contextual global
Input disponible desde cualquier vista. La pantalla/selección actual puede añadirse explícitamente al contexto.

### P1.1 — Respuestas estructuradas
Crear componentes:
- `AIAnswer`;
- `ObservedFact`;
- `AIInference`;
- `EvidenceCard`;
- `SourceCitation`;
- `LabTrend`;
- `ClinicalDiff`;
- `ClinicalTimeline`;
- `AIInsight`;
- `MissingEvidence`;
- `Confidence/EvidenceQuality`.

### P1.2 — Claim-level evidence UX
Cada afirmación relevante debe permitir abrir la fuente original: analítica, nota, medicación, protocolo, etc.

### P1.3 — Ask this data
Permitir seleccionar datos/tarjetas y ejecutar acciones: Explain, Find related history, Compare, Find guideline, Investigate, Add to workspace.

### P1.4 — Command palette y teclado
`Ctrl/Cmd + K`, navegación rápida y accesibilidad keyboard-first.

### P1.5 — Clinical Design System
Crear tokens semánticos (`critical`, `warning`, `information`, `evidence-high`, etc.). Nunca depender solo del color.

### P1.6 — Accesibilidad
WCAG, contraste, zoom, screen readers, focus states, targets adecuados y responsive desktop/tablet.

## Pantalla home recomendada

```text
ChatHCE | Patient context
----------------------------------------
Ask anything about this patient...

WHAT MATTERS NOW
[Insight] [Insight] [Insight]

SINCE YOUR LAST REVIEW
4 clinically relevant changes

CLINICAL STORY
AI-generated evidence-linked timeline

Ask | Timeline | Insights | Investigate | Workspace
```

## Definition of Done
Un médico puede abrir ChatHCE desde una HCE, comprender en segundos qué aporta la IA, hacer una pregunta y verificar cada evidencia sin sentir que ha entrado en otra HCE completa.
