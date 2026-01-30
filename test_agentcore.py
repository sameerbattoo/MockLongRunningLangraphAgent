"""Tests for the AgentCore-compatible agent wrapper."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from agentcore_agent import invoke, create_agent_graph


class TestAgentCoreWrapper:
    """Tests for the AgentCore entrypoint."""
    
    @patch('agentcore_agent.graph')
    def test_invoke_with_sql_query(self, mock_graph):
        """Test invoke with explicit SQL query."""
        # Mock the graph execution
        mock_graph.invoke.return_value = {
            "sql_query": "SELECT * FROM users",
            "query_execution_id": "test-id",
            "athena_status": "SUCCEEDED",
            "retry_count": 3,
            "max_retries": 10,
            "analysis_result": {
                "total_rows": 5,
                "summary": "Retrieved 5 rows",
                "data": [{"id": 1, "name": "Test"}]
            },
            "error": ""
        }
        
        payload = {
            "sql_query": "SELECT * FROM users",
            "max_retries": 10
        }
        
        result = invoke(payload)
        
        assert result["status"] == "success"
        assert result["query_id"] == "test-id"
        assert result["polls"] == 3
        assert result["result"]["total_rows"] == 5
    
    @patch('agentcore_agent.graph')
    def test_invoke_with_prompt(self, mock_graph):
        """Test invoke with prompt instead of sql_query."""
        mock_graph.invoke.return_value = {
            "sql_query": "SELECT * FROM users LIMIT 10",
            "query_execution_id": "test-id",
            "athena_status": "SUCCEEDED",
            "retry_count": 2,
            "max_retries": 20,
            "analysis_result": {
                "total_rows": 10,
                "summary": "Retrieved 10 rows",
                "data": []
            },
            "error": ""
        }
        
        payload = {"prompt": "Run a query"}
        
        result = invoke(payload)
        
        assert result["status"] == "success"
        assert "result" in result
    
    @patch('agentcore_agent.graph')
    def test_invoke_query_failed(self, mock_graph):
        """Test invoke when query fails."""
        mock_graph.invoke.return_value = {
            "sql_query": "SELECT * FROM invalid_table",
            "query_execution_id": "test-id",
            "athena_status": "FAILED",
            "retry_count": 1,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        payload = {"sql_query": "SELECT * FROM invalid_table"}
        
        result = invoke(payload)
        
        assert result["status"] == "failed"
        assert "error" in result
    
    @patch('agentcore_agent.graph')
    def test_invoke_query_timeout(self, mock_graph):
        """Test invoke when query times out."""
        mock_graph.invoke.return_value = {
            "sql_query": "SELECT * FROM large_table",
            "query_execution_id": "test-id",
            "athena_status": "RUNNING",
            "retry_count": 10,
            "max_retries": 10,
            "analysis_result": {},
            "error": ""
        }
        
        payload = {
            "sql_query": "SELECT * FROM large_table",
            "max_retries": 10
        }
        
        result = invoke(payload)
        
        assert result["status"] == "timeout"
        assert "error" in result
        assert result["polls"] == 10
    
    @patch('agentcore_agent.graph')
    def test_invoke_exception_handling(self, mock_graph):
        """Test invoke handles exceptions gracefully."""
        mock_graph.invoke.side_effect = Exception("Test error")
        
        payload = {"sql_query": "SELECT * FROM users"}
        
        result = invoke(payload)
        
        assert result["status"] == "error"
        assert "Test error" in result["error"]
    
    def test_create_agent_graph(self):
        """Test that agent graph is created successfully."""
        graph = create_agent_graph()
        assert graph is not None
    
    @patch('agentcore_agent.athena_client')
    @patch('agentcore_agent.graph')
    def test_invoke_default_values(self, mock_graph, mock_client):
        """Test invoke uses default values when not provided."""
        mock_graph.invoke.return_value = {
            "sql_query": "SELECT * FROM users LIMIT 10",
            "query_execution_id": "test-id",
            "athena_status": "SUCCEEDED",
            "retry_count": 1,
            "max_retries": 20,
            "analysis_result": {"total_rows": 10, "summary": "Retrieved 10 rows", "data": []},
            "error": ""
        }
        
        # Empty payload should use defaults
        result = invoke({})
        
        assert result["status"] == "success"
        # Verify default max_retries was used
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["max_retries"] == 20


class TestAgentCoreIntegration:
    """Integration tests for AgentCore deployment."""
    
    @patch('agentcore_agent.athena_client')
    def test_full_workflow_success(self, mock_client):
        """Test complete workflow from submission to results."""
        from athena_mock import QueryStatus
        
        # Mock Athena client behavior
        mock_client.ExecuteSQL.return_value = "test-query-id"
        mock_client.get_query_status.return_value = QueryStatus.SUCCEEDED
        mock_client.get_query_results.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
        
        payload = {
            "sql_query": "SELECT * FROM users",
            "max_retries": 5
        }
        
        result = invoke(payload)
        
        assert result["status"] == "success"
        assert result["result"]["total_rows"] == 2
        assert len(result["result"]["data"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
