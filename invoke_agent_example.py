"""Example script for invoking the deployed AgentCore agent programmatically."""
import json
import uuid
import boto3
import sys

# Configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:us-west-2:175918693907:runtime/longrunning_langraph_agent-7Z3Fu233jt"  # Get this from agentcore launch output
AWS_REGION = "us-west-2"

def invoke_agent(sql_query: str, max_retries: int = 20):
    """
    Invoke the deployed Athena query agent.
    
    Args:
        sql_query: SQL query to execute
        max_retries: Maximum number of polling attempts
    
    Returns:
        dict: Agent response with query results
    """
    # Initialize the AgentCore client
    client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)
    
    # Prepare the payload
    payload = json.dumps({
        "sql_query": sql_query,
        "max_retries": max_retries
    }).encode()
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    print(f"Invoking agent with session ID: {session_id}")
    print(f"SQL Query: {sql_query}")
    print("-" * 60)
    
    try:
        # Invoke the agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT"
        )
        
        # Process the streaming response
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode('utf-8'))
        
        # Parse the result
        result = json.loads(''.join(content))
        
        print("Agent Response:")
        print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        print(f"Error invoking agent: {str(e)}")
        raise


def main():
    """Main function with example invocations."""
    
    # Check if agent ARN is configured
    if AGENT_ARN == "REPLACE_WITH_YOUR_AGENT_ARN":
        print("ERROR: Please update AGENT_ARN in this script with your deployed agent ARN")
        print("Get the ARN from the output of: agentcore launch")
        sys.exit(1)
    
    # Example 1: Simple query
    print("\n" + "=" * 60)
    print("Example 1: Simple Query")
    print("=" * 60)
    invoke_agent("SELECT * FROM users WHERE active = true")
    
    # Example 2: Query with custom max retries
    print("\n" + "=" * 60)
    print("Example 2: Query with Custom Max Retries")
    print("=" * 60)
    invoke_agent("SELECT * FROM orders WHERE date > '2024-01-01'", max_retries=15)
    
    # Example 3: Complex query
    print("\n" + "=" * 60)
    print("Example 3: Complex Query")
    print("=" * 60)
    invoke_agent("""
        SELECT 
            user_id, 
            COUNT(*) as order_count,
            SUM(total) as total_spent
        FROM orders
        GROUP BY user_id
        HAVING total_spent > 1000
    """)


if __name__ == "__main__":
    main()
