"""AgentCore-compatible wrapper for the LangGraph Athena agent."""
import os
from pathlib import Path
from dotenv import load_dotenv
from bedrock_agentcore import BedrockAgentCoreApp
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from athena_mock import AthenaQuery, QueryStatus
import time

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")

# Set AWS region if not already set (required for AgentCore)
if not os.getenv('AWS_REGION'):
    os.environ['AWS_REGION'] = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    print(f"Set AWS_REGION to {os.environ['AWS_REGION']}")

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Define the state
class AgentState(TypedDict):
    sql_query: str
    query_execution_id: str
    athena_status: str
    retry_count: int
    max_retries: int
    analysis_result: dict
    error: str


# Initialize mock Athena client (in production, use real Athena client)
athena_client = AthenaQuery()


# Node A: Submit Athena Query
def submit_athena_query(state: AgentState) -> AgentState:
    """Submit SQL query to Athena and store execution ID."""
    print(f"[Node A] Submitting query: {state['sql_query']}")
    
    # Get sleep duration from environment or default to 10 seconds
    sleep_duration = int(os.environ.get("ATHENA_MOCK_DURATION", "10"))
    
    # Start query execution
    query_id = athena_client.ExecuteSQL(state["sql_query"], sleep_seconds=sleep_duration)
    
    print(f"[Node A] Query submitted with ID: {query_id}")
    
    return {
        **state,
        "query_execution_id": query_id,
        "athena_status": "RUNNING",
        "retry_count": 0
    }


# Node B: Poll Athena Status
def poll_athena_status(state: AgentState) -> AgentState:
    """Check query execution status."""
    query_id = state["query_execution_id"]
    print(f"[Node B] Polling status for query: {query_id} (attempt {state['retry_count'] + 1})")
    
    # Check status
    status = athena_client.get_query_status(query_id)
    
    print(f"[Node B] Current status: {status.value}")
    
    return {
        **state,
        "athena_status": status.value,
        "retry_count": state["retry_count"] + 1
    }


# Node C: Fetch Athena Results
def fetch_athena_results(state: AgentState) -> AgentState:
    """Retrieve and process query results."""
    query_id = state["query_execution_id"]
    print(f"[Node C] Fetching results for query: {query_id}")
    
    # Get results
    results = athena_client.get_query_results(query_id)
    
    # Process results into LLM-friendly format
    analysis = {
        "total_rows": len(results),
        "summary": f"Retrieved {len(results)} rows",
        "data": results
    }
    
    print(f"[Node C] Results fetched: {analysis['summary']}")
    
    return {
        **state,
        "analysis_result": analysis
    }


# Conditional edge: Decide next step based on status
def should_continue_polling(state: AgentState) -> Literal["fetch_results", "poll_status", "end"]:
    """Route based on query status."""
    status = state["athena_status"]
    
    if status == "SUCCEEDED":
        return "fetch_results"
    elif status == "FAILED":
        return "end"
    elif state["retry_count"] >= state["max_retries"]:
        print(f"[Router] Max retries ({state['max_retries']}) reached")
        return "end"
    else:
        # Still running, wait and poll again
        poll_interval = int(os.environ.get("POLL_INTERVAL", "2"))
        print(f"[Router] Query still running, waiting {poll_interval} seconds...")
        time.sleep(poll_interval)
        return "poll_status"


# Build the graph
def create_agent_graph():
    """Create LangGraph workflow for Athena query execution."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("submit_query", submit_athena_query)
    workflow.add_node("poll_status", poll_athena_status)
    workflow.add_node("fetch_results", fetch_athena_results)
    
    # Define edges
    workflow.set_entry_point("submit_query")
    workflow.add_edge("submit_query", "poll_status")
    workflow.add_conditional_edges(
        "poll_status",
        should_continue_polling,
        {
            "fetch_results": "fetch_results",
            "poll_status": "poll_status",
            "end": END
        }
    )
    workflow.add_edge("fetch_results", END)
    
    return workflow.compile()


# Create the graph instance
graph = create_agent_graph()


@app.entrypoint
def invoke(payload):
    """
    AgentCore entrypoint for the Athena query agent.
    
    Expected payload format:
    {
        "sql_query": "SELECT * FROM users WHERE active = true",
        "max_retries": 10  # optional, defaults to env var or 20
   }
    """
    # Extract parameters from payload
    sql_query = payload.get("sql_query") or payload.get("prompt", "SELECT * FROM users LIMIT 10")
    max_retries = payload.get("max_retries", int(os.getenv("MAX_RETRIES", "20")))

    # Initial state
    initial_state = {
        "sql_query": sql_query,
        "query_execution_id": "",
        "athena_status": "",
        "retry_count": 0,
        "max_retries": max_retries,
        "analysis_result": {},
        "error": ""
    }
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level == "INFO":
        print("=" * 60)
        print("Starting LangGraph Agent for Long-Running Athena Query")
        print(f"SQL Query: {sql_query}")
        print(f"Max Retries: {max_retries}")
        print("=" * 60)
    
    try:
        # Execute the graph
        final_state = graph.invoke(initial_state)
        
        # Return results
        if final_state["athena_status"] == "SUCCEEDED":
            return {
                "status": "success",
                "query_id": final_state["query_execution_id"],
                "polls": final_state["retry_count"],
                "result": final_state["analysis_result"]
            }
        elif final_state["athena_status"] == "FAILED":
            return {
                "status": "failed",
                "query_id": final_state["query_execution_id"],
                "polls": final_state["retry_count"],
                "error": "Query execution failed"
            }
        else:
            return {
                "status": "timeout",
                "query_id": final_state["query_execution_id"],
                "polls": final_state["retry_count"],
                "error": f"Query timed out after {max_retries} polling attempts"
            }
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    app.run()
