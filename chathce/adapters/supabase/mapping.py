"""Filas MIMIC-IV (dict PostgREST) -> DTOs canonicos. Unico lugar que conoce nombres de columna."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from chathce.domain.clinical import (
    Admission,
    Condition,
    IcdCodeEntry,
    IcuItem,
    IcuObservation,
    IcuStay,
    LabItem,
    LabObservation,
    Medication,
    Patient,
    Procedure,
    ServiceEpisode,
    Transfer,
    evidence_id,
)


def _dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


class RowMapper:
    def __init__(self, source: str):
        self.source = source

    def patient(self, row: Dict[str, Any], *, race: Optional[str] = None) -> Patient:
        dod = _date(row.get("dod"))
        return Patient(
            subject_id=int(row["subject_id"]),
            gender=_str(row.get("gender")),
            anchor_age=_int(row.get("anchor_age")),
            anchor_year_group=_str(row.get("anchor_year_group")),
            deceased=dod is not None,
            date_of_death=dod,
            race=race,
            evidence_id=evidence_id(self.source, "patient", row["subject_id"]),
        )

    def admission(self, row: Dict[str, Any]) -> Admission:
        admit, disch = _dt(row.get("admittime")), _dt(row.get("dischtime"))
        los = None
        if admit and disch:
            los = round((disch - admit).total_seconds() / 86400.0, 3)
        return Admission(
            hadm_id=int(row["hadm_id"]),
            subject_id=int(row["subject_id"]),
            admittime=admit,
            dischtime=disch,
            admission_type=_str(row.get("admission_type")),
            admission_location=_str(row.get("admission_location")),
            discharge_location=_str(row.get("discharge_location")),
            insurance=_str(row.get("insurance")),
            race=_str(row.get("race")),
            hospital_expire_flag=bool(_int(row.get("hospital_expire_flag")) or 0),
            length_of_stay_days=los,
            evidence_id=evidence_id(self.source, "admission", row["hadm_id"]),
        )

    def transfer(self, row: Dict[str, Any]) -> Transfer:
        return Transfer(
            transfer_id=int(row["transfer_id"]),
            subject_id=int(row["subject_id"]),
            hadm_id=_int(row.get("hadm_id")),
            eventtype=_str(row.get("eventtype")),
            careunit=_str(row.get("careunit")),
            intime=_dt(row.get("intime")),
            outtime=_dt(row.get("outtime")),
            evidence_id=evidence_id(self.source, "transfer", row["transfer_id"]),
        )

    def service(self, row: Dict[str, Any]) -> ServiceEpisode:
        key = f"{row['hadm_id']}:{row.get('transfertime')}"
        return ServiceEpisode(
            subject_id=int(row["subject_id"]),
            hadm_id=int(row["hadm_id"]),
            transfertime=_dt(row.get("transfertime")),
            prev_service=_str(row.get("prev_service")),
            curr_service=_str(row.get("curr_service")),
            evidence_id=evidence_id(self.source, "service", key),
        )

    def condition(self, row: Dict[str, Any], title: Optional[str]) -> Condition:
        key = f"{row['hadm_id']}:{row['seq_num']}"
        return Condition(
            subject_id=int(row["subject_id"]),
            hadm_id=int(row["hadm_id"]),
            seq_num=int(row["seq_num"]),
            icd_code=str(row["icd_code"]),
            icd_version=int(row["icd_version"]),
            title=title,
            evidence_id=evidence_id(self.source, "diagnosis", key),
        )

    def procedure(self, row: Dict[str, Any], title: Optional[str]) -> Procedure:
        key = f"{row['hadm_id']}:{row['seq_num']}"
        return Procedure(
            subject_id=int(row["subject_id"]),
            hadm_id=int(row["hadm_id"]),
            seq_num=int(row["seq_num"]),
            chartdate=_date(row.get("chartdate")),
            icd_code=str(row["icd_code"]),
            icd_version=int(row["icd_version"]),
            title=title,
            evidence_id=evidence_id(self.source, "procedure", key),
        )

    def lab(self, row: Dict[str, Any], item: Optional[Dict[str, Any]]) -> LabObservation:
        item = item or {}
        return LabObservation(
            labevent_id=int(row["labevent_id"]),
            subject_id=int(row["subject_id"]),
            hadm_id=_int(row.get("hadm_id")),
            itemid=int(row["itemid"]),
            label=_str(item.get("label")),
            fluid=_str(item.get("fluid")),
            category=_str(item.get("category")),
            charttime=_dt(row.get("charttime")),
            value=_str(row.get("value")),
            valuenum=_float(row.get("valuenum")),
            valueuom=_str(row.get("valueuom")),
            ref_range_lower=_float(row.get("ref_range_lower")),
            ref_range_upper=_float(row.get("ref_range_upper")),
            flag=_str(row.get("flag")),
            evidence_id=evidence_id(self.source, "labevent", row["labevent_id"]),
        )

    def prescription(self, row: Dict[str, Any]) -> Medication:
        key = row.get("pharmacy_id") or f"{row.get('poe_id')}:{row.get('poe_seq')}"
        return Medication(
            source="prescription",
            subject_id=int(row["subject_id"]),
            hadm_id=_int(row.get("hadm_id")),
            drug=str(row.get("drug") or ""),
            starttime=_dt(row.get("starttime")),
            stoptime=_dt(row.get("stoptime")),
            dose_val_rx=_str(row.get("dose_val_rx")),
            dose_unit_rx=_str(row.get("dose_unit_rx")),
            route=_str(row.get("route")),
            evidence_id=evidence_id(self.source, "prescription", key),
        )

    def emar(self, row: Dict[str, Any]) -> Medication:
        return Medication(
            source="emar",
            subject_id=int(row["subject_id"]),
            hadm_id=_int(row.get("hadm_id")),
            drug=str(row.get("medication") or ""),
            starttime=_dt(row.get("charttime")),
            event_txt=_str(row.get("event_txt")),
            evidence_id=evidence_id(self.source, "emar", row.get("emar_id")),
        )

    def icu_stay(self, row: Dict[str, Any]) -> IcuStay:
        return IcuStay(
            stay_id=int(row["stay_id"]),
            hadm_id=int(row["hadm_id"]),
            subject_id=int(row["subject_id"]),
            first_careunit=_str(row.get("first_careunit")),
            last_careunit=_str(row.get("last_careunit")),
            intime=_dt(row.get("intime")),
            outtime=_dt(row.get("outtime")),
            los_days=_float(row.get("los")),
            evidence_id=evidence_id(self.source, "icustay", row["stay_id"]),
        )

    def icu_observation(self, row: Dict[str, Any], item: Optional[Dict[str, Any]]) -> IcuObservation:
        item = item or {}
        key = f"{row['stay_id']}:{row['itemid']}:{row.get('charttime')}"
        return IcuObservation(
            stay_id=int(row["stay_id"]),
            subject_id=int(row["subject_id"]),
            hadm_id=_int(row.get("hadm_id")),
            itemid=int(row["itemid"]),
            label=_str(item.get("label")),
            category=_str(item.get("category")),
            param_type=_str(item.get("param_type")),
            charttime=_dt(row.get("charttime")),
            value=_str(row.get("value")),
            valuenum=_float(row.get("valuenum")),
            valueuom=_str(row.get("valueuom")),
            evidence_id=evidence_id(self.source, "chartevent", key),
        )

    @staticmethod
    def icd_entry(row: Dict[str, Any], kind: str) -> IcdCodeEntry:
        return IcdCodeEntry(
            icd_code=str(row["icd_code"]), icd_version=int(row["icd_version"]),
            long_title=str(row.get("long_title") or ""), kind=kind,  # type: ignore[arg-type]
        )

    @staticmethod
    def lab_item(row: Dict[str, Any]) -> LabItem:
        return LabItem(itemid=int(row["itemid"]), label=str(row.get("label") or ""),
                       fluid=_str(row.get("fluid")), category=_str(row.get("category")))

    @staticmethod
    def icu_item(row: Dict[str, Any]) -> IcuItem:
        return IcuItem(itemid=int(row["itemid"]), label=str(row.get("label") or ""),
                       category=_str(row.get("category")), unitname=_str(row.get("unitname")),
                       param_type=_str(row.get("param_type")))
