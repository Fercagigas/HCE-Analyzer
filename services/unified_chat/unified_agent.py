"""
Unified Chat Agent for ChatHCE

This module provides a single Claude-powered agent that integrates access to both
the MIMIC-IV-ED database and RAG-indexed clinical documents through intelligent
tool selection.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from services.medical_agent.llm_manager import ClaudeLLMManager, LLMError, AuthError, RateLimitError
from services.medical_agent.prompt_manager import PromptManager
from services.medical_agent.error_handler import handle_error, ToolExecutionError
from services.medical_agent.agent_performance_monitor import get_performance_monitor, track_performance
from services.unified_chat.tools.database_tool import create_database_tool
from services.unified_chat.tools.rag_tool import create_rag_tool
from services.medical_agent.tools.visualization_collaboration_tool import create_visualization_collaboration_tool
from services.cache_manager import cache_manager
from services.rate_limiter import rate_limiter, RateLimitExceeded

logger = logging.getLogger(__name__)


class UnifiedChatAgent:
    """
    Unified chat agent powered by Claude with access to multiple tools.
    
    This agent provides a single interface for:
    - Querying MIMIC-IV-ED database
    - Searching clinical documents via RAG
    - Generating visualizations
    
    The agent automatically selects appropriate tools based on user queries.
    """
    
    def __init__(self):
        """Initialize the unified chat agent."""
        logger.info("Initializing UnifiedChatAgent...")
        
        # Initialize LLM manager
        try:
            self.llm_manager = ClaudeLLMManager()
            logger.info("LLM manager initialized successfully")
        except AuthError as e:
            logger.error(f"Failed to initialize LLM manager: {e}")
            raise
        
        # Initialize prompt manager
        try:
            self.prompt_manager = PromptManager(
                max_tokens=8000,
                anthropic_api_key=self.llm_manager.api_key,
                enable_caching=True
            )
            logger.info("Prompt manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize prompt manager: {e}")
            raise
        
        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()
        logger.info("Performance monitor initialized")
        
        # Initialize tools
        self.tools = self._initialize_tools()
        logger.info(f"Initialized {len(self.tools)} tools")
        
        # Create agent executor
        self.agent_executor = self._create_agent_executor()
        logger.info("Agent executor created successfully")
        
        logger.info("✅ UnifiedChatAgent initialization complete")
    
    def _initialize_tools(self) -> List:
        """
        Initialize all tools for the agent.
        
        Returns:
            List of LangChain-compatible tool instances
        """
        logger.info("Initializing agent tools...")
        
        tools = []
        
        try:
            # Initialize Database Tool
            database_tool = create_database_tool()
            # Convert to LangChain tool
            tools.append(database_tool.get_langchain_tool())
            logger.info("✓ Database tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database tool: {e}")
            raise
        
        try:
            # Initialize RAG Tool
            rag_tool = create_rag_tool()
            # Convert to LangChain tool
            tools.append(rag_tool.get_langchain_tool())
            logger.info("✓ RAG tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG tool: {e}")
            raise
        
        try:
            # Initialize Visualization Collaboration Tool
            viz_tool = create_visualization_collaboration_tool()
            # Convert to LangChain tool
            tools.append(viz_tool.get_langchain_tool())
            logger.info("✓ Visualization tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize visualization tool: {e}")
            raise
        
        return tools
    
    def _create_system_prompt(self) -> str:
        """
        Create comprehensive system prompt for the agent.
        
        The system prompt is structured in the following order:
        1. IDENTIDAD DEL SISTEMA - ChatHCE identity and purpose
        2. CONTEXTO OPERATIVO - MIMIC-IV-ED dataset info (222 patients, 6 tables)
        3. HERRAMIENTAS DISPONIBLES - Tools documentation (query_mimic_database, search_clinical_documents, request_visualization)
        4. DIRECTIVAS ANTI-ALUCINACIÓN - Prohibitions, missing data handling, source citation, uncertainty acknowledgment
        5. IDIOMA Y TERMINOLOGÍA - Spanish language, medical terminology
        6. Base de Datos MIMIC-IV-ED - Database schema
        7. Herramientas Disponibles - Detailed tool descriptions with SQL rules
        8. Formato de Respuesta - Response format guidelines
        9. Guías Clínicas - Clinical reference values
        10. GUÍAS DE SELECCIÓN DE HERRAMIENTAS - When to use each tool
        
        Requirements validated:
        - 5.1: Anti-hallucination section included in system prompt
        - 5.2: Directives organized in structured format
        
        Returns:
            System prompt string with all sections integrated
        """
        logger.debug("Creating system prompt with identity, context, anti-hallucination directives, and tool guidelines...")
        
        # Get base system prompt from prompt manager
        # This includes: identity, context, tools documentation, anti-hallucination directives,
        # language directives, database schema, tool descriptions, response format, and clinical guidelines
        base_prompt = self.prompt_manager.get_system_prompt()
        
        # Add tool selection guidelines (complementary to the tools documentation)
        tool_guidelines = """

