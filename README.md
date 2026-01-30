# LangGraph Agent for Long-Running Athena Queries

This demo shows a 3-node LangGraph pattern for handling long-running tasks (simulated Athena queries).

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

## Usage

```bash
python agent.py
```

The mock Athena query sleeps for 10 seconds, and the agent polls every 2 seconds until completion.

## Key Features

- Asynchronous query pattern (submit → poll → fetch)
- Retry logic with configurable max attempts
- Conditional routing based on query status
- Clean state management through LangGraph
