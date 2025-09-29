# Session Logging System

## Overview

The Health Assistant includes a comprehensive session logging system that tracks the complete flow of each request through the system. This allows for easy inspection and debugging of:

- Original user queries
- Input guardrail checks
- API calls to Anthropic
- Web search and fetch tool usage
- Citations extracted
- Output guardrail checks
- Final responses sent to users

## Architecture

### SessionLogger Class

Located in `src/utils/session_logging.py`, the `SessionLogger` class:

1. Creates a unique session log file for each request
2. Tracks all stages of request processing with sequence numbers
3. Writes structured JSON logs for machine readability
4. Provides human-readable formatting options

### Log Stages

Each session progresses through these stages:

1. **SESSION_START** - Session initialization
2. **ORIGINAL_QUERY** - User's input query
3. **INPUT_GUARDRAIL** - Pre-API safety checks
4. **API_CALL** - Request sent to Anthropic
5. **API_RESPONSE** - Response from Anthropic
6. **TOOL_CALL** - Web search/fetch tool usage
7. **CITATIONS** - Extracted source citations
8. **OUTPUT_GUARDRAIL** - Post-API safety checks
9. **FINAL_RESPONSE** - Response sent to user
10. **SESSION_END** - Session completion with metadata

## Session Log Files

### Location
Session logs are stored in `logs/sessions/` directory as JSONL files:
```
logs/sessions/session_{session_id}_{timestamp}.jsonl
```

### Format
Each line in the log file is a JSON object with:
- `stage`: The processing stage
- `sequence`: Order number for sorting
- `session_id`: Unique session identifier
- `timestamp`: ISO format timestamp
- Stage-specific data fields

## Viewing Session Logs

### Command Line Tool

The `scripts/view_session_log.py` utility provides multiple ways to inspect logs:

#### List All Sessions
```bash
python scripts/view_session_log.py --list
```

#### View Latest Session
```bash
python scripts/view_session_log.py --latest
```

#### View Specific Session
```bash
# Formatted view (default)
python scripts/view_session_log.py <session_id>

# JSON format
python scripts/view_session_log.py <session_id> --format json

# Raw JSONL
python scripts/view_session_log.py <session_id> --format raw
```

#### Filter by Stage
```bash
# View only API calls
python scripts/view_session_log.py <session_id> --stage api_call

# View only citations
python scripts/view_session_log.py <session_id> --stage citations
```

#### Extract Specific Data
```bash
# Extract all citations
python scripts/view_session_log.py <session_id> --extract citations

# Extract tool calls
python scripts/view_session_log.py <session_id> --extract tool_call

# Extract output guardrail checks
python scripts/view_session_log.py <session_id> --extract output_guardrail
```

## Example Session Logs

### Normal Query Session

```
================================================================================
SESSION LOG: abc123
================================================================================

[001] 2025-09-13T10:00:00 - ORIGINAL_QUERY
----------------------------------------
Query: What are the symptoms of diabetes?
Mode: patient

[002] 2025-09-13T10:00:01 - INPUT_GUARDRAIL
----------------------------------------
Mode: hybrid
Intervention Required: False
Type: none
Explanation: Educational query about diabetes symptoms

[003] 2025-09-13T10:00:01 - API_CALL
----------------------------------------
Model: claude-3-5-sonnet-latest
Tools: ['web_search', 'web_fetch']

[004] 2025-09-13T10:00:15 - API_RESPONSE
----------------------------------------
Response Length: 3210
Tokens: {'input_tokens': 42308, 'output_tokens': 717}
Tool Calls: 2

[005] 2025-09-13T10:00:15 - CITATIONS
----------------------------------------
Citations: 10
  - https://mayoclinic.org/diabetes
  - https://cdc.gov/diabetes

[006] 2025-09-13T10:00:17 - OUTPUT_GUARDRAIL
----------------------------------------
Mode: hybrid
Passes: True
Web Search: True
Trusted Citations: True

[007] 2025-09-13T10:00:17 - FINAL_RESPONSE
----------------------------------------
Response Length: 3286
Processing Time: 17.2s
Guardrails Applied: False
```

### Emergency Query Session

