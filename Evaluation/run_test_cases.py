"""
Functional Test Cases Script for ChatHCE.

Executes 28 categorized functional test cases against the UnifiedChatAgent:
  - 10 TC-DB  (database queries)
  - 8  TC-RAG (document retrieval)
  - 5  TC-VIZ (visualizations)
  - 5  TC-AGENT (agent behavior)

Each test case is scored on weighted criteria (0.0-1.0 per criterion).
Weighted aggregate score = sum(w_i * s_i) / sum(w_i).
A test passes when weighted_score >= score_minimo.

Results are written to a human-readable TXT file in the output directory.

Usage:
    python evaluation/run_test_cases.py --output evaluation/results/
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from Evaluation.eval_helpers import (
    generate_result_filename,
    instantiate_agent,
    write_txt_conclusions,
    write_txt_header,
    write_txt_summary,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FunctionalTestCase:
    """Definition of a single functional test case.

    Attributes:
        test_id: Unique identifier (e.g. 'TC-DB-001').
        category: Category string ('TC-DB', 'TC-RAG', 'TC-VIZ', 'TC-AGENT').
        description: Human-readable description of what is being tested.
        query: The natural-language query sent to the agent.
        expected_tool: Name of the tool expected to be invoked.
        criteria_weights: Mapping of criterion name to its weight.
        score_minimo: Minimum weighted score required to pass (0.0-1.0).
        verification_data: Expected values used to score criteria.
    """

    test_id: str
    category: str
    description: str
    query: str
    expected_tool: str
    criteria_weights: Dict[str, float]
    score_minimo: float
    verification_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionalTestResult:
    """Result of executing a single functional test case.

    Attributes:
        test_id: Identifier matching the test case.
        category: Category of the test case.
        query: Query that was sent to the agent.
        criteria_scores: Per-criterion scores (0.0-1.0).
        weighted_score: Aggregate weighted score.
        passed: True if weighted_score >= score_minimo.
        error: Exception message if the agent raised an error, else None.
    """

    test_id: str
    category: str
    query: str
    criteria_scores: Dict[str, float]
    weighted_score: float
    passed: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# TC-DB test cases (10)
# ---------------------------------------------------------------------------

TC_DB_CASES: List[FunctionalTestCase] = [
    FunctionalTestCase(
        test_id="TC-DB-001",
        category="TC-DB",
        description="Patient summary retrieval for subject_id 10014729",
        query="Dame un resumen completo del paciente 10014729 incluyendo estancia, género y disposición.",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.40,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-002",
        category="TC-DB",
        description="Vital signs query for subject_id 10018328",
        query="¿Cuáles son los signos vitales del paciente 10018328?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.40,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10018328"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-003",
        category="TC-DB",
        description="Diagnosis lookup for subject_id 10026255",
        query="¿Cuáles son los diagnósticos del paciente 10026255?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.40,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10026255"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-004",
        category="TC-DB",
        description="Medication listing for subject_id 10014729",
        query="Lista todos los medicamentos administrados al paciente 10014729 en urgencias.",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.40,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-005",
        category="TC-DB",
        description="Triage data for subject_id 10015272",
        query="¿Cuáles fueron los datos de triaje del paciente 10015272?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.40,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10015272"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-006",
        category="TC-DB",
        description="Cross-table join: edstays + diagnosis",
        query=(
            "Muestra las estancias del paciente 10014729 junto con sus diagnósticos ICD. "
            "Necesito ver la información combinada de edstays y diagnosis."
        ),
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.35,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-007",
        category="TC-DB",
        description="Temporal query: vitalsign ordered by charttime",
        query=(
            "Muestra la evolución temporal de los signos vitales del paciente 10014729, "
            "ordenados por hora de registro."
        ),
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.35,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-008",
        category="TC-DB",
        description="Aggregate statistics: COUNT diagnoses",
        query="¿Cuántos diagnósticos distintos hay en total en la base de datos MIMIC-IV-ED?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.35,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": [],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-009",
        category="TC-DB",
        description="Null edge case: patient with no vitals recorded",
        query="¿Tiene el paciente 10019003 registros de signos vitales durante su estancia?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.30,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": [],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-DB-010",
        category="TC-DB",
        description="Multi-patient comparison",
        query=(
            "Compara los niveles de acuidad de triaje de los pacientes 10014729 y 10018328. "
            "¿Cuál tuvo mayor urgencia?"
        ),
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.35,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": ["10014729", "10018328"],
            "expected_tool": "query_mimic_database",
        },
    ),
]

# ---------------------------------------------------------------------------
# TC-RAG test cases (8)
# ---------------------------------------------------------------------------

TC_RAG_CASES: List[FunctionalTestCase] = [
    FunctionalTestCase(
        test_id="TC-RAG-001",
        category="TC-RAG",
        description="Clinical protocol search: sepsis",
        query="¿Cuál es el protocolo de manejo de sepsis en urgencias?",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["sepsis"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-002",
        category="TC-RAG",
        description="Medication guideline: vancomycin",
        query="¿Cuáles son las guías de dosificación de vancomicina en urgencias?",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["vancomicina", "vancomycin"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-003",
        category="TC-RAG",
        description="Emergency procedure query",
        query="¿Cuál es el procedimiento de intubación de secuencia rápida en urgencias?",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["intubación", "secuencia rápida"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-004",
        category="TC-RAG",
        description="Multi-document synthesis",
        query=(
            "Resume los protocolos de manejo del dolor en urgencias, "
            "incluyendo analgesia y sedación."
        ),
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.15,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["dolor", "analgesia"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-005",
        category="TC-RAG",
        description="Specialty-filtered search",
        query="¿Qué dice el protocolo de cardiología sobre el manejo del infarto agudo de miocardio?",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["infarto", "miocardio"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-006",
        category="TC-RAG",
        description="Source citation verification",
        query="¿Cuáles son las guías de manejo de la hipertensión arterial en urgencias? Cita las fuentes.",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.20,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.15,
            "fuentes_citadas": 0.20,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["hipertensión"],
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-007",
        category="TC-RAG",
        description="Out-of-domain question handling",
        query="¿Cuál es la receta del gazpacho andaluz?",
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.20,
            "herramienta_correcta": 0.20,
            "no_alucinacion": 0.40,
            "formato_respuesta": 0.20,
        },
        score_minimo=0.50,
        verification_data={
            "expected_values": [],
            "out_of_domain": True,
            "expected_tool": "search_clinical_documents",
        },
    ),
    FunctionalTestCase(
        test_id="TC-RAG-008",
        category="TC-RAG",
        description="Spanish medical terminology query",
        query=(
            "¿Qué es la taquicardia supraventricular paroxística y cómo se maneja "
            "en el servicio de urgencias?"
        ),
        expected_tool="search_clinical_documents",
        criteria_weights={
            "contiene_valor": 0.30,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["taquicardia", "supraventricular"],
            "expected_tool": "search_clinical_documents",
        },
    ),
]

# ---------------------------------------------------------------------------
# TC-VIZ test cases (5)
# ---------------------------------------------------------------------------

TC_VIZ_CASES: List[FunctionalTestCase] = [
    FunctionalTestCase(
        test_id="TC-VIZ-001",
        category="TC-VIZ",
        description="Vital signs timeline for patient 10014729",
        query=(
            "Genera una gráfica de líneas con la evolución temporal de los signos vitales "
            "(frecuencia cardíaca y presión arterial) del paciente 10014729."
        ),
        expected_tool="generate_visualization",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.35,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "generate_visualization",
        },
    ),
    FunctionalTestCase(
        test_id="TC-VIZ-002",
        category="TC-VIZ",
        description="Diagnosis distribution bar chart",
        query=(
            "Crea un gráfico de barras con los 10 diagnósticos más frecuentes "
            "en el dataset MIMIC-IV-ED."
        ),
        expected_tool="generate_visualization",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.35,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": [],
            "expected_tool": "generate_visualization",
        },
    ),
    FunctionalTestCase(
        test_id="TC-VIZ-003",
        category="TC-VIZ",
        description="Medication frequency chart",
        query=(
            "Genera una visualización de los medicamentos más administrados en urgencias, "
            "mostrando la frecuencia de cada uno."
        ),
        expected_tool="generate_visualization",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.35,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": [],
            "expected_tool": "generate_visualization",
        },
    ),
    FunctionalTestCase(
        test_id="TC-VIZ-004",
        category="TC-VIZ",
        description="Multi-metric comparison chart",
        query=(
            "Crea una gráfica comparando la presión arterial sistólica, diastólica "
            "y la frecuencia cardíaca del paciente 10014729 a lo largo del tiempo."
        ),
        expected_tool="generate_visualization",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.35,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "generate_visualization",
        },
    ),
    FunctionalTestCase(
        test_id="TC-VIZ-005",
        category="TC-VIZ",
        description="Custom visualization request",
        query=(
            "Genera un histograma de la distribución de los niveles de acuidad de triaje "
            "en todos los pacientes del dataset."
        ),
        expected_tool="generate_visualization",
        criteria_weights={
            "contiene_valor": 0.20,
            "herramienta_correcta": 0.40,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": [],
            "expected_tool": "generate_visualization",
        },
    ),
]

# ---------------------------------------------------------------------------
# TC-AGENT test cases (5)
# ---------------------------------------------------------------------------

TC_AGENT_CASES: List[FunctionalTestCase] = [
    FunctionalTestCase(
        test_id="TC-AGENT-001",
        category="TC-AGENT",
        description="Automatic tool selection based on query intent",
        query="¿Cuántas estancias hay registradas en urgencias en total?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.40,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
        },
        score_minimo=0.60,
        verification_data={
            "expected_values": [],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-AGENT-002",
        category="TC-AGENT",
        description="Multi-tool orchestration: database + RAG",
        query=(
            "Analiza los signos vitales del paciente 10014729 y compáralos con "
            "los valores normales según los protocolos clínicos."
        ),
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.25,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.25,
            "formato_respuesta": 0.10,
            "fuentes_citadas": 0.10,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-AGENT-003",
        category="TC-AGENT",
        description="Context maintenance across conversation turns",
        query=(
            "El paciente del que hablamos antes, ¿cuáles son sus diagnósticos? "
            "(Contexto: paciente 10014729 mencionado previamente)"
        ),
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.20,
            "herramienta_correcta": 0.30,
            "no_alucinacion": 0.30,
            "formato_respuesta": 0.20,
        },
        score_minimo=0.50,
        verification_data={
            "expected_values": [],
            "expected_tool": "query_mimic_database",
        },
    ),
    FunctionalTestCase(
        test_id="TC-AGENT-004",
        category="TC-AGENT",
        description="Error recovery: graceful handling of invalid patient ID",
        query="Dame los datos del paciente 99999999.",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.20,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.40,
            "formato_respuesta": 0.15,
        },
        score_minimo=0.50,
        verification_data={
            "expected_values": [],
            "expected_tool": "query_mimic_database",
            "expect_no_data": True,
        },
    ),
    FunctionalTestCase(
        test_id="TC-AGENT-005",
        category="TC-AGENT",
        description="Response language consistency: always Spanish",
        query="What are the vital signs of patient 10014729?",
        expected_tool="query_mimic_database",
        criteria_weights={
            "contiene_valor": 0.20,
            "herramienta_correcta": 0.25,
            "no_alucinacion": 0.20,
            "formato_respuesta": 0.35,
        },
        score_minimo=0.55,
        verification_data={
            "expected_values": ["10014729"],
            "expected_tool": "query_mimic_database",
            "expect_spanish": True,
        },
    ),
]

# ---------------------------------------------------------------------------
# All test cases combined
# ---------------------------------------------------------------------------

ALL_TEST_CASES: List[FunctionalTestCase] = (
    TC_DB_CASES + TC_RAG_CASES + TC_VIZ_CASES + TC_AGENT_CASES
)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

# Spanish language indicator words used to detect Spanish responses
_SPANISH_INDICATORS = [
    "el ", "la ", "los ", "las ", "de ", "del ", "en ", "con ", "que ",
    "para ", "por ", "una ", "uno ", "es ", "son ", "tiene ", "hay ",
    "paciente", "datos", "signos", "vitales", "diagnóstico",
]

# Hallucination indicator phrases (fabricated data signals)
_HALLUCINATION_INDICATORS = [
    "inventé", "inventado", "ficticio", "fabricado", "supongo",
    "asumo que", "probablemente tiene", "debe tener",
]


def score_contiene_valor(
    response: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> float:
    """Score whether the response contains expected values.

    Args:
        response: Agent response dict.
        verification_data: Test case verification_data dict.

    Returns:
        1.0 if all expected values are found, partial score otherwise.
    """
    expected_values: List[str] = verification_data.get("expected_values", [])
    if not expected_values:
        # No specific values to check — give partial credit if response has content
        content = response.get("content", "")
        return 0.7 if len(content) > 50 else 0.3

    content = response.get("content", "").lower()
    found = sum(1 for val in expected_values if str(val).lower() in content)
    return found / len(expected_values) if expected_values else 1.0


def score_herramienta_correcta(
    response: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> float:
    """Score whether the correct tool was used.

    Checks the ``tools_used`` list in the agent response against the expected tool.

    Args:
        response: Agent response dict.
        verification_data: Test case verification_data dict.

    Returns:
        1.0 if expected tool is found in tools_used, 0.0 otherwise.
    """
    expected_tool: str = verification_data.get("expected_tool", "")
    if not expected_tool:
        return 1.0

    tools_used: List[str] = response.get("tools_used", [])
    if not tools_used:
        return 0.0

    # Partial match: check if any tool name contains the expected tool substring
    for tool in tools_used:
        if expected_tool.lower() in tool.lower() or tool.lower() in expected_tool.lower():
            return 1.0
    return 0.0


def score_no_alucinacion(
    response: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> float:
    """Score whether the response avoids hallucinated data.

    Args:
        response: Agent response dict.
        verification_data: Test case verification_data dict.

    Returns:
        1.0 if no hallucination indicators found, 0.0 otherwise.
    """
    content = response.get("content", "").lower()

    # Check for explicit hallucination indicators
    if any(ind in content for ind in _HALLUCINATION_INDICATORS):
        return 0.0

    # For out-of-domain queries, check that agent acknowledges limitation
    if verification_data.get("out_of_domain"):
        no_data_phrases = [
            "no encontré", "no tengo", "no disponible", "fuera de mi",
            "no está en", "no puedo", "no hay información",
        ]
        if any(phrase in content for phrase in no_data_phrases):
            return 1.0
        return 0.5

    # For expect_no_data cases, verify agent doesn't fabricate
    if verification_data.get("expect_no_data"):
        no_data_phrases = [
            "no encontré", "no existe", "no hay datos", "no disponible",
            "no se encontró", "no tengo información",
        ]
        if any(phrase in content for phrase in no_data_phrases):
            return 1.0
        # If agent returned data for a non-existent patient, penalize
        if "99999999" in content and len(content) > 200:
            return 0.2
        return 0.7

    return 1.0


def score_formato_respuesta(
    response: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> float:
    """Score whether the response is in Spanish and well formatted.

    Args:
        response: Agent response dict.
        verification_data: Test case verification_data dict.

    Returns:
        Score between 0.0 and 1.0.
    """
    content = response.get("content", "")
    if not content or len(content) < 20:
        return 0.0

    content_lower = content.lower()
    score = 0.0

    # Check Spanish language indicators
    spanish_count = sum(1 for ind in _SPANISH_INDICATORS if ind in content_lower)
    if spanish_count >= 5:
        score += 0.6
    elif spanish_count >= 2:
        score += 0.3

    # Check for expect_spanish flag
    if verification_data.get("expect_spanish"):
        if spanish_count >= 3:
            score = min(score + 0.4, 1.0)
        else:
            score = max(score - 0.3, 0.0)

    # Check for reasonable length (not too short, not just an error)
    if len(content) > 100:
        score = min(score + 0.2, 1.0)
    if len(content) > 300:
        score = min(score + 0.2, 1.0)

    return min(score, 1.0)


def score_fuentes_citadas(
    response: Dict[str, Any],
    verification_data: Dict[str, Any],
) -> float:
    """Score whether sources are cited in the response (for RAG tests).

    Args:
        response: Agent response dict.
        verification_data: Test case verification_data dict.

    Returns:
        1.0 if sources are cited, 0.5 if sources list is non-empty, 0.0 otherwise.
    """
    # Check sources list in response
    sources: List[Any] = response.get("sources", [])
    if sources:
        return 1.0

    # Check content for citation indicators
    content = response.get("content", "").lower()
    citation_indicators = [
        "fuente:", "según", "de acuerdo con", "protocolo", "guía",
        "documento", "referencia", "fuentes:", "basado en",
    ]
    if any(ind in content for ind in citation_indicators):
        return 0.7

    return 0.0

# ---------------------------------------------------------------------------
# Weighted scoring computation
# ---------------------------------------------------------------------------

# Mapping of criterion name to scoring function
_CRITERION_SCORERS = {
    "contiene_valor": score_contiene_valor,
    "herramienta_correcta": score_herramienta_correcta,
    "no_alucinacion": score_no_alucinacion,
    "formato_respuesta": score_formato_respuesta,
    "fuentes_citadas": score_fuentes_citadas,
}


def compute_weighted_score(
    criteria_scores: Dict[str, float],
    criteria_weights: Dict[str, float],
) -> float:
    """Compute the weighted aggregate score for a test case.

    Formula: sum(w_i * s_i) / sum(w_i)

    Args:
        criteria_scores: Mapping of criterion name to score (0.0-1.0).
        criteria_weights: Mapping of criterion name to weight.

    Returns:
        Weighted aggregate score between 0.0 and 1.0.
    """
    total_weight = sum(criteria_weights.values())
    if total_weight == 0.0:
        return 0.0

    weighted_sum = sum(
        criteria_weights.get(criterion, 0.0) * score
        for criterion, score in criteria_scores.items()
    )
    return weighted_sum / total_weight


def score_test_case(
    test_case: FunctionalTestCase,
    response: Dict[str, Any],
) -> Dict[str, float]:
    """Score all criteria for a test case against the agent response.

    Args:
        test_case: The functional test case definition.
        response: Agent response dict.

    Returns:
        Dict mapping criterion name to score (0.0-1.0).
    """
    criteria_scores: Dict[str, float] = {}
    for criterion in test_case.criteria_weights:
        scorer = _CRITERION_SCORERS.get(criterion)
        if scorer is None:
            logger.warning("Unknown criterion '%s' in test %s", criterion, test_case.test_id)
            criteria_scores[criterion] = 0.0
        else:
            criteria_scores[criterion] = scorer(response, test_case.verification_data)
    return criteria_scores


# ---------------------------------------------------------------------------
# Test execution
# ---------------------------------------------------------------------------

def run_test_case(
    agent: Any,
    test_case: FunctionalTestCase,
) -> FunctionalTestResult:
    """Execute a single functional test case and return the result.

    Args:
        agent: An instantiated ``UnifiedChatAgent``.
        test_case: The test case to execute.

    Returns:
        A :class:`FunctionalTestResult` with scores and pass/fail status.
    """
    logger.info(
        "Running %s [%s]: %s",
        test_case.test_id,
        test_case.category,
        test_case.description,
    )

    try:
        response = agent.process_message(
            test_case.query,
            context=None,
            session_id=f"eval-func-{test_case.test_id}",
        )
        if not isinstance(response, dict):
            response = {"content": str(response), "tools_used": [], "sources": []}

        criteria_scores = score_test_case(test_case, response)
        weighted_score = compute_weighted_score(criteria_scores, test_case.criteria_weights)
        passed = weighted_score >= test_case.score_minimo

        status = "PASS" if passed else "FAIL"
        logger.info(
            "  %s → %s (score=%.3f, minimo=%.2f)",
            test_case.test_id,
            status,
            weighted_score,
            test_case.score_minimo,
        )

        return FunctionalTestResult(
            test_id=test_case.test_id,
            category=test_case.category,
            query=test_case.query,
            criteria_scores=criteria_scores,
            weighted_score=weighted_score,
            passed=passed,
            error=None,
        )

    except Exception as exc:
        logger.error("  %s → ERROR: %s", test_case.test_id, exc)
        # Assign score 0.0 on exception and continue
        zero_scores = {criterion: 0.0 for criterion in test_case.criteria_weights}
        return FunctionalTestResult(
            test_id=test_case.test_id,
            category=test_case.category,
            query=test_case.query,
            criteria_scores=zero_scores,
            weighted_score=0.0,
            passed=False,
            error=str(exc),
        )


def run_all_test_cases(
    agent: Any,
    test_cases: List[FunctionalTestCase],
) -> List[FunctionalTestResult]:
    """Execute all functional test cases and return results.

    Args:
        agent: An instantiated ``UnifiedChatAgent``.
        test_cases: List of test case definitions to execute.

    Returns:
        List of :class:`FunctionalTestResult`, one per test case.
    """
    results: List[FunctionalTestResult] = []
    for test_case in test_cases:
        result = run_test_case(agent, test_case)
        results.append(result)
    return results

# ---------------------------------------------------------------------------
# TXT output
# ---------------------------------------------------------------------------

# Category display order and labels
_CATEGORY_ORDER = ["TC-DB", "TC-RAG", "TC-VIZ", "TC-AGENT"]
_CATEGORY_THRESHOLD = 0.7  # Pass threshold for category-level summary


def write_results_txt(
    output_path: str,
    results: List[FunctionalTestResult],
    test_cases: List[FunctionalTestCase],
    start_time: datetime,
    duration_seconds: float,
) -> None:
    """Write the full functional test results to a TXT file.

    Args:
        output_path: Full path to the output TXT file.
        results: List of result objects from run_all_test_cases().
        test_cases: Original test case definitions (for score_minimo lookup).
        start_time: Test run start datetime.
        duration_seconds: Total elapsed seconds.
    """
    error_count = sum(1 for r in results if r.error is not None)
    total_items = len(results)

    # Build a lookup for score_minimo by test_id
    minimo_by_id: Dict[str, float] = {tc.test_id: tc.score_minimo for tc in test_cases}

    with open(output_path, "w", encoding="utf-8") as f:
        write_txt_header(f, "FUNCTIONAL TEST CASES", golden_set_path=None)

        # ---- Per-test results section ----
        f.write("-" * 80 + "\n")
        f.write("RESULTS — PER TEST CASE\n")
        f.write("-" * 80 + "\n\n")

        for category in _CATEGORY_ORDER:
            cat_results = [r for r in results if r.category == category]
            if not cat_results:
                continue

            f.write(f"  Category: {category}\n")
            f.write(f"  {'-' * 76}\n")

            # Header row
            f.write(
                f"  {'Test ID':<16} | {'Score':>6} | {'Minimo':>6} | "
                f"{'Status':<6} | Criteria Scores\n"
            )
            f.write(
                f"  {'-' * 16}-+-{'-' * 6}-+-{'-' * 6}-+-{'-' * 6}-+-{'-' * 30}\n"
            )

            for r in cat_results:
                status = "PASS" if r.passed else "FAIL"
                minimo = minimo_by_id.get(r.test_id, 0.0)
                criteria_str = ", ".join(
                    f"{k}={v:.2f}" for k, v in r.criteria_scores.items()
                )
                f.write(
                    f"  {r.test_id:<16} | {r.weighted_score:>6.3f} | {minimo:>6.2f} | "
                    f"{status:<6} | {criteria_str}\n"
                )
                if r.error:
                    f.write(f"  {'':16}   ERROR: {r.error[:80]}\n")

            f.write("\n")

        # ---- Summary section (one row per category) ----
        summary_data: List[Dict[str, Any]] = []
        for category in _CATEGORY_ORDER:
            cat_results = [r for r in results if r.category == category]
            if not cat_results:
                continue
            passed_count = sum(1 for r in cat_results if r.passed)
            total_count = len(cat_results)
            score_ratio = passed_count / total_count if total_count > 0 else 0.0
            summary_data.append({
                "name": category,
                "score": score_ratio,
                "threshold": _CATEGORY_THRESHOLD,
                "status": "PASS" if score_ratio >= _CATEGORY_THRESHOLD else "FAIL",
            })

        write_txt_summary(f, summary_data)

        # ---- Conclusions section ----
        total_passed = sum(1 for r in results if r.passed)
        pass_cats = [d["name"] for d in summary_data if d["status"] == "PASS"]
        fail_cats = [d["name"] for d in summary_data if d["status"] == "FAIL"]
        overall = "PASS" if not fail_cats else "FAIL"

        conclusions_parts = [
            f"Overall result: {overall} ({total_passed}/{total_items} test cases passed).",
        ]
        if fail_cats:
            conclusions_parts.append(
                f"Categories below threshold ({_CATEGORY_THRESHOLD:.0%}): "
                f"{', '.join(fail_cats)}. "
                "Review agent tool selection and response quality for these categories."
            )
        if pass_cats:
            conclusions_parts.append(
                f"Categories meeting threshold: {', '.join(pass_cats)}."
            )
        if error_count > 0:
            conclusions_parts.append(
                f"{error_count} test case(s) raised exceptions during execution."
            )

        write_txt_conclusions(
            f,
            conclusions_text=" ".join(conclusions_parts),
            duration_seconds=duration_seconds,
            total_items=total_items,
            error_count=error_count,
        )

    logger.info("Results written to: %s", output_path)


# ---------------------------------------------------------------------------
# Summary to stdout
# ---------------------------------------------------------------------------

def print_summary(results: List[FunctionalTestResult]) -> None:
    """Print a summary of functional test results to stdout.

    Args:
        results: List of result objects from run_all_test_cases().
    """
    sep = "-" * 70
    print(sep)
    print("  FUNCTIONAL TEST CASES SUMMARY")
    print(sep)
    print(
        f"  {'Category':<12} | {'Passed':>6} | {'Total':>5} | "
        f"{'Score':>6} | {'Threshold':>9} | Status"
    )
    print(
        f"  {'-' * 12}-+-{'-' * 6}-+-{'-' * 5}-+-{'-' * 6}-+-{'-' * 9}-+-------"
    )

    overall_pass = True
    for category in _CATEGORY_ORDER:
        cat_results = [r for r in results if r.category == category]
        if not cat_results:
            continue
        passed = sum(1 for r in cat_results if r.passed)
        total = len(cat_results)
        score = passed / total if total > 0 else 0.0
        status = "PASS" if score >= _CATEGORY_THRESHOLD else "FAIL"
        if status == "FAIL":
            overall_pass = False
        print(
            f"  {category:<12} | {passed:>6} | {total:>5} | "
            f"{score:>6.2f} | {_CATEGORY_THRESHOLD:>9.2f} | {status}"
        )

    total_passed = sum(1 for r in results if r.passed)
    total_all = len(results)
    overall_label = "PASS" if overall_pass else "FAIL"
    print(f"\n  Overall: {overall_label} ({total_passed}/{total_all} test cases passed)")
    print(sep)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional list of argument strings (defaults to sys.argv).

    Returns:
        Parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        description="Run functional test cases on ChatHCE UnifiedChatAgent.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        default="evaluation/results/",
        help="Output directory for the results TXT file.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the functional test cases script.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Exit code: 0 on success, 1 on fatal error.
    """
    args = parse_args(argv)

    logger.info(
        "Starting functional test cases: %d total (%d TC-DB, %d TC-RAG, "
        "%d TC-VIZ, %d TC-AGENT)",
        len(ALL_TEST_CASES),
        len(TC_DB_CASES),
        len(TC_RAG_CASES),
        len(TC_VIZ_CASES),
        len(TC_AGENT_CASES),
    )

    # ---- Ensure output directory exists ----
    os.makedirs(args.output, exist_ok=True)

    # ---- Instantiate agent ----
    try:
        agent = instantiate_agent()
    except Exception as exc:
        logger.error("Failed to instantiate UnifiedChatAgent: %s", exc)
        return 1

    # ---- Run all test cases ----
    start_time = datetime.now()
    results: List[FunctionalTestResult] = []
    try:
        results = run_all_test_cases(agent, ALL_TEST_CASES)
    except Exception as exc:
        logger.error("Unexpected error during test execution: %s", exc)
    finally:
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        # ---- Write results TXT (always, even on partial results) ----
        filename = generate_result_filename("test_cases")
        output_path = os.path.join(args.output, filename)
        try:
            write_results_txt(
                output_path=output_path,
                results=results,
                test_cases=ALL_TEST_CASES,
                start_time=start_time,
                duration_seconds=duration_seconds,
            )
        except Exception as write_exc:
            logger.error("Failed to write results TXT: %s", write_exc)

    # ---- Print summary to stdout ----
    if results:
        print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
