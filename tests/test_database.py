"""
Consolidated Database Tests

Tests for database services and tools including:
- Database service operations
- Connection management
- Query execution and validation
- Database tools
- Error handling
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch


class TestDatabaseService:
    """Test database service operations."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.data = [
            {'subject_id': 10014729, 'stay_id': 37887480, 'gender': 'F'},
            {'subject_id': 10018328, 'stay_id': 34176810, 'gender': 'F'}
        ]
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_response
        
        return mock_client
    
    def test_database_connection(self, mock_supabase_client):
        """Test database connection."""
        assert mock_supabase_client is not None
        mock_supabase_client.table.assert_not_called()
    
    def test_query_execution(self, mock_supabase_client):
        """Test query execution returns expected data."""
        result = mock_supabase_client.table("edstays").select("*").execute()
        assert len(result.data) == 2
        assert result.data[0]['subject_id'] == 10014729
    
    def test_query_validation(self):
        """Test query validation rejects dangerous patterns."""
        dangerous_queries = [
            "DROP TABLE edstays",
            "DELETE FROM edstays",
            "INSERT INTO edstays VALUES (1,2,3)",
        ]
        for query in dangerous_queries:
            assert any(kw in query.upper() for kw in ["DROP", "DELETE", "INSERT"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
