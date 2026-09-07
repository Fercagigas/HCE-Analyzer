"""Cliente PostgREST/Supabase en memoria.

Reproduce la cadena que usa el proyecto:
``client.schema(s).table(t).select(cols).eq(k, v).in_(k, vs).ilike(k, p).gte/lte(k, v)
.order(k, desc=..).limit(n).range(a, b).execute()``, ``insert``/``update``/``delete`` con
filtros, ``select(count="exact", head=True)`` y ``client.rpc(name, params).execute()``.

Sirve para tests (fixtures grabadas) y para el perfil ``clinical.provider=memory``.
``register_clinical_aggregate_rpcs`` emula las funciones SQL de ``db/migrations/0001``.
"""

from __future__ import annotations

import operator
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

TableKey = Tuple[str, str]


@dataclass
class RecordedCall:
    schema: str
    table: str
    operation: str
    filters: List[Tuple[str, str, Any]]
    limit: Optional[int] = None
    columns: Optional[str] = None


class InMemoryAPIError(Exception):
    """Error simulado del backend (p. ej. RPC inexistente)."""


@dataclass
class InMemoryPostgrestClient:
    tables: Dict[TableKey, List[dict]] = field(default_factory=dict)
    rpc_handlers: Dict[str, Callable[[dict], Any]] = field(default_factory=dict)
    calls: List[RecordedCall] = field(default_factory=list)
    default_schema: str = "public"

    # ---- construccion --------------------------------------------------
    @classmethod
    def from_tables(cls, tables: Dict[str, Dict[str, List[dict]]]) -> "InMemoryPostgrestClient":
        """``{"mimiciv_hosp": {"patients": [...]}, ...}`` -> cliente."""
        flat: Dict[TableKey, List[dict]] = {}
        for schema, by_table in tables.items():
            for table, rows in by_table.items():
                flat[(schema, table)] = [dict(r) for r in rows]
        return cls(tables=flat)

    def rows(self, table: str, schema: Optional[str] = None) -> List[dict]:
        return self.tables.setdefault((schema or self.default_schema, table), [])

    # ---- API supabase-py ----------------------------------------------
    def schema(self, name: str) -> "_SchemaView":
        return _SchemaView(self, name)

    def table(self, name: str) -> "_QueryBuilder":
        return _QueryBuilder(self, self.default_schema, name)

    def from_(self, name: str) -> "_QueryBuilder":
        return self.table(name)

    def rpc(self, name: str, params: Optional[dict] = None) -> "_RpcBuilder":
        return _RpcBuilder(self, name, params or {})

    # ---- utilidades de test --------------------------------------------
    def count_calls(self, table: Optional[str] = None, operation: Optional[str] = None) -> int:
        return sum(
            1 for c in self.calls
            if (table is None or c.table == table) and (operation is None or c.operation == operation)
        )


@dataclass
class _SchemaView:
    client: InMemoryPostgrestClient
    name: str

    def table(self, name: str) -> "_QueryBuilder":
        return _QueryBuilder(self.client, self.name, name)

    def from_(self, name: str) -> "_QueryBuilder":
        return self.table(name)

    def rpc(self, name: str, params: Optional[dict] = None) -> "_RpcBuilder":
        return _RpcBuilder(self.client, name, params or {})


def _ilike(value: Any, pattern: str) -> bool:
    if value is None:
        return False
    regex = "^" + re.escape(pattern).replace("%", ".*").replace("_", ".") + "$"
    return re.match(regex, str(value), flags=re.IGNORECASE) is not None


def _cmp(op):
    def inner(a, b):
        if a is None or b is None:
            return False
        try:
            return op(a, b)
        except TypeError:
            return op(str(a), str(b))
    return inner


