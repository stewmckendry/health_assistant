# Base Assistant Documentation

## Overview

The `BaseAssistant` class serves as the foundational component for all assistant implementations in the Health Assistant system. It handles core interactions with Anthropic's Claude API, including web search and fetch capabilities, multi-turn conversation support, and citation management.

## Architecture

```
BaseAssistant (handles Anthropic API calls)
      ↓
Settings (configuration management)
```

The BaseAssistant provides a clean abstraction layer for Claude API interactions while supporting multiple specialized assistant types that extend its functionality.

## Class: `BaseAssistant`

**Location:** `src/assistants/base.py`

Base class for all assistant implementations, handling core Anthropic API interactions.

### Constructor

```python
BaseAssistant(config: Optional[AssistantConfig] = None)
```

**Parameters:**
- `config`: Optional configuration object. If not provided, uses default settings.

**Configuration (AssistantConfig):**
- `model`: Claude model to use (default: "claude-3-5-sonnet-latest")
- `max_tokens`: Maximum response tokens (default: 1500)
- `temperature`: Model temperature 0.0-1.0 (default: 0.7)
- `system_prompt`: System instruction for the model
- `trusted_domains`: List of allowed domains for web_fetch (97 medical domains)
- `enable_web_fetch`: Enable/disable web fetching (default: True)
- `citations_enabled`: Include citations in responses (default: True)
- `max_web_fetch_uses`: Max web fetches per query (default: 5)

### Methods

#### `query(query: str, session_id: Optional[str] = None, user_id: Optional[str] = None, session_logger: Optional[Any] = None, message_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]`

Send a query to the Anthropic API with support for multi-turn conversations.

**Parameters:**
- `query`: User's question or query text
- `session_id`: Optional session identifier for logging
- `user_id`: Optional user identifier for tracking
- `session_logger`: Optional SessionLogger instance for detailed logging
- `message_history`: Optional conversation history for multi-turn support (list of alternating user/assistant messages)

**Returns:**
```python
{
    "content": str,           # Response text with citations if enabled
    "model": str,             # Model used for generation
    "usage": {
        "input_tokens": int,  # Input token count
        "output_tokens": int  # Output token count
    },
    "citations": List[Dict],  # List of citations from web_fetch
    "tool_calls": List[Dict], # Tool calls made (web_search, web_fetch)
    "session_id": str,        # Session identifier
    "user_id": str            # User identifier
}
```

**Multi-Turn Conversation Support:**
The `message_history` parameter enables Claude to maintain context across multiple conversation turns:
```python
# Example message history format
message_history = [
    {"role": "user", "content": "What are flu symptoms?"},
    {"role": "assistant", "content": "Flu symptoms include fever, cough..."},
    {"role": "user", "content": "How long do they last?"}  # Claude understands "they" = flu symptoms
]
```

**Raises:**
- `ValueError`: If ANTHROPIC_API_KEY is not set
- `Exception`: If API call fails

### Internal Methods

#### `_build_messages(query: str, message_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]`
Constructs the message list for the API request, including conversation history for multi-turn support.

#### `_build_tools() -> Optional[List[Dict[str, Any]]]`
Configures the web_search and web_fetch tools with allowed domains.

#### `_extract_citations(response: Message) -> List[Dict[str, str]]`
Extracts citations from the API response.

#### `_format_response_with_citations(content: str, citations: List[Dict]) -> str`
Formats the response with citation links.

## Tool Integration

### Web Search and Fetch

The BaseAssistant integrates Anthropic's web_search and web_fetch tools:

1. **Web Search**: Finds relevant pages from trusted medical sources
2. **Web Fetch**: Retrieves detailed content from specific URLs
3. **Domain Filtering**: Restricts fetches to 97 trusted medical domains
4. **Citation Extraction**: Automatically formats citations from fetched content

### Trusted Domains

The system uses a curated list of 97 trusted medical domains including:
- Government health sites (.gov)
- Major medical institutions (Mayo Clinic, Cleveland Clinic)
- Academic medical centers
- Professional medical organizations

## Error Handling

All methods include comprehensive error handling:

1. **API Errors**: Caught and logged, safe error message returned
2. **Configuration Errors**: Validated at startup with clear messages
3. **Network Issues**: Graceful degradation with user-friendly messages
4. **Tool Failures**: Fallback to standard responses without web content

## Usage Examples

### Basic Query
```python
from src.assistants.base import BaseAssistant

assistant = BaseAssistant()
response = assistant.query(
    "What are the common symptoms of diabetes?",
    session_id="user-123"
)

print(response["content"])
# Returns educational information with citations
```

### Multi-Turn Conversation
```python
# First message
response1 = assistant.query(
    "What are flu symptoms?",
    session_id="user-123"
)

# Follow-up with context
message_history = [
    {"role": "user", "content": "What are flu symptoms?"},
    {"role": "assistant", "content": response1["content"]}
]

response2 = assistant.query(
    "How long do they typically last?",
    session_id="user-123",
    message_history=message_history
)
# Claude understands "they" refers to flu symptoms
```

### With Custom Configuration
```python
from src.config.settings import AssistantConfig

config = AssistantConfig(
    model="claude-3-opus-20240229",
    max_tokens=2000,
    temperature=0.5,
    enable_web_fetch=True
)

assistant = BaseAssistant(config=config)
```

## Logging

All operations are logged with structured JSON format:

```json
{
    "timestamp": "2024-01-01T12:00:00",
    "level": "INFO",
    "name": "src.assistants.base",
    "message": "Query received",
    "session_id": "user-123",
    "query_length": 45,
    "model": "claude-3-5-sonnet-latest",
    "tokens_used": 1250
}
```

## Performance Characteristics

- **Response Time**: Typically 2-5 seconds
- **Token Limits**: 1500 tokens per response (configurable)
- **Web Fetch**: Max 5 fetches per query (configurable)
- **Caching**: Not implemented (stateless design)

## Extension Points

The BaseAssistant is designed for extension by specialized assistants:

1. **System Prompts**: Override with specialized medical contexts
2. **Guardrails**: Add safety checks before and after API calls
3. **Post-processing**: Modify responses for specific audiences
4. **Configuration**: Extend with mode-specific settings

## Testing

The BaseAssistant includes comprehensive test coverage:

```bash
# Run base assistant tests
pytest tests/unit/test_base_assistant.py

# Test with web tools
pytest tests/integration/test_base_assistant_integration.py
```

## Security Considerations

1. **API Key Protection**: Never log or expose API keys
2. **Input Validation**: All user input sanitized
3. **Domain Restriction**: Only trusted medical sources
4. **Session Isolation**: No cross-session data leakage
5. **Rate Limiting**: Configurable limits on web fetches