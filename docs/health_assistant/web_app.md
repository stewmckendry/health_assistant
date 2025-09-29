# Health Assistant Web Application

## Overview
The Health Assistant web application provides a modern, responsive interface for interacting with the AI-powered medical education platform. Built with Next.js 14 and TypeScript, it features real-time chat, multi-turn conversations, streaming responses, and comprehensive observability through Langfuse.

### Recent Enhancements (Performance Optimization Update)
- **Streaming Responses**: Real-time message streaming with SSE for faster perceived performance
- **Message Regeneration**: Re-generate last assistant response while preserving conversation context
- **Enhanced Feedback System**: 5-star rating with optional comments replacing thumbs up/down
- **Provider Mode Security**: Password-protected access to provider mode
- **Settings Panel**: Read-only configuration viewer for transparency
- **UI/UX Improvements**: Contextual input placeholders, improved button layouts, and research disclaimer

## Architecture

### Technology Stack
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **UI Components**: shadcn/ui, Lucide icons
- **Backend API**: FastAPI (Python)
- **Observability**: Langfuse v3
- **State Management**: React hooks, localStorage

### Server Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│  FastAPI Backend │────▶│ PatientAssistant│
│   (Port 3000)   │◀────│   (Port 8000)    │◀────│  (Anthropic)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                        │                         │
         └────────────────────────┴─────────────────────────┘
                                 │
                          ┌──────▼────────┐
                          │   Langfuse    │
                          │ (Observability)│
                          └───────────────┘
```

## Multi-Turn Conversations

### Implementation
The application supports full multi-turn conversations using Anthropic's native message history feature:

1. **Message History Management**
   - Frontend maintains conversation in ChatInterface component
   - Backend stores sessions in memory (main.py)
   - History passed to Anthropic API in proper format

2. **Anthropic Integration**
   ```python
   # BaseAssistant._build_messages()
   messages = [
       {"role": "user", "content": "What are flu symptoms?"},
       {"role": "assistant", "content": "Flu symptoms include..."},
       {"role": "user", "content": "How long do they last?"}  # Context preserved
   ]
   ```

3. **Context Preservation**
   - Each query includes full conversation history
   - Claude maintains context across turns
   - Enables natural follow-up questions

## Session & User Management

### Session IDs
- **Generation**: UUID v4 format
- **Storage**: localStorage with 24-hour expiration
- **Rotation**: New session on button click or expiration
- **Format**: `66226e22-17a7-42bb-84a7-0c0b5eb92610`

### User IDs
- **Generation**: `user_${UUID}` format
- **Storage**: localStorage with no expiration
- **Persistence**: Maintained across all sessions
- **Purpose**: Track user across multiple conversations

### Lifecycle
```javascript
// useSession hook behavior
1. Page Load:
   - Check localStorage for existing session
   - If valid (< 24 hours) → reuse
   - If invalid/missing → create new via /api/sessions

2. New Session Button:
   - Call /api/sessions for fresh session ID
   - Keep same user ID
   - Reload page to clear chat

3. Storage Keys:
   - Session: 'health_assistant_session'
   - User: 'health_assistant_user'
```

## Mode Selection System

### Assistant Mode Toggle
The web application supports switching between two assistant modes:

#### Patient Mode (Default)
- **Target Audience**: General public, patients, caregivers
- **Content Style**: Patient-friendly language, educational focus
- **Guardrails**: Strict safety measures, emergency detection
- **Sources**: 119 trusted medical domains
- **Features**: Comprehensive disclaimers, emergency redirects

#### Provider Mode
- **Target Audience**: Healthcare professionals, clinicians
- **Content Style**: Technical medical terminology, clinical details
- **Guardrails**: Relaxed safety measures for professional context
- **Sources**: 169 trusted domains (119 + 76 provider-specific)
- **Features**: Clinical decision support, professional formatting
- **Access Control**: Password-protected (password: `iunderstandthisisaresearchproject`)
  - Password dialog with visibility toggle
  - Access persisted in localStorage after authentication
  - Clear research project disclaimer

### Mode Toggle Implementation

#### Frontend Components
1. **ModeToggle Component** (`web/components/ModeToggle.tsx`)
   ```typescript
   interface ModeToggleProps {
     onModeChange?: (mode: AssistantMode) => void;
     defaultMode?: AssistantMode;
   }
   
   type AssistantMode = 'patient' | 'provider';
   ```

2. **Persistent Storage**
   - Mode preference stored in localStorage
   - Key: `'assistantMode'`
   - Restored on page reload
   - Defaults to 'patient' mode

3. **UI Design**
   - Toggle switch with clear mode labels
   - Visual indicators for current mode
   - Accessible design with proper ARIA labels

#### Backend Integration
The mode selection affects assistant instantiation:

```python
# src/web/api/main.py
def get_assistant(mode: str = "patient"):
    global patient_assistant, provider_assistant
    
    if mode == "provider":
        if provider_assistant is None:
            provider_assistant = ProviderAssistant()
        return provider_assistant
    else:
        if patient_assistant is None:
            patient_assistant = PatientAssistant()
        return patient_assistant