_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": operator.eq,
    "neq": operator.ne,
    "gt": _cmp(operator.gt),
    "gte": _cmp(operator.ge),
    "lt": _cmp(operator.lt),
    "lte": _cmp(operator.le),
    "in": lambda a, b: a in b,
    "is": lambda a, b: (a is None) if b in (None, "null") else (a == b),
    "ilike": _ilike,
    "like": lambda a, b: _ilike(a, b),
}


class _QueryBuilder:
    def __init__(self, client: InMemoryPostgrestClient, schema: str, table: str):
        self._client = client
        self._schema = schema
        self._table = table
        self._filters: List[Tuple[str, str, Any]] = []
        self._order: List[Tuple[str, bool]] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._columns: Optional[str] = None
        self._count: Optional[str] = None
        self._head: bool = False
        self._single: bool = False
        self._operation: str = "select"
        self._payload: Any = None

    # -- proyeccion / mutaciones
    def select(self, columns: str = "*", count: Optional[str] = None, head: bool = False) -> "_QueryBuilder":
        self._operation = "select"
        self._columns = columns
        self._count = count
        self._head = head
        return self

    def insert(self, rows: Any, **_: Any) -> "_QueryBuilder":
        self._operation = "insert"
        self._payload = rows
        return self

    def upsert(self, rows: Any, **_: Any) -> "_QueryBuilder":
        self._operation = "upsert"
        self._payload = rows
        return self

    def update(self, values: dict, **_: Any) -> "_QueryBuilder":
        self._operation = "update"
        self._payload = values
        return self

    def delete(self, **_: Any) -> "_QueryBuilder":
        self._operation = "delete"
        return self

    # -- filtros
    def _add(self, op: str, column: str, value: Any) -> "_QueryBuilder":
        self._filters.append((op, column, value))
        return self

    def eq(self, column: str, value: Any):
        return self._add("eq", column, value)

    def neq(self, column: str, value: Any):
        return self._add("neq", column, value)

    def gt(self, column: str, value: Any):
        return self._add("gt", column, value)

    def gte(self, column: str, value: Any):
        return self._add("gte", column, value)

    def lt(self, column: str, value: Any):
        return self._add("lt", column, value)

    def lte(self, column: str, value: Any):
        return self._add("lte", column, value)

    def in_(self, column: str, values: Iterable[Any]):
        return self._add("in", column, list(values))

    def is_(self, column: str, value: Any):
        return self._add("is", column, value)

    def ilike(self, column: str, pattern: str):
        return self._add("ilike", column, pattern)

    def like(self, column: str, pattern: str):
        return self._add("like", column, pattern)

    def order(self, column: str, desc: bool = False, **_: Any) -> "_QueryBuilder":
        self._order.append((column, desc))
        return self

    def limit(self, n: int, **_: Any) -> "_QueryBuilder":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "_QueryBuilder":
        self._offset = start
        self._limit = end - start + 1
        return self

    def single(self) -> "_QueryBuilder":
        self._single = True
        return self

    def maybe_single(self) -> "_QueryBuilder":
        self._single = True
        return self

    # -- ejecucion
    def _matches(self, row: dict) -> bool:
        return all(_OPS[op](row.get(col), val) for op, col, val in self._filters)

    def _project(self, row: dict) -> dict:
        if not self._columns or self._columns.strip() == "*":
            return dict(row)
        cols = [c.strip() for c in self._columns.split(",") if c.strip()]
        return {c: row.get(c) for c in cols}

    def execute(self) -> SimpleNamespace:
        rows = self._client.rows(self._table, self._schema)
        self._client.calls.append(RecordedCall(
            schema=self._schema, table=self._table, operation=self._operation,
            filters=list(self._filters), limit=self._limit, columns=self._columns,
        ))
        if self._operation == "select":
            matched = [r for r in rows if self._matches(r)]
            for column, desc in reversed(self._order):
                matched.sort(key=lambda r: (r.get(column) is None, str(r.get(column))), reverse=desc)
            total = len(matched)
            if self._offset:
                matched = matched[self._offset:]
            if self._limit is not None:
                matched = matched[: self._limit]
            data = [] if self._head else [self._project(r) for r in matched]
            if self._single:
                data = data[0] if data else None
            return SimpleNamespace(data=data, count=total if self._count else None)
        if self._operation in ("insert", "upsert"):
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for item in payload:
                record = dict(item)
                record.setdefault("id", str(uuid.uuid4()))
                rows.append(record)
                inserted.append(dict(record))
            return SimpleNamespace(data=inserted, count=None)
        if self._operation == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self._payload)
                    updated.append(dict(r))
            return SimpleNamespace(data=updated, count=None)
        if self._operation == "delete":
            kept, deleted = [], []
            for r in rows:
                (deleted if self._matches(r) else kept).append(r)
            rows[:] = kept
            return SimpleNamespace(data=[dict(r) for r in deleted], count=None)
        raise InMemoryAPIError(f"operacion no soportada: {self._operation}")


