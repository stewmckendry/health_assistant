"""
Comprehensive search operation logger for traceability.
Logs each step of the search process with timing and metadata.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class SearchEvent(Enum):
    """Types of search events to log"""
    SEARCH_START = "search_start"
    QUERY_CLASSIFIED = "query_classified"
    SQL_SEARCH = "sql_search"
    VECTOR_SEARCH = "vector_search"
    LLM_RERANKING = "llm_reranking"
    RESULT_MERGE = "result_merge"
    FILTERING = "filtering"
    SEARCH_COMPLETE = "search_complete"
    ERROR = "error"


class SearchLogger:
    """
    Comprehensive logging for search operations.
    Tracks individual operations with timing and results.
    """
    
    def __init__(self, session_id: str, log_dir: Optional[Path] = None):
        """
        Initialize search logger.
        
        Args:
            session_id: Session identifier for correlation
            log_dir: Directory for search logs (creates if not exists)
        """
        self.session_id = session_id
        self.operation_id = None
        self.operation_start = None
        
        # Setup log directory
        if log_dir is None:
            log_dir = Path("logs/dr_off_agent/search_operations")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create operation log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"search_{session_id}_{timestamp}.jsonl"
        
        # Track metrics for summary
        self.metrics = {
            "total_operations": 0,
            "sql_searches": 0,
            "vector_searches": 0,
            "reranks": 0,
            "errors": 0,
            "total_duration_ms": 0
        }
        
    def start_operation(self, tool: str, query: str, request_data: Dict[str, Any] = None) -> str:
        """
        Start a new search operation.
        
        Args:
            tool: Tool name (schedule.get, odb.get, etc.)
            query: Search query string
            request_data: Full request parameters
            
        Returns:
            Operation ID for correlation
        """
        self.operation_id = f"{tool}_{uuid.uuid4().hex[:8]}"
        self.operation_start = datetime.now()
        self.metrics["total_operations"] += 1
        
        self._log_event({
            "event": SearchEvent.SEARCH_START.value,
            "operation_id": self.operation_id,
            "tool": tool,
            "query": query,
            "request_data": request_data or {},
            "timestamp": self.operation_start.isoformat()
        })
        
        logger.info(f"Search operation started: {self.operation_id} for query: {query[:100]}")
        return self.operation_id
        
    def log_classification(self, strategy: str, reason: str, details: Dict[str, Any] = None):
        """
        Log query classification result.
        
        Args:
            strategy: Chosen search strategy
            reason: Reason for classification
            details: Additional classification details
        """
        self._log_event({
            "event": SearchEvent.QUERY_CLASSIFIED.value,
            "operation_id": self.operation_id,
            "strategy": strategy,
            "reason": reason,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"Query classified as {strategy}: {reason}")
        
    def log_sql_search(
        self, 
        query: str, 
        results_count: int, 
        duration_ms: float,
        table: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Log SQL search operation.
        
        Args:
            query: SQL query executed
            results_count: Number of results found
            duration_ms: Query execution time
            table: Database table queried
            error: Error message if failed
        """
        self.metrics["sql_searches"] += 1
        
        event_data = {
            "event": SearchEvent.SQL_SEARCH.value,
            "operation_id": self.operation_id,
            "query": query[:500],  # Truncate long queries
            "results_count": results_count,
            "duration_ms": duration_ms,
            "table": table,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            event_data["error"] = error
            self.metrics["errors"] += 1
            
        self._log_event(event_data)
        
        if error:
            logger.warning(f"SQL search failed: {error}")
        else:
            logger.debug(f"SQL search returned {results_count} results in {duration_ms:.2f}ms")
            
    def log_vector_search(
        self,
        query: str,
        results_count: int,
        duration_ms: float,
        collection: Optional[str] = None,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        error: Optional[str] = None
    ):
        """
        Log vector search operation.
        
        Args:
            query: Search query text
            results_count: Number of results found
            duration_ms: Search execution time
            collection: Vector collection searched
            top_k: Number of results requested
            min_score: Minimum similarity score
            max_score: Maximum similarity score
            error: Error message if failed
        """
        self.metrics["vector_searches"] += 1
        
        event_data = {
            "event": SearchEvent.VECTOR_SEARCH.value,
            "operation_id": self.operation_id,
            "query": query[:500],
            "results_count": results_count,
            "duration_ms": duration_ms,
            "collection": collection,
            "top_k": top_k,
            "score_range": {
                "min": min_score,
                "max": max_score
            } if min_score is not None else None,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            event_data["error"] = error
            self.metrics["errors"] += 1
            
        self._log_event(event_data)
        
        if error:
            logger.warning(f"Vector search failed: {error}")
        else:
            logger.debug(f"Vector search returned {results_count} results in {duration_ms:.2f}ms")
            
    def log_reranking(
        self,
        input_count: int,
        output_count: int,
        duration_ms: float,
        model: Optional[str] = None,
        score_distribution: Optional[Dict[str, float]] = None,
        error: Optional[str] = None
    ):
        """
        Log LLM reranking operation.
        
        Args:
            input_count: Number of documents to rerank
            output_count: Number of documents after reranking
            duration_ms: Reranking execution time
            model: LLM model used
            score_distribution: Score statistics (min, max, mean)
            error: Error message if failed
        """
        self.metrics["reranks"] += 1
        
        event_data = {
            "event": SearchEvent.LLM_RERANKING.value,
            "operation_id": self.operation_id,
            "input_count": input_count,
            "output_count": output_count,
            "duration_ms": duration_ms,
            "model": model,
            "score_distribution": score_distribution,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            event_data["error"] = error
            self.metrics["errors"] += 1
            
        self._log_event(event_data)
        
        if error:
            logger.warning(f"Reranking failed: {error}")
        else:
            logger.debug(f"Reranked {input_count} to {output_count} results in {duration_ms:.2f}ms")
            
    def log_merge(
        self,
        sql_count: int,
        vector_count: int,
        final_count: int,
        merge_strategy: str = "union",
        conflicts: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Log result merging operation.
        
        Args:
            sql_count: Number of SQL results
            vector_count: Number of vector results
            final_count: Number of merged results
            merge_strategy: How results were merged
            conflicts: List of conflicts found
        """
        event_data = {
            "event": SearchEvent.RESULT_MERGE.value,
            "operation_id": self.operation_id,
            "sql_count": sql_count,
            "vector_count": vector_count,
            "final_count": final_count,
            "merge_strategy": merge_strategy,
            "conflicts_count": len(conflicts) if conflicts else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        if conflicts and len(conflicts) > 0:
            event_data["sample_conflicts"] = conflicts[:3]  # Log first 3 conflicts
            
        self._log_event(event_data)
        
        logger.debug(f"Merged {sql_count} SQL + {vector_count} vector = {final_count} results")
        
    def log_filtering(
        self,
        input_count: int,
        output_count: int,
        filters: Dict[str, Any],
        duration_ms: float
    ):
        """
        Log filtering operation.
        
        Args:
            input_count: Number of documents before filtering
            output_count: Number of documents after filtering
            filters: Filter criteria applied
            duration_ms: Filtering execution time
        """
        self._log_event({
            "event": SearchEvent.FILTERING.value,
            "operation_id": self.operation_id,
            "input_count": input_count,
            "output_count": output_count,
            "filters": filters,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"Filtered {input_count} to {output_count} results")
        
    def complete_operation(
        self,
        final_count: int,
        confidence: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Mark operation as complete and log summary.
        
        Args:
            final_count: Final number of results
            confidence: Confidence score if available
            success: Whether operation succeeded
            error_message: Error if failed
        """
        if self.operation_start:
            duration_ms = (datetime.now() - self.operation_start).total_seconds() * 1000
            self.metrics["total_duration_ms"] += duration_ms
        else:
            duration_ms = 0
            
        self._log_event({
            "event": SearchEvent.SEARCH_COMPLETE.value,
            "operation_id": self.operation_id,
            "final_count": final_count,
            "confidence": confidence,
            "success": success,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        })
        
        if success:
            logger.info(f"Search operation completed: {final_count} results in {duration_ms:.2f}ms")
        else:
            logger.error(f"Search operation failed: {error_message}")
            self.metrics["errors"] += 1
            
    def log_error(self, error: Exception, context: str = ""):
        """
        Log an error during search.
        
        Args:
            error: Exception that occurred
            context: Additional context about where error occurred
        """
        self.metrics["errors"] += 1
        
        self._log_event({
            "event": SearchEvent.ERROR.value,
            "operation_id": self.operation_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.error(f"Search error in {context}: {type(error).__name__}: {str(error)}")
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get accumulated metrics.
        
        Returns:
            Dictionary of search metrics
        """
        return {
            "session_id": self.session_id,
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    def write_summary(self):
        """Write session summary to file"""
        summary_file = self.log_dir / f"summary_{self.session_id}.json"
        
        summary = {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Search session summary written to: {summary_file}")
        
    def _log_event(self, event_data: Dict[str, Any]):
        """
        Write event to log file.
        
        Args:
            event_data: Event data to log
        """
        # Add session ID to all events
        event_data["session_id"] = self.session_id
        
        # Write to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event_data) + '\n')
            
        # Also log to standard logger at debug level
        logger.debug(f"Search event: {event_data.get('event')} for {event_data.get('operation_id')}")