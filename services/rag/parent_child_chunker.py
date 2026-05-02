"""
Parent-Child Chunker for RAG System

This module implements hierarchical chunking where large parent chunks provide
context and small child chunks enable precise search.
"""

import uuid
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ParentChildChunker:
    """
    Chunker that creates hierarchical parent-child chunk relationships.
    
    Parent chunks (1500-2000 chars) provide full context.
    Child chunks (300-500 chars) enable precise search.
    """
    
    def __init__(self, parent_size: int = 3000, child_size: int = 800):
        """
        Initialize the ParentChildChunker.
        
        Args:
            parent_size: Target size for parent chunks (default 3000)
            child_size: Target size for child chunks (default 800)
        """
        self.parent_size = parent_size
        self.child_size = child_size
        
        # Validate sizes
        if not (1000 <= parent_size <= 6000):
            logger.warning(
                f"parent_size {parent_size} outside recommended range [1000, 6000]"
            )
        if not (200 <= child_size <= 1500):
            logger.warning(
                f"child_size {child_size} outside recommended range [200, 1500]"
            )
    
    def chunk_document(
        self, 
        text: str, 
        metadata: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Chunk a document into parent and child chunks with linked metadata.
        
        Args:
            text: Document text to chunk
            metadata: Metadata for the document (filename, document_id, etc.)
            
        Returns:
            Tuple of (parent_chunks, child_chunks) where each chunk is a dict with:
                - chunk_id: Unique identifier
                - content: Chunk text
                - metadata: ChunkMetadata dict
                
        Requirements: 1.1, 1.3
        """
        if not text or not text.strip():
            logger.warning("Empty document provided to chunk_document")
            return [], []
        
        # Sanitize null bytes and control characters that PostgreSQL rejects (error 22P05)
        import re
        text = text.replace("\x00", "")
        text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        
        parent_chunks = []
        child_chunks = []
        
        # Extract document metadata
        document_id = metadata.get('document_id', str(uuid.uuid4()))
        filename = metadata.get('filename', 'unknown')
        
        # Create parent chunks
        parent_chunk_texts = self._split_text(text, self.parent_size)
        
        for parent_idx, parent_text in enumerate(parent_chunk_texts):
            parent_id = f"parent_{document_id}_{parent_idx}"
            parent_start = sum(len(t) for t in parent_chunk_texts[:parent_idx])
            parent_end = parent_start + len(parent_text)
            
            parent_chunk = {
                'chunk_id': parent_id,
                'content': parent_text,
                'metadata': {
                    'chunk_id': parent_id,
                    'parent_id': None,
                    'is_parent': True,
                    'document_id': document_id,
                    'filename': filename,
                    'chunk_index': parent_idx,
                    'char_start': parent_start,
                    'char_end': parent_end
                }
            }
            parent_chunks.append(parent_chunk)
            
            # Create child chunks for this parent
            child_chunk_texts = self._split_text(parent_text, self.child_size)
            
            for child_idx, child_text in enumerate(child_chunk_texts):
                child_id = f"child_{document_id}_{parent_idx}_{child_idx}"
                child_start = parent_start + sum(
                    len(t) for t in child_chunk_texts[:child_idx]
                )
                child_end = child_start + len(child_text)
                
                child_chunk = {
                    'chunk_id': child_id,
                    'content': child_text,
                    'metadata': {
                        'chunk_id': child_id,
                        'parent_id': parent_id,
                        'is_parent': False,
                        'document_id': document_id,
                        'filename': filename,
                        'chunk_index': child_idx,
                        'char_start': child_start,
                        'char_end': child_end
                    }
                }
                child_chunks.append(child_chunk)
        
        logger.info(
            f"Created {len(parent_chunks)} parent chunks and "
            f"{len(child_chunks)} child chunks for document {document_id}"
        )
        
        return parent_chunks, child_chunks
    
    def _split_text(self, text: str, target_size: int) -> List[str]:
        """
        Split text into chunks of approximately target_size.
        
        Tries to split on sentence boundaries when possible.
        Merges small trailing chunks with previous chunk to avoid very small chunks.
        
        Args:
            text: Text to split
            target_size: Target size for each chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= target_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split on sentence boundaries (., !, ?)
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            # If adding this sentence would exceed target size
            if len(current_chunk) + len(sentence) > target_size:
                # If current chunk is not empty, save it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Sentence itself is too long, split it by words
                    if len(sentence) > target_size:
                        word_chunks = self._split_by_words(sentence, target_size)
                        chunks.extend(word_chunks[:-1])
                        current_chunk = word_chunks[-1]
                    else:
                        current_chunk = sentence
            else:
                current_chunk += sentence
        
        # Add remaining chunk
        if current_chunk:
            current_chunk = current_chunk.strip()
            
            # If the last chunk is too small (less than 40% of target), 
            # merge it with the previous chunk
            min_chunk_size = int(target_size * 0.4)
            if len(chunks) > 0 and len(current_chunk) < min_chunk_size:
                chunks[-1] = chunks[-1] + " " + current_chunk
            else:
                chunks.append(current_chunk)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        import re
        # Split on sentence boundaries but keep the delimiter
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Recombine sentences with their delimiters
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        
        # Add last sentence if odd number
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        
        return [s for s in result if s.strip()]
    
    def _split_by_words(self, text: str, target_size: int) -> List[str]:
        """
        Split text by words when sentence splitting isn't enough.
        
        Args:
            text: Text to split
            target_size: Target size for each chunk
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > target_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Single word is too long, just add it
                    chunks.append(word)
            else:
                current_chunk += (" " if current_chunk else "") + word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def get_parent_for_child(
        self, 
        child_id: str, 
        parents: Dict[str, Dict]
    ) -> Optional[Dict]:
        """
        Retrieve parent chunk for a given child chunk ID.
        
        Args:
            child_id: ID of the child chunk
            parents: Dictionary mapping parent_id to parent chunk dict
            
        Returns:
            Parent chunk dict or None if not found
            
        Requirements: 1.2
        """
        # Extract parent_id from child_id
        # Format: child_{document_id}_{parent_idx}_{child_idx}
        parts = child_id.split('_')
        
        if len(parts) < 4 or parts[0] != 'child':
            logger.warning(f"Invalid child_id format: {child_id}")
            return None
        
        # Reconstruct parent_id: parent_{document_id}_{parent_idx}
        document_id = '_'.join(parts[1:-2])
        parent_idx = parts[-2]
        parent_id = f"parent_{document_id}_{parent_idx}"
        
        parent = parents.get(parent_id)
        
        if parent is None:
            logger.warning(f"Parent {parent_id} not found for child {child_id}")
        
        return parent
    
    def pretty_print_hierarchy(
        self, 
        parents: List[Dict], 
        children: List[Dict]
    ) -> str:
        """
        Generate readable representation of chunk hierarchy for debugging.
        
        Args:
            parents: List of parent chunk dicts
            children: List of child chunk dicts
            
        Returns:
            Pretty-printed string representation of hierarchy
            
        Requirements: 1.4
        """
        lines = []
        lines.append("=== Chunk Hierarchy ===")
        lines.append("")
        
        # Group children by parent_id
        children_by_parent = {}
        for child in children:
            parent_id = child['metadata']['parent_id']
            if parent_id not in children_by_parent:
                children_by_parent[parent_id] = []
            children_by_parent[parent_id].append(child)
        
        # Print each parent with its children
        for parent in parents:
            parent_id = parent['chunk_id']
            parent_meta = parent['metadata']
            
            lines.append(f"PARENT: {parent_id}")
            lines.append(f"  Document: {parent_meta['filename']}")
            lines.append(f"  Index: {parent_meta['chunk_index']}")
            lines.append(f"  Range: [{parent_meta['char_start']}, {parent_meta['char_end']})")
            lines.append(f"  Length: {len(parent['content'])} chars")
            lines.append(f"  Content: {parent['content'][:100]}...")
            lines.append("")
            
            # Print children
            parent_children = children_by_parent.get(parent_id, [])
            for child in parent_children:
                child_meta = child['metadata']
                lines.append(f"  CHILD: {child['chunk_id']}")
                lines.append(f"    Index: {child_meta['chunk_index']}")
                lines.append(f"    Range: [{child_meta['char_start']}, {child_meta['char_end']})")
                lines.append(f"    Length: {len(child['content'])} chars")
                lines.append(f"    Content: {child['content'][:80]}...")
                lines.append("")
        
        lines.append("=== End Hierarchy ===")
        
        return "\n".join(lines)
    
    def parse_hierarchy(self, hierarchy_str: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse pretty-printed hierarchy back to chunk structures.
        
        Args:
            hierarchy_str: Pretty-printed hierarchy string
            
        Returns:
            Tuple of (parent_chunks, child_chunks)
            
        Requirements: 1.5
        """
        parents = []
        children = []
        
        lines = hierarchy_str.split('\n')
        
        current_parent = None
        current_child = None
        
        for line in lines:
            line = line.rstrip()
            
            if line.startswith("PARENT: "):
                # Save previous parent if exists
                if current_parent is not None:
                    parents.append(current_parent)
                
                # Save previous child if exists
                if current_child is not None:
                    children.append(current_child)
                    current_child = None
                
                # Start new parent
                chunk_id = line.replace("PARENT: ", "").strip()
                current_parent = {
                    'chunk_id': chunk_id,
                    'content': '',
                    'metadata': {
                        'chunk_id': chunk_id,
                        'parent_id': None,
                        'is_parent': True
                    }
                }
            
            elif line.startswith("  CHILD: "):
                # Save previous child if exists
                if current_child is not None:
                    children.append(current_child)
                
                # Start new child
                chunk_id = line.replace("  CHILD: ", "").strip()
                current_child = {
                    'chunk_id': chunk_id,
                    'content': '',
                    'metadata': {
                        'chunk_id': chunk_id,
                        'parent_id': current_parent['chunk_id'] if current_parent else None,
                        'is_parent': False
                    }
                }
            
            elif line.startswith("  Document: ") and current_parent and not current_child:
                filename = line.replace("  Document: ", "").strip()
                current_parent['metadata']['filename'] = filename
            
            elif line.startswith("  Index: ") and current_parent and not current_child:
                index = int(line.replace("  Index: ", "").strip())
                current_parent['metadata']['chunk_index'] = index
            
            elif line.startswith("    Index: ") and current_child:
                index = int(line.replace("    Index: ", "").strip())
                current_child['metadata']['chunk_index'] = index
            
            elif line.startswith("  Range: ") and current_parent and not current_child:
                range_str = line.replace("  Range: ", "").strip()
                # Parse [start, end)
                range_str = range_str.replace('[', '').replace(')', '')
                start, end = map(int, range_str.split(','))
                current_parent['metadata']['char_start'] = start
                current_parent['metadata']['char_end'] = end
            
            elif line.startswith("    Range: ") and current_child:
                range_str = line.replace("    Range: ", "").strip()
                range_str = range_str.replace('[', '').replace(')', '')
                start, end = map(int, range_str.split(','))
                current_child['metadata']['char_start'] = start
                current_child['metadata']['char_end'] = end
            
            elif line.startswith("  Content: ") and current_parent and not current_child:
                content = line.replace("  Content: ", "").strip()
                # Remove trailing ...
                if content.endswith('...'):
                    content = content[:-3]
                current_parent['content'] = content
            
            elif line.startswith("    Content: ") and current_child:
                content = line.replace("    Content: ", "").strip()
                if content.endswith('...'):
                    content = content[:-3]
                current_child['content'] = content
        
        # Save last chunks
        if current_parent is not None:
            parents.append(current_parent)
        if current_child is not None:
            children.append(current_child)
        
        # Extract document_id from chunk_ids
        for parent in parents:
            if 'document_id' not in parent['metadata']:
                # Extract from chunk_id: parent_{document_id}_{parent_idx}
                parts = parent['chunk_id'].split('_')
                if len(parts) >= 3:
                    document_id = '_'.join(parts[1:-1])
                    parent['metadata']['document_id'] = document_id
        
        for child in children:
            if 'document_id' not in child['metadata']:
                # Extract from chunk_id: child_{document_id}_{parent_idx}_{child_idx}
                parts = child['chunk_id'].split('_')
                if len(parts) >= 4:
                    document_id = '_'.join(parts[1:-2])
                    child['metadata']['document_id'] = document_id
        
        return parents, children
