"""Enhanced session-based logging for tracking complete request flow."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pythonjsonlogger import jsonlogger

from src.utils.logging import get_logger

logger = get_logger(__name__)


class SessionLogger:
    """Session-specific logger that tracks the complete flow of a request."""
    
    def __init__(self, session_id: str, log_dir: str = "logs/sessions"):
        """
        Initialize session logger.
        
        Args:
            session_id: Unique session identifier
            log_dir: Directory for session-specific logs
        """
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session-specific log file
        self.log_file = self.log_dir / f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Track sequence number for ordering
        self.sequence = 0
        
        # Initialize session metadata
        self.metadata = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "stages": []
        }
        
        # Write initial session entry
        self._write_log({
            "stage": "SESSION_START",
            "sequence": self.sequence,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write a log entry to the session file."""
        with open(self.log_file, 'a') as f:
            json.dump(entry, f)
            f.write('\n')
    
    def _next_sequence(self) -> int:
        """Get the next sequence number."""
        self.sequence += 1
        return self.sequence
    
    def log_original_query(self, query: str, mode: str = "patient") -> None:
        """
        Log the original user query.
        
        Args:
            query: The user's original query text
            mode: Assistant mode (patient/physician)
        """
        entry = {
            "stage": "ORIGINAL_QUERY",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "query_length": len(query),
            "mode": mode
        }
        self._write_log(entry)
        self.metadata["stages"].append("ORIGINAL_QUERY")
        
        logger.info(
            "Original query received",
            extra={
                "session_id": self.session_id,
                "stage": "ORIGINAL_QUERY",
                "query_length": len(query),
                "mode": mode
            }
        )
    
    def log_input_guardrail(
        self,
        check_result: Dict[str, Any],
        guardrail_mode: str = "hybrid"
    ) -> None:
        """
        Log input guardrail check results.
        
        Args:
            check_result: Result from guardrail check
            guardrail_mode: Mode used (llm/regex/hybrid)
        """
        entry = {
            "stage": "INPUT_GUARDRAIL",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "guardrail_mode": guardrail_mode,
            "requires_intervention": check_result.get("requires_intervention", False),
            "intervention_type": check_result.get("intervention_type", "none"),
            "explanation": check_result.get("explanation", ""),
            "should_block": check_result.get("should_block", False)
        }
        self._write_log(entry)
        self.metadata["stages"].append("INPUT_GUARDRAIL")
        
        level = logging.WARNING if check_result.get("requires_intervention") else logging.INFO
        logger.log(
            level,
            f"Input guardrail check: {check_result.get('intervention_type', 'none')}",
            extra={
                "session_id": self.session_id,
                "stage": "INPUT_GUARDRAIL",
                "intervention_required": check_result.get("requires_intervention", False)
            }
        )
    
    def log_api_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> None:
        """
        Log the API call to Anthropic.
        
        Args:
            model: Model being used
            messages: Messages sent to API
            tools: Tools configured for the call
            system_prompt: System prompt if used
        """
        entry = {
            "stage": "API_CALL",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "message_count": len(messages),
            "has_system_prompt": bool(system_prompt),
            "tools_configured": [t.get("name", t.get("type", "unknown")) for t in (tools or [])]
        }
        
        # Include full details for debugging
        entry["api_request"] = {
            "messages": messages,
            "tools": tools,
            "system_prompt": system_prompt[:500] if system_prompt else None  # Truncate for space
        }
        
        self._write_log(entry)
        self.metadata["stages"].append("API_CALL")
        
        logger.info(
            f"API call to {model}",
            extra={
                "session_id": self.session_id,
                "stage": "API_CALL",
                "model": model,
                "tools_count": len(tools) if tools else 0
            }
        )
    
    def log_api_response(
        self,
        response_text: str,
        usage: Dict[str, int],
        tool_calls: List[Dict[str, Any]] = None
    ) -> None:
        """
        Log the API response from Anthropic.
        
        Args:
            response_text: The response text
            usage: Token usage information
            tool_calls: Any tool calls made
        """
        entry = {
            "stage": "API_RESPONSE",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "response_length": len(response_text),
            "usage": usage,
            "tool_calls_made": len(tool_calls) if tool_calls else 0,
            "response_preview": response_text[:500]  # First 500 chars
        }
        
        # Include full response for inspection
        entry["full_response"] = response_text
        entry["tool_calls"] = tool_calls
        
        self._write_log(entry)
        self.metadata["stages"].append("API_RESPONSE")
        
        logger.info(
            "API response received",
            extra={
                "session_id": self.session_id,
                "stage": "API_RESPONSE",
                "response_length": len(response_text),
                "tokens": usage
            }
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        tool_type: str,
        tool_input: Dict[str, Any] = None,
        tool_output: Any = None
    ) -> None:
        """
        Log individual tool calls (web_search, web_fetch).
        
        Args:
            tool_name: Name of the tool
            tool_type: Type of tool call
            tool_input: Input to the tool
            tool_output: Output from the tool
        """
        entry = {
            "stage": "TOOL_CALL",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "tool_type": tool_type,
            "tool_input": tool_input,
            "tool_output": tool_output
        }
        
        self._write_log(entry)
        
        logger.info(
            f"Tool call: {tool_name}",
            extra={
                "session_id": self.session_id,
                "stage": "TOOL_CALL",
                "tool_name": tool_name,
                "tool_type": tool_type
            }
        )
    
    def log_citations(self, citations: List[Dict[str, str]]) -> None:
        """
        Log extracted citations.
        
        Args:
            citations: List of citations with url and title
        """
        entry = {
            "stage": "CITATIONS",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "citation_count": len(citations),
            "citations": citations,
            "domains": [c.get("url", "").split("/")[2] if "/" in c.get("url", "") else "" for c in citations]
        }
        
        self._write_log(entry)
        self.metadata["stages"].append("CITATIONS")
        
        logger.info(
            f"Citations extracted: {len(citations)}",
            extra={
                "session_id": self.session_id,
                "stage": "CITATIONS",
                "citation_count": len(citations)
            }
        )
    
    def log_output_guardrail(
        self,
        check_result: Dict[str, Any],
        guardrail_mode: str = "hybrid",
        original_response: str = None,
        modified_response: str = None
    ) -> None:
        """
        Log output guardrail check results.
        
        Args:
            check_result: Result from guardrail check
            guardrail_mode: Mode used (llm/regex/hybrid)
            original_response: Original response before modifications
            modified_response: Response after modifications
        """
        entry = {
            "stage": "OUTPUT_GUARDRAIL",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "guardrail_mode": guardrail_mode,
            "passes_guardrails": check_result.get("passes_guardrails", True),
            "violations": check_result.get("violations", []),
            "explanation": check_result.get("explanation", ""),
            "suggested_action": check_result.get("suggested_action", "pass"),
            "web_search_performed": check_result.get("web_search_performed", False),
            "has_trusted_citations": check_result.get("has_trusted_citations", False),
            "response_modified": original_response != modified_response if original_response else False
        }
        
        # Include response comparison for debugging
        if original_response and modified_response and original_response != modified_response:
            entry["modifications"] = {
                "original_length": len(original_response),
                "modified_length": len(modified_response),
                "original_preview": original_response[:300],
                "modified_preview": modified_response[:300]
            }
        
        self._write_log(entry)
        self.metadata["stages"].append("OUTPUT_GUARDRAIL")
        
        level = logging.WARNING if check_result.get("violations") else logging.INFO
        logger.log(
            level,
            f"Output guardrail check: {len(check_result.get('violations', []))} violations",
            extra={
                "session_id": self.session_id,
                "stage": "OUTPUT_GUARDRAIL",
                "violations": check_result.get("violations", [])
            }
        )
    
    def log_final_response(
        self,
        response: Dict[str, Any],
        processing_time: float = None
    ) -> None:
        """
        Log the final response sent to the user.
        
        Args:
            response: Final response dictionary
            processing_time: Total processing time in seconds
        """
        entry = {
            "stage": "FINAL_RESPONSE",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "response_length": len(response.get("content", "")),
            "guardrails_applied": response.get("guardrails_applied", False),
            "violations": response.get("violations", []),
            "emergency_detected": response.get("emergency_detected", False),
            "mental_health_crisis": response.get("mental_health_crisis", False),
            "citation_count": len(response.get("citations", [])),
            "processing_time": processing_time,
            "response_preview": response.get("content", "")[:500]
        }
        
        # Include full response
        entry["full_response"] = response
        
        self._write_log(entry)
        self.metadata["stages"].append("FINAL_RESPONSE")
        
        # Update metadata
        self.metadata["completed_at"] = datetime.now().isoformat()
        self.metadata["total_sequences"] = self.sequence
        self.metadata["processing_time"] = processing_time
        
        # Write final metadata
        self._write_log({
            "stage": "SESSION_END",
            "sequence": self._next_sequence(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": self.metadata
        })
        
        logger.info(
            "Final response sent",
            extra={
                "session_id": self.session_id,
                "stage": "FINAL_RESPONSE",
                "processing_time": processing_time,
                "violations": response.get("violations", [])
            }
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the session for quick inspection.
        
        Returns:
            Summary dictionary with key metrics
        """
        return {
            "session_id": self.session_id,
            "log_file": str(self.log_file),
            "stages_completed": self.metadata["stages"],
            "total_sequences": self.sequence,
            "started_at": self.metadata["started_at"],
            "completed_at": self.metadata.get("completed_at"),
            "processing_time": self.metadata.get("processing_time")
        }


def read_session_log(session_id: str, log_dir: str = "logs/sessions") -> List[Dict[str, Any]]:
    """
    Read and parse a session log file.
    
    Args:
        session_id: Session ID to look for
        log_dir: Directory containing session logs
        
    Returns:
        List of log entries in chronological order
    """
    log_path = Path(log_dir)
    
    # Find the session log file
    session_files = list(log_path.glob(f"session_{session_id}_*.jsonl"))
    
    if not session_files:
        raise FileNotFoundError(f"No log file found for session {session_id}")
    
    # Use the most recent file if multiple exist
    session_file = sorted(session_files)[-1]
    
    entries = []
    with open(session_file, 'r') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    # Sort by sequence number to ensure correct order
    entries.sort(key=lambda x: x.get("sequence", 0))
    
    return entries


def format_session_log(session_id: str, log_dir: str = "logs/sessions") -> str:
    """
    Format a session log for human-readable display.
    
    Args:
        session_id: Session ID to format
        log_dir: Directory containing session logs
        
    Returns:
        Formatted string representation of the session
    """
    entries = read_session_log(session_id, log_dir)
    
    output = []
    output.append(f"\n{'='*80}")
    output.append(f"SESSION LOG: {session_id}")
    output.append(f"{'='*80}\n")
    
    for entry in entries:
        stage = entry.get("stage", "UNKNOWN")
        timestamp = entry.get("timestamp", "")
        sequence = entry.get("sequence", 0)
        
        output.append(f"[{sequence:03d}] {timestamp} - {stage}")
        output.append("-" * 40)
        
        if stage == "ORIGINAL_QUERY":
            output.append(f"Query: {entry.get('query', 'N/A')}")
            output.append(f"Mode: {entry.get('mode', 'N/A')}")
            
        elif stage == "INPUT_GUARDRAIL":
            output.append(f"Mode: {entry.get('guardrail_mode', 'N/A')}")
            output.append(f"Intervention Required: {entry.get('requires_intervention', False)}")
            output.append(f"Type: {entry.get('intervention_type', 'none')}")
            if entry.get('explanation'):
                output.append(f"Explanation: {entry.get('explanation')}")
                
        elif stage == "API_CALL":
            output.append(f"Model: {entry.get('model', 'N/A')}")
            output.append(f"Tools: {entry.get('tools_configured', [])}")
            
        elif stage == "API_RESPONSE":
            output.append(f"Response Length: {entry.get('response_length', 0)}")
            output.append(f"Tokens: {entry.get('usage', {})}")
            output.append(f"Tool Calls: {entry.get('tool_calls_made', 0)}")
            
        elif stage == "TOOL_CALL":
            output.append(f"Tool: {entry.get('tool_name', 'N/A')} ({entry.get('tool_type', 'N/A')})")
            
        elif stage == "CITATIONS":
            output.append(f"Citations: {entry.get('citation_count', 0)}")
            for citation in entry.get('citations', [])[:3]:  # Show first 3
                output.append(f"  - {citation.get('url', 'N/A')}")
                
        elif stage == "OUTPUT_GUARDRAIL":
            output.append(f"Mode: {entry.get('guardrail_mode', 'N/A')}")
            output.append(f"Passes: {entry.get('passes_guardrails', True)}")
            violations = entry.get('violations', [])
            if violations:
                output.append(f"Violations: {', '.join(violations)}")
            output.append(f"Web Search: {entry.get('web_search_performed', False)}")
            output.append(f"Trusted Citations: {entry.get('has_trusted_citations', False)}")
            
        elif stage == "FINAL_RESPONSE":
            output.append(f"Response Length: {entry.get('response_length', 0)}")
            output.append(f"Processing Time: {entry.get('processing_time', 0):.2f}s")
            output.append(f"Guardrails Applied: {entry.get('guardrails_applied', False)}")
            if entry.get('violations'):
                output.append(f"Violations: {', '.join(entry.get('violations', []))}")
                
        output.append("")  # Empty line between entries
    
    return "\n".join(output)