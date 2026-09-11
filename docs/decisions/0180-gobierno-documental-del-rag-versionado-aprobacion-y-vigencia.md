# ADR 0180 - Gobierno documental del RAG: versionado, aprobacion y vigencia

Estado: Aceptada

Fecha: 2026-09-11

## Contexto

El corpus RAG compartia `rag_chunks` sin tenant, version, vigencia ni estado de
aprobacion. La ruta legacy indexaba un archivo directamente, por lo que un
contenido obsoleto, de otro hospital o con instrucciones adversariales podia
participar en una respuesta clinica. Es el control pendiente para AI-09 y
AI-10 del threat model y para 08 P0.1-P0.5.

## Opciones consideradas (incluidas las descartadas y por que)

1. Mantener metadata opcional y filtrar solo en el prompt. Descartada: el
   modelo no es un punto de control y los chunks sin metadata seguirian siendo
   recuperables.
2. Crear un indice/vector store por tenant. Descartada por ahora: aumenta la
   operacion y no resuelve aprobacion, hash, vigencia ni versiones. RLS y filtro
   determinista dejan abierta esa evolucion.
3. Aprobar automaticamente si el archivo pasa extension y tamano. Descartada:
   no detecta poisoning ni sustituye el juicio del responsable clinico.
4. Sustituir de una vez el RAG legacy por un servicio nuevo. Descartada en esta
   oleada: su superficie excede el gate de seguridad. Se encapsula y se bloquea
   su upload directo para que solo indexe tras aprobar.

## Decision

Se añade a documentos y chunks: `tenant_id`, `document_key`, `version`,
`effective_from`/`effective_to`, `status` (`draft`, `approved`, `retired`),
aprobador, fecha de aprobacion y SHA-256 del contenido. La migracion 0007 deja
el corpus heredado en `draft`, aplica RLS por tenant y redefine las RPC de
busqueda para admitir tenant y fecha, recuperar solo `approved` vigentes y
resolver una version actual por `document_key`.

La aplicacion carga primero como borrador, valida extension/tamano/metadata,
evita hashes duplicados y marca patrones basicos de inyeccion. No existe
auto-aprobacion; aprobar o retirar exige el puerto `KnowledgeApprovalAuthorizer`.
Su implementacion temporal comprueba `knowledge_manager` en el contexto y debe
conectarse al provider RBAC/ABAC de Fase 2 en una integracion posterior.

El adaptador vuelve a filtrar tenant, estado y vigencia aun cuando la base ya
lo hace. `Source` y `Evidence` exponen version, estado y vigencia.

## Consecuencias

- Un documento nuevo no es consultable hasta que una persona autorizada lo
  aprueba; los marcados por inyeccion requieren revision previa.
- La aplicacion de 0007 es un paso operativo obligatorio. Los documentos
  existentes dejan de aparecer hasta ser revisados y aprobados con hash real.
- La UI legacy no puede indexar directamente: su metodo queda deprecado y
  bloqueado sin la marca interna de aprobacion.
- La comprobacion de rol es minima y temporal; no sustituye la autorizacion
  centralizada que aporta el paquete RBAC/ABAC.
