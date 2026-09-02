"""Repositorios y proveedor de identidad en memoria."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from chathce.domain.clinical import ProviderHealth
from chathce.domain.context import RequestContext
from chathce.domain.conversation import AnalysisRecord, ConversationSession, MessageMetadata, StoredMessage
from chathce.domain.errors import AuthenticationFailed, NotFound
from chathce.domain.identity import AuthSession, Principal
from chathce.domain.knowledge import DocumentRecord, KnowledgeHit, KnowledgeStats, UploadResult
from chathce.domain.visualization import VisualizationArtifact


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryIdentityProvider:
    """Usuarios y tokens en memoria. ``tokens`` mapea access_token -> Principal."""

    def __init__(self, users: Optional[Dict[str, Principal]] = None, tokens: Optional[Dict[str, Principal]] = None):
        self.users: Dict[str, Principal] = dict(users or {})  # email -> principal
        self.passwords: Dict[str, str] = {}
        self.tokens: Dict[str, Principal] = dict(tokens or {})
        self.refresh_tokens: Dict[str, Principal] = {}
        self.revoked: set[str] = set()

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
        hits = [h for h in self.hits if specialty is None or h.specialty == specialty]
        return hits[:top_k]

    async def add_document(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        document_id = uuid.uuid4().hex
        filename = metadata.get("original_filename") or file_path.replace("\\", "/").rsplit("/", 1)[-1]
        self.documents[document_id] = DocumentRecord(
            document_id=document_id, filename=filename, doc_type=metadata.get("document_type"),
            specialty=metadata.get("specialty"), chunks=1, uploaded_at=_now(), metadata=dict(metadata),
        )
        return UploadResult(success=True, document_id=document_id, filename=filename, chunks_processed=1,
                            message="Documento indexado (memoria)")

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]:
        return list(self.documents.values())

    async def delete_document(self, ctx: RequestContext, *, document_id: str) -> int:
        return 1 if self.documents.pop(document_id, None) else 0

    async def stats(self, ctx: RequestContext) -> KnowledgeStats:
        sources = sorted({d.filename for d in self.documents.values()})
        return KnowledgeStats(total_documents=len(self.documents), unique_sources=len(sources), sources=sources)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, latency_ms=0, detail="memory")


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
