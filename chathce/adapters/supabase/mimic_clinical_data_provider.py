"""MimicClinicalDataProvider: implementacion del port sobre PostgREST (Supabase) o su emulacion en memoria.

Reglas:
- Solo operaciones allowlisted; nunca SQL libre ni nombres de tabla desde fuera.
- Defensa en profundidad: toda consulta clinica anade ``.eq("subject_id", ...)`` con el
  paciente del contexto cuando existe, ademas del enforcement del ScopeGuard.
- Agregados dataset-wide unicamente mediante RPC fijas versionadas (db/migrations/0001).
- Llamadas sincronas del SDK ejecutadas en hilo con timeout.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple, TypeVar

from chathce.adapters.supabase.dictionaries import HOSP, ICU, Dictionaries
from chathce.adapters.supabase.mapping import RowMapper
from chathce.domain.clinical import (
    Admission,
    AdmissionDetails,
    Condition,
    DatasetSummary,
    FrequencyBucket,
    FrequencyResult,
    IcdCodeEntry,
    IcuItem,
    IcuObservation,
    IcuStay,
    LabItem,
    LabObservation,
    Medication,
    Page,
    Patient,
    PatientSummary,
    PatientSummaryStats,
    ProviderHealth,
    TimeRange,
)
from chathce.domain.context import RequestContext
from chathce.domain.errors import NotFound, ProviderUnavailable, ToolTimeout

T = TypeVar("T")

RPC_DATASET_SUMMARY = "clinical_dataset_summary_v1"
RPC_TOP_DIAGNOSES = "clinical_top_diagnoses_v1"
RPC_TOP_DRUGS = "clinical_top_drugs_v1"
RPC_ADMISSION_TYPES = "clinical_admission_type_distribution_v1"


class MimicClinicalDataProvider:
    source_name: str

    def __init__(
        self,
        client: Any,
        *,
        source_name: str = "mimic-iv-demo-2.2",
        default_limit: int = 100,
        max_limit: int = 200,
        aggregate_limit: int = 50,
        timeout_s: float = 30.0,
        dictionaries: Optional[Dictionaries] = None,
    ):
        self._client = client
        self.source_name = source_name
        self._default_limit = default_limit
        self._max_limit = max_limit
        self._aggregate_limit = aggregate_limit
        self._timeout = timeout_s
        self._dict = dictionaries or Dictionaries(client)
        self._map = RowMapper(source_name)

    # ------------------------------------------------------------------
    # infraestructura
    # ------------------------------------------------------------------
    def _limit(self, requested: Optional[int], ceiling: Optional[int] = None) -> int:
        ceiling = ceiling or self._max_limit
        if requested is None:
            return min(self._default_limit, ceiling)
        return max(1, min(int(requested), ceiling))

    async def _run(self, fn: Callable[[], T], *, what: str) -> T:
        try:
            return await asyncio.wait_for(asyncio.to_thread(fn), timeout=self._timeout)
        except asyncio.TimeoutError as exc:
            raise ToolTimeout(f"Tiempo de espera agotado ({self._timeout:.0f}s) en {what}") from exc
        except (ToolTimeout, ProviderUnavailable, NotFound):
            raise
        except Exception as exc:  # noqa: BLE001 - traducimos cualquier error del SDK
            raise ProviderUnavailable(self._sanitize(exc, what)) from exc

    @staticmethod
    def _sanitize(exc: Exception, what: str) -> str:
        text = str(exc)
        if "Could not find the function" in text:
            return (
                f"La funcion de agregados no esta instalada en la base de datos ({what}); "
                "aplique db/migrations/0001_clinical_aggregates_v1.sql."
            )
        # sin URLs ni claves en el mensaje que llega al usuario/modelo
        cleaned = text.split("http", 1)[0].strip() or exc.__class__.__name__
        return f"El origen de datos clinicos no esta disponible ({what}): {cleaned[:200]}"

    def _table(self, schema: str, table: str):
        return self._client.schema(schema).table(table)

    def _scoped(self, query, ctx: RequestContext):
        """Defensa en profundidad: filtra por el paciente del contexto si existe."""
        if ctx.patient_id is not None:
            query = query.eq("subject_id", int(ctx.patient_id))
        return query

    async def _select(self, ctx: RequestContext, schema: str, table: str, columns: str = "*", *,
                      scoped: bool = True, build: Optional[Callable[[Any], Any]] = None,
                      order: Optional[Tuple[str, bool]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        def run():
            q = self._table(schema, table).select(columns)
            if scoped:
                q = self._scoped(q, ctx)
            if build:
                q = build(q)
            if order:
                q = q.order(order[0], desc=order[1])
            if limit is not None:
                q = q.limit(limit)
            return q.execute().data or []

        return await self._run(run, what=f"lectura de {table}")

    async def _count(self, ctx: RequestContext, schema: str, table: str, build: Callable[[Any], Any]) -> int:
        def run():
            q = self._scoped(self._table(schema, table).select("*", count="exact", head=True), ctx)
            return build(q).execute().count or 0

        return await self._run(run, what=f"recuento de {table}")

    @staticmethod
    def _page(items: List[T], limit: int) -> Page[T]:
        return Page.from_items(items, limit)

    @staticmethod
    def _apply_time_range(query, column: str, time_range: Optional[TimeRange]):
        if time_range and time_range.start:
            query = query.gte(column, time_range.start.isoformat())
        if time_range and time_range.end:
            query = query.lte(column, time_range.end.isoformat())
        return query

    # ------------------------------------------------------------------
    # resolucion de propietario
    # ------------------------------------------------------------------
    async def resolve_admission_owner(self, hadm_id: int) -> Tuple[int, int]:
        rows = await self._run(
            lambda: self._table(HOSP, "admissions").select("subject_id,hadm_id").eq("hadm_id", int(hadm_id)).limit(1).execute().data or [],
            what="resolucion de admision",
        )
        if not rows:
            raise NotFound(f"No existe la admision {hadm_id}")
        return int(rows[0]["subject_id"]), int(rows[0]["hadm_id"])

    async def resolve_icu_stay_owner(self, stay_id: int) -> Tuple[int, int]:
        rows = await self._run(
            lambda: self._table(ICU, "icustays").select("subject_id,hadm_id,stay_id").eq("stay_id", int(stay_id)).limit(1).execute().data or [],
            what="resolucion de estancia UCI",
        )
        if not rows:
            raise NotFound(f"No existe la estancia UCI {stay_id}")
        return int(rows[0]["subject_id"]), int(rows[0]["hadm_id"])

    # ------------------------------------------------------------------
    # paciente / episodio
    # ------------------------------------------------------------------
    async def get_patient(self, ctx: RequestContext, subject_id: int) -> Patient:
        rows = await self._select(ctx, HOSP, "patients", build=lambda q: q.eq("subject_id", int(subject_id)), limit=1)
        if not rows:
            raise NotFound(f"No existe el paciente {subject_id}")
        adm = await self._select(ctx, HOSP, "admissions", "race,admittime",
                                 build=lambda q: q.eq("subject_id", int(subject_id)), order=("admittime", True), limit=1)
        race = adm[0].get("race") if adm else None
        return self._map.patient(rows[0], race=race)

    async def list_admissions(self, ctx: RequestContext, subject_id: int, *, limit: int = 50) -> Page[Admission]:
        lim = self._limit(limit)
        rows = await self._select(ctx, HOSP, "admissions", build=lambda q: q.eq("subject_id", int(subject_id)),
                                  order=("admittime", True), limit=lim + 1)
        return self._page([self._map.admission(r) for r in rows], lim)

    async def get_admission_details(self, ctx: RequestContext, hadm_id: int) -> AdmissionDetails:
        hadm = int(hadm_id)
        adm_rows = await self._select(ctx, HOSP, "admissions", build=lambda q: q.eq("hadm_id", hadm), limit=1)
        if not adm_rows:
            raise NotFound(f"No existe la admision {hadm_id}")
        admission = self._map.admission(adm_rows[0])

        diag_rows = await self._select(ctx, HOSP, "diagnoses_icd", build=lambda q: q.eq("hadm_id", hadm),
                                       order=("seq_num", False), limit=self._max_limit)
        proc_rows = await self._select(ctx, HOSP, "procedures_icd", build=lambda q: q.eq("hadm_id", hadm),
                                       order=("seq_num", False), limit=self._max_limit)
        transfer_rows = await self._select(ctx, HOSP, "transfers", build=lambda q: q.eq("hadm_id", hadm),
                                           order=("intime", False), limit=self._max_limit)
        service_rows = await self._select(ctx, HOSP, "services", build=lambda q: q.eq("hadm_id", hadm),
                                          order=("transfertime", False), limit=self._max_limit)
        icu_rows = await self._select(ctx, ICU, "icustays", build=lambda q: q.eq("hadm_id", hadm),
                                      order=("intime", False), limit=self._max_limit)
        conditions = await self._conditions(diag_rows)
        procedures = await self._procedures(proc_rows)
        return AdmissionDetails(
            admission=admission,
            conditions=conditions,
            procedures=procedures,
            transfers=[self._map.transfer(r) for r in transfer_rows],
            services=[self._map.service(r) for r in service_rows],
            icu_stays=[self._map.icu_stay(r) for r in icu_rows],
        )

    async def get_patient_summary(self, ctx: RequestContext, subject_id: int) -> PatientSummary:
        sid = int(subject_id)
        patient = await self.get_patient(ctx, sid)
        admissions = await self.list_admissions(ctx, sid, limit=20)
        conditions = await self.list_conditions(ctx, subject_id=sid, limit=30)
        labs = await self.list_lab_observations(ctx, subject_id=sid, limit=20)
        meds = await self.list_medications(ctx, subject_id=sid, limit=30)
        icu = await self.list_icu_stays(ctx, subject_id=sid, limit=10)

        total_adm = await self._count(ctx, HOSP, "admissions", lambda q: q.eq("subject_id", sid))
        total_icu = await self._count(ctx, ICU, "icustays", lambda q: q.eq("subject_id", sid))
        diag_codes = await self._select(ctx, HOSP, "diagnoses_icd", "icd_code,icd_version",
                                        build=lambda q: q.eq("subject_id", sid), limit=1000)
        drug_rows = await self._select(ctx, HOSP, "prescriptions", "drug",
                                       build=lambda q: q.eq("subject_id", sid), limit=1000)
        admit_times = [a.admittime for a in admissions.items if a.admittime]
        stats = PatientSummaryStats(
            total_admissions=total_adm,
            total_icu_stays=total_icu,
            distinct_diagnoses=len({(r["icd_code"], r["icd_version"]) for r in diag_codes}),
            distinct_medications=len({r.get("drug") for r in drug_rows if r.get("drug")}),
            first_admission=min(admit_times) if admit_times else None,
            last_admission=max(admit_times) if admit_times else None,
        )
        # medicaciones distintas por farmaco para el resumen
        seen: set = set()
        distinct_meds: List[Medication] = []
        for m in meds.items:
            if m.drug not in seen:
                seen.add(m.drug)
                distinct_meds.append(m)
        return PatientSummary(
            patient=patient,
            admissions=admissions.items,
            conditions=conditions.items,
            recent_labs=labs.items,
            medications=distinct_meds,
            icu_stays=icu.items,
            stats=stats,
            truncated={
                "admissions": admissions.truncated,
                "conditions": conditions.truncated,
                "recent_labs": labs.truncated,
                "medications": meds.truncated,
                "icu_stays": icu.truncated,
            },
        )

    # ------------------------------------------------------------------
    # diagnosticos
    # ------------------------------------------------------------------
    async def _conditions(self, rows: List[Dict[str, Any]]) -> List[Condition]:
        if not rows:
            return []
        titles = await self._run(
            lambda: self._dict.icd_titles(((r["icd_code"], r["icd_version"]) for r in rows), kind="diagnosis"),
            what="diccionario ICD",
        )
        return [self._map.condition(r, titles.get((str(r["icd_code"]), int(r["icd_version"])))) for r in rows]

    async def _procedures(self, rows: List[Dict[str, Any]]):
        if not rows:
            return []
        titles = await self._run(
            lambda: self._dict.icd_titles(((r["icd_code"], r["icd_version"]) for r in rows), kind="procedure"),
            what="diccionario ICD de procedimientos",
        )
        return [self._map.procedure(r, titles.get((str(r["icd_code"]), int(r["icd_version"])))) for r in rows]

    async def list_conditions(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                              limit: int = 100) -> Page[Condition]:
        lim = self._limit(limit)

        def build(q):
            q = q.eq("subject_id", int(subject_id))
            if hadm_id is not None:
                q = q.eq("hadm_id", int(hadm_id))
            return q.order("hadm_id").order("seq_num")

        rows = await self._select(ctx, HOSP, "diagnoses_icd", build=build, limit=lim + 1)
        truncated = len(rows) > lim
        conditions = await self._conditions(rows[:lim])
        return Page(items=conditions, count=len(conditions), limit=lim, truncated=truncated)

    # ------------------------------------------------------------------
    # laboratorio
    # ------------------------------------------------------------------
    async def list_lab_observations(
        self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
        itemids: Optional[Sequence[int]] = None, label_contains: Optional[str] = None,
        time_range: Optional[TimeRange] = None, abnormal_only: bool = False, limit: int = 100,
    ) -> Page[LabObservation]:
        lim = self._limit(limit)
        ids: Optional[List[int]] = list(itemids) if itemids else None
        if label_contains:
            matched = await self._run(lambda: self._dict.lab_itemids_matching(label_contains), what="diccionario de laboratorio")
            ids = sorted(set(ids) & set(matched)) if ids else matched
            if not ids:
                return Page(items=[], count=0, limit=lim, truncated=False)

        def build(q):
            q = q.eq("subject_id", int(subject_id))
            if hadm_id is not None:
                q = q.eq("hadm_id", int(hadm_id))
            if ids:
                q = q.in_("itemid", ids)
            if abnormal_only:
                q = q.eq("flag", "abnormal")
            return self._apply_time_range(q, "charttime", time_range)

        rows = await self._select(ctx, HOSP, "labevents", build=build, order=("charttime", True), limit=lim + 1)
        items = await self._run(self._dict.lab_items, what="diccionario de laboratorio")
        labs = [self._map.lab(r, items.get(int(r["itemid"]))) for r in rows]
        return self._page(labs, lim)

    async def search_lab_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[LabItem]:
        lim = self._limit(limit)
        rows = await self._run(lambda: self._dict.lab_items_matching(label_contains, lim + 1), what="diccionario de laboratorio")
        return self._page([self._map.lab_item(r) for r in rows], lim)

    # ------------------------------------------------------------------
    # medicacion
    # ------------------------------------------------------------------
    async def list_medications(
        self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
        drug_contains: Optional[str] = None, include_emar: bool = False, limit: int = 100,
    ) -> Page[Medication]:
        lim = self._limit(limit)

        def build_rx(q):
            q = q.eq("subject_id", int(subject_id))
            if hadm_id is not None:
                q = q.eq("hadm_id", int(hadm_id))
            if drug_contains:
                q = q.ilike("drug", f"%{drug_contains}%")
            return q

        rows = await self._select(ctx, HOSP, "prescriptions", build=build_rx, order=("starttime", True), limit=lim + 1)
        meds: List[Medication] = [self._map.prescription(r) for r in rows]
        if include_emar:
            def build_emar(q):
                q = q.eq("subject_id", int(subject_id))
                if hadm_id is not None:
                    q = q.eq("hadm_id", int(hadm_id))
                if drug_contains:
                    q = q.ilike("medication", f"%{drug_contains}%")
                return q

            emar_rows = await self._select(ctx, HOSP, "emar", build=build_emar, order=("charttime", True), limit=lim + 1)
            meds.extend(self._map.emar(r) for r in emar_rows)
            meds.sort(key=lambda m: (m.starttime is None, m.starttime or datetime.min), reverse=True)
        return self._page(meds, lim)

    # ------------------------------------------------------------------
    # UCI
    # ------------------------------------------------------------------
    async def list_icu_stays(self, ctx: RequestContext, *, subject_id: int, hadm_id: Optional[int] = None,
                             limit: int = 20) -> Page[IcuStay]:
        lim = self._limit(limit)

        def build(q):
            q = q.eq("subject_id", int(subject_id))
            if hadm_id is not None:
                q = q.eq("hadm_id", int(hadm_id))
            return q

        rows = await self._select(ctx, ICU, "icustays", build=build, order=("intime", True), limit=lim + 1)
        return self._page([self._map.icu_stay(r) for r in rows], lim)

    async def list_icu_observations(
        self, ctx: RequestContext, *, stay_id: int, itemids: Optional[Sequence[int]] = None,
        label_contains: Optional[str] = None, time_range: Optional[TimeRange] = None, limit: int = 200,
    ) -> Page[IcuObservation]:
        lim = self._limit(limit)
        ids: Optional[List[int]] = list(itemids) if itemids else None
        if label_contains:
            matched = await self._run(lambda: self._dict.icu_itemids_matching(label_contains), what="diccionario UCI")
            ids = sorted(set(ids) & set(matched)) if ids else matched
            if not ids:
                return Page(items=[], count=0, limit=lim, truncated=False)

        def build(q):
            q = q.eq("stay_id", int(stay_id))
            if ids:
                q = q.in_("itemid", ids)
            return self._apply_time_range(q, "charttime", time_range)

        rows = await self._select(ctx, ICU, "chartevents", build=build, order=("charttime", True), limit=lim + 1)
        items = await self._run(self._dict.icu_items, what="diccionario UCI")
        obs = [self._map.icu_observation(r, items.get(int(r["itemid"]))) for r in rows]
        return self._page(obs, lim)

    async def search_icu_items(self, ctx: RequestContext, *, label_contains: str, limit: int = 50) -> Page[IcuItem]:
        lim = self._limit(limit)
        rows = await self._run(lambda: self._dict.icu_items_matching(label_contains, lim + 1), what="diccionario UCI")
        return self._page([self._map.icu_item(r) for r in rows], lim)

    # ------------------------------------------------------------------
    # diccionario ICD
    # ------------------------------------------------------------------
    async def search_icd_codes(
        self, ctx: RequestContext, *, code_prefix: Optional[str] = None, title_contains: Optional[str] = None,
        icd_version: Optional[int] = None, kind: Literal["diagnosis", "procedure"] = "diagnosis", limit: int = 50,
    ) -> Page[IcdCodeEntry]:
        if not code_prefix and not title_contains:
            return Page(items=[], count=0, limit=self._limit(limit), truncated=False)
        lim = self._limit(limit)
        table = "d_icd_diagnoses" if kind == "diagnosis" else "d_icd_procedures"

        def build(q):
            if code_prefix:
                q = q.ilike("icd_code", f"{code_prefix}%")
            if title_contains:
                q = q.ilike("long_title", f"%{title_contains}%")
            if icd_version is not None:
                q = q.eq("icd_version", int(icd_version))
            return q.order("icd_code")

        rows = await self._select(ctx, HOSP, table, "icd_code,icd_version,long_title", scoped=False, build=build, limit=lim + 1)
        return self._page([self._map.icd_entry(r, kind) for r in rows], lim)

    # ------------------------------------------------------------------
    # agregados (RPC fijas)
    # ------------------------------------------------------------------
    async def _rpc(self, name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self._run(lambda: self._client.rpc(name, params).execute().data or [], what=name)

    async def get_dataset_summary(self, ctx: RequestContext) -> DatasetSummary:
        rows = await self._rpc(RPC_DATASET_SUMMARY, {})
        row = rows[0] if rows else {}
        return DatasetSummary(
            patients=int(row.get("patients", 0)), admissions=int(row.get("admissions", 0)),
            icu_stays=int(row.get("icu_stays", 0)), diagnoses=int(row.get("diagnoses", 0)),
            lab_events=int(row.get("lab_events", 0)), prescriptions=int(row.get("prescriptions", 0)),
            source=self.source_name, computed_at=datetime.now(timezone.utc),
        )

    def _frequency(self, operation: str, rows: List[Dict[str, Any]], limit: int, key: str, label: Optional[str]) -> FrequencyResult:
        buckets = [
            FrequencyBucket(key=str(r.get(key)), label=(str(r.get(label)) if label and r.get(label) is not None else None), count=int(r.get("n", 0)))
            for r in rows[:limit]
        ]
        return FrequencyResult(
            operation=operation, buckets=buckets, total_rows=sum(b.count for b in buckets), limit=limit,
            truncated=len(rows) > limit, computed_at=datetime.now(timezone.utc), source=self.source_name,
        )

    async def top_diagnoses(self, ctx: RequestContext, *, limit: int = 20, icd_version: Optional[int] = None) -> FrequencyResult:
        lim = self._limit(limit, self._aggregate_limit)
        rows = await self._rpc(RPC_TOP_DIAGNOSES, {"p_limit": lim + 1, "p_icd_version": icd_version})
        return self._frequency("top_diagnoses", rows, lim, "icd_code", "long_title")

    async def top_drugs(self, ctx: RequestContext, *, limit: int = 20) -> FrequencyResult:
        lim = self._limit(limit, self._aggregate_limit)
        rows = await self._rpc(RPC_TOP_DRUGS, {"p_limit": lim + 1})
        return self._frequency("top_drugs", rows, lim, "drug", None)

    async def admission_type_distribution(self, ctx: RequestContext) -> FrequencyResult:
        rows = await self._rpc(RPC_ADMISSION_TYPES, {})
        return self._frequency("admission_type_distribution", rows, self._aggregate_limit, "admission_type", None)

    # ------------------------------------------------------------------
    async def health(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            await self._run(lambda: self._table(HOSP, "patients").select("subject_id").limit(1).execute(), what="health")
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, latency_ms=int((time.perf_counter() - start) * 1000), detail=str(exc)[:200])
        return ProviderHealth(ok=True, latency_ms=int((time.perf_counter() - start) * 1000), detail=self.source_name)
