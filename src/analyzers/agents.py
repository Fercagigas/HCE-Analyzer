
"""
Sistema de agentes multi-modelo para HCE Analyzer con capacidades RAG
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import os
from groq import Groq
from config.config import MODEL_CONFIG, RATE_LIMITS
from services.rag_service import RAGService
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    """Gestor de modelos con sistema de cascada y fallback"""
    
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY no configurada. Verifica tu archivo .env")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.models = MODEL_CONFIG["models"]
        self.current_model_index = 0
        self.model_errors = {}
        self.last_reset = datetime.now()
        
    def get_current_model(self) -> str:
        """Obtiene el modelo actual disponible"""
        # Resetear errores cada hora
        if datetime.now() - self.last_reset > timedelta(hours=1):
            self.model_errors = {}
            self.current_model_index = 0
            self.last_reset = datetime.now()
            
        return self.models[self.current_model_index]
    
    def mark_model_error(self, model: str, error: str):
        """Marca un modelo como problemático"""
        self.model_errors[model] = {
            'error': error,
            'timestamp': datetime.now()
        }
        
        # Avanzar al siguiente modelo
        if self.current_model_index < len(self.models) - 1:
            self.current_model_index += 1
            logger.warning(f"Cambiando al modelo: {self.get_current_model()}")
    
    def generate_response(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[bool, str]:
        """Genera respuesta usando el modelo actual con fallback"""
        max_retries = len(self.models)
        
        for attempt in range(max_retries):
            current_model = self.get_current_model()
            
            try:
                logger.info(f"Intentando con modelo: {current_model}")
                
                response = self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=MODEL_CONFIG["max_tokens"],
                    top_p=MODEL_CONFIG["top_p"]
                )
                
                content = response.choices[0].message.content
                logger.info(f"Respuesta exitosa con modelo: {current_model}")
                return True, content
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error con modelo {current_model}: {error_msg}")
                self.mark_model_error(current_model, error_msg)
                
                if attempt == max_retries - 1:
                    return False, f"Error en todos los modelos. Último error: {error_msg}"
                    
                time.sleep(1)  # Pausa antes del siguiente intento
        
        return False, "No se pudo generar respuesta con ningún modelo"

class AnalysisAgent:
    """Agente especializado en análisis de historias clínicas"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.rag_service = RAGService()
        self.daily_usage = {}
        self.learning_context = []
        
    def check_rate_limit(self, user_id: str) -> Tuple[bool, int]:
        """Verifica límites de uso diario"""
        today = datetime.now().date()
        user_key = f"{user_id}_{today}"
        
        current_usage = self.daily_usage.get(user_key, 0)
        limit = RATE_LIMITS["daily_analyses"]
        
        if current_usage >= limit:
            return False, 0
            
        return True, limit - current_usage
    
    def increment_usage(self, user_id: str):
        """Incrementa el contador de uso diario"""
        today = datetime.now().date()
        user_key = f"{user_id}_{today}"
        self.daily_usage[user_key] = self.daily_usage.get(user_key, 0) + 1
    
    def add_to_learning_context(self, analysis_type: str, result: str):
        """Añade resultado al contexto de aprendizaje"""
        self.learning_context.append({
            'type': analysis_type,
            'result': result,
            'timestamp': datetime.now()
        })
        
        # Mantener solo los últimos 10 análisis
        if len(self.learning_context) > 10:
            self.learning_context.pop(0)
    
    def get_enhanced_prompt(self, analysis_type: str, data: str) -> str:
        """Genera prompt mejorado con contexto clínico"""
        base_prompt = self._get_base_prompt(analysis_type)
        
        # Añadir contexto de aprendizaje
        context = ""
        if self.learning_context:
            context = "\n\nContexto de análisis previos:\n"
            for item in self.learning_context[-3:]:  # Últimos 3
                context += f"- {item['type']}: {item['result'][:100]}...\n"
        
        # Intentar obtener contexto RAG relevante
        rag_context = ""
        try:
            rag_results = self.rag_service.search_clinical_guidelines(
                f"análisis {analysis_type} interpretación clínica"
            )
            if rag_results:
                rag_context = "\n\nGuías clínicas relevantes:\n"
                for result in rag_results[:2]:  # Top 2 resultados
                    rag_context += f"- {result['content'][:200]}...\n"
        except Exception as e:
            logger.warning(f"Error obteniendo contexto RAG: {e}")
        
        return f"{base_prompt}{context}{rag_context}\n\nDatos a analizar:\n{data}"
    
    def _get_base_prompt(self, analysis_type: str) -> str:
        """Obtiene el prompt base según el tipo de análisis"""
        prompts = {
            "blood_test": """
Eres un especialista médico experto en interpretación de análisis de sangre. 
Analiza los siguientes resultados y proporciona:

1. **Resumen Ejecutivo**: Interpretación general del estado de salud
2. **Análisis Detallado**: Explicación de cada parámetro fuera de rango
3. **Posibles Diagnósticos**: Condiciones que podrían explicar los resultados
4. **Recomendaciones**: Acciones sugeridas y seguimiento
5. **Urgencia**: Nivel de prioridad médica (Baja/Media/Alta/Crítica)

Usa terminología médica precisa pero incluye explicaciones comprensibles.
""",
            "general_report": """
Eres un médico especialista en análisis de reportes médicos. 
Analiza el siguiente reporte y proporciona:

1. **Interpretación Clínica**: Significado médico de los hallazgos
2. **Correlación de Síntomas**: Relación entre hallazgos y síntomas
3. **Diagnóstico Diferencial**: Posibles diagnósticos a considerar
4. **Plan de Manejo**: Recomendaciones terapéuticas y seguimiento
5. **Pronóstico**: Expectativas de evolución

Mantén un enfoque clínico riguroso y basado en evidencia.
""",
            "imaging": """
Eres un radiólogo especialista en interpretación de estudios de imagen.
Analiza el siguiente reporte y proporciona:

1. **Hallazgos Principales**: Descripción de anomalías encontradas
2. **Interpretación Radiológica**: Significado clínico de los hallazgos
3. **Diagnósticos Sugeridos**: Posibles diagnósticos radiológicos
4. **Recomendaciones**: Estudios adicionales o seguimiento
5. **Correlación Clínica**: Necesidad de correlación con síntomas

Usa la terminología radiológica estándar.
"""
        }
        
        return prompts.get(analysis_type, prompts["general_report"])
    
    def analyze_clinical_data(self, user_id: str, analysis_type: str, data: str) -> Dict[str, Any]:
        """Analiza datos clínicos con IA"""
        # Verificar límites de uso
        can_analyze, remaining = self.check_rate_limit(user_id)
        if not can_analyze:
            return {
                'success': False,
                'error': 'Límite diario de análisis alcanzado',
                'remaining_analyses': 0
            }
        
        try:
            # Generar prompt mejorado
            prompt = self.get_enhanced_prompt(analysis_type, data)
            
            messages = [
                {
                    "role": "system",
                    "content": "Eres un asistente médico especializado en análisis clínico. Proporciona análisis precisos, profesionales y basados en evidencia médica."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Generar respuesta
            success, response = self.model_manager.generate_response(messages)
            
            if success:
                # Incrementar uso y añadir al contexto de aprendizaje
                self.increment_usage(user_id)
                self.add_to_learning_context(analysis_type, response)
                
                return {
                    'success': True,
                    'analysis': response,
                    'model_used': self.model_manager.get_current_model(),
                    'remaining_analyses': remaining - 1,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': response,
                    'remaining_analyses': remaining
                }
                
        except Exception as e:
            logger.error(f"Error en análisis clínico: {e}")
            return {
                'success': False,
                'error': f'Error interno: {str(e)}',
                'remaining_analyses': remaining
            }

class RAGAgent:
    """Agente especializado en consultas RAG sobre guías clínicas"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.rag_service = RAGService()
        self.query_history = []
    
    def process_clinical_query(self, user_id: str, query: str, specialty: str = None) -> Dict[str, Any]:
        """Procesa consulta clínica usando RAG"""
        try:
            # Buscar en guías clínicas
            rag_results = self.rag_service.search_clinical_guidelines(
                query, 
                specialty=specialty,
                top_k=5
            )
            
            if not rag_results:
                return {
                    'success': False,
                    'error': 'No se encontraron guías clínicas relevantes',
                    'suggestions': self._get_query_suggestions()
                }
            
            # Construir contexto para el LLM
            context = self._build_context_from_results(rag_results)
            
            # Generar respuesta con contexto
            prompt = f"""
Basándote en las siguientes guías clínicas hospitalarias, responde la consulta médica.

GUÍAS CLÍNICAS RELEVANTES:
{context}

CONSULTA: {query}

Proporciona una respuesta estructurada que incluya:
1. **Respuesta Directa**: Respuesta clara a la consulta
2. **Fundamento Clínico**: Base científica de la recomendación
3. **Consideraciones Adicionales**: Factores a tener en cuenta
4. **Referencias**: Guías consultadas

Mantén un enfoque clínico profesional y cita las fuentes utilizadas.
"""
            
            messages = [
                {
                    "role": "system",
                    "content": "Eres un especialista médico que consulta guías clínicas hospitalarias para responder consultas médicas. Proporciona respuestas precisas basadas únicamente en la información proporcionada."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            success, response = self.model_manager.generate_response(messages, temperature=0.3)
            
            if success:
                # Guardar en historial
                self.query_history.append({
                    'user_id': user_id,
                    'query': query,
                    'response': response,
                    'sources': [r['metadata'] for r in rag_results],
                    'timestamp': datetime.now()
                })
                
                return {
                    'success': True,
                    'response': response,
                    'sources': rag_results,
                    'model_used': self.model_manager.get_current_model(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': response
                }
                
        except Exception as e:
            logger.error(f"Error en consulta RAG: {e}")
            return {
                'success': False,
                'error': f'Error procesando consulta: {str(e)}'
            }
    
    def _build_context_from_results(self, results: List[Dict]) -> str:
        """Construye contexto a partir de resultados RAG"""
        context = ""
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            source = metadata.get('filename', 'Documento desconocido')
            content = result.get('content', '')
            
            context += f"\n--- FUENTE {i}: {source} ---\n"
            context += f"{content}\n"
        
        return context
    
    def _get_query_suggestions(self) -> List[str]:
        """Obtiene sugerencias de consultas comunes"""
        return [
            "Protocolo de manejo de dolor torácico en urgencias",
            "Guía de administración de antibióticos en sepsis",
            "Criterios de alta en pacientes con neumonía",
            "Manejo de crisis hipertensiva",
            "Protocolo de sedación en UCI"
        ]

class ClinicalChatAgent:
    """Agente para chat clínico integrado (análisis + RAG)"""
    
    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.rag_agent = RAGAgent()
        self.model_manager = ModelManager()
    
    def process_message(self, user_id: str, message: str, context: List[Dict] = None) -> Dict[str, Any]:
        """Procesa mensaje de chat clínico"""
        try:
            # Determinar tipo de consulta
            query_type = self._classify_query(message)
            
            if query_type == "clinical_analysis":
                # Redirigir a análisis clínico
                return self.analysis_agent.analyze_clinical_data(
                    user_id, "general_report", message
                )
            
            elif query_type == "guideline_query":
                # Redirigir a consulta RAG
                return self.rag_agent.process_clinical_query(user_id, message)
            
            else:
                # Chat general con contexto
                return self._handle_general_chat(user_id, message, context)
                
        except Exception as e:
            logger.error(f"Error en chat clínico: {e}")
            return {
                'success': False,
                'error': f'Error procesando mensaje: {str(e)}'
            }
    
    def _classify_query(self, message: str) -> str:
        """Clasifica el tipo de consulta"""
        analysis_keywords = ["analizar", "interpretar", "resultado", "reporte", "análisis"]
        guideline_keywords = ["protocolo", "guía", "recomendación", "tratamiento", "manejo"]
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in analysis_keywords):
            return "clinical_analysis"
        elif any(keyword in message_lower for keyword in guideline_keywords):
            return "guideline_query"
        else:
            return "general_chat"
    
    def _handle_general_chat(self, user_id: str, message: str, context: List[Dict] = None) -> Dict[str, Any]:
        """Maneja chat general con contexto"""
        try:
            # Construir contexto de conversación
            conversation_context = ""
            if context:
                for msg in context[-5:]:  # Últimos 5 mensajes
                    role = "Usuario" if msg['role'] == 'user' else "Asistente"
                    conversation_context += f"{role}: {msg['content']}\n"
            
            prompt = f"""
Contexto de conversación:
{conversation_context}

Mensaje actual: {message}

Responde como un asistente médico profesional. Si la consulta requiere análisis específico o consulta de guías, sugiere usar las funciones especializadas correspondientes.
"""
            
            messages = [
                {
                    "role": "system",
                    "content": "Eres un asistente médico profesional. Proporciona información médica general pero siempre recomienda consultar con profesionales de la salud para diagnósticos específicos."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            success, response = self.model_manager.generate_response(messages)
            
            return {
                'success': success,
                'response': response if success else "Error generando respuesta",
                'type': 'general_chat',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error en chat general: {str(e)}'
            }