# DIRECTIVAS DE CALIDAD DE RESPUESTA

## CONCISIÓN Y RELEVANCIA (OBLIGATORIO):
- Responde ÚNICAMENTE lo que se pregunta. NO añadas información adicional no solicitada.
- Si te preguntan por un dato específico (ej: género del paciente), responde con ese dato directamente.
- NO incluyas interpretaciones clínicas extensas a menos que se soliciten explícitamente.
- NO repitas la pregunta del usuario en tu respuesta.
- Sé directo y preciso. Menos es más.

## FIDELIDAD AL CONTEXTO (OBLIGATORIO):
- Basa tu respuesta EXCLUSIVAMENTE en los datos obtenidos de las herramientas (query_mimic_database, search_clinical_documents).
- NO añadas información de tu conocimiento general que no provenga de los datos recuperados.
- Si los datos no contienen la información solicitada, di "No encontré esa información en los datos disponibles".
- Cita siempre la fuente: "Según los datos de la tabla [nombre]..." o "Según el documento [nombre]...".

# GUÍAS DE SELECCIÓN DE HERRAMIENTAS

## Cuándo usar query_mimic_database:
- Consultas sobre pacientes específicos atendidos en urgencias (con subject_id o stay_id)
- Datos de triaje y signos vitales de urgencias
- Diagnósticos de urgencias de un paciente específico
- Medicamentos administrados en urgencias
- Información demográfica de pacientes de urgencias
- Análisis estadísticos de datos de urgencias
- Tiempos de estancia en urgencias
- Disposición de pacientes (alta, ingreso, traslado)

## Cuándo usar search_clinical_documents:
**REGLA FUNDAMENTAL**: Si la pregunta NO contiene un subject_id o stay_id específico de paciente, SIEMPRE invoca search_clinical_documents antes de responder desde tu conocimiento general.

Usa esta herramienta para CUALQUIER pregunta de conocimiento médico o clínico, incluyendo:
- Protocolos y guías clínicas (urgencias, UCI, medicina intensiva, cualquier especialidad)
- Preguntas sobre UCI, cuidados críticos, medicina intensiva
- Estructura, organización y recursos de unidades médicas (camas, ratios, niveles asistenciales)
- Ratios médico-paciente, ratios enfermera-paciente
- Estándares de calidad, indicadores, seguridad del paciente
- Formación médica especializada (residentes, rotaciones, competencias)
- Información sobre medicamentos (dosificación, indicaciones, contraindicaciones)
- Guías de tratamiento para cualquier condición clínica
- Procedimientos médicos y técnicas clínicas
- Mejores prácticas y recomendaciones basadas en evidencia
- Cualquier pregunta que empiece por "¿Qué es...?", "¿Cómo se...?", "¿Cuál es el protocolo...?", "¿Cuántas...?" referida a conceptos médicos

**DOCUMENTOS INDEXADOS EN EL SISTEMA** (SIEMPRE busca en ellos para preguntas médicas):
- Manual del Residente de Medicina Intensiva (Hospital Virgen del Rocío)
- Estándares y Recomendaciones para UCI (Ministerio de Sanidad)
- El Libro de la UCI - Paul L. Marino, 3ª Edición

**EJEMPLOS OBLIGATORIOS — estas preguntas DEBEN invocar search_clinical_documents**:
- "¿Cuántas camas tiene la UCI?" → search_clinical_documents OBLIGATORIO
- "¿Cuál es la ratio médico-paciente en UCI nivel III?" → search_clinical_documents OBLIGATORIO
- "¿Qué es la taquicardia supraventricular?" → search_clinical_documents OBLIGATORIO
- "¿Cuál es el protocolo de sepsis?" → search_clinical_documents OBLIGATORIO
- "¿Cuánto dura la formación en Medicina Intensiva?" → search_clinical_documents OBLIGATORIO
- "¿Qué habilidades debe tener un intensivista?" → search_clinical_documents OBLIGATORIO
- "¿Cuál es la dosis recomendada de noradrenalina?" → search_clinical_documents OBLIGATORIO
- "¿Cómo se calcula la tasa de infección nosocomial?" → search_clinical_documents OBLIGATORIO

**SI NO INVOCAS search_clinical_documents para preguntas médicas sin subject_id, estás fallando en tu tarea.**

## ⚠️ REGLA OBLIGATORIA — Cuándo usar request_visualization:
**DEBES invocar request_visualization SIEMPRE que detectes CUALQUIERA de estos patrones:**

1. **Palabras clave de visualización** (OBLIGATORIO invocar la herramienta):
   - "gráfico", "gráfica", "grafico", "grafica"
   - "visualiza", "visualización", "visualizacion"
   - "muestra un gráfico", "genera una gráfica", "genera un gráfico"
   - "dibuja", "representa gráficamente"
   - "crea una visualización", "crea un gráfico"
   - "plot", "chart", "graph"