```

### API Updates

#### Request Format
The chat request now includes mode selection:
```json
{
  "query": "What are current AHA guidelines for AFib anticoagulation?",
  "sessionId": "uuid",
  "userId": "user_uuid",
  "mode": "provider"
}
```

#### Response Enhancements
Provider mode responses include:
- Enhanced markdown formatting
- Technical medical terminology
- Extended citation sources
- Professional disclaimers

## Clinical Decision Support - Emergency Department Triage

### Overview
The ED Triage page provides a comprehensive clinical decision support tool for emergency department triage assessment using the Canadian Triage and Acuity Scale (CTAS). Built with OpenAI Agents SDK v0.3.1, it uses a multi-agent orchestration pattern inspired by MAI-DxO.

### Features
- **Real-time Progress Updates**: Streaming SSE shows which specialist agent is analyzing
- **Multi-Agent Coordination**: Orchestrator coordinates three specialist agents
- **CTAS Assessment**: Standardized 1-5 level triage scoring
- **Visual Progress Indicators**: Color-coded updates for different analysis phases
- **Test Case Presets**: Quick-load common emergency scenarios

### Agent Architecture
```
Emergency Triage Orchestrator
├── Red Flag Detector (Critical symptoms identification)
├── CTAS Triage Assessor (Acuity level determination)  
└── Workup Suggester (Initial diagnostic recommendations)
```

### UI Components
- **Patient Information Form**: Age, sex, chief complaint, symptoms
- **Vital Signs Input**: Blood pressure, heart rate, temperature, SpO2
- **Medical History Section**: Conditions, medications, allergies
- **Progress Display**: Real-time streaming updates with:
  - Blue activity icons for tool calls
  - Green checkmarks for completed analyses
  - Tool output summaries (e.g., "✓ No red flags identified")
- **Results Panel**: CTAS level badge, disposition, recommended actions

### Streaming Implementation
```typescript
// Real-time SSE updates
data: {"type": "tool_call", "tool": "Red Flag Detector", "progress": 30}
data: {"type": "tool_result", "data": {"summary": "✓ No red flags"}, "progress": 40}
data: {"type": "final", "result": {...complete assessment...}, "progress": 100}
```

### API Endpoints

#### POST /api/agents/triage/stream
Stream emergency triage assessment with real-time updates.
```json
Request:
{
  "age": 65,
  "sex": "Male",
  "chief_complaint": "Chest pain",
  "history": "Sudden onset crushing chest pain...",
  "symptoms": ["Chest pain", "Shortness of breath"],
  "vitals": {
    "blood_pressure": "150/95",
    "heart_rate": 110,
    "respiratory_rate": 24,
    "temperature": 36.8,
    "oxygen_saturation": 94,
    "pain_scale": 9
  },
  "medical_history": ["Hypertension", "Diabetes"],
  "medications": ["Metoprolol", "Metformin"],
  "allergies": [],
  "session_id": "triage_12345"
}

Response: Server-Sent Events (text/event-stream)
```

#### POST /api/agents/triage
Non-streaming version for synchronous triage assessment.

### Performance Metrics
- **Response Time**: <5 seconds for complete assessment
- **Accuracy**: 80% alignment with expert triage decisions
- **Agent Coordination**: Single-call to each specialist (no duplicates)

## API Endpoints

### Backend (FastAPI - Port 8000/8001)

#### POST /chat
Process a chat message with the AI assistant.
```json
Request:
{
  "query": "What are flu symptoms?",
  "sessionId": "uuid",
  "userId": "user_uuid",
  "mode": "patient"
}

