"""Genera el golden set DB v2 (MIMIC-IV hosp/icu) de forma determinista y verificable.

La verdad de referencia se calcula con el mismo `MimicClinicalDataProvider` que usan las
tools del agente, de modo que cada `ground_truth` es exactamente lo que devolveria la
operacion allowlisted indicada en `ground_truth_operation`. No se escribe SQL.

Uso (PowerShell, con .env):

    conda activate HCE ; python scripts/build_golden_set_mimiciv.py --output Evaluation/golden_set_ragas.json --n-patients 8

Deterministico salvo `metadata.fecha_generacion`. Las preguntas cuya redaccion requiere
criterio clinico quedan marcadas `clinical_validation.required=true, status=pending`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chathce.adapters.supabase.dictionaries import HOSP, ICU  # noqa: E402
from chathce.adapters.supabase.mimic_clinical_data_provider import MimicClinicalDataProvider  # noqa: E402
from chathce.composition.async_runner import run_sync  # noqa: E402
from chathce.domain.clinical import FrequencyBucket, FrequencyResult  # noqa: E402
from chathce.domain.context import Channel, Purpose, RequestContext  # noqa: E402
from chathce.domain.errors import ProviderUnavailable  # noqa: E402
from Evaluation.golden_set import CATEGORY_ID_PREFIX, GOLDEN_SET_VERSION, validate_question  # noqa: E402

DATASET = "MIMIC-IV Clinical Database Demo 2.2 (mimiciv_hosp, mimiciv_icu)"
THRESHOLDS = {"faithfulness": 0.85, "answer_relevancy": 0.80, "context_precision": 0.75, "context_recall": 0.70}


def fmt_dt(value) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "fecha no registrada"


def fmt_num(value) -> str:
    if value is None:
        return "sin valor numérico"
    return f"{value:g}"


class Builder:
    def __init__(self, provider: MimicClinicalDataProvider, client: Any):
        self.provider = provider
        self.client = client
        self.questions: List[Dict[str, Any]] = []
        self.counters: Counter = Counter()
        self.subjects_used: set = set()

    # ------------------------------------------------------------------
    def ctx(self, subject_id: Optional[int] = None) -> RequestContext:
        if subject_id is None:
            return RequestContext(user_id="golden-set-builder", channel=Channel.cli, purpose=Purpose.research,
                                  roles=frozenset({"researcher"}))
        return RequestContext(user_id="golden-set-builder", channel=Channel.cli, patient_id=str(subject_id))

    def add(self, *, category: str, question: str, ground_truth: str, operation: str, arguments: Dict[str, Any],
            scope: Dict[str, Optional[int]], expected_tool: str, contexts: List[str],
            validation_required: bool, notes: str = "") -> None:
        self.counters[category] += 1
        qid = f"{CATEGORY_ID_PREFIX[category]}{self.counters[category]:03d}"
        if scope.get("subject_id"):
            self.subjects_used.add(int(scope["subject_id"]))
        entry = {
            "id": qid,
            "category": category,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_operation": {"operation": operation, "arguments": arguments},
            "scope": {"subject_id": scope.get("subject_id"), "hadm_id": scope.get("hadm_id"), "stay_id": scope.get("stay_id")},
            "expected_tool": expected_tool,
            "contexts": contexts,
            "clinical_validation": {
                "required": validation_required,
                "status": "pending" if validation_required else "n/a",
                "notes": notes,
            },
        }
        errors = validate_question(entry)
        assert not errors, f"{qid}: {errors}"
        self.questions.append(entry)

    # ------------------------------------------------------------------
    def select_subjects(self, n: int) -> List[int]:
        rows = self.client.schema(HOSP).table("patients").select("subject_id").order("subject_id").execute().data or []
        chosen: List[int] = []
        for row in rows:
            sid = int(row["subject_id"])
            adm = self.client.schema(HOSP).table("admissions").select("*", count="exact", head=True).eq("subject_id", sid).execute().count or 0
            icu = self.client.schema(ICU).table("icustays").select("*", count="exact", head=True).eq("subject_id", sid).execute().count or 0
            if adm >= 1 and icu >= 1:
                chosen.append(sid)
            if len(chosen) == n:
                break
        if len(chosen) < n:
            raise SystemExit(f"Solo {len(chosen)} pacientes con ingreso y estancia UCI")
        return chosen

    # ------------------------------------------------------------------
    def build_patient_summary(self, subjects: List[int]) -> None:
        for sid in subjects[:3]:
            patient = run_sync(self.provider.get_patient(self.ctx(sid), sid))
            sexo = {"F": "femenino", "M": "masculino"}.get(patient.gender or "", patient.gender or "no registrado")
            self.add(
                category="patient_summary",
                question=f"¿Cuál es el sexo y la edad de referencia del paciente {sid}?",
                ground_truth=(
                    f"El paciente {sid} es de sexo {sexo}, con una edad de referencia (anchor_age) de "
                    f"{patient.anchor_age} años y grupo de año de referencia {patient.anchor_year_group}."
                ),
                operation="get_patient", arguments={"subject_id": sid},
                scope={"subject_id": sid}, expected_tool="get_patient_summary",
                contexts=[patient.model_dump_json(exclude={"evidence_id"})], validation_required=False,
            )
        for sid in subjects[3:6]:
            summary = run_sync(self.provider.get_patient_summary(self.ctx(sid), sid))
            st = summary.stats
            self.add(
                category="patient_summary",
                question=f"¿Cuántos ingresos hospitalarios y cuántas estancias en UCI tiene registrados el paciente {sid}?",
                ground_truth=(
                    f"El paciente {sid} tiene {st.total_admissions} ingreso(s) hospitalario(s) y "
                    f"{st.total_icu_stays} estancia(s) en UCI registradas; el último ingreso comenzó el "
                    f"{fmt_dt(st.last_admission)}."
                ),
                operation="get_patient_summary", arguments={"subject_id": sid},
                scope={"subject_id": sid}, expected_tool="get_patient_summary",
                contexts=[st.model_dump_json(), json.dumps([a.model_dump(mode="json", exclude={"evidence_id"}) for a in summary.admissions], ensure_ascii=False)],
                validation_required=False,
            )

    def build_admission(self, subjects: List[int]) -> None:
        for i, sid in enumerate(subjects[:6]):
            admissions = run_sync(self.provider.list_admissions(self.ctx(sid), sid, limit=20))
            adm = sorted(admissions.items, key=lambda a: a.hadm_id)[0]
            details = run_sync(self.provider.get_admission_details(self.ctx(sid), adm.hadm_id))
            a = details.admission
            if i < 3:
                self.add(
                    category="admission",
                    question=f"¿Cuándo ingresó y cuándo fue dado de alta el paciente {sid} en su ingreso {adm.hadm_id}, y de qué tipo fue el ingreso?",
                    ground_truth=(
                        f"El ingreso {adm.hadm_id} del paciente {sid} comenzó el {fmt_dt(a.admittime)} y terminó el "
                        f"{fmt_dt(a.dischtime)}; el tipo de ingreso fue {a.admission_type} con procedencia {a.admission_location}."
                    ),
                    operation="get_admission_details", arguments={"hadm_id": adm.hadm_id},
                    scope={"subject_id": sid, "hadm_id": adm.hadm_id}, expected_tool="get_admission_details",
                    contexts=[a.model_dump_json(exclude={"evidence_id"})], validation_required=False,
                )
            else:
                los = f"{a.length_of_stay_days:.1f} días" if a.length_of_stay_days is not None else "duración no calculable"
                self.add(
                    category="admission",
                    question=f"¿A dónde fue dado de alta el paciente {sid} tras el ingreso {adm.hadm_id} y cuántos días duró el ingreso?",
                    ground_truth=(
                        f"Tras el ingreso {adm.hadm_id}, el paciente {sid} fue dado de alta a {a.discharge_location}; "
                        f"el ingreso duró {los} ({fmt_dt(a.admittime)} a {fmt_dt(a.dischtime)})."
                    ),
                    operation="get_admission_details", arguments={"hadm_id": adm.hadm_id},
                    scope={"subject_id": sid, "hadm_id": adm.hadm_id}, expected_tool="get_admission_details",
                    contexts=[a.model_dump_json(exclude={"evidence_id"})], validation_required=False,
                )

    def build_diagnoses(self, subjects: List[int]) -> None:
        for i, sid in enumerate(subjects[:6]):
            admissions = run_sync(self.provider.list_admissions(self.ctx(sid), sid, limit=20))
            hadm = sorted(a.hadm_id for a in admissions.items)[0]
            page = run_sync(self.provider.list_conditions(self.ctx(sid), subject_id=sid, hadm_id=hadm, limit=100))
            items = page.items
            contexts = [json.dumps([c.model_dump(mode="json", exclude={"evidence_id"}) for c in items[:20]], ensure_ascii=False)]
            if i < 3:
                titles = "; ".join(f"{c.icd_code} ({c.title})" for c in items[:5])
                self.add(
                    category="diagnoses",
                    question=f"¿Cuáles son los diagnósticos codificados del ingreso {hadm} del paciente {sid}?",
                    ground_truth=(
                        f"El ingreso {hadm} del paciente {sid} tiene {len(items)} diagnósticos codificados. "
                        f"Los cinco primeros por orden de secuencia son: {titles}."
                    ),
                    operation="list_conditions", arguments={"subject_id": sid, "hadm_id": hadm},
                    scope={"subject_id": sid, "hadm_id": hadm}, expected_tool="get_diagnoses",
                    contexts=contexts, validation_required=False,
                )
            else:
                first = sorted(items, key=lambda c: c.seq_num)[0]
                self.add(
                    category="diagnoses",
                    question=f"¿Qué diagnóstico aparece codificado en primera posición (seq_num 1) en el ingreso {hadm} del paciente {sid}?",
                    ground_truth=(
                        f"En el ingreso {hadm} del paciente {sid}, el diagnóstico codificado en primera posición es "
                        f"{first.icd_code} (ICD-{first.icd_version}): {first.title}."
                    ),
                    operation="list_conditions", arguments={"subject_id": sid, "hadm_id": hadm},
                    scope={"subject_id": sid, "hadm_id": hadm}, expected_tool="get_diagnoses",
                    contexts=contexts, validation_required=True,
                    notes="Confirmar si seq_num 1 puede presentarse como 'diagnóstico principal' o solo como primera posición de secuencia.",
                )

    def build_labs(self, subjects: List[int]) -> None:
        for sid in subjects[:6]:
            page = run_sync(self.provider.list_lab_observations(self.ctx(sid), subject_id=sid, limit=200))
            labels = Counter(l.label for l in page.items if l.label and l.valuenum is not None)
            if not labels:
                continue
            label = labels.most_common(1)[0][0]
            latest = run_sync(self.provider.list_lab_observations(self.ctx(sid), subject_id=sid, label_contains=label, limit=5))
            top = latest.items[0]
            flag = " (marcado como anormal)" if top.flag == "abnormal" else ""
            rango = ""
            if top.ref_range_lower is not None and top.ref_range_upper is not None:
                rango = f"; rango de referencia {fmt_num(top.ref_range_lower)}-{fmt_num(top.ref_range_upper)}"
            self.add(
                category="labs",
                question=f"¿Cuál es el último valor registrado de {label} para el paciente {sid}?",
                ground_truth=(
                    f"El último valor registrado de {label} para el paciente {sid} es {fmt_num(top.valuenum)} {top.valueuom or ''}".rstrip()
                    + f"{flag}, con fecha {fmt_dt(top.charttime)}{rango}."
                ),
                operation="list_lab_observations", arguments={"subject_id": sid, "label_contains": label, "limit": 5},
                scope={"subject_id": sid}, expected_tool="get_labs",
                contexts=[json.dumps([l.model_dump(mode="json", exclude={"evidence_id"}) for l in latest.items], ensure_ascii=False)],
                validation_required=True,
                notes="Validar la interpretacion de 'flag' y del rango de referencia en la redaccion.",
            )

    def build_medications(self, subjects: List[int]) -> None:
        for sid in subjects[:6]:
            admissions = run_sync(self.provider.list_admissions(self.ctx(sid), sid, limit=20))
            hadm = sorted(a.hadm_id for a in admissions.items)[0]
            page = run_sync(self.provider.list_medications(self.ctx(sid), subject_id=sid, hadm_id=hadm, limit=200))
            drugs = []
            for m in page.items:
                if m.drug not in drugs:
                    drugs.append(m.drug)
            self.add(
                category="medications",
                question=f"¿Qué fármacos se prescribieron al paciente {sid} durante el ingreso {hadm}?",
                ground_truth=(
                    f"Durante el ingreso {hadm} se registraron {len(page.items)} prescripciones para el paciente {sid}, "
                    f"con {len(drugs)} fármacos distintos. Entre ellos: {', '.join(drugs[:8])}."
                ),
                operation="list_medications", arguments={"subject_id": sid, "hadm_id": hadm, "limit": 200},
                scope={"subject_id": sid, "hadm_id": hadm}, expected_tool="get_medications",
                contexts=[json.dumps([m.model_dump(mode="json", exclude={"evidence_id"}) for m in page.items[:30]], ensure_ascii=False)],
                validation_required=True,
                notes="Confirmar que 'prescrito' (prescriptions) no se presente como 'administrado' (emar).",
            )

    def build_icu(self, subjects: List[int]) -> None:
        for i, sid in enumerate(subjects[:5]):
            stays = run_sync(self.provider.list_icu_stays(self.ctx(sid), subject_id=sid, limit=20))
            stay = sorted(stays.items, key=lambda s: s.stay_id)[0]
            if i < 3:
                los = f"{stay.los_days:.2f} días" if stay.los_days is not None else "duración no registrada"
                self.add(
                    category="icu",
                    question=f"¿En qué unidad ingresó el paciente {sid} en su estancia de UCI {stay.stay_id} y cuánto duró?",
                    ground_truth=(
                        f"La estancia de UCI {stay.stay_id} del paciente {sid} comenzó en {stay.first_careunit} el "
                        f"{fmt_dt(stay.intime)}, terminó el {fmt_dt(stay.outtime)} en {stay.last_careunit} y duró {los}."
                    ),
                    operation="list_icu_stays", arguments={"subject_id": sid},
                    scope={"subject_id": sid, "hadm_id": stay.hadm_id, "stay_id": stay.stay_id}, expected_tool="get_icu_stays",
                    contexts=[stay.model_dump_json(exclude={"evidence_id"})], validation_required=False,
                )
            else:
                obs = run_sync(self.provider.list_icu_observations(self.ctx(sid), stay_id=stay.stay_id, label_contains="Heart Rate", limit=5))
                if not obs.items:
                    continue
                top = obs.items[0]
                self.add(
                    category="icu",
                    question=f"¿Cuál es el último valor de frecuencia cardíaca registrado en la estancia de UCI {stay.stay_id} del paciente {sid}?",
                    ground_truth=(
                        f"El último valor de {top.label} registrado en la estancia {stay.stay_id} es {fmt_num(top.valuenum)} "
                        f"{top.valueuom or ''} el {fmt_dt(top.charttime)}."
                    ).replace("  ", " "),
                    operation="list_icu_observations", arguments={"stay_id": stay.stay_id, "label_contains": "Heart Rate", "limit": 5},
                    scope={"subject_id": sid, "hadm_id": stay.hadm_id, "stay_id": stay.stay_id}, expected_tool="get_icu_observations",
                    contexts=[json.dumps([o.model_dump(mode="json", exclude={"evidence_id"}) for o in obs.items], ensure_ascii=False)],
                    validation_required=True,
                    notes="Validar el mapeo de 'frecuencia cardíaca' al item 'Heart Rate' de d_items.",
                )

    # ------------------------------------------------------------------
    def _aggregate(self, name: str, **kwargs) -> Any:
        ctx = self.ctx()
        try:
            return run_sync(getattr(self.provider, name)(ctx, **kwargs))
        except ProviderUnavailable:
            print(f"  [aviso] RPC de agregados no disponible; calculando '{name}' con emulacion en memoria")
            return self._aggregate_fallback(name, **kwargs)

    def _paged(self, schema: str, table: str, columns: str) -> List[Dict[str, Any]]:
        rows, start = [], 0
        while True:
            page = self.client.schema(schema).table(table).select(columns).range(start, start + 999).execute().data or []
            rows.extend(page)
            if len(page) < 1000:
                return rows
            start += 1000

    def _aggregate_fallback(self, name: str, **kwargs) -> Any:
        from chathce.adapters.memory.postgrest_client import InMemoryPostgrestClient, register_clinical_aggregate_rpcs

        mem = InMemoryPostgrestClient()
        if name == "get_dataset_summary":
            def count(schema, table):
                return self.client.schema(schema).table(table).select("*", count="exact", head=True).execute().count or 0
            from chathce.domain.clinical import DatasetSummary
            return DatasetSummary(
                patients=count(HOSP, "patients"), admissions=count(HOSP, "admissions"), icu_stays=count(ICU, "icustays"),
                diagnoses=count(HOSP, "diagnoses_icd"), lab_events=count(HOSP, "labevents"),
                prescriptions=count(HOSP, "prescriptions"), source=self.provider.source_name,
                computed_at=datetime.now(timezone.utc),
            )
        if name == "top_diagnoses":
            mem.tables[(HOSP, "diagnoses_icd")] = self._paged(HOSP, "diagnoses_icd", "icd_code,icd_version")
            codes = {(r["icd_code"], r["icd_version"]) for r in mem.tables[(HOSP, "diagnoses_icd")]}
            titles = self.provider._dict.icd_titles(codes)
            mem.tables[(HOSP, "d_icd_diagnoses")] = [{"icd_code": c, "icd_version": v, "long_title": t} for (c, v), t in titles.items()]
        elif name == "top_drugs":
            mem.tables[(HOSP, "prescriptions")] = self._paged(HOSP, "prescriptions", "drug")
        elif name == "admission_type_distribution":
            mem.tables[(HOSP, "admissions")] = self._paged(HOSP, "admissions", "admission_type")
        register_clinical_aggregate_rpcs(mem)
        shadow = MimicClinicalDataProvider(mem, source_name=self.provider.source_name)
        return run_sync(getattr(shadow, name)(self.ctx(), **kwargs))

    def build_aggregates(self) -> None:
        summary = self._aggregate("get_dataset_summary")
        self.add(
            category="aggregates",
            question="¿Cuántos pacientes, ingresos hospitalarios y estancias en UCI contiene el conjunto de datos?",
            ground_truth=(
                f"El conjunto de datos contiene {summary.patients} pacientes, {summary.admissions} ingresos hospitalarios y "
                f"{summary.icu_stays} estancias en UCI, con {summary.diagnoses} diagnósticos codificados, "
                f"{summary.lab_events} resultados de laboratorio y {summary.prescriptions} prescripciones."
            ),
            operation="get_dataset_summary", arguments={}, scope={}, expected_tool="get_dataset_statistics",
            contexts=[summary.model_dump_json(exclude={"computed_at"})], validation_required=False,
        )

        def freq_gt(freq: FrequencyResult, intro: str) -> str:
            parts = [f"{b.label or b.key} ({b.count})" for b in freq.buckets]
            return f"{intro}: " + "; ".join(parts) + "."

        top = self._aggregate("top_diagnoses", limit=10)
        self.add(
            category="aggregates",
            question="¿Cuáles son los 10 diagnósticos más frecuentes en el conjunto de datos?",
            ground_truth=freq_gt(top, "Los 10 diagnósticos codificados más frecuentes, con su número de apariciones, son"),
            operation="top_diagnoses", arguments={"limit": 10}, scope={}, expected_tool="get_dataset_statistics",
            contexts=[top.model_dump_json(exclude={"computed_at"})], validation_required=True,
            notes="Validar la redaccion de los titulos ICD largos (abreviaturas clinicas).",
        )
        top10 = self._aggregate("top_diagnoses", limit=5, icd_version=10)
        self.add(
            category="aggregates",
            question="¿Cuáles son los 5 diagnósticos ICD-10 más frecuentes en el conjunto de datos?",
            ground_truth=freq_gt(top10, "Los 5 diagnósticos ICD-10 más frecuentes son"),
            operation="top_diagnoses", arguments={"limit": 5, "icd_version": 10}, scope={}, expected_tool="get_dataset_statistics",
            contexts=[top10.model_dump_json(exclude={"computed_at"})], validation_required=True,
            notes="Validar la redaccion de los titulos ICD largos.",
        )
        drugs = self._aggregate("top_drugs", limit=10)
        self.add(
            category="aggregates",
            question="¿Cuáles son los 10 fármacos más prescritos en el conjunto de datos?",
            ground_truth=freq_gt(drugs, "Los 10 fármacos con más prescripciones son"),
            operation="top_drugs", arguments={"limit": 10}, scope={}, expected_tool="get_dataset_statistics",
            contexts=[drugs.model_dump_json(exclude={"computed_at"})], validation_required=True,
            notes="Validar que se hable de prescripciones (no de administraciones).",
        )
        types = self._aggregate("admission_type_distribution")
        self.add(
            category="aggregates",
            question="¿Cómo se distribuyen los ingresos hospitalarios por tipo de ingreso en el conjunto de datos?",
            ground_truth=freq_gt(types, "La distribución de ingresos por tipo es"),
            operation="admission_type_distribution", arguments={}, scope={}, expected_tool="get_dataset_statistics",
            contexts=[types.model_dump_json(exclude={"computed_at"})], validation_required=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "Evaluation" / "golden_set_ragas.json")
    parser.add_argument("--n-patients", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42, help="registrado en metadata; la seleccion es determinista")
    args = parser.parse_args()

    from config.settings import get_settings
    from chathce.adapters.supabase.client_factory import SupabaseClients

    settings = get_settings()
    db = settings.require_database()
    clients = SupabaseClients(url=db.supabase_url, service_key=db.supabase_key,
                              clinical_key=settings.clinical.supabase_clinical_key)
    client = clients.clinical_client()
    provider = MimicClinicalDataProvider(client, source_name=settings.clinical.source_name)

    builder = Builder(provider, client)
    subjects = builder.select_subjects(args.n_patients)
    print(f"Pacientes seleccionados: {subjects}")
    builder.build_patient_summary(subjects)
    builder.build_admission(subjects)
    builder.build_diagnoses(subjects)
    builder.build_labs(subjects)
    builder.build_medications(subjects)
    builder.build_icu(subjects)
    builder.build_aggregates()

    snapshot = builder._aggregate("get_dataset_summary")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        commit = "unknown"

    questions = sorted(builder.questions, key=lambda q: q["id"])
    distribution = dict(sorted(Counter(q["category"] for q in questions).items()))
    payload = {
        "metadata": {
            "version": GOLDEN_SET_VERSION,
            "dataset": DATASET,
            "fecha_generacion": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generador": {"script": "scripts/build_golden_set_mimiciv.py", "seed": args.seed, "n_patients": args.n_patients, "commit": commit},
            "data_snapshot": {
                "patients": snapshot.patients, "admissions": snapshot.admissions, "icu_stays": snapshot.icu_stays,
                "diagnoses": snapshot.diagnoses, "lab_events": snapshot.lab_events, "prescriptions": snapshot.prescriptions,
            },
            "total_preguntas": len(questions),
            "distribucion": distribution,
            "umbrales_ragas": THRESHOLDS,
            "operaciones_referenciadas": sorted({q["ground_truth_operation"]["operation"] for q in questions}),
            "subject_ids_usados": sorted(builder.subjects_used),
            "requiere_validacion_clinica": [q["id"] for q in questions if q["clinical_validation"]["required"]],
        },
        "questions": questions,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Golden set escrito en {args.output}: {len(questions)} preguntas, distribucion {distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
