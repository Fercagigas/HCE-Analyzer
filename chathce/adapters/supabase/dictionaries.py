"""Cache de diccionarios MIMIC (d_labitems, d_items, d_icd_*) para resolver etiquetas sin N+1.

- ``d_labitems`` (~1.6k) y ``d_items`` (~4k) se cargan completos, paginados, una vez por proceso
  y se refrescan cada ``ttl_s``.
- ``d_icd_diagnoses``/``d_icd_procedures`` son grandes (>100k): se resuelven por lotes
  (``in_`` sobre los codigos pedidos) con memoizacion.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

HOSP = "mimiciv_hosp"
ICU = "mimiciv_icu"
PAGE = 1000
MAX_IN_CLAUSE = 200


class Dictionaries:
    def __init__(self, client: Any, *, ttl_s: float = 3600.0):
        self._client = client
        self._ttl = ttl_s
        self._lab_items: Dict[int, Dict[str, Any]] = {}
        self._icu_items: Dict[int, Dict[str, Any]] = {}
        self._loaded_at: Dict[str, float] = {}
        self._icd: Dict[Tuple[str, str, int], Optional[str]] = {}

    # ---- carga paginada -------------------------------------------------
    def _load_all(self, schema: str, table: str, columns: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        start = 0
        while True:
            page = (
                self._client.schema(schema).table(table).select(columns)
                .order("itemid").range(start, start + PAGE - 1).execute().data or []
            )
            rows.extend(page)
            if len(page) < PAGE:
                return rows
            start += PAGE

    def _fresh(self, key: str) -> bool:
        return key in self._loaded_at and (time.monotonic() - self._loaded_at[key]) < self._ttl

    def lab_items(self) -> Dict[int, Dict[str, Any]]:
        if not self._fresh("lab"):
            rows = self._load_all(HOSP, "d_labitems", "itemid,label,fluid,category")
            self._lab_items = {int(r["itemid"]): r for r in rows}
            self._loaded_at["lab"] = time.monotonic()
        return self._lab_items

    def icu_items(self) -> Dict[int, Dict[str, Any]]:
        if not self._fresh("icu"):
            rows = self._load_all(ICU, "d_items", "itemid,label,category,unitname,param_type")
            self._icu_items = {int(r["itemid"]): r for r in rows}
            self._loaded_at["icu"] = time.monotonic()
        return self._icu_items

    # ---- busqueda por etiqueta -------------------------------------------
    @staticmethod
    def _matching(items: Dict[int, Dict[str, Any]], text: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        needle = text.strip().lower()
        if not needle:
            return []
        found = [r for r in items.values() if needle in str(r.get("label") or "").lower()]
        found.sort(key=lambda r: (len(str(r.get("label") or "")), int(r["itemid"])))
        return found[:limit] if limit else found

    def lab_items_matching(self, text: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._matching(self.lab_items(), text, limit)

    def icu_items_matching(self, text: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._matching(self.icu_items(), text, limit)

    def lab_itemids_matching(self, text: str) -> List[int]:
        return [int(r["itemid"]) for r in self.lab_items_matching(text, MAX_IN_CLAUSE)]

    def icu_itemids_matching(self, text: str) -> List[int]:
        return [int(r["itemid"]) for r in self.icu_items_matching(text, MAX_IN_CLAUSE)]

    # ---- ICD por lotes ---------------------------------------------------
    def icd_titles(self, codes: Iterable[Tuple[str, int]], *, kind: str = "diagnosis") -> Dict[Tuple[str, int], Optional[str]]:
        table = "d_icd_diagnoses" if kind == "diagnosis" else "d_icd_procedures"
        wanted = {(str(c), int(v)) for c, v in codes if c}
        missing = [key for key in wanted if (kind, *key) not in self._icd]
        codes_only = sorted({c for c, _ in missing})
        for i in range(0, len(codes_only), MAX_IN_CLAUSE):
            chunk = codes_only[i:i + MAX_IN_CLAUSE]
            rows = (
                self._client.schema(HOSP).table(table).select("icd_code,icd_version,long_title")
                .in_("icd_code", chunk).execute().data or []
            )
            for r in rows:
                self._icd[(kind, str(r["icd_code"]), int(r["icd_version"]))] = r.get("long_title")
        for key in missing:
            self._icd.setdefault((kind, *key), None)
        return {key: self._icd.get((kind, *key)) for key in wanted}