Response:
{
  "content": "Flu symptoms include...",
  "citations": [...],
  "traceId": "langfuse-trace-id",
  "sessionId": "uuid",
  "guardrailTriggered": false,
  "toolCalls": [...],
  "mode": "patient"
}
```

#### POST /feedback
Submit user feedback for a specific interaction.
```json
Request:
{
  "traceId": "langfuse-trace-id",
  "sessionId": "uuid",
  "userId": "user_uuid",
  "rating": 5,
  "thumbsUp": true,
  "comment": "Helpful response"
}
```

#### POST /sessions
Create a new chat session.
```json
Request:
{
  "userId": "user_uuid"
}

Response:
{
  "sessionId": "new-uuid",
  "userId": "user_uuid",
  "createdAt": "2025-01-15T10:00:00Z"
}
```

#### GET /sessions/{session_id}
Retrieve session information and message history.

#### POST /chat/stream
Stream chat responses using Server-Sent Events (SSE) for real-time response delivery.
```
Request:
{
  "query": "What are symptoms of the flu?",
  "sessionId": "uuid",
  "mode": "patient",
  "messages": [...]  // Full conversation history for context
}

Response: text/event-stream
data: {"type": "start", "traceId": "..."}
data: {"type": "text", "content": "Influenza..."}
data: {"type": "text", "content": " symptoms include..."}
data: {"type": "citation", "content": {...}}
data: {"type": "end", "guardrailTriggered": false}
```

**Streaming Implementation Details**:
- Chunks are sent as they're generated
- Frontend updates message in real-time
- Citations collected and displayed at end
- Trace ID included for Langfuse integration
- Graceful fallback to non-streaming if disabled

#### GET /sessions/{session_id}/settings
Get current settings for a session.
```json
Response:
{
  "enable_input_guardrails": true,
  "enable_output_guardrails": false,
  "enable_streaming": true,
  "enable_web_search": true,
  "max_web_fetches": 2,
  "blocked_domains": [],
  "custom_trusted_domains": []
}
```

#### PUT /sessions/{session_id}/settings
Update settings for a session.
```json
Request:
{
  "enable_output_guardrails": true,
  "enable_streaming": false
}

Response:
{
  "sessionId": "uuid",
  "settings": {...},
  "success": true
}
```

#### GET /settings/trusted-domains
Get list of default trusted medical domains.
```json
Response:
{
  "trusted_domains": ["pubmed.ncbi.nlm.nih.gov", ...],
  "count": 97
}
```

### Frontend API Routes (Next.js - Port 3000)

- `/api/chat` - Proxy to backend chat endpoint
- `/api/feedback` - Proxy to backend feedback endpoint
- `/api/sessions` - Proxy to backend sessions endpoint

## Langfuse Integration

### Trace Architecture
```
patient_query/provider_query (Main Trace) - Created by @observe decorator
├── llm_call (Generation) - BaseAssistant API call
├── web_search (Span) - If web search performed
├── web_fetch (Span) - If URLs fetched
└── guardrails (Span) - Output validation (patient mode only)
```

### Mode-Specific Tagging
The system includes mode-specific tags for observability:

**Patient Mode Tags:**
- `mode:patient` - Identifies patient assistant queries
- `patient_assistant` - Assistant type tag
- `guardrail_hybrid` - Guardrail mode applied

**Provider Mode Tags:**
- `mode:provider` - Identifies provider assistant queries  
- `provider_assistant` - Assistant type tag
- `guardrail_hybrid` - Guardrail mode (minimal for providers)

### Key Implementation Details

1. **Single Trace Per Turn**
   - PatientAssistant's `@observe` decorator creates the main trace
   - No duplicate traces in web API layer
   - Trace ID passed through response chain

2. **Session Linking**
   - All conversation turns share same session_id
   - Enables conversation flow analysis in Langfuse
   - User ID links sessions across conversations

3. **Trace ID Flow**
   ```python
   # PatientAssistant.query() - Inside @observe context
   trace_id = langfuse.get_current_trace_id()
   api_response["trace_id"] = trace_id
   
   # main.py - Outside @observe context
   trace_id = response.get('trace_id')  # From PatientAssistant
   if not trace_id:
       trace_id = str(uuid.uuid4())  # Fallback
   ```

4. **Feedback Attachment**
   ```python
   # Feedback uses trace_id to attach scores
   langfuse_client.create_score(
       trace_id=request.traceId,
       name="user-rating",
       value=float(request.rating)
   )
   ```

## UI Components

### ChatInterface
Main chat component handling:
- Message display with markdown rendering
- Input handling and submission
- Loading states with streaming support
- Feedback integration
- Auto-scrolling
- **New Features**:
  - Message regeneration button
  - Start new session button
  - Contextual input placeholders
  - Research project disclaimer banner
  - Conversation history preservation

### Message Component
- Markdown rendering with react-markdown
- Citation display with deduplication
- Role-based styling (user/assistant/system)
- Timestamp display
- Error state handling
- Streaming text support

### FeedbackButtons (Enhanced)
- **5-star rating system** (replaced thumbs up/down)
- **Comment dialog** that appears after rating selection
- **Skip option** for rating without comment
- **Visual feedback** with "Thank you" confirmation
- **Hover effects** on star ratings
- Direct Langfuse integration with structured feedback

### Action Buttons
Located below assistant messages:
- **Regenerate Button**: Re-generates last assistant response
  - Preserves full conversation history
  - Removes only the last assistant message
  - Maintains context for follow-up
- **Start New Session**: Clears chat and starts fresh
  - Resets to initial system message
  - Creates new session ID
  - Maintains user ID

### Settings Panel (Read-Only)
Comprehensive settings viewer with four tabs:
- **Safety Tab**:
  - Input/Output guardrails status
  - Guardrail mode (regex/LLM/hybrid)
  - Trusted domains configuration
  - Custom domain management (view only)
- **Performance Tab**:
  - Streaming enable/disable status
  - Web search limits
  - Response timeout settings
  - Detail level configuration
- **Model Tab**:
  - AI model selection display
  - Temperature settings
  - Max token limits
  - Confidence score visibility
- **Display Tab**:
  - Tool call visibility
  - Response timing display
  - Markdown rendering options

**Note**: All settings are read-only with "View Only" badge to indicate configuration is controlled by administrators

## Styling & Responsiveness

### Design System
- **Theme**: Light/dark mode support via next-themes
- **Components**: shadcn/ui for consistent design
- **Layout**: Responsive flex layout
- **Typography**: Tailwind prose for content

### CSS Handling
```css
/* Overflow handling for long content */
.overflow-hidden
.break-words
.overflow-wrap-anywhere

