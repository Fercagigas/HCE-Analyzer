"""
Cargador de datos MIMIC-IV Clinical Database Demo 2.2 a Supabase.

Lee los CSV.gz del dataset y los inserta en los esquemas `mimiciv_hosp` y
`mimiciv_icu` mediante el cliente Supabase (service_role). Es idempotente:
por defecto vacía cada tabla destino antes de cargarla.

Uso (con el entorno HCE activo):
    conda activate HCE ; python scripts/load_mimiciv.py
    conda activate HCE ; python scripts/load_mimiciv.py --only chartevents
    conda activate HCE ; python scripts/load_mimiciv.py --skip chartevents
    conda activate HCE ; python scripts/load_mimiciv.py --verify-only

Requiere SUPABASE_URL y SUPABASE_KEY (service_role) en el entorno / .env.
"""
from __future__ import annotations

import argparse
import gzip
import csv
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

BASE = Path(__file__).resolve().parent.parent / "_mimic_iv_extract" / "mimic-iv-clinical-database-demo-2.2"
BATCH_SIZE = 2000

# --- Type coercion helpers -------------------------------------------------

def _int(v: str) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None

def _float(v: str) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None

def _str(v: str) -> Optional[str]:
    if v is None or v == "":
        return None
    return v

def _ts(v: str) -> Optional[str]:
    # Postgres acepta el formato ISO de MIMIC directamente.
    return _str(v)


# --- Table definitions: (module, filename, schema.table, {col: coercer}) ---