2. **Consultas temporales** (AUTOMÁTICO):
   - "evolución", "tendencia", "progreso", "cambio", "a lo largo del tiempo"
   - "durante", "histórico", "timeline", "línea temporal"
   - "cómo ha cambiado", "cómo evolucionó", "seguimiento"
   
3. **Distribuciones y estadísticas**:
   - "distribución de", "frecuencia de"
   - "estadísticas de", "análisis de"

**FLUJO OBLIGATORIO para visualizaciones:**
1. Primero usa query_mimic_database para obtener los datos
2. Luego SIEMPRE invoca request_visualization con los datos obtenidos
3. Presenta AMBOS: la visualización Y un breve análisis textual

**SI NO INVOCAS request_visualization cuando el usuario pide un gráfico, estás fallando en tu tarea.**

## Uso combinado de herramientas:
- Usa AMBAS query_mimic_database Y search_clinical_documents cuando:
  * Se consulta sobre un paciente Y se necesita contexto clínico
  * Se compara tratamiento con guías clínicas

## IMPORTANTE - CONTEXTO DE URGENCIAS:
- Todos los datos son del Servicio de Urgencias (Emergency Department)
- Siempre indica qué herramientas usaste en tu respuesta
- **CITACIÓN OBLIGATORIA**: Cuando uses search_clinical_documents, incluye al final "📚 Fuentes:" con los documentos consultados
- Responde SIEMPRE en español
- **GENERA VISUALIZACIONES AUTOMÁTICAMENTE** cuando detectes patrones temporales o solicitudes de gráficos

