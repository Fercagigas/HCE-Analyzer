# 14 — Deployment y DevSecOps hospitalario

## Objetivo
Que ChatHCE pueda desplegarse de forma reproducible, aislada, actualizable y auditable.

## Tareas

### P1.1 — Containers
Dockerfiles mínimos, non-root, multi-stage, imágenes fijadas/versionadas.

### P1.2 — Environments
Separar dev/test/staging/pilot/prod. Nunca utilizar PHI real en desarrollo salvo entorno y autorización expresos.

### P1.3 — CI/CD security gates
- unit/integration/e2e;
- clinical/eval regression;
- SAST;
- dependency/SCA;
- secret scanning;
- container scan;
- IaC scan;
- SBOM;
- signed/reproducible artifacts cuando sea viable.

### P1.4 — Secrets
Secret manager; rotación; no `.env` de producción ni claves en logs/repo.

### P1.5 — Network architecture
API gateway/WAF, private networking para DB/vector stores, egress allowlisting para proveedores externos y administración restringida.

### P1.6 — Deployment models
Soportar según cliente:
- hospital/on-prem;
- private cloud/VPC;
- EU-region managed deployment;
- híbrido.

### P1.7 — Infrastructure as Code
Terraform/OpenTofu u opción equivalente para reproducibilidad.

### P1.8 — Kubernetes solo si aporta valor
No introducirlo prematuramente; considerar para HA/multi-service/multi-hospital. Un piloto puede comenzar con arquitectura más simple pero production-grade.

### P1.9 — Release/rollback
Blue-green/canary cuando proceda, feature flags para capacidades IA y rollback de modelo/prompt/RAG.

### P1.10 — Dependency governance
Pinning, Renovate/Dependabot, política de CVEs y revisión de proveedores críticos.

## Definition of Done
Un entorno nuevo puede desplegarse de forma reproducible sin configuración manual insegura; una release insegura no supera CI; existen rollback y trazabilidad de la versión completa en producción.