TABLES: List[Dict[str, Any]] = [
    # hosp dictionaries
    {"file": "hosp/d_icd_diagnoses.csv.gz", "table": "mimiciv_hosp.d_icd_diagnoses",
     "cols": {"icd_code": _str, "icd_version": _int, "long_title": _str}},
    {"file": "hosp/d_icd_procedures.csv.gz", "table": "mimiciv_hosp.d_icd_procedures",
     "cols": {"icd_code": _str, "icd_version": _int, "long_title": _str}},
    {"file": "hosp/d_labitems.csv.gz", "table": "mimiciv_hosp.d_labitems",
     "cols": {"itemid": _int, "label": _str, "fluid": _str, "category": _str}},
    # hosp core
    {"file": "hosp/patients.csv.gz", "table": "mimiciv_hosp.patients",
     "cols": {"subject_id": _int, "gender": _str, "anchor_age": _int, "anchor_year": _int,
              "anchor_year_group": _str, "dod": _str}},
    {"file": "hosp/admissions.csv.gz", "table": "mimiciv_hosp.admissions",
     "cols": {"subject_id": _int, "hadm_id": _int, "admittime": _ts, "dischtime": _ts,
              "deathtime": _ts, "admission_type": _str, "admit_provider_id": _str,
              "admission_location": _str, "discharge_location": _str, "insurance": _str,
              "language": _str, "marital_status": _str, "race": _str, "edregtime": _ts,
              "edouttime": _ts, "hospital_expire_flag": _int}},
    {"file": "hosp/transfers.csv.gz", "table": "mimiciv_hosp.transfers",
     "cols": {"subject_id": _int, "hadm_id": _int, "transfer_id": _int, "eventtype": _str,
              "careunit": _str, "intime": _ts, "outtime": _ts}},
    {"file": "hosp/services.csv.gz", "table": "mimiciv_hosp.services",
     "cols": {"subject_id": _int, "hadm_id": _int, "transfertime": _ts, "prev_service": _str,
              "curr_service": _str}},
    {"file": "hosp/diagnoses_icd.csv.gz", "table": "mimiciv_hosp.diagnoses_icd",
     "cols": {"subject_id": _int, "hadm_id": _int, "seq_num": _int, "icd_code": _str,
              "icd_version": _int}},
    {"file": "hosp/procedures_icd.csv.gz", "table": "mimiciv_hosp.procedures_icd",
     "cols": {"subject_id": _int, "hadm_id": _int, "seq_num": _int, "chartdate": _ts,
              "icd_code": _str, "icd_version": _int}},
    {"file": "hosp/labevents.csv.gz", "table": "mimiciv_hosp.labevents",
     "cols": {"labevent_id": _int, "subject_id": _int, "hadm_id": _int, "specimen_id": _int,
              "itemid": _int, "order_provider_id": _str, "charttime": _ts, "storetime": _ts,
              "value": _str, "valuenum": _float, "valueuom": _str, "ref_range_lower": _float,
              "ref_range_upper": _float, "flag": _str, "priority": _str, "comments": _str}},
    {"file": "hosp/microbiologyevents.csv.gz", "table": "mimiciv_hosp.microbiologyevents",
     "cols": {"microevent_id": _int, "subject_id": _int, "hadm_id": _int, "micro_specimen_id": _int,
              "order_provider_id": _str, "chartdate": _ts, "charttime": _ts, "spec_itemid": _int,
              "spec_type_desc": _str, "test_seq": _int, "storedate": _ts, "storetime": _ts,
              "test_itemid": _int, "test_name": _str, "org_itemid": _int, "org_name": _str,
              "isolate_num": _int, "quantity": _str, "ab_itemid": _int, "ab_name": _str,
              "dilution_text": _str, "dilution_comparison": _str, "dilution_value": _float,
              "interpretation": _str, "comments": _str}},
    {"file": "hosp/omr.csv.gz", "table": "mimiciv_hosp.omr",
     "cols": {"subject_id": _int, "chartdate": _str, "seq_num": _int, "result_name": _str,
              "result_value": _str}},
    {"file": "hosp/prescriptions.csv.gz", "table": "mimiciv_hosp.prescriptions",
     "cols": {"subject_id": _int, "hadm_id": _int, "pharmacy_id": _int, "poe_id": _str,
              "poe_seq": _int, "order_provider_id": _str, "starttime": _ts, "stoptime": _ts,
              "drug_type": _str, "drug": _str, "formulary_drug_cd": _str, "gsn": _str, "ndc": _str,
              "prod_strength": _str, "form_rx": _str, "dose_val_rx": _str, "dose_unit_rx": _str,
              "form_val_disp": _str, "form_unit_disp": _str, "doses_per_24_hrs": _float,
              "route": _str}},
    {"file": "hosp/pharmacy.csv.gz", "table": "mimiciv_hosp.pharmacy",
     "cols": {"subject_id": _int, "hadm_id": _int, "pharmacy_id": _int, "poe_id": _str,
              "starttime": _ts, "stoptime": _ts, "medication": _str, "proc_type": _str,
              "status": _str, "entertime": _ts, "verifiedtime": _ts, "route": _str,
              "frequency": _str, "disp_sched": _str, "infusion_type": _str, "sliding_scale": _str,
              "lockout_interval": _str, "basal_rate": _float, "one_hr_max": _str,
              "doses_per_24_hrs": _float, "duration": _float, "duration_interval": _str,
              "expiration_value": _int, "expiration_unit": _str, "expirationdate": _ts,
              "dispensation": _str, "fill_quantity": _str}},
    {"file": "hosp/emar.csv.gz", "table": "mimiciv_hosp.emar",
     "cols": {"subject_id": _int, "hadm_id": _int, "emar_id": _str, "emar_seq": _int,
              "poe_id": _str, "pharmacy_id": _int, "enter_provider_id": _str, "charttime": _ts,
              "medication": _str, "event_txt": _str, "scheduletime": _ts, "storetime": _ts}},
    # icu
    {"file": "icu/d_items.csv.gz", "table": "mimiciv_icu.d_items",
     "cols": {"itemid": _int, "label": _str, "abbreviation": _str, "linksto": _str,
              "category": _str, "unitname": _str, "param_type": _str, "lownormalvalue": _float,
              "highnormalvalue": _float}},
    {"file": "icu/icustays.csv.gz", "table": "mimiciv_icu.icustays",
     "cols": {"subject_id": _int, "hadm_id": _int, "stay_id": _int, "first_careunit": _str,
              "last_careunit": _str, "intime": _ts, "outtime": _ts, "los": _float}},
    {"file": "icu/chartevents.csv.gz", "table": "mimiciv_icu.chartevents",
     "cols": {"subject_id": _int, "hadm_id": _int, "stay_id": _int, "caregiver_id": _int,
              "charttime": _ts, "storetime": _ts, "itemid": _int, "value": _str,
              "valuenum": _float, "valueuom": _str, "warning": _int}},
]


