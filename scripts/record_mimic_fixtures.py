"""Graba fixtures MIMIC-IV (demo) para tests de caracterizacion y de contrato.

Lectura unica sobre Supabase (solo SELECT). Selecciona de forma determinista N
pacientes con al menos una admision, una estancia UCI y un numero acotado de
labevents, y descarga sus filas y los subconjuntos de diccionario necesarios.
`expected/` conserva la salida congelada del DatabaseService legacy como baseline de contrato.

Uso (PowerShell, una sola vez o cuando cambie el dataset):

    conda activate HCE ; python scripts/record_mimic_fixtures.py --n-subjects 3

Salida: tests/fixtures/mimic/{tables/*.json, expected/*.json, manifest.json}
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.fakes.normalize import dump_json, normalize  # noqa: E402

HOSP = "mimiciv_hosp"
ICU = "mimiciv_icu"

PER_SUBJECT_TABLES = {
    HOSP: {
        "patients": None,
        "admissions": None,
        "transfers": None,
        "services": None,
        "diagnoses_icd": None,
        "procedures_icd": None,
        "labevents": 500,
        "prescriptions": 300,
        "emar": 300,
        "omr": 200,
        "microbiologyevents": 200,
    },
    ICU: {"icustays": None},
}
CHARTEVENTS_PER_STAY = 500


def _count(client, schema: str, table: str, column: str, value: Any) -> int:
    res = (
        client.schema(schema).table(table)
        .select("*", count="exact", head=True)
        .eq(column, value)
        .execute()
    )
    return int(res.count or 0)


def _fetch(client, schema: str, table: str, column: str, value: Any, limit: int | None) -> List[dict]:
    query = client.schema(schema).table(table).select("*").eq(column, value)
    if limit:
        query = query.limit(limit)
    return list(query.execute().data or [])


def _fetch_in(client, schema: str, table: str, column: str, values: List[Any]) -> List[dict]:
    rows: List[dict] = []
    values = sorted({v for v in values if v is not None})
    for i in range(0, len(values), 100):
        chunk = values[i:i + 100]
        rows.extend(
            client.schema(schema).table(table).select("*").in_(column, chunk).execute().data or []
        )
    return rows


def select_subjects(client, n: int, min_labs: int, max_labs: int) -> List[int]:
    candidates = (
        client.schema(HOSP).table("patients").select("subject_id").order("subject_id").execute().data or []
    )
    chosen: List[int] = []
    for row in candidates:
        sid = int(row["subject_id"])
        if _count(client, HOSP, "admissions", "subject_id", sid) < 1:
            continue
        if _count(client, ICU, "icustays", "subject_id", sid) < 1:
            continue
        labs = _count(client, HOSP, "labevents", "subject_id", sid)
        if not (min_labs <= labs <= max_labs):
            continue
        chosen.append(sid)
        if len(chosen) == n:
            break
    if len(chosen) < n:
        raise SystemExit(f"Solo {len(chosen)} pacientes cumplen los criterios; ajuste --max-labs")
    return chosen


def record_tables(client, subjects: List[int]) -> Dict[str, Dict[str, List[dict]]]:
    tables: Dict[str, Dict[str, List[dict]]] = {HOSP: {}, ICU: {}}
    for schema, spec in PER_SUBJECT_TABLES.items():
        for table, limit in spec.items():
            rows: List[dict] = []
            for sid in subjects:
                rows.extend(_fetch(client, schema, table, "subject_id", sid, limit))
            tables[schema][table] = rows

    stays = [int(r["stay_id"]) for r in tables[ICU]["icustays"]]
    chart_rows: List[dict] = []
    for stay in stays:
        chart_rows.extend(_fetch(client, ICU, "chartevents", "stay_id", stay, CHARTEVENTS_PER_STAY))
    tables[ICU]["chartevents"] = chart_rows

    # Diccionarios: solo las entradas referenciadas.
    diag_codes = [r["icd_code"] for r in tables[HOSP]["diagnoses_icd"]]
    proc_codes = [r["icd_code"] for r in tables[HOSP]["procedures_icd"]]
    lab_items = [r["itemid"] for r in tables[HOSP]["labevents"]]
    icu_items = [r["itemid"] for r in chart_rows]
    tables[HOSP]["d_icd_diagnoses"] = _fetch_in(client, HOSP, "d_icd_diagnoses", "icd_code", diag_codes)
    tables[HOSP]["d_icd_procedures"] = _fetch_in(client, HOSP, "d_icd_procedures", "icd_code", proc_codes)
    tables[HOSP]["d_labitems"] = _fetch_in(client, HOSP, "d_labitems", "itemid", lab_items)
    tables[ICU]["d_items"] = _fetch_in(client, ICU, "d_items", "itemid", icu_items)

    # Orden estable para diffs legibles.
    for schema in tables:
        for table, rows in tables[schema].items():
            rows.sort(key=lambda r: json.dumps(normalize(r), sort_keys=True))
    return tables


# NOTA: `tests/fixtures/mimic/expected/` es la salida congelada del DatabaseService legacy (retirado en
# WP12) y sirve como baseline de contrato para MimicClinicalDataProvider. No se regenera.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-subjects", type=int, default=3)
    parser.add_argument("--min-labs", type=int, default=20)
    parser.add_argument("--max-labs", type=int, default=500)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "tests" / "fixtures" / "mimic")
    args = parser.parse_args()

    from config.settings import get_settings
    from supabase import create_client

    db = get_settings().require_database()
    client = create_client(db.supabase_url, db.supabase_key)

    subjects = select_subjects(client, args.n_subjects, args.min_labs, args.max_labs)
    print(f"Pacientes seleccionados: {subjects}")
    tables = record_tables(client, subjects)

    out = args.output
    (out / "tables").mkdir(parents=True, exist_ok=True)
    for old in (out / "tables").glob("*.json"):
        old.unlink()

    counts: Dict[str, int] = {}
    for schema, by_table in tables.items():
        for table, rows in by_table.items():
            (out / "tables" / f"{schema}__{table}.json").write_text(dump_json(rows) + "\n", encoding="utf-8")
            counts[f"{schema}.{table}"] = len(rows)

    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        commit = "unknown"
    manifest = {
        "dataset": "MIMIC-IV Clinical Database Demo 2.2 (mimiciv_hosp, mimiciv_icu)",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "subject_ids": subjects,
        "selection": {"min_labs": args.min_labs, "max_labs": args.max_labs, "chartevents_per_stay": CHARTEVENTS_PER_STAY},
        "row_counts": counts,
        "expected_files": sorted(p.stem for p in (out / "expected").glob("*.json")) if (out / "expected").exists() else [],
    }
    (out / "manifest.json").write_text(dump_json(manifest) + "\n", encoding="utf-8")
    print(f"Fixtures escritas en {out}: {sum(counts.values())} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
