"""
Prueba rápida del sistema RAG — verifica que el agente invoca search_clinical_documents
y recupera contexto real de los documentos indexados.

Usa 4 preguntas representativas del golden set RAG.
No requiere RAGAS — solo verifica invocación de herramienta y presencia de contexto.

Uso:
    python -m scripts.test_rag_quick
"""
import logging
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.WARNING,  # Silenciar logs del agente para output limpio
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Preguntas representativas del golden set RAG (una por tipo)
TEST_CASES = [
    {
        "id": "GS-RAG-01",
        "tipo": "directa",
        "pregunta": "¿Cuántas camas tiene en total la UGC de Medicina Intensiva del Hospital Virgen del Rocío?",
        "fragmento_esperado": "84",  # Dato exacto del documento
    },
    {
        "id": "GS-RAG-12",
        "tipo": "directa",
        "pregunta": "¿Cuál es la ratio médico-paciente recomendada en una UCI de nivel asistencial III durante el turno de día?",
        "fragmento_esperado": "4-5",  # "1 médico por cada 4-5 pacientes"
    },
    {
        "id": "GS-RAG-21",
        "tipo": "directa",
        "pregunta": "¿Cuál es la tasa normal de excreción de ácido a través de los pulmones según el Libro de la UCI de Marino?",
        "fragmento_esperado": "9 mEq/min",
    },
    {
        "id": "GS-RAG-11",
        "tipo": "estadistica",
        "pregunta": "¿Qué porcentaje de pacientes presentó algún incidente en el estudio SEMICYUC realizado en 79 UCI?",
        "fragmento_esperado": "58",  # 58.1%
    },
]

SEP = "─" * 70


def run_test(agent, case: dict) -> dict:
    """Ejecuta una pregunta y evalúa si el agente usó RAG y recuperó contexto."""
    pregunta = case["pregunta"]
    fragmento = case["fragmento_esperado"]

    response = agent.process_message(
        pregunta,
        context=None,
        session_id=f"test-rag-{case['id']}",
    )

    content = response.get("content", "")
    tools_used = response.get("tools_used", [])
    sources = response.get("sources", [])
    tool_results = response.get("tool_results", [])

    # ¿Invocó search_clinical_documents?
    used_rag = any("search_clinical_documents" in t for t in tools_used)

    # ¿Hay contexto recuperado (sources o tool_results con contenido)?
    has_context = bool(sources) or bool(tool_results)

    # ¿La respuesta contiene el fragmento esperado?
    contains_expected = fragmento.lower() in content.lower()

    return {
        "id": case["id"],
        "tipo": case["tipo"],
        "pregunta": pregunta[:70] + "...",
        "used_rag": used_rag,
        "has_context": has_context,
        "contains_expected": contains_expected,
        "fragmento_esperado": fragmento,
        "respuesta_preview": content[:200].replace("\n", " "),
        "tools_used": tools_used,
        "n_sources": len(sources),
    }


def main() -> int:
    print(SEP)
    print("  PRUEBA RÁPIDA — Sistema RAG (4 preguntas del golden set)")
    print(SEP)

    # Inicializar agente
    print("\n  Inicializando agente...")
    try:
        from services.unified_chat.unified_agent import UnifiedChatAgent
        agent = UnifiedChatAgent()
        print("  ✅ Agente inicializado\n")
    except Exception as e:
        print(f"  ❌ Error inicializando agente: {e}")
        return 1

    results = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"  [{i}/{len(TEST_CASES)}] {case['id']} ({case['tipo']})")
        print(f"  Pregunta: {case['pregunta'][:70]}...")
        try:
            result = run_test(agent, case)
            results.append(result)

            rag_icon  = "✅" if result["used_rag"]          else "❌"
            ctx_icon  = "✅" if result["has_context"]        else "❌"
            ans_icon  = "✅" if result["contains_expected"]  else "⚠️ "

            print(f"  {rag_icon} Invocó search_clinical_documents: {result['used_rag']}")
            print(f"  {ctx_icon} Contexto recuperado:              {result['has_context']} ({result['n_sources']} fuentes)")
            print(f"  {ans_icon} Contiene '{result['fragmento_esperado']}':  {result['contains_expected']}")
            print(f"  Herramientas usadas: {result['tools_used']}")
            print(f"  Respuesta: {result['respuesta_preview'][:120]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"id": case["id"], "used_rag": False, "has_context": False,
                            "contains_expected": False, "error": str(e)})
        print()

    # Resumen
    print(SEP)
    print("  RESUMEN")
    print(SEP)
    n = len(results)
    n_rag     = sum(1 for r in results if r.get("used_rag"))
    n_ctx     = sum(1 for r in results if r.get("has_context"))
    n_ans     = sum(1 for r in results if r.get("contains_expected"))

    print(f"  Invocó search_clinical_documents: {n_rag}/{n}")
    print(f"  Recuperó contexto de documentos:  {n_ctx}/{n}")
    print(f"  Respuesta contiene dato esperado: {n_ans}/{n}")
    print()

    if n_rag == n:
        print("  ✅ El agente usa RAG en todos los casos — las métricas DEBERÍAN mejorar.")
    elif n_rag >= n // 2:
        print("  ⚠️  El agente usa RAG en algunos casos — mejora parcial esperada.")
    else:
        print("  ❌ El agente NO está usando RAG — revisar el system prompt.")

    print(SEP)
    return 0 if n_rag == n else 1


if __name__ == "__main__":
    sys.exit(main())
