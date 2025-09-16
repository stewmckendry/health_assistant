# Health Assistant Web Application

## Overview
The Health Assistant web application provides a modern, responsive interface for interacting with the AI-powered medical education platform. Built with Next.js 14 and TypeScript, it features real-time chat, multi-turn conversations, and comprehensive observability through Langfuse.

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

## API Endpoints

### Backend (FastAPI - Port 8000)

#### POST /chat
Process a chat message with the AI assistant.
```json
Request:
{
  "query": "What are flu symptoms?",
  "sessionId": "uuid",
  "userId": "user_uuid"
}

Response:
{
  "content": "Flu symptoms include...",
  "citations": [...],
  "traceId": "langfuse-trace-id",
  "sessionId": "uuid",
  "guardrailTriggered": false,
  "toolCalls": [...]
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

### Frontend API Routes (Next.js - Port 3000)

- `/api/chat` - Proxy to backend chat endpoint
- `/api/feedback` - Proxy to backend feedback endpoint
- `/api/sessions` - Proxy to backend sessions endpoint

## Langfuse Integration

### Trace Architecture
```
patient_query (Main Trace) - Created by @observe decorator
├── llm_call (Generation) - BaseAssistant API call
├── web_search (Span) - If web search performed
├── web_fetch (Span) - If URLs fetched
└── guardrails (Span) - Output validation
```

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
- Loading states
- Feedback integration
- Auto-scrolling

### Message Component
- Markdown rendering with react-markdown
- Citation display
- Role-based styling (user/assistant/system)
- Timestamp display
- Error state handling

### FeedbackButtons
- Thumbs up/down quick feedback
- Rating modal (1-5 stars)
- Comment submission
- Direct Langfuse integration

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