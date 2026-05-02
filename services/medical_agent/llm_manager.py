"""
Claude LLM Manager for ChatHCE

This module manages Claude LLM initialization, fallback chain logic,
and error handling for the medical agent system.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from langchain_anthropic import ChatAnthropic
from anthropic import APIError, RateLimitError as AnthropicRateLimitError, AuthenticationError

from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class RateLimitError(LLMError):
    """Exception for rate limiting errors"""
    pass


class AuthError(LLMError):
    """Exception for authentication errors"""
    pass


class ClaudeLLMManager:
    """
    Manages Claude LLM initialization and fallback chain.
    
    This class handles:
    - Claude API initialization with proper authentication
    - Fallback chain with multiple Claude models
    - Retry logic with exponential backoff
    - Comprehensive error handling and logging
    """
    
    def __init__(self):
        """
        Initialize LLM manager with configuration.
        
        Raises:
            AuthError: If ANTHROPIC_API_KEY is missing or invalid
        """
        logger.info("Initializing ClaudeLLMManager")
        
        # Validate API key
        try:
            self.api_key = settings.claude_agent.anthropic_api_key
            if not self.api_key or self.api_key.strip() == "":
                raise AuthError(
                    "ANTHROPIC_API_KEY no está configurada. "
                    "Por favor, añade tu clave API de Anthropic al archivo .env"
                )
        except AttributeError:
            raise AuthError(
                "No se pudo cargar la configuración de Claude. "
                "Verifica que ANTHROPIC_API_KEY esté en el archivo .env"
            )
        
        # Get model chain configuration
        self.models = self._get_model_chain()
        self.current_model_index = 0
        self.current_llm: Optional[ChatAnthropic] = None
        
        # Retry configuration
        self.max_retries = settings.claude_agent.max_retries
        self.retry_delay = settings.claude_agent.retry_delay
        self.backoff_multiplier = settings.claude_agent.backoff_multiplier
        
        logger.info(
            f"ClaudeLLMManager initialized with {len(self.models)} models in fallback chain"
        )
    
    def get_llm(self) -> ChatAnthropic:
        """
        Get initialized Claude LLM instance.
        
        Returns the current LLM if already initialized, otherwise creates
        a new instance with the primary model.
        
        Returns:
            ChatAnthropic: Initialized Claude LLM instance
            
        Raises:
            LLMError: If initialization fails
            AuthError: If authentication fails
        """
        if self.current_llm is not None:
            logger.debug("Returning existing LLM instance")
            return self.current_llm
        
        logger.info("Initializing new Claude LLM instance")
        
        # Get current model configuration
        model_config = self.models[self.current_model_index]
        
        try:
            # Create ChatAnthropic instance
            llm = ChatAnthropic(
                model=model_config['name'],
                anthropic_api_key=self.api_key,
                max_tokens=model_config['max_tokens'],
                temperature=model_config['temperature'],
                timeout=model_config['timeout']
            )
            
            # Test the model
            if self._test_model(llm):
                self.current_llm = llm
                logger.info(
                    f"✅ Successfully initialized Claude model: {model_config['name']} "
                    f"(version: {model_config['version']}, max_tokens: {model_config['max_tokens']})"
                )
                return llm
            else:
                raise LLMError(
                    f"Model {model_config['name']} failed validation test"
                )
                
        except AuthenticationError as e:
            error_msg = (
                "Error de autenticación con la API de Claude. "
                "Verifica que tu ANTHROPIC_API_KEY sea válida."
            )
            logger.error(f"Authentication error: {str(e)}")
            raise AuthError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error al inicializar el modelo Claude: {str(e)}"
            logger.error(error_msg)
            raise LLMError(error_msg) from e
    
    def switch_to_fallback(self) -> bool:
        """
        Switch to next fallback model in the chain.
        
        This method attempts to switch to the next available model in the
        fallback chain. It logs the switch and updates the current model index.
        
        Returns:
            bool: True if switch successful, False if no more fallbacks available
        """
        # Check if we have more models in the chain
        if self.current_model_index >= len(self.models) - 1:
            logger.warning("No more fallback models available")
            return False
        
        # Move to next model
        self.current_model_index += 1
        previous_model = self.models[self.current_model_index - 1]['name']
        new_model = self.models[self.current_model_index]['name']
        
        logger.warning(
            f"Switching from {previous_model} to fallback model {new_model}"
        )
        
        # Reset current LLM to force reinitialization
        self.current_llm = None
        
        try:
            # Try to initialize the new model
            self.get_llm()
            logger.info(f"Successfully switched to fallback model: {new_model}")
            return True
            
        except AuthError:
            # Don't attempt more fallbacks on auth errors
            logger.error("Authentication error - not attempting further fallbacks")
            raise
            
        except Exception as e:
            logger.error(f"Failed to switch to fallback model {new_model}: {str(e)}")
            # Try next fallback if available
            if self.current_model_index < len(self.models) - 1:
                return self.switch_to_fallback()
            return False
    
    def _test_model(self, llm: ChatAnthropic) -> bool:
        """
        Test model with a simple query to validate functionality.
        
        Args:
            llm: ChatAnthropic instance to test
            
        Returns:
            bool: True if model responds successfully, False otherwise
        """
        logger.debug("Testing model functionality")
        
        try:
            # Simple test query
            response = llm.invoke("Responde con 'OK' si puedes procesar este mensaje.")
            
            # Check if we got a valid response
            if response and hasattr(response, 'content'):
                logger.debug("Model test successful")
                return True
            else:
                logger.warning("Model test returned invalid response")
                return False
                
        except Exception as e:
            logger.warning(f"Model test failed: {str(e)}")
            return False
    
    def _get_model_chain(self) -> List[Dict[str, Any]]:
        """
        Get ordered list of Claude models for fallback chain.
        
        Primary model: Claude Haiku 4.5 (claude-haiku-4-5-20251001)
        Secondary model: Claude Sonnet 4.5
        Tertiary model: Claude Opus 4
        
        Returns:
            List[Dict[str, Any]]: List of model configurations in fallback order
        """
        base_max_tokens = settings.claude_agent.max_tokens
        
        # Log the primary model being configured
        logger.info(
            f"Configuring model chain - Primary: {settings.claude_agent.primary_model} "
            f"(version: {settings.claude_agent.primary_model_version})"
        )
        
        model_chain = [
            {
                'name': settings.claude_agent.primary_model,
                'version': settings.claude_agent.primary_model_version,
                'max_tokens': base_max_tokens,  # Haiku 4.5: 4096
                'temperature': settings.claude_agent.temperature,
                'timeout': settings.claude_agent.timeout_seconds
            },
            {
                'name': settings.claude_agent.secondary_model,
                'version': settings.claude_agent.secondary_model_version,
                'max_tokens': min(base_max_tokens * 2, 8192),  # Sonnet: 8192 (or double base)
                'temperature': settings.claude_agent.temperature,
                'timeout': settings.claude_agent.timeout_seconds + 15  # Extra time for fallback
            },
            {
                'name': settings.claude_agent.tertiary_model,
                'version': settings.claude_agent.tertiary_model_version,
                'max_tokens': base_max_tokens,  # Opus: 4096
                'temperature': settings.claude_agent.temperature,
                'timeout': settings.claude_agent.timeout_seconds + 30  # Extra time for tertiary
            }
        ]
        
        # Log the complete fallback chain
        logger.debug(
            f"Fallback chain configured: {[m['name'] for m in model_chain]}"
        )
        
        return model_chain
    
    def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        This method wraps API calls with automatic retry logic for transient
        failures, implementing exponential backoff between attempts.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result from the function
            
        Raises:
            RateLimitError: If rate limit is hit and all retries exhausted
            AuthError: If authentication fails
            LLMError: If all retries fail
        """
        last_exception = None
        delay = self.retry_delay
        fallback_attempted = False
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
                
            except AuthenticationError as e:
                # Don't retry authentication errors
                logger.error("Authentication error - not retrying")
                raise AuthError(
                    "Error de autenticación con Claude API. "
                    "Verifica tu ANTHROPIC_API_KEY."
                ) from e
                
            except AnthropicRateLimitError as e:
                last_exception = e
                logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}/{self.max_retries}. "
                    f"Waiting {delay} seconds before retry..."
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= self.backoff_multiplier
                else:
                    # Try fallback model on final retry (only once)
                    if not fallback_attempted:
                        logger.warning("Max retries reached, attempting fallback model")
                        fallback_attempted = True
                        if self.switch_to_fallback():
                            # Reset delay and try once with new model
                            delay = self.retry_delay
                            try:
                                return func(*args, **kwargs)
                            except Exception as fallback_error:
                                logger.error(f"Fallback model also failed: {str(fallback_error)}")
                                # Continue to raise original error
                    
                    raise RateLimitError(
                        "Límite de tasa alcanzado y no hay más modelos de respaldo disponibles"
                    ) from e
                        
            except APIError as e:
                last_exception = e
                logger.warning(
                    f"API error on attempt {attempt + 1}/{self.max_retries}: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= self.backoff_multiplier
                else:
                    raise LLMError(
                        f"Error de API después de {self.max_retries} intentos: {str(e)}"
                    ) from e
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= self.backoff_multiplier
                else:
                    raise LLMError(
                        f"Error inesperado después de {self.max_retries} intentos: {str(e)}"
                    ) from e
        
        # Should not reach here, but just in case
        raise LLMError(
            f"Falló después de {self.max_retries} intentos"
        ) from last_exception
    
    def get_current_model_name(self) -> str:
        """
        Get the name of the currently active model.
        
        Returns:
            str: Name of the current model
        """
        return self.models[self.current_model_index]['name']
    
    def reset_to_primary(self):
        """
        Reset to primary model.
        
        This can be called to reset the fallback chain back to the primary model,
        useful for periodic health checks or after successful operations.
        """
        if self.current_model_index != 0:
            logger.info("Resetting to primary model")
            self.current_model_index = 0
            self.current_llm = None
    
    @staticmethod
    def create_visualization_llm() -> ChatAnthropic:
        """
        Create a Claude LLM instance specifically configured for visualization.
        
        Uses Claude Sonnet 4.5 with settings optimized for code generation.
        This is a static method that creates a new instance independent of
        the fallback chain used by the main agent.
        
        Returns:
            ChatAnthropic: Claude Sonnet 4.5 instance configured for visualization
            
        Raises:
            AuthError: If ANTHROPIC_API_KEY is missing or invalid
            LLMError: If initialization fails
        """
        logger.info("Creating visualization-specific LLM (Claude Sonnet 4.5)")
        
        try:
            # Get visualization settings
            viz_settings = settings.visualization
            
            # Validate API key
            api_key = settings.claude_agent.anthropic_api_key
            if not api_key or api_key.strip() == "":
                raise AuthError(
                    "ANTHROPIC_API_KEY no está configurada. "
                    "Se requiere para el sistema de visualización."
                )
            
            # Create ChatAnthropic instance with visualization settings
            llm = ChatAnthropic(
                model=viz_settings.model_name,
                anthropic_api_key=api_key,
                max_tokens=viz_settings.max_tokens,
                temperature=viz_settings.temperature,
                timeout=viz_settings.timeout_seconds
            )
            
            logger.info(
                f"✅ Visualization LLM initialized: {viz_settings.model_name} "
                f"(max_tokens={viz_settings.max_tokens}, "
                f"temperature={viz_settings.temperature})"
            )
            
            return llm
            
        except AttributeError as e:
            error_msg = (
                "No se pudo cargar la configuración de visualización. "
                "Verifica que las variables de entorno estén configuradas correctamente."
            )
            logger.error(f"Configuration error: {str(e)}")
            raise LLMError(error_msg) from e
            
        except AuthenticationError as e:
            error_msg = (
                "Error de autenticación con la API de Claude. "
                "Verifica que tu ANTHROPIC_API_KEY sea válida."
            )
            logger.error(f"Authentication error: {str(e)}")
            raise AuthError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error al inicializar el LLM de visualización: {str(e)}"
            logger.error(error_msg)
            raise LLMError(error_msg) from e
