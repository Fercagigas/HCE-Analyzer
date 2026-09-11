"""Repositorios y proveedor de identidad en memoria."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, FrozenSet, List, Optional

from chathce.domain.clinical import ProviderHealth
from chathce.domain.context import RequestContext
from chathce.domain.conversation import AnalysisRecord, ConversationSession, MessageMetadata, StoredMessage
from chathce.domain.errors import AuthenticationFailed, NotFound
from chathce.domain.identity import AuthSession, Principal
from chathce.domain.knowledge import DocumentRecord, DocumentStatus, KnowledgeHit, KnowledgeStats, UploadResult
from chathce.domain.visualization import VisualizationArtifact


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryIdentityProvider:
    """Usuarios y tokens en memoria. ``tokens`` mapea access_token -> Principal."""

    def __init__(self, users: Optional[Dict[str, Principal]] = None, tokens: Optional[Dict[str, Principal]] = None,
                 *, allow_all_patient_access_for_tests: bool = False):
        self.users: Dict[str, Principal] = dict(users or {})  # email -> principal
        self.passwords: Dict[str, str] = {}
        self.tokens: Dict[str, Principal] = dict(tokens or {})
        self.refresh_tokens: Dict[str, Principal] = {}
        self.revoked: set[str] = set()
        self.patient_access: list[dict[str, Any]] = []
        self._allow_all_patient_access_for_tests = allow_all_patient_access_for_tests

    def add_user(self, email: str, password: str, principal: Principal) -> None:
        self.users[email] = principal
        self.passwords[email] = password

    def issue(self, principal: Principal, *, ttl: timedelta = timedelta(hours=1)) -> AuthSession:
        access = f"access_{uuid.uuid4().hex}"
        refresh = f"refresh_{uuid.uuid4().hex}"
        expires = _now() + ttl
        stamped = principal.model_copy(update={"expires_at": expires})
        self.tokens[access] = stamped
        self.refresh_tokens[refresh] = stamped
        return AuthSession(access_token=access, refresh_token=refresh, expires_at=expires, principal=stamped)

    async def verify_access_token(self, token: str) -> Principal:
        principal = self.tokens.get(token)
        if principal is None or token in self.revoked:
            raise AuthenticationFailed("Token invalido o revocado")
        if principal.expires_at and principal.expires_at < _now():
            raise AuthenticationFailed("Token expirado")
        return principal

    async def login(self, email: str, password: str) -> AuthSession:
        if email not in self.users or self.passwords.get(email) != password:
            raise AuthenticationFailed("Credenciales invalidas")
        return self.issue(self.users[email])

    async def refresh(self, refresh_token: str) -> AuthSession:
        principal = self.refresh_tokens.pop(refresh_token, None)
        if principal is None:
            raise AuthenticationFailed("Refresh token invalido")
        return self.issue(principal)

    async def logout(self, access_token: str) -> None:
        self.revoked.add(access_token)

    async def register(self, *, email: str, password: str, name: str, specialty: Optional[str] = None,
                       medical_license: Optional[str] = None) -> Principal:
        principal = Principal(user_id=f"user_{uuid.uuid4().hex[:8]}", display_name=name)
        self.add_user(email, password, principal)
        return principal

    async def reset_password(self, email: str) -> None:
        return None

    async def has_active_patient_access(self, *, user_id: str, tenant_id: str, subject_id: int | str,
                                        service_id: str, at: datetime) -> bool:
        if self._allow_all_patient_access_for_tests:
            return True
        return any(
            grant["user_id"] == user_id and grant["tenant_id"] == tenant_id
            and str(grant["subject_id"]) == str(subject_id) and grant["service_id"] == service_id
            and grant["valid_from"] <= at and (grant["valid_until"] is None or at < grant["valid_until"])
            for grant in self.patient_access
        )

    async def assign_roles(self, *, user_id: str, tenant_id: str, roles: FrozenSet[str]) -> None:
        for token, principal in list(self.tokens.items()):
            if principal.user_id == user_id and principal.tenant_id == tenant_id:
                self.tokens[token] = principal.model_copy(update={"roles": roles})
        for email, principal in list(self.users.items()):
            if principal.user_id == user_id and principal.tenant_id == tenant_id:
                self.users[email] = principal.model_copy(update={"roles": roles})

    async def grant_patient_access(self, *, user_id: str, tenant_id: str, subject_id: int | str, service_id: str,
                                   valid_from: datetime, valid_until: Optional[datetime], granted_by: str) -> None:
        self.patient_access = [g for g in self.patient_access if not (
            g["user_id"] == user_id and g["tenant_id"] == tenant_id and str(g["subject_id"]) == str(subject_id)
            and g["service_id"] == service_id
        )]
        self.patient_access.append({"user_id": user_id, "tenant_id": tenant_id, "subject_id": str(subject_id),
                                    "service_id": service_id, "valid_from": valid_from, "valid_until": valid_until,
                                    "granted_by": granted_by})


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.sessions: Dict[str, ConversationSession] = {}
        self.messages: Dict[str, List[StoredMessage]] = {}

    def _owned(self, ctx: RequestContext, session_id: str) -> ConversationSession:
        session = self.sessions.get(session_id)
        if session is None or session.user_id != ctx.user_id:
            raise NotFound("Sesion no encontrada para este usuario")
        return session

    async def create_session(self, ctx: RequestContext, *, title: str) -> ConversationSession:
        session = ConversationSession(
            session_id=uuid.uuid4().hex, user_id=ctx.user_id, title=title, created_at=_now(), updated_at=_now(),
        )
        self.sessions[session.session_id] = session
        self.messages[session.session_id] = []
        return session

    async def list_sessions(self, ctx: RequestContext, *, limit: int = 3) -> List[ConversationSession]:
        own = [s for s in self.sessions.values() if s.user_id == ctx.user_id]
        own.sort(key=lambda s: s.updated_at or _now(), reverse=True)
        return own[:limit]

    async def get_session(self, ctx: RequestContext, *, session_id: str) -> Optional[ConversationSession]:
        try:
            return self._owned(ctx, session_id)
        except NotFound:
            return None

    async def delete_session(self, ctx: RequestContext, *, session_id: str) -> bool:
        try:
            self._owned(ctx, session_id)
        except NotFound:
            return False
        self.sessions.pop(session_id, None)
        self.messages.pop(session_id, None)
        return True

    async def rename_session(self, ctx: RequestContext, *, session_id: str, title: str) -> bool:
        try:
            session = self._owned(ctx, session_id)
        except NotFound:
            return False
        self.sessions[session_id] = session.model_copy(update={"title": title, "updated_at": _now()})
        return True

    async def append_message(self, ctx: RequestContext, *, session_id: str, role: str, content: str,
                             metadata: Optional[MessageMetadata] = None) -> StoredMessage:
        session = self._owned(ctx, session_id)
        message = StoredMessage(
            message_id=uuid.uuid4().hex, session_id=session_id, role=role, content=content,  # type: ignore[arg-type]
            metadata=metadata or MessageMetadata(), created_at=_now(),
        )
        self.messages[session_id].append(message)
        self.sessions[session_id] = session.model_copy(update={"updated_at": _now()})
        return message

    async def list_messages(self, ctx: RequestContext, *, session_id: str) -> List[StoredMessage]:
        self._owned(ctx, session_id)
        return list(self.messages.get(session_id, []))


class InMemoryAnalysisRepository:
    def __init__(self) -> None:
        self.records: List[AnalysisRecord] = []

    async def save(self, ctx: RequestContext, record: AnalysisRecord) -> bool:
        self.records.append(record)
        return True

    async def stats(self, ctx: RequestContext) -> Dict[str, Any]:
        own = [r for r in self.records if r.user_id == ctx.user_id]
        by_type: Dict[str, int] = {}
        for r in own:
            by_type[r.analysis_type] = by_type.get(r.analysis_type, 0) + 1
        return {"total_analyses": len(own), "by_type": by_type}


class InMemoryUserPreferencesRepository:
    def __init__(self) -> None:
        self.store: Dict[str, Dict[str, Any]] = {}

    async def load(self, ctx: RequestContext) -> Dict[str, Any]:
        return dict(self.store.get(ctx.user_id, {}))

    async def save(self, ctx: RequestContext, preferences: Dict[str, Any]) -> bool:
        self.store[ctx.user_id] = dict(preferences)
        return True


class InMemoryKnowledgeRepository:
    """Devuelve hits guionizados; registra las consultas recibidas."""

    def __init__(self, hits: Optional[List[KnowledgeHit]] = None):
        self.hits: List[KnowledgeHit] = list(hits or [])
        self.documents: Dict[str, DocumentRecord] = {}
        self.queries: List[str] = []

    async def search(self, ctx: RequestContext, *, query: str, top_k: int = 5,
                     specialty: Optional[str] = None) -> List[KnowledgeHit]:
        self.queries.append(query)
        today = ctx.created_at.date()
        candidates = [
            h for h in self.hits
            # ``default`` mantiene los fixtures historicos del fake; los datos
            # gobernados de pruebas siempre declaran tenant explicito y nunca
            # atraviesan esta frontera. El adapter Supabase no admite comodin.
            if h.tenant_id in (ctx.tenant_id, "default")
            and h.status == DocumentStatus.approved
            and h.effective_from <= today
            and (h.effective_to is None or h.effective_to >= today)
            and (specialty is None or h.specialty == specialty)
        ]
        # Todas las partes de una misma version se conservan; entre versiones
        # se selecciona de forma determinista la vigente mas reciente.
        selected_versions: Dict[str, KnowledgeHit] = {}
        for hit in candidates:
            key = hit.document_key or hit.filename
            previous = selected_versions.get(key)
            if previous is None or _knowledge_version_key(hit) > _knowledge_version_key(previous):
                selected_versions[key] = hit
        hits = [h for h in candidates if selected_versions[h.document_key or h.filename].version == h.version]
        return hits[:top_k]

    async def find_by_content_hash(self, ctx: RequestContext, *, content_hash: str) -> bool:
        return any(doc.tenant_id == ctx.tenant_id and doc.content_hash == content_hash for doc in self.documents.values())

    async def create_draft(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        document_id = uuid.uuid4().hex
        filename = metadata.get("original_filename") or file_path.replace("\\", "/").rsplit("/", 1)[-1]
        self.documents[document_id] = DocumentRecord(
            document_id=document_id, filename=filename, doc_type=metadata.get("doc_type") or metadata.get("document_type"),
            specialty=metadata.get("specialty"), chunks=0, uploaded_at=_now(),
            tenant_id=ctx.tenant_id, document_key=metadata.get("document_key") or metadata.get("title") or filename,
            version=metadata.get("version", ""), effective_from=datetime.fromisoformat(metadata["effective_from"]).date(),
            effective_to=(datetime.fromisoformat(metadata["effective_to"]).date() if metadata.get("effective_to") else None),
            status=DocumentStatus.draft, content_hash=metadata.get("content_hash", ""), metadata=dict(metadata),
        )
        return UploadResult(success=True, document_id=document_id, filename=filename, chunks_processed=0,
                            status=DocumentStatus.draft, message="Documento cargado como borrador (memoria)")

    async def approve_document(self, ctx: RequestContext, *, document_id: str, approved_by: str) -> UploadResult:
        document = self.documents.get(document_id)
        if document is None or document.tenant_id != ctx.tenant_id:
            return UploadResult(success=False, filename="documento", error="documento_no_encontrado")
        if document.metadata.get("security_flags"):
            return UploadResult(success=False, document_id=document_id, filename=document.filename,
                                error="revision_de_seguridad_pendiente", message="El documento marcado no puede aprobarse")
        now = _now()
        approved = document.model_copy(update={"status": DocumentStatus.approved, "approved_by": approved_by, "approved_at": now, "chunks": 1})
        self.documents[document_id] = approved
        self.hits.append(KnowledgeHit(
            chunk_id=f"{document_id}:1", document_id=document_id, filename=document.filename, content="Contenido aprobado (memoria)",
            specialty=document.specialty, doc_type=document.doc_type, tenant_id=document.tenant_id,
            document_key=document.document_key, version=document.version, effective_from=document.effective_from,
            effective_to=document.effective_to, status=DocumentStatus.approved, approved_by=approved_by,
            approved_at=now, content_hash=document.content_hash,
        ))
        return UploadResult(success=True, document_id=document_id, filename=document.filename, chunks_processed=1,
                            status=DocumentStatus.approved, message="Documento aprobado (memoria)")

    async def retire_document(self, ctx: RequestContext, *, document_id: str) -> bool:
        document = self.documents.get(document_id)
        if document is None or document.tenant_id != ctx.tenant_id:
            return False
        self.documents[document_id] = document.model_copy(update={"status": DocumentStatus.retired})
        self.hits = [h.model_copy(update={"status": DocumentStatus.retired}) if h.document_id == document_id else h for h in self.hits]
        return True

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]:
        today = ctx.created_at.date()
        return [doc for doc in self.documents.values() if doc.tenant_id == ctx.tenant_id and doc.status == DocumentStatus.approved
                and doc.effective_from <= today and (doc.effective_to is None or doc.effective_to >= today)]

    async def delete_document(self, ctx: RequestContext, *, document_id: str) -> int:
        return 1 if self.documents.pop(document_id, None) else 0

    async def stats(self, ctx: RequestContext) -> KnowledgeStats:
        documents = await self.list_documents(ctx)
        sources = sorted({d.filename for d in documents})
        return KnowledgeStats(total_documents=len(documents), unique_sources=len(sources), sources=sources)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, latency_ms=0, detail="memory")


def _knowledge_version_key(hit: KnowledgeHit) -> tuple:
    """Ordena versiones simples (2.10 > 2.9) y conserva fallback estable."""
    tokens = tuple((1, int(part)) if part.isdigit() else (0, part.lower()) for part in hit.version.replace("-", ".").split("."))
    return hit.effective_from, tokens


class InMemoryVisualizationRepository:
    def __init__(self, *, ttl_minutes: int = 30, max_items: int = 200):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_items = max_items
        self._items: Dict[str, VisualizationArtifact] = {}

    def _purge(self) -> None:
        now = _now()
        for key in [k for k, v in self._items.items() if v.expires_at < now]:
            self._items.pop(key, None)
        while len(self._items) > self.max_items:
            oldest = min(self._items.values(), key=lambda a: a.created_at)
            self._items.pop(oldest.viz_id, None)

    async def put(self, ctx: RequestContext, artifact: VisualizationArtifact) -> str:
        self._purge()
        self._items[artifact.viz_id] = artifact
        return artifact.viz_id

    async def get(self, ctx: RequestContext, viz_id: str) -> Optional[VisualizationArtifact]:
        self._purge()
        artifact = self._items.get(viz_id)
        if artifact is None or artifact.user_id != ctx.user_id or artifact.tenant_id != ctx.tenant_id:
            return None
        return artifact

    async def list_for_session(self, ctx: RequestContext, session_id: str) -> List[VisualizationArtifact]:
        self._purge()
        return [a for a in self._items.values() if a.session_id == session_id and a.user_id == ctx.user_id]

    def new_artifact(self, ctx: RequestContext, *, title: str, viz_type: str, figure_json: str,
                     metadata: Optional[Dict[str, str]] = None) -> VisualizationArtifact:
        now = _now()
        return VisualizationArtifact(
            viz_id=f"viz_{uuid.uuid4().hex[:12]}", tenant_id=ctx.tenant_id, user_id=ctx.user_id,
            session_id=ctx.session_id, title=title, viz_type=viz_type, figure_json=figure_json,
            created_at=now, expires_at=now + self.ttl, metadata=dict(metadata or {}),
        )
