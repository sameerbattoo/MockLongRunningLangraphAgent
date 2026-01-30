"""Tests for the LangGraph Athena agent."""
import pytest
from unittest.mock import Mock, patch
from athena_mock import AthenaQuery, QueryStatus
from agent import (
    submit_athena_query,
    poll_athena_status,
    fetch_athena_results,
    should_continue_polling,
    create_agent_graph
)


class TestAthenaQuery:
    """Tests for the mock Athena client."""
    
    def test_execute_sql_returns_query_id(self):
        """Test that ExecuteSQL returns a query ID."""
        client = AthenaQuery()
        query_id = client.ExecuteSQL("SELECT * FROM test", sleep_seconds=1)
        assert query_id is not None
        assert isinstance(query_id, str)
        assert len(query_id) > 0
    
    def test_query_status_initially_running(self):
        """Test that query status is initially RUNNING."""
        client = AthenaQuery()
        query_id = client.ExecuteSQL("SELECT * FROM test", sleep_seconds=5)
        status = client.get_query_status(query_id)
        assert status == QueryStatus.RUNNING
    
    def test_query_status_succeeds_after_duration(self):
        """Test that query status becomes SUCCEEDED after sleep duration."""
        client = AthenaQuery()
        query_id = client.ExecuteSQL("SELECT * FROM test", sleep_seconds=0)
        status = client.get_query_status(query_id)
        assert status == QueryStatus.SUCCEEDED
    
    def test_get_query_results(self):
        """Test retrieving query results."""
        client = AthenaQuery()
        query_id = client.ExecuteSQL("SELECT * FROM test", sleep_seconds=0)
        client.get_query_status(query_id)  # Trigger completion
        results = client.get_query_results(query_id)
        assert isinstance(results, list)
        assert len(results) == 3
        assert results[0]["name"] == "Alice"


class TestAgentNodes:
    """Tests for individual agent nodes."""
    
    def test_submit_athena_query_node(self):
        """Test Node A: submit_athena_query."""
        initial_state = {
            "sql_query": "SELECT * FROM users",
            "query_execution_id": "",
            "athena_status": "",
            "retry_count": 0,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        result = submit_athena_query(initial_state)
        
        assert result["query_execution_id"] != ""
        assert result["athena_status"] == "RUNNING"
        assert result["retry_count"] == 0
    
    @patch('agent.athena_client')
    def test_poll_athena_status_node(self, mock_client):
        """Test Node B: poll_athena_status."""
        mock_client.get_query_status.return_value = QueryStatus.SUCCEEDED
        
        state = {
            "sql_query": "SELECT * FROM test",
            "query_execution_id": "test-query-id",
            "athena_status": "RUNNING",
            "retry_count": 0,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        result = poll_athena_status(state)
        
        assert result["athena_status"] == "SUCCEEDED"
        assert result["retry_count"] == 1
        mock_client.get_query_status.assert_called_once_with("test-query-id")
    
    @patch('agent.athena_client')
    def test_fetch_athena_results_node(self, mock_client):
        """Test Node C: fetch_athena_results."""
        mock_results = [{"id": 1, "name": "Test"}]
        mock_client.get_query_results.return_value = mock_results
        
        state = {
            "sql_query": "SELECT * FROM test",
            "query_execution_id": "test-query-id",
            "athena_status": "SUCCEEDED",
            "retry_count": 1,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        result = fetch_athena_results(state)
        
        assert "analysis_result" in result
        assert result["analysis_result"]["total_rows"] == 1
        assert "data" in result["analysis_result"]
        mock_client.get_query_results.assert_called_once_with("test-query-id")


class TestConditionalRouting:
    """Tests for conditional edge routing."""
    
    def test_should_continue_polling_on_success(self):
        """Test routing when query succeeds."""
        state = {
            "athena_status": "SUCCEEDED",
            "retry_count": 2,
            "max_retries": 10
        }
        
        result = should_continue_polling(state)
        assert result == "fetch_results"
    
    def test_should_continue_polling_on_failure(self):
        """Test routing when query fails."""
        state = {
            "athena_status": "FAILED",
            "retry_count": 2,
            "max_retries": 10
        }
        
        result = should_continue_polling(state)
        assert result == "end"
    
    def test_should_continue_polling_on_max_retries(self):
        """Test routing when max retries reached."""
        state = {
            "athena_status": "RUNNING",
            "retry_count": 10,
            "max_retries": 10
        }
        
        result = should_continue_polling(state)
        assert result == "end"
    
    @patch('time.sleep')
    def test_should_continue_polling_on_running(self, mock_sleep):
        """Test routing when query still running."""
        state = {
            "athena_status": "RUNNING",
            "retry_count": 2,
            "max_retries": 10
        }
        
        result = should_continue_polling(state)
        assert result == "poll_status"
        mock_sleep.assert_called_once_with(2)


class TestAgentGraph:
    """Integration tests for the complete agent graph."""
    
    def test_create_agent_graph(self):
        """Test that agent graph is created successfully."""
        graph = create_agent_graph()
        assert graph is not None
    
    def test_agent_graph_execution_success(self):
        """Test complete agent execution with successful query."""
        graph = create_agent_graph()
        
        initial_state = {
            "sql_query": "SELECT * FROM users WHERE active = true",
            "query_execution_id": "",
            "athena_status": "",
            "retry_count": 0,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        # Use fast query for testing
        with patch.object(AthenaQuery, 'ExecuteSQL') as mock_execute:
            mock_execute.return_value = "test-query-id"
            
            with patch.object(AthenaQuery, 'get_query_status') as mock_status:
                mock_status.return_value = QueryStatus.SUCCEEDED
                
                with patch.object(AthenaQuery, 'get_query_results') as mock_results:
                    mock_results.return_value = [{"id": 1, "name": "Test"}]
                    
                    final_state = graph.invoke(initial_state)
                    
                    assert final_state["athena_status"] == "SUCCEEDED"
                    assert final_state["analysis_result"]["total_rows"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