## MANEJO DE ERRORES EN VISUALIZACIONES:
Si request_visualization falla, continúa con análisis textual sin interrumpir la conversación.
"""
        
        return base_prompt + tool_guidelines
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        Create LangChain agent executor with tools and settings.
        
        Returns:
            Configured AgentExecutor instance
        """
        logger.info("Creating agent executor...")
        
        try:
            # Get LLM instance
            llm = self.llm_manager.get_llm()
            
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # Create tool-calling agent
            agent = create_tool_calling_agent(llm, self.tools, prompt)
            
            # Create agent executor with error handling
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
                max_execution_time=120,  # 2 minutes timeout
                return_intermediate_steps=True
            )
            
            logger.info("Agent executor created successfully")
            return agent_executor
            
        except Exception as e:
            logger.error(f"Failed to create agent executor: {e}")
            raise
    
    @track_performance(operation="process_message", query_type="unified_chat")
    def process_message(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user message with automatic tool selection.
        
        Args:
            message: User message to process
            context: Optional conversation context (list of previous messages)
            session_id: Optional session identifier
            
        Returns:
            Dict containing:
                - success: bool
                - content: str (agent response)
                - tools_used: List[str] (tools that were invoked)
                - visualizations: List[Dict] (any visualizations generated)
                - sources: List[Dict] (RAG sources if applicable)
                - metadata: Dict (additional metadata)
                - model_used: str (model name)
                - tokens_used: int (estimated token count)
        """
        logger.info(f"Processing message: '{message[:100]}...'")
        
        # === Rate limiting and input validation ===
        try:
            rate_limiter.validate_message_length(message)
            rate_limiter.check_rate_limit(
                user_id=session_id,
                ip_address=None
            )
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for session {session_id}: {e.message}")
            return {
                "success": False,
                "content": f"⚠️ {e.message}",
                "tools_used": [],
                "visualizations": [],
                "sources": [],
                "metadata": {"error_type": "rate_limit", "retry_after": e.retry_after},
                "model_used": "none",
                "tokens_used": 0
            }
        except ValueError as e:
            logger.warning(f"Input validation failed: {e}")
            return {
                "success": False,
                "content": f"⚠️ {str(e)}",
                "tools_used": [],
                "visualizations": [],
                "sources": [],
                "metadata": {"error_type": "validation"},
                "model_used": "none",
                "tokens_used": 0
            }
        
        # Check cache first
        cache_key = f"unified_chat:{message}:{str(context)}"
        cached_response = cache_manager.get(cache_key)
        
        if cached_response:
            logger.info("✅ Cache hit - returning cached response")
            cached_response['cached'] = True
            return cached_response
        
        # Start performance tracking
        metrics = self.performance_monitor.start_tracking(
            operation="process_message",
            query_type="unified_chat",
            session_id=session_id
        )
        
        try:
            # Prepare conversation history
            chat_history = self._prepare_chat_history(context)
            
            # Execute agent with retry logic
            result = self.llm_manager.execute_with_retry(
                self._invoke_agent,
                message=message,
                chat_history=chat_history
            )
            
            # Format response
            formatted_response = self._format_response(result)
            
            # Add metadata
            formatted_response['metadata'] = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'model_used': self.llm_manager.get_current_model_name(),
                'query_length': len(message)
            }
            
            # End performance tracking
            self.performance_monitor.end_tracking(
                metrics,
                tokens_used=formatted_response.get('tokens_used'),
                model_name=formatted_response['metadata']['model_used'],
                success=True
            )
            
            # Cache the response (TTL from config, default 300 seconds)
            cache_ttl = 300  # 5 minutes
            cache_manager.set(cache_key, formatted_response, ttl=cache_ttl)
            logger.info(f"Response cached with key: {cache_key[:50]}...")
            
            logger.info("✅ Message processed successfully")
            return formatted_response
            
        except (AuthError, RateLimitError, LLMError) as e:
            # Handle LLM-specific errors
            logger.error(f"LLM error processing message: {e}")
            error_response = handle_error(
                e,
                operation="process_message",
                user_query=message,
                model_name=self.llm_manager.get_current_model_name()
            )
            
            # End performance tracking with error
            self.performance_monitor.end_tracking(
                metrics,
                success=False,
                error_type=type(e).__name__
            )
            
            return error_response
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            error_response = handle_error(
                e,
                operation="process_message",
                user_query=message,
                model_name=self.llm_manager.get_current_model_name()
            )
            
            # End performance tracking with error
            self.performance_monitor.end_tracking(
                metrics,
                success=False,
                error_type=type(e).__name__
            )
            
            return error_response
    
    def _invoke_agent(
        self,
        message: str,
        chat_history: List
    ) -> Dict[str, Any]:
        """
        Invoke the agent executor.
        
        Args:
            message: User message
            chat_history: Conversation history
            
        Returns:
            Agent execution result
        """
        logger.debug("Invoking agent executor...")
        
        result = self.agent_executor.invoke({
            "input": message,
            "chat_history": chat_history
        })
        
        logger.debug("Agent execution complete")
        return result
    
    # Maximum tokens for chat history to prevent exceeding Claude's context limit
    # Claude has 200K token limit, we reserve space for system prompt (~10K) and response (~4K)
    MAX_HISTORY_TOKENS = 150000
    # Minimum messages to always keep (most recent)
    MIN_MESSAGES_TO_KEEP = 4
    # Maximum characters per message content to prevent individual messages from being too large
    MAX_MESSAGE_CONTENT_LENGTH = 50000
    # Maximum characters for tool result context to prevent bloating the history
    MAX_TOOL_CONTEXT_LENGTH = 2000
    MAX_RAW_OUTPUT_LENGTH = 1000
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~1.33 tokens per word, or ~4 characters per token
        return len(text) // 4
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Truncate text to maximum length with indicator.
        
        Args:
            text: Text to truncate
            max_length: Maximum character length
            
        Returns:
            Truncated text with indicator if truncated
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "\n...[contenido truncado por límite de tokens]"
    
    def _prepare_chat_history(
        self,
        context: Optional[List[Dict[str, str]]]
    ) -> List:
        """
        Prepare chat history for agent with tool results context.
        
        This method enriches assistant messages with summaries of tool results
        from previous interactions, allowing the LLM to reference past data
        without re-executing tools.
        
        Implements token limiting to prevent exceeding Claude's context window.
        
        Args:
            context: List of previous messages with optional tool_results
            
        Returns:
            List of LangChain message objects with enriched context
        """
        if not context:
            return []
        
        chat_history = []
        recent_tool_results = []  # Track recent tool results for context
        total_tokens = 0
        
        # Process messages from newest to oldest to prioritize recent context
        messages_to_process = list(enumerate(context))
        processed_messages = []
        
        for i, msg in messages_to_process:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Truncate individual message content if too large
            if isinstance(content, str) and len(content) > self.MAX_MESSAGE_CONTENT_LENGTH:
                content = self._truncate_text(content, self.MAX_MESSAGE_CONTENT_LENGTH)
                logger.warning(f"Truncated message {i} content from {len(msg.get('content', ''))} to {len(content)} chars")
            
            if role == 'user':
                message_obj = HumanMessage(content=content)
                message_tokens = self._estimate_tokens(content)
                processed_messages.append((i, message_obj, message_tokens))
                
            elif role == 'assistant':
                # Handle both string content and dict content (with metadata)
                if isinstance(content, dict):
                    # Extract text content
                    text_content = content.get('content', '')
                    
                    # Truncate if too large
                    if len(text_content) > self.MAX_MESSAGE_CONTENT_LENGTH:
                        text_content = self._truncate_text(text_content, self.MAX_MESSAGE_CONTENT_LENGTH)
                    
                    # Extract tool results if available
                    tool_results = content.get('tool_results', [])
                    
                    # Add to recent tool results (keep last 5 for context)
                    if tool_results:
                        recent_tool_results.extend(tool_results)
                        recent_tool_results = recent_tool_results[-5:]  # Keep only last 5
                    
                    # Enrich content with tool results context
                    enriched_content = self._enrich_message_with_context(
                        text_content,
                        tool_results,
                        is_recent=(i >= len(context) - 3)  # Last 3 messages get full data
                    )
                    
                    message_obj = AIMessage(content=enriched_content)
                    message_tokens = self._estimate_tokens(enriched_content)
                else:
                    # Legacy format: just string content
                    if isinstance(content, str) and len(content) > self.MAX_MESSAGE_CONTENT_LENGTH:
                        content = self._truncate_text(content, self.MAX_MESSAGE_CONTENT_LENGTH)
                    message_obj = AIMessage(content=content)
                    message_tokens = self._estimate_tokens(content)
                
                processed_messages.append((i, message_obj, message_tokens))
        
        # Now apply token limit, keeping most recent messages
        # Sort by index (oldest first for final order)
        processed_messages.sort(key=lambda x: x[0])
        
        # Calculate total tokens
        total_tokens = sum(tokens for _, _, tokens in processed_messages)
        
        if total_tokens > self.MAX_HISTORY_TOKENS:
            logger.warning(f"Chat history exceeds token limit ({total_tokens} > {self.MAX_HISTORY_TOKENS}). Truncating older messages.")
            
            # Keep removing oldest messages until under limit, but always keep MIN_MESSAGES_TO_KEEP
            while total_tokens > self.MAX_HISTORY_TOKENS and len(processed_messages) > self.MIN_MESSAGES_TO_KEEP:
                removed = processed_messages.pop(0)  # Remove oldest
                total_tokens -= removed[2]
                logger.debug(f"Removed message {removed[0]} ({removed[2]} tokens) from history")
            
            logger.info(f"Chat history truncated to {len(processed_messages)} messages ({total_tokens} tokens)")
        
        # Build final chat history
        chat_history = [msg for _, msg, _ in processed_messages]
        
        # Log context statistics
        logger.debug(f"Prepared chat history: {len(chat_history)} messages, "
                    f"{total_tokens} estimated tokens, "
                    f"{len(recent_tool_results)} tool results in context")
        
        return chat_history
    
    def _enrich_message_with_context(
        self,
        text_content: str,
        tool_results: List[Dict[str, Any]],
        is_recent: bool = True
    ) -> str:
        """
        Enrich message content with tool results context.
        
        Implements size limits to prevent context from growing too large.
        
        Args:
            text_content: Original text content
            tool_results: List of tool results from this message
            is_recent: Whether this is a recent message (gets more detail)
            
        Returns:
            Enriched content string with size limits applied
        """
        if not tool_results:
            return text_content
        
        # Add context section
        context_parts = [text_content]
        context_parts.append("\n\n---")
        context_parts.append("[CONTEXTO DE DATOS - Disponible para referencia]")
        
        total_context_length = 0
        
        for result in tool_results:
            # Check if we've exceeded the context limit
            if total_context_length >= self.MAX_TOOL_CONTEXT_LENGTH:
                context_parts.append("\n[...contexto adicional omitido por límite de tamaño]")
                break
            
            tool_name = result.get('tool', 'unknown')
            summary = result.get('summary', '')
            
            # Truncate summary if too long
            if len(summary) > 500:
                summary = summary[:500] + "..."
            
            if is_recent and result.get('raw_output'):
                # For recent messages, include more detail but with limits
                context_parts.append(f"\n{summary}")
                total_context_length += len(summary)
                
                # Add truncated raw data for database queries
                if tool_name == 'query_mimic_database':
                    raw = result.get('raw_output')
                    if isinstance(raw, dict):
                        # Include key fields only
                        keys_info = f"Datos completos disponibles: {list(raw.keys())[:10]}"
                        context_parts.append(keys_info)
                        total_context_length += len(keys_info)
                    elif isinstance(raw, list) and len(raw) > 0:
                        # For list results, just show count
                        count_info = f"Total registros: {len(raw)}"
                        context_parts.append(count_info)
                        total_context_length += len(count_info)
                    elif isinstance(raw, str) and len(raw) > self.MAX_RAW_OUTPUT_LENGTH:
                        # Truncate string output
                        truncated = raw[:self.MAX_RAW_OUTPUT_LENGTH] + "...[truncado]"
                        context_parts.append(truncated)
                        total_context_length += len(truncated)
                    elif isinstance(raw, list) and len(raw) > 0:
                        context_parts.append(f"Total registros: {len(raw)}")
            else:
                # For older messages, just include summary
                context_parts.append(f"\n{summary}")
        
        context_parts.append("---\n")
        
        return "\n".join(context_parts)
    
    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent response with metadata and tool results for context preservation.
        
        Args:
            result: Raw agent execution result
            
        Returns:
            Formatted response dictionary with tool_results for memory
        """
        logger.debug("Formatting agent response...")
        
        # Extract output
        output = result.get('output', '')
        
        # Handle case where output is a list (from Claude's response format)
        if isinstance(output, list):
            # Extract text from list of response blocks
            text_parts = []
            for block in output:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
                elif isinstance(block, str):
                    text_parts.append(block)
            output = '\n'.join(text_parts)
        
        # Ensure output is a string
        if not isinstance(output, str):
            output = str(output)
        
        # Extract intermediate steps (tool calls)
        intermediate_steps = result.get('intermediate_steps', [])
        tools_used = []
        visualizations = []
        sources = []
        tool_results = []  # NEW: Store structured tool results for context
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                tool_name = action.tool if hasattr(action, 'tool') else 'unknown'
                tools_used.append(tool_name)
                
                # Extract and store tool results with data
                tool_result = self._extract_tool_result(
                    tool_name=tool_name,
                    action=action,
                    observation=observation
                )
                if tool_result:
                    tool_results.append(tool_result)
                
                # Extract visualizations with improved parsing
                if tool_name == 'request_visualization':
                    viz_data = self._extract_visualization_data(observation)
                    if viz_data:
                        visualizations.append(viz_data)
                
                # Extract RAG sources with structured document info
                if tool_name == 'search_clinical_documents':
                    rag_sources = self._extract_rag_sources(observation)
                    if rag_sources:
                        sources.extend(rag_sources)
                    else:
                        sources.append({
                            'tool': tool_name,
                            'content': observation[:500] if isinstance(observation, str) else str(observation)[:500]
                        })
        
        # Organize visualizations coherently
        if visualizations:
            output = self._integrate_visualizations_in_response(output, visualizations)
        
        # Estimate token usage (rough estimate)
        tokens_used = self.prompt_manager.estimate_tokens(output)
        
        formatted = {
            'success': True,
            'content': output,
            'tools_used': list(set(tools_used)),  # Remove duplicates
            'tool_results': tool_results,  # NEW: Structured data for context
            'visualizations': visualizations,
            'sources': sources,
            'tokens_used': tokens_used,
            'model_used': self.llm_manager.get_current_model_name()
        }
        
        logger.debug(f"Response formatted: {len(tools_used)} tools used, "
                    f"{len(visualizations)} visualizations, {len(sources)} sources, "
                    f"{len(tool_results)} tool results preserved")
        
        return formatted
    
    def _extract_tool_result(
        self,
        tool_name: str,
        action: Any,
        observation: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured tool result for context preservation.
        
        Args:
            tool_name: Name of the tool
            action: Tool action object
            observation: Tool observation/result
            
        Returns:
            Dict with structured tool result or None
        """
        from datetime import datetime
        
        try:
            # Get tool input
            tool_input = action.tool_input if hasattr(action, 'tool_input') else {}
            
            # Create base result
            result = {
                'tool': tool_name,
                'timestamp': datetime.now().isoformat(),
                'input': tool_input,
                'raw_output': None,
                'summary': None
            }
            
            # Extract data based on tool type
            if tool_name == 'query_mimic_database':
                result['raw_output'] = observation if isinstance(observation, (dict, list)) else str(observation)
                result['summary'] = self._create_database_summary(observation, tool_input)
                
            elif tool_name == 'search_clinical_documents':
                # Preserve full observation so extract_contexts can parse document sections
                result['raw_output'] = observation if isinstance(observation, str) else str(observation)
                result['raw_observation'] = observation if isinstance(observation, str) else str(observation)
                result['summary'] = self._create_rag_summary(observation, tool_input)
                
            elif tool_name == 'request_visualization':
                # Don't store full image data, just metadata
                result['raw_output'] = 'visualization_generated'
                result['summary'] = f"Visualización generada para: {tool_input.get('description', 'datos')}"
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to extract tool result for {tool_name}: {e}")
            return None
    
    def _create_database_summary(self, observation: Any, tool_input: Dict) -> str:
        """
        Create concise summary of database query results.
        
        Args:
            observation: Database query result
            tool_input: Tool input parameters
            
        Returns:
            Concise summary string
        """
        try:
            summary_parts = ["[DATOS: query_mimic_database]"]
            
            # Add query type if available
            query_type = tool_input.get('query_type', 'unknown')
            summary_parts.append(f"Tipo: {query_type}")
            
            # Add subject_id if available
            if 'subject_id' in tool_input:
                summary_parts.append(f"Paciente: {tool_input['subject_id']}")
            
            # Try to extract key data points from observation
            if isinstance(observation, dict):
                # Extract vital signs if present
                if 'temperature' in observation or 'heartrate' in observation:
                    vitals = []
                    if 'temperature' in observation:
                        vitals.append(f"T={observation['temperature']}°F")
                    if 'heartrate' in observation:
                        vitals.append(f"HR={observation['heartrate']}")
                    if 'sbp' in observation and 'dbp' in observation:
                        vitals.append(f"BP={observation['sbp']}/{observation['dbp']}")
                    if 'o2sat' in observation:
                        vitals.append(f"O2={observation['o2sat']}%")
                    if vitals:
                        summary_parts.append(f"Signos vitales: {', '.join(vitals)}")
                
                # Count diagnoses if present
                if 'diagnoses' in observation:
                    count = len(observation['diagnoses']) if isinstance(observation['diagnoses'], list) else 1
                    summary_parts.append(f"Diagnósticos: {count}")
                
                # Count medications if present
                if 'medications' in observation:
                    count = len(observation['medications']) if isinstance(observation['medications'], list) else 1
                    summary_parts.append(f"Medicamentos: {count}")
            
            elif isinstance(observation, list):
                summary_parts.append(f"Registros: {len(observation)}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.warning(f"Failed to create database summary: {e}")
            return "[DATOS: query_mimic_database] - Datos disponibles"
    
    def _create_rag_summary(self, observation: Any, tool_input: Dict) -> str:
        """
        Create concise summary of RAG search results.
        
        Args:
            observation: RAG search result
            tool_input: Tool input parameters
            
        Returns:
            Concise summary string
        """
        try:
            summary_parts = ["[DATOS: search_clinical_documents]"]
            
            # Add query if available
            query = tool_input.get('query', '')
            if query:
                summary_parts.append(f"Búsqueda: '{query[:50]}...'")
            
            # Extract source citations from observation
            if isinstance(observation, str):
                sources = self._extract_rag_sources(observation)
                if sources:
                    summary_parts.append(f"Documentos: {len(sources)} encontrados")
                    for src in sources:
                        summary_parts.append(f"  - {src.get('filename', 'Desconocido')}")
                else:
                    doc_count = observation.count("Documento") 
                    if doc_count > 0:
                        summary_parts.append(f"Documentos: ~{doc_count} encontrados")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.warning(f"Failed to create RAG summary: {e}")
            return "[DATOS: search_clinical_documents] - Documentos encontrados"

    def _extract_rag_sources(self, observation: Any) -> List[Dict[str, str]]:
        """
        Extract structured source citations and retrieved content from RAG tool observation.
        
        Parses both the document content sections and the "FUENTES CITADAS" section
        from the formatted RAG output to produce structured source data for the UI,
        including the original retrieved text.
        
        Args:
            observation: RAG tool observation (string)
            
        Returns:
            List of dicts with filename, page, specialty, doc_type, retrieved_content keys
        """
        if not isinstance(observation, str):
            return []
        
        sources = []
        try:
            # Step 1: Extract document content sections
            # Format: "--- Documento N: source ---\ncontent\n"
            import re
            doc_contents = {}
            doc_pattern = re.compile(
                r'--- Documento (\d+): .+? ---\n(.*?)(?=\n--- Documento \d+:|=== FUENTES CITADAS ===|\Z)',
                re.DOTALL
            )
            for match in doc_pattern.finditer(observation):
                doc_num = int(match.group(1))
                content_text = match.group(2).strip()
                if content_text:
                    doc_contents[doc_num] = content_text
            
            # Step 2: Parse the FUENTES CITADAS section
            marker = "=== FUENTES CITADAS ==="
            if marker not in observation:
                return []
            
            citation_section = observation.split(marker)[1].strip()
            
            doc_index = 0
            for line in citation_section.split("\n"):
                line = line.strip()
                if not line or line.startswith("IMPORTANTE"):
                    continue
                
                doc_index += 1
                source = {'tool': 'search_clinical_documents'}
                
                # Parse "[N] 📄 filename | p. X | Especialidad: Y | Tipo: Z"
                rank_num = doc_index
                clean = line
                if clean.startswith("["):
                    bracket_end = clean.find("]")
                    if bracket_end > 0:
                        try:
                            rank_num = int(clean[1:bracket_end])
                        except ValueError:
                            pass
                        clean = clean[bracket_end + 1:].strip()
                # Remove emoji
                clean = clean.replace("📄", "").strip()
                
                parts = [p.strip() for p in clean.split("|")]
                
                if parts:
                    source['filename'] = parts[0]
                    source['content'] = f"📄 {parts[0]}"
                    
                    for part in parts[1:]:
                        if part.startswith("p."):
                            source['page'] = part.replace("p.", "").strip()
                            source['content'] += f" (p. {source['page']})"
                        elif part.startswith("Especialidad:"):
                            source['specialty'] = part.replace("Especialidad:", "").strip()
                        elif part.startswith("Tipo:"):
                            source['doc_type'] = part.replace("Tipo:", "").strip()
                    
                    # Attach the original retrieved content
                    if rank_num in doc_contents:
                        source['retrieved_content'] = doc_contents[rank_num]
                    
                    sources.append(source)
            
        except Exception as e:
            logger.warning(f"Failed to extract RAG sources: {e}")
        
        return sources
    
    def _extract_visualization_data(self, observation: str) -> Optional[Dict[str, Any]]:
        """
        Extract visualization data from tool observation.
        
        Handles:
        1. VISUALIZATION_IDS marker (new approach - prevents token overflow)
        2. Legacy base64 images (backward compatibility)
        
        Args:
            observation: Tool observation string
            
        Returns:
            Dict with visualization data or None
        """
        if not isinstance(observation, str):
            return None
        
        # Check for VISUALIZATION_IDS marker (new approach)
        # This prevents base64 images from being passed to LLM
        import re
        viz_ids_match = re.search(r'\[VISUALIZATION_IDS:([^\]]+)\]', observation)
        
        if viz_ids_match:
            viz_ids = viz_ids_match.group(1).split(',')
            viz_ids = [vid.strip() for vid in viz_ids if vid.strip()]
            
            if viz_ids:
                logger.info(f"Found {len(viz_ids)} visualization IDs in observation")
                
                # Extract metadata from observation (excluding the IDs marker)
                metadata_parts = []
                for line in observation.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('[VISUALIZATION_IDS:'):
                        if line.startswith('✅') or line.startswith('⚠️') or line.startswith('⏱️') or line.startswith('📊'):
                            metadata_parts.append(line)
                
                return {
                    'type': 'visualization_ids',
                    'ids': viz_ids,
                    'count': len(viz_ids),
                    'metadata': '\n'.join(metadata_parts) if metadata_parts else None,
                    'tool': 'request_visualization'
                }
        
        # Legacy approach: Extract base64 images directly
        # Split observation into lines
        lines = observation.split('\n')
        
        # Extract all image data and metadata
        images = []
        metadata_parts = []
        current_title = None
        
        for line in lines:
            line = line.strip()
            
            # Check for image data
            if line.startswith('data:image'):
                images.append({
                    'data': line,
                    'title': current_title
                })
                current_title = None
            # Check for section titles (### format)
            elif line.startswith('### '):
                current_title = line.replace('### ', '').strip()
            # Check for visualization type info
            elif line.startswith('📈 Tipo:') or line.startswith('📊'):
                if current_title:
                    metadata_parts.append(f"{current_title}: {line}")
                else:
                    metadata_parts.append(line)
            # Collect other metadata
            elif line and not line.startswith('data:') and '**Plan de Visualización:**' not in line:
                # Skip empty lines and plan headers
                if line.startswith('•') or line.startswith('-') or line.startswith('✅') or line.startswith('⚠️') or line.startswith('⏱️'):
                    metadata_parts.append(line)
        
        if not images:
            return None
        
        # Return single image or multiple images
        if len(images) == 1:
            return {
                'type': 'image',
                'data': images[0]['data'],
                'title': images[0].get('title'),
                'metadata': '\n'.join(metadata_parts) if metadata_parts else None,
                'tool': 'request_visualization'
            }
        else:
            # Multiple images - return as a list
            return {
                'type': 'multiple_images',
                'images': images,
                'count': len(images),
                'metadata': '\n'.join(metadata_parts) if metadata_parts else None,
                'tool': 'request_visualization'
            }
    
    def _integrate_visualizations_in_response(
        self,
        output: str,
        visualizations: List[Dict[str, Any]]
    ) -> str:
        """
        Integrate visualizations coherently into the response.
        
        Args:
            output: Original output text
            visualizations: List of visualization data
            
        Returns:
            Enhanced output with visualization references
        """
        if not visualizations:
            return output
        
        # Add visualization section header if not already present
        viz_section_markers = [
            '📊 Visualización',
            '📈 Gráfica',
            '🔍 Análisis Visual',
            'visualización generada',
            'gráfica generada'
        ]
        
        has_viz_section = any(marker.lower() in output.lower() for marker in viz_section_markers)
        
        if not has_viz_section and len(visualizations) > 0:
            # Add a clear section for visualizations
            viz_count = len(visualizations)
            
            if viz_count == 1:
                viz_header = "\n\n📊 **Visualización Generada**\n"
            else:
                viz_header = f"\n\n📊 **Visualizaciones Generadas ({viz_count})**\n"
            
            # Add metadata if available
            metadata_parts = []
            for i, viz in enumerate(visualizations, 1):
                if viz.get('metadata'):
                    if viz_count > 1:
                        metadata_parts.append(f"\n**Visualización {i}:**")
                    metadata_parts.append(viz['metadata'])
            
            if metadata_parts:
                viz_header += '\n'.join(metadata_parts)
            
            # Append visualization section to output
            output = output + viz_header
        
        return output
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the agent.
        
        Returns:
            Dictionary containing performance statistics
        """
        return self.performance_monitor.get_statistics(operation="process_message")
    
    def reset_to_primary_model(self):
        """Reset LLM manager to primary model."""
        self.llm_manager.reset_to_primary()
        logger.info("Reset to primary model")


def create_unified_agent() -> UnifiedChatAgent:
    """
    Create a unified chat agent instance.
    
    Returns:
        UnifiedChatAgent instance
    """
    return UnifiedChatAgent()
