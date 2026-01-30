# AWS AgentCore Deployment Guide

This guide explains how to deploy the LangGraph Athena agent to AWS Bedrock AgentCore Runtime.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials (`aws configure`)
3. **Python 3.13+** installed
4. **Docker** installed (for local testing and ARM64 builds)
5. **All dependencies installed** (including boto3/botocore)

```bash
# Install all dependencies
uv pip install -r requirements.txt

# Verify boto3 is installed
python -c "import boto3; print('boto3 version:', boto3.__version__)"
```

## Installation

Install the required dependencies including the AgentCore toolkit:

```bash
# Using uv
uv pip install bedrock-agentcore bedrock-agentcore-starter-toolkit

# Or using pip
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit
```

Verify the installation:

```bash
agentcore --help
```

## Local Testing

Before deploying to AWS, test the agent locally:

### 1. Start the Development Server

```bash
agentcore dev
```

This starts a local server on port 8080 (or next available port).

### 2. Test the Agent Locally

In a separate terminal:

```bash
# Test with default query
agentcore invoke --dev '{"sql_query": "SELECT * FROM users WHERE active = true"}'

# Test with custom query and max retries
agentcore invoke --dev '{"sql_query": "SELECT * FROM orders", "max_retries": 15}'

# Test with simple prompt (will use default query)
agentcore invoke --dev "Run a query"
```

## Deployment to AWS

### Step 1: Configure AWS Credentials

Ensure your AWS credentials are configured:

```bash
uv run agentcore configure -e agentcore_agent.py 
```

### Step 2: Enable Model Access (if using Bedrock models)

If you plan to integrate with Bedrock models in the future:
1. Go to AWS Console → Amazon Bedrock → Model access
2. Enable access to Claude models (e.g., Claude 3.5 Sonnet)

### Step 3: Enable Observability (Recommended)

Enable CloudWatch Transaction Search for monitoring:
1. Go to AWS Console → CloudWatch → Settings
2. Enable Transaction Search
3. This allows you to trace and debug your agent executions

### Step 4: Deploy the Agent

Deploy using the AgentCore CLI:

```bash
uv run agentcore launch \
	--env ATHENA_MOCK_DURATION=100 \
  --env MAX_RETRIES=60  \
  --env AWS_REGION="us-west-2" \
  --env POLL_INTERVAL=2 \
  --env LOG_LEVEL="INFO"
```

This command will:
- Build a Docker container (ARM64 for AWS Graviton)
- Push the container to Amazon ECR
- Create an AgentCore Runtime
- Deploy your agent

**Note the output:**
- **Agent ARN**: Used for programmatic invocation
- **Log Group**: CloudWatch logs location

### Step 5: Test the Deployed Agent

Test your deployed agent:

```bash
# Test with JSON payload
agentcore invoke '{"sql_query": "SELECT * FROM users WHERE active = true", "max_retries": 70}'

# Test with no prompt
agentcore invoke
```



## Programmatic Invocation

After deployment, invoke your agent using the AWS SDK:

```python
import json
import uuid
import boto3

# Replace with your agent ARN from deployment output
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/athena-query-agent"

# Initialize the AgentCore client
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Prepare the payload
payload = json.dumps({
    "sql_query": "SELECT * FROM users WHERE active = true",
    "max_retries": 20
}).encode()

# Invoke the agent
response = client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=str(uuid.uuid4()),
    payload=payload,
    qualifier="DEFAULT"
)

# Process the response
content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))

result = json.loads(''.join(content))
print(json.dumps(result, indent=2))
```

## Additional Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
