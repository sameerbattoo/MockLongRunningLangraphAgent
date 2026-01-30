"""LangGraph agent with 3-node pattern for long-running Athena queries."""
import time
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from athena_mock import AthenaQuery, QueryStatus


# Define the state
class AgentState(TypedDict):
    sql_query: str
    query_execution_id: str
    athena_status: str
    retry_count: int
    max_retries: int
    analysis_result: dict
    error: str


# Initialize mock Athena client
athena_client = AthenaQuery()


# Node A: Submit Athena Query
def submit_athena_query(state: AgentState) -> AgentState:
    """Submit SQL query to Athena and store execution ID."""
    print(f"[Node A] Submitting query: {state['sql_query']}")
    
    # Start query execution (simulates 100 seconds)
    query_id = athena_client.ExecuteSQL(state["sql_query"], sleep_seconds=100)
    
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
        print("[Router] Query still running, waiting 2 seconds...")
        time.sleep(2)
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


# Run the agent
if __name__ == "__main__":
    # Create the graph
    app = create_agent_graph()
    
    # Initial state
    initial_state = {
        "sql_query": "SELECT * FROM users WHERE active = true",
        "query_execution_id": "",
        "athena_status": "",
        "retry_count": 0,
        "max_retries": 50,
        "analysis_result": {},
        "error": ""
    }
    
    print("=" * 60)
    print("Starting LangGraph Agent for Long-Running Athena Query")
    print("=" * 60)
    
    # Execute the graph
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("Final Results:")
    print("=" * 60)
    print(f"Status: {final_state['athena_status']}")
    print(f"Total Polls: {final_state['retry_count']}")
    if final_state.get("analysis_result"):
        print(f"Analysis: {final_state['analysis_result']}")
