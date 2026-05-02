"""
Optimized Message Handler for Chat Interface
Handles message pagination, incremental updates, and efficient rendering
"""
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import hashlib
import json

logger = logging.getLogger(__name__)

# Note: ui_cache_manager and ui_performance_monitor were removed
# These decorators are now no-ops for compatibility
def cached_ui_component(func):
    """Compatibility decorator - caching removed"""
    return func

def monitor_ui_component(component_name, operation_name):
    """Compatibility decorator - monitoring removed"""
    def decorator(func):
        return func
    return decorator

def track_user_interaction(interaction_type, metadata=None):
    """Compatibility function - tracking removed"""
    pass

@dataclass
class MessageChunk:
    """Represents a chunk of messages for pagination"""
    messages: List[Dict[str, Any]]
    start_index: int
    end_index: int
    total_count: int
    has_more_before: bool
    has_more_after: bool

class OptimizedMessageHandler:
    """Handles message loading, pagination, and rendering optimization"""
    
    def __init__(self, messages_per_page: int = 20, cache_ttl: int = 300):
        self.messages_per_page = messages_per_page
        self.cache_ttl = cache_ttl
        self.max_message_preview_length = 500
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize message handler session state"""
        if 'message_pagination' not in st.session_state:
            st.session_state.message_pagination = {
                'current_page': 0,
                'messages_per_page': self.messages_per_page,
                'total_messages': 0,
                'last_message_id': None,
                'auto_scroll_enabled': True
            }
        
        if 'message_cache_keys' not in st.session_state:
            st.session_state.message_cache_keys = set()
    
    @monitor_ui_component("message_handler", "load_messages")
    def load_messages_paginated(self, session_id: str, page: int = 0, 
                              force_refresh: bool = False) -> MessageChunk:
        """
        Load messages with pagination and caching
        
        Args:
            session_id: Session identifier
            page: Page number (0-based)
            force_refresh: Force refresh from database
        
        Returns:
            MessageChunk with paginated messages
        """
        cache_key = f"messages_page_{session_id}_{page}_{self.messages_per_page}"
        
        # Try cache first unless force refresh
        if not force_refresh:
            cached_chunk = ui_cache.get(cache_key)
            if cached_chunk:
                logger.debug(f"Cache hit for message page {page}")
                return MessageChunk(**cached_chunk)
        
        try:
            # Load all messages from database
            all_messages = self._load_all_messages(session_id, force_refresh)
            
            # Calculate pagination
            total_count = len(all_messages)
            start_idx = page * self.messages_per_page
            end_idx = min(start_idx + self.messages_per_page, total_count)
            
            # Get messages for current page
            page_messages = all_messages[start_idx:end_idx] if all_messages else []
            
            # Create message chunk
            chunk = MessageChunk(
                messages=page_messages,
                start_index=start_idx,
                end_index=end_idx,
                total_count=total_count,
                has_more_before=start_idx > 0,
                has_more_after=end_idx < total_count
            )
            
            # Cache the chunk
            ui_cache.set(cache_key, chunk.__dict__, ttl=self.cache_ttl)
            st.session_state.message_cache_keys.add(cache_key)
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error loading paginated messages: {e}")
            return MessageChunk([], 0, 0, 0, False, False)
    
    @cached_ui_component(ttl=60, key_func=lambda self, session_id, force_refresh=False: f"all_messages_{session_id}")
    def _load_all_messages(self, session_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Load all messages for a session with caching"""
        try:
            if not st.session_state.get('auth_service'):
                return []
            
            success, messages = st.session_state.auth_service.get_session_messages(session_id)
            
            if success and messages:
                # Add message IDs and processing metadata
                processed_messages = []
                for i, msg in enumerate(messages):
                    processed_msg = msg.copy()
                    processed_msg['message_id'] = self._generate_message_id(msg, i)
                    processed_msg['processed_at'] = datetime.now().isoformat()
                    processed_messages.append(processed_msg)
                
                return processed_messages
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading all messages: {e}")
            return []
    
    def _generate_message_id(self, message: Dict[str, Any], index: int) -> str:
        """Generate unique message ID for tracking"""
        content = message.get('content', '')
        role = message.get('role', '')
        timestamp = message.get('timestamp', str(index))
        
        id_string = f"{role}_{content[:50]}_{timestamp}_{index}"
        return hashlib.md5(id_string.encode()).hexdigest()[:12]
    
    @monitor_ui_component("message_handler", "render_messages")
    def render_messages_optimized(self, session_id: str, container=None) -> Dict[str, Any]:
        """
        Render messages with optimization and pagination
        
        Args:
            session_id: Session identifier
            container: Streamlit container to render in
        
        Returns:
            Rendering statistics
        """
        pagination = st.session_state.message_pagination
        current_page = pagination['current_page']
        
        # Load current page
        chunk = self.load_messages_paginated(session_id, current_page)
        
        # Update pagination info
        pagination['total_messages'] = chunk.total_count
        
        # Render pagination controls
        self._render_pagination_controls(chunk)
        
        # Render messages
        render_stats = self._render_message_chunk(chunk, container)
        
        # Update last message tracking for incremental updates
        if chunk.messages:
            last_message = chunk.messages[-1]
            pagination['last_message_id'] = last_message.get('message_id')
        
        return render_stats
    
    def _render_pagination_controls(self, chunk: MessageChunk):
        """Render pagination controls"""
        if chunk.total_count <= self.messages_per_page:
            return
        
        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
        
        pagination = st.session_state.message_pagination
        current_page = pagination['current_page']
        total_pages = (chunk.total_count + self.messages_per_page - 1) // self.messages_per_page
        
        with col1:
            if st.button("⬅️ Anterior", disabled=not chunk.has_more_before, key="msg_prev"):
                track_user_interaction("pagination", "previous_page")
                pagination['current_page'] = max(0, current_page - 1)
                st.rerun()
        
        with col2:
            st.caption(f"Página {current_page + 1} de {total_pages}")
        
        with col3:
            st.caption(f"Mensajes {chunk.start_index + 1}-{chunk.end_index} de {chunk.total_count}")
        
        with col4:
            if st.button("Siguiente ➡️", disabled=not chunk.has_more_after, key="msg_next"):
                track_user_interaction("pagination", "next_page")
                pagination['current_page'] = current_page + 1
                st.rerun()
        
        # Jump to page
        if total_pages > 5:
            with st.expander("🔍 Ir a página específica"):
                target_page = st.number_input(
                    "Número de página",
                    min_value=1,
                    max_value=total_pages,
                    value=current_page + 1,
                    key="jump_to_page"
                ) - 1
                
                if st.button("Ir", key="jump_btn"):
                    track_user_interaction("pagination", "jump_to_page", {"target_page": target_page})
                    pagination['current_page'] = target_page
                    st.rerun()
    
    def _render_message_chunk(self, chunk: MessageChunk, container=None) -> Dict[str, Any]:
        """Render a chunk of messages efficiently"""
        render_stats = {
            'messages_rendered': 0,
            'long_messages': 0,
            'render_time_ms': 0
        }
        
        start_time = datetime.now()
        
        # Use provided container or create new one
        if container is None:
            container = st.container()
        
        with container:
            for i, message in enumerate(chunk.messages):
                try:
                    self._render_single_message(message, i)
                    render_stats['messages_rendered'] += 1
                    
                    # Track long messages
                    content_length = len(message.get('content', ''))
                    if content_length > self.max_message_preview_length:
                        render_stats['long_messages'] += 1
                        
                except Exception as e:
                    logger.error(f"Error rendering message {i}: {e}")
                    st.error(f"Error renderizando mensaje: {str(e)}")
        
        # Calculate render time
        end_time = datetime.now()
        render_stats['render_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return render_stats
    
    def _render_single_message(self, message: Dict[str, Any], index: int):
        """Render a single message with optimization"""
        role = message.get('role', 'user')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        message_id = message.get('message_id', f'msg_{index}')
        
        with st.chat_message(role, avatar=self._get_avatar(role)):
            # Handle long messages with preview/expand
            if len(content) > self.max_message_preview_length:
                self._render_long_message(content, message_id)
            else:
                st.markdown(content)
            
            # Message metadata
            self._render_message_metadata(message, index)
    
    def _render_long_message(self, content: str, message_id: str):
        """Render long message with preview and expand option"""
        preview = content[:self.max_message_preview_length] + "..."
        
        # Show preview
        st.markdown(preview)
        
        # Expandable full content
        with st.expander(f"📄 Ver mensaje completo ({len(content)} caracteres)", expanded=False):
            st.markdown(content)
            
            # Copy button for long messages
            if st.button("📋 Copiar", key=f"copy_{message_id}"):
                track_user_interaction("copy", "long_message", {"message_id": message_id})
                # In a real implementation, this would copy to clipboard
                st.success("Contenido copiado (simulado)")
    
    def _render_message_metadata(self, message: Dict[str, Any], index: int):
        """Render message metadata efficiently"""
        metadata = message.get('metadata', {})
        timestamp = message.get('timestamp', '')
        
        # Basic timestamp
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%H:%M:%S')
                st.caption(f"🕒 {formatted_time}")
            except:
                st.caption(f"🕒 {timestamp[:19]}")
        
        # Extended metadata in expander for assistant messages
        if message.get('role') == 'assistant' and metadata:
            with st.expander("ℹ️ Detalles técnicos", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    if metadata.get('model_used'):
                        st.caption(f"🤖 Modelo: {metadata['model_used']}")
                    if metadata.get('response_time_ms'):
                        st.caption(f"⏱️ Tiempo: {metadata['response_time_ms']:.0f}ms")
                
                with col2:
                    if metadata.get('cached'):
                        st.caption("🚀 Respuesta en caché")
                    if metadata.get('sources'):
                        st.caption(f"📚 {len(metadata['sources'])} fuentes")
                    if metadata.get('tokens_used'):
                        st.caption(f"🔤 Tokens: {metadata['tokens_used']}")
    
    def _get_avatar(self, role: str) -> Optional[str]:
        """Get avatar for message role"""
        avatars = {
            'user': '👤',
            'assistant': '🤖',
            'system': '⚙️'
        }
        return avatars.get(role)
    
    def add_message_incremental(self, session_id: str, role: str, content: str, 
                              metadata: Dict[str, Any] = None) -> bool:
        """
        Add message with incremental update
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            metadata: Additional metadata
        
        Returns:
            Success status
        """
        try:
            # Save to database
            if st.session_state.get('auth_service'):
                st.session_state.auth_service.save_message(session_id, content, role)
            
            # Invalidate relevant caches
            self._invalidate_message_caches(session_id)
            
            # Update pagination to show latest messages
            pagination = st.session_state.message_pagination
            
            # If auto-scroll is enabled, go to last page
            if pagination.get('auto_scroll_enabled', True):
                # Calculate new last page after adding message
                new_total = pagination.get('total_messages', 0) + 1
                last_page = max(0, (new_total - 1) // self.messages_per_page)
                pagination['current_page'] = last_page
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding message incrementally: {e}")
            return False
    
    def _invalidate_message_caches(self, session_id: str):
        """Invalidate message caches for a session"""
        # Invalidate all cached pages for this session
        cache_keys_to_remove = []
        for cache_key in st.session_state.message_cache_keys:
            if f"messages_page_{session_id}" in cache_key:
                cache_keys_to_remove.append(cache_key)
        
        for cache_key in cache_keys_to_remove:
            ui_cache.invalidate(cache_key)
            st.session_state.message_cache_keys.discard(cache_key)
        
        # Also invalidate all messages cache
        ui_cache.invalidate(f"all_messages_{session_id}")
    
    def check_for_new_messages(self, session_id: str) -> bool:
        """
        Check if there are new messages since last load
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if new messages are available
        """
        try:
            # Get current message count from cache or database
            current_chunk = self.load_messages_paginated(session_id, 0)
            pagination = st.session_state.message_pagination
            
            last_known_count = pagination.get('total_messages', 0)
            current_count = current_chunk.total_count
            
            return current_count > last_known_count
            
        except Exception as e:
            logger.error(f"Error checking for new messages: {e}")
            return False
    
    def get_message_stats(self, session_id: str) -> Dict[str, Any]:
        """Get message statistics for the session"""
        try:
            all_messages = self._load_all_messages(session_id)
            
            user_messages = [m for m in all_messages if m.get('role') == 'user']
            assistant_messages = [m for m in all_messages if m.get('role') == 'assistant']
            
            # Calculate average response time
            response_times = []
            for msg in assistant_messages:
                metadata = msg.get('metadata', {})
                if metadata.get('response_time_ms'):
                    response_times.append(metadata['response_time_ms'])
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'total_messages': len(all_messages),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
                'average_response_time_ms': avg_response_time,
                'cached_responses': len([m for m in assistant_messages 
                                       if m.get('metadata', {}).get('cached')]),
                'total_pages': (len(all_messages) + self.messages_per_page - 1) // self.messages_per_page
            }
            
        except Exception as e:
            logger.error(f"Error getting message stats: {e}")
            return {}
    
    def clear_message_cache(self, session_id: str = None):
        """Clear message cache for session or all sessions"""
        if session_id:
            self._invalidate_message_caches(session_id)
        else:
            # Clear all message caches
            ui_cache.invalidate("messages_page_")
            ui_cache.invalidate("all_messages_")
            st.session_state.message_cache_keys.clear()
    
    def export_messages(self, session_id: str, format: str = "txt") -> str:
        """Export messages in specified format"""
        try:
            all_messages = self._load_all_messages(session_id)
            
            if format == "txt":
                return self._export_as_text(all_messages)
            elif format == "json":
                return self._export_as_json(all_messages)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting messages: {e}")
            return f"Error exporting messages: {str(e)}"
    
    def _export_as_text(self, messages: List[Dict[str, Any]]) -> str:
        """Export messages as plain text"""
        lines = [
            f"Chat Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]
        
        for msg in messages:
            role = "Usuario" if msg.get('role') == 'user' else "Asistente"
            timestamp = msg.get('timestamp', '')[:19].replace('T', ' ')
            content = msg.get('content', '')
            
            lines.extend([
                f"[{timestamp}] {role}:",
                content,
                "-" * 40,
                ""
            ])
        
        return "\n".join(lines)
    
    def _export_as_json(self, messages: List[Dict[str, Any]]) -> str:
        """Export messages as JSON"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_messages': len(messages),
            'messages': messages
        }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)

# Global message handler instance
message_handler = OptimizedMessageHandler()