class _RpcBuilder:
    def __init__(self, client: InMemoryPostgrestClient, name: str, params: dict):
        self._client = client
        self._name = name
        self._params = params

    def execute(self) -> SimpleNamespace:
        self._client.calls.append(RecordedCall(schema="rpc", table=self._name, operation="rpc", filters=[]))
        handler = self._client.rpc_handlers.get(self._name)
        if handler is None:
            raise InMemoryAPIError(
                f"Could not find the function public.{self._name} in the schema cache"
            )
        return SimpleNamespace(data=handler(self._params), count=None)


# ---------------------------------------------------------------------------
# Emulacion de las RPC de agregados (db/migrations/0001_clinical_aggregates_v1.sql)
# ---------------------------------------------------------------------------

def _clamp(value: Any, low: int = 1, high: int = 200) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 20
    return max(low, min(n, high))


def register_clinical_aggregate_rpcs(client: InMemoryPostgrestClient) -> InMemoryPostgrestClient:
    hosp, icu = "mimiciv_hosp", "mimiciv_icu"

    def dataset_summary(_: dict):
        return [{
            "patients": len(client.rows("patients", hosp)),
            "admissions": len(client.rows("admissions", hosp)),
            "icu_stays": len(client.rows("icustays", icu)),
            "diagnoses": len(client.rows("diagnoses_icd", hosp)),
            "lab_events": len(client.rows("labevents", hosp)),
            "prescriptions": len(client.rows("prescriptions", hosp)),
        }]

    def top_diagnoses(params: dict):
        limit = _clamp(params.get("p_limit"))
        version = params.get("p_icd_version")
        rows = client.rows("diagnoses_icd", hosp)
        if version is not None:
            rows = [r for r in rows if r.get("icd_version") == version]
        counter = Counter((r["icd_code"], r["icd_version"]) for r in rows)
        titles = {(d["icd_code"], d["icd_version"]): d.get("long_title") for d in client.rows("d_icd_diagnoses", hosp)}
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0][0]))[:limit]
        return [{"icd_code": c, "icd_version": v, "long_title": titles.get((c, v)), "n": n} for (c, v), n in ranked]

    def top_drugs(params: dict):
        limit = _clamp(params.get("p_limit"))
        counter = Counter(r["drug"] for r in client.rows("prescriptions", hosp) if r.get("drug"))
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return [{"drug": d, "n": n} for d, n in ranked]

    def admission_type_distribution(_: dict):
        counter = Counter(r.get("admission_type") for r in client.rows("admissions", hosp))
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
        return [{"admission_type": t, "n": n} for t, n in ranked]

    client.rpc_handlers.update({
        "clinical_dataset_summary_v1": dataset_summary,
        "clinical_top_diagnoses_v1": top_diagnoses,
        "clinical_top_drugs_v1": top_drugs,
        "clinical_admission_type_distribution_v1": admission_type_distribution,
    })
    return client
