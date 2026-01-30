# LangGraph Agent for Long-Running Athena Queries

This demo shows a 3-node LangGraph pattern for handling long-running tasks (simulated Athena queries). **Ready for deployment on AWS Bedrock AgentCore Runtime.**

## Features

- **3-Node Pattern**: Submit → Poll → Fetch for async query handling
- **AgentCore Ready**: Deploy to AWS with one command
- **Configurable**: Adjust polling intervals, timeouts, and retries
- **Production Ready**: Includes tests, monitoring, and error handling

## Quick Start

### Local Development

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run locally
python agent.py
```

### Deploy to AWS AgentCore

```bash
# Install AgentCore toolkit
uv pip install bedrock-agentcore-starter-toolkit

# Test locally
agentcore dev
agentcore invoke --dev '{"sql_query": "SELECT * FROM users"}'

# Deploy to AWS
uv run agentcore launch \
	--env ATHENA_MOCK_DURATION=100 \
  --env MAX_RETRIES=60  \
  --env AWS_REGION="us-west-2" \
  --env POLL_INTERVAL=2 \
  --env LOG_LEVEL="INFO"
```
```

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup or [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide.

## Architecture

The agent splits query execution into three explicit nodes:

1. **Node A (submit_athena_query)**: Submits SQL query and stores execution ID
2. **Node B (poll_athena_status)**: Polls query status with retry logic
3. **Node C (fetch_athena_results)**: Retrieves and processes results when complete

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Node A: Submit     │
                  │   Athena Query       │
                  │                      │
                  │ - Build SQL          │
                  │ - Start execution    │
                  │ - Store query_id     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Node B: Poll       │◄─────────┐
                  │   Athena Status      │          │
                  │                      │          │
                  │ - Check status       │          │
                  │ - Increment retry    │          │
                  └──────────┬───────────┘          │
                             │                      │
                             ▼                      │
                  ┌──────────────────────┐          │
                  │  Conditional Router  │          │
                  └──────────┬───────────┘          │
                             │                      │
                ┌────────────┼────────────┐         │
                │            │            │         │
                ▼            ▼            ▼         │
         [SUCCEEDED]    [RUNNING]    [FAILED]      │
                │            │            │         │
                │            │            │         │
                │      ┌─────┴─────┐      │         │
                │      │ retry <   │      │         │
                │      │ max_retry?│      │         │
                │      └─────┬─────┘      │         │
                │            │            │         │
                │       Yes  │  No        │         │
                │            │            │         │
                │            └────────────┼─────────┘
                │                         │
                ▼                         ▼
     ┌──────────────────────┐    ┌──────────────┐
     │   Node C: Fetch      │    │     END      │
     │   Athena Results     │    │   (Timeout   │
     │                      │    │   or Failed) │
     │ - Get results        │    └──────────────┘
     │ - Format data        │
     │ - Store in state     │
     └──────────┬───────────┘
                │
                ▼
         ┌──────────────┐
         │     END      │
         │  (Success)   │
         └──────────────┘
```

### Edge Conditions

- **submit_query → poll_status**: Unconditional (always proceeds to polling)
- **poll_status → poll_status**: When status is RUNNING and retry_count < max_retries (loops back)
- **poll_status → fetch_results**: When status is SUCCEEDED
- **poll_status → END**: When status is FAILED or retry_count >= max_retries

## Installation

```bash
pip install -r requirements.txt
```

Or with uv:

```bash
uv pip install langgraph langchain-core bedrock-agentcore python-dotenv boto3
```

For AgentCore deployment:

```bash
uv pip install bedrock-agentcore-starter-toolkit
```

Verify all dependencies:

```bash
python verify_dependencies.py
```

## Configuration

Copy the example environment file and customize:

```bash
cp .env.example .env
```

Edit `.env` to configure:
- `ATHENA_MOCK_DURATION`: Query duration in seconds (default: 10)
- `POLL_INTERVAL`: Polling interval in seconds (default: 2)
- `MAX_RETRIES`: Maximum polling attempts (default: 20)
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

### Local Testing

```bash
python agent.py
```

### AgentCore Deployment

For deploying to AWS Bedrock AgentCore Runtime, see [DEPLOYMENT.md](DEPLOYMENT.md).


The mock Athena query sleeps for 10 seconds, and the agent polls every 2 seconds until completion.

## Key Features

- Asynchronous query pattern (submit → poll → fetch)
- Retry logic with configurable max attempts
- Conditional routing based on query status
- Clean state management through LangGraph
- **AWS AgentCore Runtime compatible**
- Environment-based configuration
- Comprehensive test coverage

## Project Structure

```
.
├── agent.py                    # Standalone LangGraph agent
├── agentcore_agent.py         # AgentCore-compatible wrapper
├── athena_mock.py             # Mock Athena client
├── test.py                    # Tests for standalone agent
├── test_agentcore.py          # Tests for AgentCore wrapper
├── invoke_agent_example.py    # Example AWS SDK invocation
├── .env                       # Environment configuration (create from .env.example)
├── .env.example               # Environment template
├── .bedrock_agentcore.yaml    # AgentCore configuration
├── pyproject.toml             # Python dependencies
├── QUICKSTART.md              # 5-minute setup guide
├── DEPLOYMENT.md              # Detailed deployment guide
├── AGENTCORE_CHECKLIST.md     # Deployment checklist
├── ENV_SETUP.md               # Environment variable guide
├── PROJECT_SUMMARY.md         # Complete project overview
└── README.md                  # This file
```

## Configuration

The agent behavior can be configured via environment variables in `.env`:

- `ATHENA_MOCK_DURATION`: Mock query duration in seconds (default: 10)
- `POLL_INTERVAL`: Polling interval in seconds (default: 2)
- `MAX_RETRIES`: Maximum polling attempts (default: 20)
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)

Copy `.env.example` to `.env` and customize as needed.

## Testing

Run all tests:

```bash
# Test standalone agent
uv run pytest test.py -v

# Test AgentCore wrapper
uv run pytest test_agentcore.py -v

# Run all tests
uv run pytest -v
```

## Troubleshooting

Having issues? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems and solutions, including:
- AWS region configuration errors
- Environment variable issues
- Deployment failures
- Runtime timeouts
- Missing dependencies (bedrock-agentcore, botocore)

Before deploying, check [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) to avoid common issues.

## Documentation
