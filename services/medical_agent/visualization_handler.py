"""
Visualization Handler - Manages visualization display and storage

This module handles the processing and delivery of visualizations generated
by the Visualization Agent to the frontend (Streamlit).
"""

import logging
import base64
import io
from typing import Dict, Any, List, Optional
from datetime import datetime
import streamlit as st
from PIL import Image

logger = logging.getLogger(__name__)


class VisualizationHandler:
    """
    Handles visualization processing and display for the frontend.
    
    This class manages:
    - Extraction of visualizations from agent responses
    - Conversion of base64 images to displayable format
    - Storage of visualizations in session state
    - Display of visualizations in Streamlit
    """
    
    def __init__(self):
        """Initialize the visualization handler."""
        self.visualization_history = []
        
    def process_agent_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process agent response and extract visualizations.
        
        Args:
            response: Response dictionary from agent
            
        Returns:
            Processed response with visualization metadata
        """
        try:
            if not response.get('success', False):
                return response
            
            # Extract visualizations
            visualizations = response.get('visualizations', [])
            
            if not visualizations:
                return response
            
            # Process each visualization
            processed_vizs = []
            for viz in visualizations:
                processed_viz = self._process_visualization(viz)
                if processed_viz:
                    processed_vizs.append(processed_viz)
            
            # Update response with processed visualizations
            response['visualizations'] = processed_vizs
            response['has_visualizations'] = len(processed_vizs) > 0
            
            # Store in history
            self._store_in_history(processed_vizs)
            
            logger.info(f"Processed {len(processed_vizs)} visualizations")
            return response
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            return response
    
    def _process_visualization(self, viz: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single visualization.
        
        Args:
            viz: Visualization dictionary
            
        Returns:
            Processed visualization or None if error
        """
        try:
            viz_type = viz.get('type', 'image')
            data = viz.get('data', '')
            
            if viz_type == 'image' and data.startswith('data:image/'):
                # Extract base64 data
                base64_data = self._extract_base64_from_data_url(data)
                
                if base64_data:
                    return {
                        'type': 'image',
                        'format': 'png',
                        'base64_data': base64_data,
                        'data_url': data,
                        'timestamp': datetime.now().isoformat(),
                        'size': len(base64_data)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing visualization: {e}")
            return None
    
    def _extract_base64_from_data_url(self, data_url: str) -> Optional[str]:
        """
        Extract base64 data from data URL.
        
        Args:
            data_url: Data URL string (e.g., "data:image/png;base64,...")
            
        Returns:
            Base64 string or None
        """
        try:
            if ';base64,' in data_url:
                return data_url.split(';base64,')[1]
            return None
        except Exception as e:
            logger.error(f"Error extracting base64: {e}")
            return None
    
    def _store_in_history(self, visualizations: List[Dict[str, Any]]):
        """Store visualizations in history."""
        for viz in visualizations:
            self.visualization_history.append({
                'visualization': viz,
                'timestamp': datetime.now().isoformat()
            })
        
        # Keep only last 50 visualizations
        if len(self.visualization_history) > 50:
            self.visualization_history = self.visualization_history[-50:]
    
    def display_visualizations(
        self,
        visualizations: List[Dict[str, Any]],
        container=None
    ):
        """
        Display visualizations in Streamlit.
        
        Args:
            visualizations: List of visualization dictionaries
            container: Optional Streamlit container to display in
        """
        if not visualizations:
            return
        
        display_func = container if container else st
        
        for i, viz in enumerate(visualizations, 1):
            try:
                self._display_single_visualization(viz, display_func, i)
            except Exception as e:
                logger.error(f"Error displaying visualization {i}: {e}")
                display_func.error(f"Error mostrando visualización {i}")
    
    def _display_single_visualization(
        self,
        viz: Dict[str, Any],
        display_func,
        index: int
    ):
        """
        Display a single visualization.
        
        Args:
            viz: Visualization dictionary
            display_func: Streamlit display function
            index: Visualization index
        """
        viz_type = viz.get('type', 'image')
        
        if viz_type == 'image':
            # Get base64 data
            base64_data = viz.get('base64_data')
            
            if not base64_data:
                logger.warning(f"No base64 data for visualization {index}")
                return
            
            # Decode base64 to image
            try:
                image_bytes = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Display with caption
                display_func.image(
                    image,
                    caption=f"Visualización {index}",
                    use_column_width=True
                )
                
                # Add download button
                self._add_download_button(
                    image_bytes,
                    f"visualization_{index}.png",
                    display_func
                )
                
            except Exception as e:
                logger.error(f"Error decoding image: {e}")
                display_func.error(f"Error decodificando imagen {index}")
    
    def _add_download_button(
        self,
        image_bytes: bytes,
        filename: str,
        display_func
    ):
        """
        Add download button for visualization.
        
        Args:
            image_bytes: Image bytes
            filename: Filename for download
            display_func: Streamlit display function
        """
        try:
            display_func.download_button(
                label="📥 Descargar visualización",
                data=image_bytes,
                file_name=filename,
                mime="image/png",
                key=f"download_{filename}_{datetime.now().timestamp()}"
            )
        except Exception as e:
            logger.error(f"Error adding download button: {e}")
    
    def get_visualization_history(self) -> List[Dict[str, Any]]:
        """Get visualization history."""
        return self.visualization_history.copy()
    
    def clear_history(self):
        """Clear visualization history."""
        self.visualization_history.clear()
        logger.info("Visualization history cleared")


class StreamlitVisualizationDisplay:
    """
    Streamlit-specific visualization display utilities.
    
    This class provides helper methods for displaying visualizations
    in Streamlit with proper formatting and styling.
    """
    
    @staticmethod
    def display_with_expander(
        visualizations: List[Dict[str, Any]],
        title: str = "📊 Visualizaciones",
        expanded: bool = True
    ):
        """
        Display visualizations in an expander.
        
        Args:
            visualizations: List of visualizations
            title: Expander title
            expanded: Whether expander is initially expanded
        """
        if not visualizations:
            return
        
        with st.expander(title, expanded=expanded):
            handler = VisualizationHandler()
            handler.display_visualizations(visualizations)
    
    @staticmethod
    def display_in_columns(
        visualizations: List[Dict[str, Any]],
        columns: int = 2
    ):
        """
        Display visualizations in columns.
        
        Args:
            visualizations: List of visualizations
            columns: Number of columns
        """
        if not visualizations:
            return
        
        cols = st.columns(columns)
        handler = VisualizationHandler()
        
        for i, viz in enumerate(visualizations):
            col_index = i % columns
            with cols[col_index]:
                handler._display_single_visualization(viz, st, i + 1)
    
    @staticmethod
    def display_in_tabs(
        visualizations: List[Dict[str, Any]],
        tab_names: Optional[List[str]] = None
    ):
        """
        Display visualizations in tabs.
        
        Args:
            visualizations: List of visualizations
            tab_names: Optional list of tab names
        """
        if not visualizations:
            return
        
        if not tab_names:
            tab_names = [f"Visualización {i+1}" for i in range(len(visualizations))]
        
        tabs = st.tabs(tab_names)
        handler = VisualizationHandler()
        
        for i, (tab, viz) in enumerate(zip(tabs, visualizations)):
            with tab:
                handler._display_single_visualization(viz, st, i + 1)



