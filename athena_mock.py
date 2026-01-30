"""Mock Athena Query class that simulates long-running queries."""
import time
import uuid
from enum import Enum


class QueryStatus(Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AthenaQuery:
    """Mock Athena client that simulates query execution with sleep."""
    
    def __init__(self):
        self.queries = {}
    
    def ExecuteSQL(self, sql: str, sleep_seconds: int = 5) -> str:
        """Start query execution and return execution ID."""
        query_id = str(uuid.uuid4())
        self.queries[query_id] = {
            "sql": sql,
            "status": QueryStatus.RUNNING,
            "start_time": time.time(),
            "sleep_duration": sleep_seconds,
            "results": None
        }
        return query_id
    
    def get_query_status(self, query_id: str) -> QueryStatus:
        """Check if query has completed (based on elapsed time)."""
        if query_id not in self.queries:
            raise ValueError(f"Query {query_id} not found")
        
        query = self.queries[query_id]
        elapsed = time.time() - query["start_time"]
        
        if elapsed >= query["sleep_duration"]:
            query["status"] = QueryStatus.SUCCEEDED
            # Generate mock results
            query["results"] = [
                {"id": 1, "name": "Alice", "value": 100},
                {"id": 2, "name": "Bob", "value": 200},
                {"id": 3, "name": "Charlie", "value": 300}
            ]
        
        return query["status"]
    
    def get_query_results(self, query_id: str) -> list:
        """Retrieve query results."""
        if query_id not in self.queries:
            raise ValueError(f"Query {query_id} not found")
        
        query = self.queries[query_id]
        if query["status"] != QueryStatus.SUCCEEDED:
            raise ValueError(f"Query {query_id} not yet completed")
        
        return query["results"]