/* Flexible layout for expansion */
.flex.flex-col.h-full (not fixed height)
```

## Error Handling

### Frontend
- Try-catch blocks in API calls
- Fallback error messages
- Loading state management
- Network error recovery

### Backend
- Validation with Pydantic models
- HTTP exception handling
- Langfuse context errors handled gracefully
- Fallback trace ID generation

## Security Considerations

1. **No Authentication** (Demo phase)
   - Sessions are client-generated
   - No user verification
   - In-memory storage only

2. **Input Validation**
   - Pydantic models for request/response
   - Required field validation
   - Type checking

3. **CORS Configuration**
   - Allowed origins: localhost:3000, localhost:3001
   - Credentials allowed for session management

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Environment variables configured

### Running the Application

1. **Start Backend**
   ```bash
   source ~/spacy_env/bin/activate
   python scripts/start_backend.py
   # Or directly:
   uvicorn src.web.api.main:app --port 8000
   ```

2. **Start Frontend**
   ```bash
   cd web
   npm install
   npm run dev
   ```

3. **Access Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Testing

### Manual Testing Flow
1. Open browser to http://localhost:3000
2. Send initial message (e.g., "What are flu symptoms?")
3. Send follow-up (e.g., "How long do they last?")
4. Verify context preservation
5. Check Langfuse for traces
6. Test feedback submission

### Verification Points
- ✅ Multi-turn context maintained
- ✅ Single trace per conversation turn
- ✅ Feedback attached to correct trace
- ✅ Session persistence across refresh
- ✅ New session button functionality

## Known Issues & Limitations

1. **In-Memory Storage**
   - Sessions lost on backend restart
   - Not suitable for production
   - No persistence between deployments

2. **Session Mismatch**
   - Frontend persists session ID in localStorage
   - Backend loses sessions on restart
   - Can cause empty conversation history

3. **No Rate Limiting**
   - No API rate limiting implemented
   - Could be abused in production

4. **Limited Error Recovery**
   - Basic error messages
   - No retry logic
   - No offline support

## Future Enhancements

1. **Persistent Storage**
   - Database for session storage
   - Redis for caching
   - Message history persistence

2. **Authentication**
   - User authentication system
   - Session validation
   - API key management

3. **Enhanced Features**
   - Streaming responses
   - File uploads
   - Voice input/output
   - Export conversations

4. **Production Ready**
   - Rate limiting
   - Request queuing
   - Health checks
   - Monitoring/alerting