"""Autorizacion minima para transiciones del ciclo documental.

La integracion con el proveedor RBAC/ABAC se conecta aqui, sin acoplar el
pipeline de conocimiento a su implementacion concreta.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from chathce.domain.context import RequestContext


@runtime_checkable
class KnowledgeApprovalAuthorizer(Protocol):
    def can_approve_documents(self, ctx: RequestContext) -> bool: ...
