# Settings System Documentation

## Overview

The Health Assistant application provides a comprehensive settings system that allows users to configure their experience at the session level. Settings are stored per session and persist throughout the conversation, providing fine-grained control over safety features, performance optimization, and display preferences.

## Architecture

### Session Settings Model

The core settings are defined in `src/config/session_settings.py` using Pydantic:

```python
class SessionSettings(BaseModel):
    # Safety Settings
    enable_input_guardrails: bool = Field(default=True)
    enable_output_guardrails: bool = Field(default=False)
    guardrail_mode: Optional[str] = Field(default=None)
    
    # Performance Settings  
    enable_streaming: bool = Field(default=True)
    enable_web_search: bool = Field(default=True)
    max_web_fetches: int = Field(default=2)
    blocked_domains: List[str] = Field(default_factory=list)
    custom_trusted_domains: List[str] = Field(default_factory=list)
    
    # Model Settings
    model: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None)
    max_tokens: Optional[int] = Field(default=None)
    
    # Display Settings
    show_citations: bool = Field(default=True)
    show_thinking_process: bool = Field(default=False)
    response_format: str = Field(default="markdown")
```

### Storage

Settings are stored in-memory using a dictionary in the FastAPI application state:

- Key: Session ID (UUID)
- Value: SessionSettings instance
- Lifetime: Application lifetime (resets on server restart)

## API Endpoints

### Create Session
```http
POST /sessions
```
Creates a new session with default settings.

**Response:**
```json
{
  "sessionId": "uuid",
  "userId": "user_uuid",
  "createdAt": "2025-09-16T20:00:00.000Z"
}
```

### Get Session Settings
```http
GET /sessions/{session_id}/settings
```
Retrieves current settings for a session.

**Response:**
```json
{
  "enable_input_guardrails": true,
  "enable_output_guardrails": false,
  "enable_streaming": true,
  "enable_web_search": true,
  "max_web_fetches": 2,
  "blocked_domains": [],
  "custom_trusted_domains": [],
  "model": null,
  "temperature": null,
  "max_tokens": null,
  "show_citations": true,
  "show_thinking_process": false,
  "response_format": "markdown"
}
```

### Update Session Settings
```http
PUT /sessions/{session_id}/settings
```
Updates settings for a session. Only provided fields are updated.

**Request Body:**
```json
{
  "enable_output_guardrails": true,
  "enable_streaming": false,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "sessionId": "uuid",
  "settings": { /* updated settings */ },
  "success": true
}
```

### Get Trusted Domains
```http
GET /settings/trusted-domains
```
Returns the list of default trusted medical domains (97 domains).

**Response:**
```json
{
  "trusted_domains": [
    "pubmed.ncbi.nlm.nih.gov",
    "mayoclinic.org",
    "cdc.gov",
    // ... 94 more domains
  ],
  "count": 97
}
```

## Settings Behavior

### Guardrails and Streaming Interaction

The settings system enforces important compatibility rules:

1. **Output Guardrails Disable Streaming**: When `enable_output_guardrails` is true, streaming is automatically disabled regardless of the `enable_streaming` setting. This is because output guardrails need the complete response to analyze.

2. **Input Guardrails Work with Both**: Input guardrails are compatible with both streaming and non-streaming modes.

### Decision Logic (in `main.py`)

```python
# Determine actual streaming behavior
use_streaming = settings.enable_streaming and not settings.enable_output_guardrails

if settings.enable_output_guardrails:
    # Force non-streaming for output guardrails
    use_streaming = False
```

### Domain Management

Users can customize which domains are used for web search:

1. **Default Trusted Domains**: 97 pre-configured medical and health websites
2. **Blocked Domains**: User can block specific domains from the default list
3. **Custom Trusted Domains**: User can add additional trusted domains

The effective domain list is calculated as:
```
Effective = (Default - Blocked) + Custom
```

## Frontend Integration

### Settings Panel Component

Located at `web/components/settings/SettingsPanel.tsx`, the settings panel provides:

- **Tabbed Interface**: Safety, Performance, Model, and Display tabs
- **Real-time Updates**: Changes are saved immediately via API
- **Visual Feedback**: Success/error toast notifications
- **Domain Search**: Filter and search through trusted domains
- **Responsive Design**: Mobile-friendly layout

### Key Features

1. **Safety Tab**
   - Toggle input/output guardrails
   - Select guardrail mode (LLM, Regex, Hybrid)
   - Warning when output guardrails disable streaming

2. **Performance Tab**
   - Enable/disable streaming
   - Configure web search and fetch limits
   - Manage trusted domains (search, block, add custom)

3. **Model Tab**
   - Select AI model
   - Adjust temperature (0-1)
   - Set max tokens

4. **Display Tab**
   - Toggle citation visibility
   - Show/hide thinking process
   - Choose response format

## Session Lifecycle

1. **Session Creation**: User starts chat → new session with default settings
2. **Settings Modification**: User adjusts settings via UI → PUT request updates session
3. **Query Processing**: Each query uses session settings to determine behavior
4. **Session Persistence**: Settings persist for session lifetime
5. **Session Cleanup**: Settings cleared on server restart (in-memory storage)

## Default Settings Rationale

The defaults are chosen for optimal user experience:

- **Input Guardrails ON**: Protect against harmful requests
- **Output Guardrails OFF**: Enable fast streaming responses
- **Streaming ON**: Provide immediate feedback (<1 second)
- **Web Search ON**: Access latest medical information
- **Max Fetches 2**: Balance thoroughness with performance
- **Citations ON**: Transparency about information sources

## Performance Impact

Settings directly affect response time:

| Configuration | Time to First Token | Total Time |
|--------------|-------------------|------------|
| Streaming + No Output Guardrails | <1 second | 15-20 seconds |
| Non-streaming + Output Guardrails | 20-30 seconds | 20-30 seconds |
| No Web Tools | <1 second | 3-5 seconds |

## Future Enhancements

Potential improvements to the settings system:

1. **Persistent Storage**: Move from in-memory to database storage
2. **User Profiles**: Save preferred settings across sessions
3. **Presets**: Quick-select configurations (Safe Mode, Fast Mode, Research Mode)
4. **Export/Import**: Share settings configurations
5. **Analytics**: Track which settings correlate with user satisfaction
6. **A/B Testing**: Experiment with default values
7. **Granular Guardrails**: Configure specific safety rules
8. **Rate Limiting**: Per-session API usage limits