```
================================================================================
SESSION LOG: emergency123
================================================================================

[001] 2025-09-13T10:05:00 - ORIGINAL_QUERY
----------------------------------------
Query: I'm having chest pain right now
Mode: patient

[002] 2025-09-13T10:05:01 - INPUT_GUARDRAIL
----------------------------------------
Mode: hybrid
Intervention Required: True
Type: emergency
Explanation: Chest pain requires immediate medical attention

[003] 2025-09-13T10:05:01 - FINAL_RESPONSE
----------------------------------------
Response Length: 196
Processing Time: 1.5s
Guardrails Applied: True
Emergency Detected: True
```

## Programmatic Access

### Reading Session Logs in Python

```python
from src.utils.session_logging import read_session_log, format_session_log

# Read raw log entries
entries = read_session_log("abc123")

# Get formatted string
formatted = format_session_log("abc123")
print(formatted)

# Process specific stages
for entry in entries:
    if entry["stage"] == "CITATIONS":
        print(f"Found {entry['citation_count']} citations")
        for citation in entry["citations"]:
            print(f"  - {citation['url']}")
```

### Creating Custom Reports

```python
def analyze_session(session_id):
    """Analyze a session for key metrics."""
    entries = read_session_log(session_id)
    
    metrics = {
        "session_id": session_id,
        "processing_time": 0,
        "tokens_used": {"input": 0, "output": 0},
        "citations_count": 0,
        "guardrails_triggered": False,
        "emergency_detected": False
    }
    
    for entry in entries:
        if entry["stage"] == "API_RESPONSE":
            metrics["tokens_used"] = entry["usage"]
        elif entry["stage"] == "CITATIONS":
            metrics["citations_count"] = entry["citation_count"]
        elif entry["stage"] == "OUTPUT_GUARDRAIL":
            metrics["guardrails_triggered"] = not entry["passes_guardrails"]
        elif entry["stage"] == "FINAL_RESPONSE":
            metrics["processing_time"] = entry["processing_time"]
            metrics["emergency_detected"] = entry.get("emergency_detected", False)
    
    return metrics
```

## Integration with Main Logging

The session logging system works alongside the main application logging:

1. **Main logs** (`logs/health_assistant.log`) - High-level application events
2. **Session logs** (`logs/sessions/`) - Detailed request flow tracking

Both use structured JSON format for easy parsing and analysis.

## Monitoring and Analysis

### Key Metrics to Track

1. **Response Time**: Time from query to final response
2. **Token Usage**: Input and output tokens per request
3. **Guardrail Triggers**: Frequency and types of violations
4. **Citation Quality**: Number and domains of sources
5. **Tool Usage**: Web search vs fetch patterns
6. **Error Rates**: Failed requests and error types

### Example Analysis Script

```bash
# Find sessions with guardrail violations
for file in logs/sessions/*.jsonl; do
  if grep -q '"violations":\s*\[' "$file"; then
    basename "$file" | cut -d_ -f2
  fi
done

# Count emergency detections today
grep -l '"intervention_type":\s*"emergency"' logs/sessions/*$(date +%Y%m%d)*.jsonl | wc -l
```

## Best Practices

1. **Session ID Generation**: Use meaningful IDs for testing (e.g., "test-diabetes-001")
2. **Log Retention**: Archive old session logs periodically
3. **Privacy**: Ensure PII is not logged in production
4. **Performance**: Session logging adds ~50ms overhead per request
5. **Storage**: Each session log is typically 5-20KB

## Troubleshooting

### Common Issues

1. **Missing Stages**: Check for exceptions in main application logs
2. **Out of Order**: Verify sequence numbers are incrementing
3. **Large Files**: Long conversations may create large log files
4. **Permission Errors**: Ensure logs/sessions/ directory is writable

### Debug Commands

```bash
# Check latest session for errors
python scripts/view_session_log.py --latest | grep -i error

# Find incomplete sessions (no SESSION_END)
for file in logs/sessions/*.jsonl; do
  if ! grep -q "SESSION_END" "$file"; then
    echo "Incomplete: $file"
  fi
done

# View raw JSON for debugging
python scripts/view_session_log.py <session_id> --format raw | jq '.'
```

## Future Enhancements

1. **Web Dashboard**: Visual session log viewer
2. **Real-time Streaming**: Live session monitoring
3. **Analytics Integration**: Export to monitoring platforms
4. **Compression**: Automatic log compression for storage
5. **Search Interface**: Full-text search across sessions