def get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: faltan SUPABASE_URL / SUPABASE_KEY en el entorno.", file=sys.stderr)
        sys.exit(1)
    return create_client(url, key)


def read_rows(path: Path, cols: Dict[str, Callable]):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            yield {c: fn(raw.get(c)) for c, fn in cols.items()}


def truncate_table(client: Client, schema: str, table: str) -> None:
    # service_role puede borrar; usamos un filtro siempre verdadero.
    client.schema(schema).table(table).delete().neq("__none__", "__none__").execute()


def load_table(client: Client, spec: Dict[str, Any], truncate: bool = True) -> int:
    path = BASE / spec["file"]
    schema, table = spec["table"].split(".")
    if not path.exists():
        print(f"  SKIP {spec['table']}: no existe {path}")
        return 0

    if truncate:
        # Vaciar usando la primera columna, con un filtro siempre verdadero
        # apropiado al tipo (int -> gte -1e18, str -> neq sentinel improbable).
        first_col = list(spec["cols"].keys())[0]
        first_fn = spec["cols"][first_col]
        try:
            if first_fn in (_int, _float):
                client.schema(schema).table(table).delete().gte(first_col, -999999999).execute()
            else:
                client.schema(schema).table(table).delete().neq(first_col, "\x01__never__\x01").execute()
        except Exception as e:
            print(f"    aviso: no se pudo vaciar {spec['table']} ({e}); se continúa con insert")

    batch: List[Dict[str, Any]] = []
    total = 0
    t0 = time.time()
    for row in read_rows(path, spec["cols"]):
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            client.schema(schema).table(table).insert(batch).execute()
            total += len(batch)
            batch = []
            print(f"    {spec['table']}: {total} filas...", end="\r")
    if batch:
        client.schema(schema).table(table).insert(batch).execute()
        total += len(batch)
    print(f"  OK   {spec['table']}: {total} filas en {time.time() - t0:.1f}s" + " " * 20)
    return total


def verify(client: Client) -> None:
    print("\n=== Verificación de conteos ===")
    for spec in TABLES:
        schema, table = spec["table"].split(".")
        try:
            res = client.schema(schema).table(table).select("*", count="exact").limit(1).execute()
            print(f"  {spec['table']}: {res.count} filas")
        except Exception as e:
            print(f"  {spec['table']}: ERROR {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="cargar solo estas tablas (nombre sin schema)")
    ap.add_argument("--skip", nargs="*", default=[], help="omitir estas tablas")
    ap.add_argument("--no-truncate", action="store_true", help="no vaciar antes de cargar")
    ap.add_argument("--verify-only", action="store_true", help="solo verificar conteos")
    args = ap.parse_args()

    client = get_client()

    if args.verify_only:
        verify(client)
        return

    grand_total = 0
    for spec in TABLES:
        name = spec["table"].split(".")[1]
        if args.only and name not in args.only:
            continue
        if name in args.skip:
            print(f"  SKIP {spec['table']} (--skip)")
            continue
        grand_total += load_table(client, spec, truncate=not args.no_truncate)

    print(f"\nTotal cargado: {grand_total} filas")
    verify(client)


if __name__ == "__main__":
    main()
