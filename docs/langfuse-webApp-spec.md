# Langfuse Web Application Integration Specification

## Overview

This specification outlines the integration of Langfuse user feedback collection and observability features into the Health Assistant web application (Phase 3). The web app will enable multi-turn conversations with the patient assistant while collecting user feedback that feeds directly into Langfuse for evaluation and improvement.

## Architecture Overview

```
┌─────────────────────┐
│   React/Next.js     │
│   Web Application   │
├─────────────────────┤
│  - Chat Interface   │
│  - Feedback UI      │
│  - Session Mgmt     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    API Routes       │
│   (Next.js/FastAPI) │
├─────────────────────┤
│  - /api/chat        │
│  - /api/feedback    │
│  - /api/sessions    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Health Assistant   │
│    Backend          │
├─────────────────────┤
│  - PatientAssistant │
│  - Langfuse SDK     │
│  - Session Logger   │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│     Langfuse        │
│   Cloud Platform    │
├─────────────────────┤
│  - Traces           │
│  - User Scores      │
│  - Analytics        │
└─────────────────────┘
```

## Core Requirements

### 1. Multi-Turn Conversation Support
- Maintain session continuity across multiple user interactions
- Track conversation history within Langfuse sessions
- Associate all messages in a conversation with the same session ID
- Enable conversation reset/new session functionality

### 2. User Feedback Collection
- **Feedback Types**:
  - Binary feedback (thumbs up/down)
  - Numeric ratings (1-5 stars)
  - Text comments/suggestions
  - Category-based feedback (helpful, accurate, unclear, etc.)
- **Feedback Association**:
  - Link feedback to specific traces (entire conversations)
  - Link feedback to specific observations (individual messages)
  - Include session and user IDs for aggregation

### 3. Langfuse Integration Points
- **Frontend**: LangfuseWeb SDK for browser-side feedback submission
- **Backend**: Langfuse SDK for server-side tracing and scoring
- **API**: REST endpoints for custom feedback flows

## Technical Implementation

### Frontend Components

#### 1. Session Management Hook
```typescript
// hooks/useSessionTracking.ts
export function useSessionTracking() {
  const [sessionId, setSessionId] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  
  useEffect(() => {
    // Initialize or retrieve session
    const storedSessionId = localStorage.getItem('health_assistant_session');
    const storedUserId = localStorage.getItem('health_assistant_user');
    
    if (!storedSessionId) {
      const newSessionId = `session_${uuidv4()}`;
      localStorage.setItem('health_assistant_session', newSessionId);
      setSessionId(newSessionId);
    } else {
      setSessionId(storedSessionId);
    }
    
    if (!storedUserId) {
      const newUserId = `user_${uuidv4()}`;
      localStorage.setItem('health_assistant_user', newUserId);
      setUserId(newUserId);
    } else {
      setUserId(storedUserId);
    }
  }, []);
  
  return { sessionId, userId, startNewSession };
}
```

#### 2. Feedback Component Interface
```typescript
interface UserFeedbackProps {
  traceId: string;           // Required: Links to conversation trace
  observationId?: string;    // Optional: Links to specific message
  sessionId: string;         // Required: Current session
  userId?: string;           // Optional: User identifier
  onFeedbackSubmitted?: () => void;  // Callback after submission
}
```

#### 3. Chat Interface Requirements
- Display conversation history
- Show typing indicators during API calls
- Display citations from assistant responses
- Show guardrail warnings if triggered
- Enable feedback on each assistant message
- Support conversation export/sharing

### Backend Integration

#### 1. API Endpoints

**POST /api/chat**
```typescript
interface ChatRequest {
  message: string;
  sessionId: string;
  userId?: string;
  conversationHistory: Message[];
}

interface ChatResponse {
  response: string;
  citations: Citation[];
  traceId: string;
  observationId: string;
  sessionId: string;
  guardrailsApplied: boolean;
  emergencyDetected: boolean;
}
```

**POST /api/feedback**
```typescript
interface FeedbackRequest {
  traceId: string;
  observationId?: string;
  sessionId: string;
  userId?: string;
  feedbackType: 'thumbs' | 'rating' | 'comment' | 'category';
  value: number | string;
  comment?: string;
}
```

**GET /api/sessions/:sessionId**
```typescript
interface SessionResponse {
  sessionId: string;
  messages: Message[];
  feedbackScores: FeedbackScore[];
  metadata: {
    startTime: Date;
    lastActivity: Date;
    messageCount: number;
  };
}
```

#### 2. Langfuse Trace Structure
```
Web Conversation Trace
├── chat_request (SPAN)
│   ├── input_guardrail_check (SPAN)
│   ├── llm_call (GENERATION)
│   │   ├── tool:web_search (SPAN)
│   │   └── tool:web_fetch (SPAN)
│   └── output_guardrail_check (SPAN)
└── user_feedback (SCORE) [Added post-response]
```

### Configuration

#### Environment Variables
```bash
# Frontend (.env.local)
NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY=pk-lf-...
NEXT_PUBLIC_LANGFUSE_HOST=https://cloud.langfuse.com
NEXT_PUBLIC_API_URL=http://localhost:3000

# Backend (.env)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
ANTHROPIC_API_KEY=sk-ant-...
```

#### Langfuse Web SDK Initialization
```typescript
// lib/langfuse-client.ts
import { LangfuseWeb } from 'langfuse';

export const langfuseWeb = new LangfuseWeb({
  publicKey: process.env.NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY!,
  baseUrl: process.env.NEXT_PUBLIC_LANGFUSE_HOST,
});
```

## UI/UX Guidelines

### 1. Chat Interface Design
- **Message Layout**: Clear visual distinction between user and assistant messages
- **Timestamp Display**: Show relative times (e.g., "2 minutes ago")
- **Citation Display**: Inline links to trusted sources
- **Loading States**: Skeleton loaders or typing indicators
- **Error States**: User-friendly error messages with retry options

### 2. Feedback UI Patterns
- **Immediate Feedback**: Thumbs up/down buttons on each message
- **Detailed Feedback**: Expandable section for ratings and comments
- **Confirmation**: Visual feedback when score is submitted
- **Non-intrusive**: Feedback UI shouldn't obstruct conversation flow

### 3. Session Management UI
- **New Conversation**: Clear button to start fresh session
- **Conversation History**: Sidebar or dropdown to access past sessions
- **Export Options**: Download conversation as PDF or text
- **Clear History**: Option to clear local session data

## Data Privacy & Security

### 1. Client-Side Security
- Only use public keys in browser code
- No sensitive medical data in localStorage
- Session IDs should be anonymous identifiers
- Implement HTTPS for all communications

### 2. Feedback Privacy
- No PII in feedback comments
- Anonymous user IDs by default
- Option to opt-out of tracking
- Clear data retention policy display

### 3. Compliance Considerations
- HIPAA-compliant if handling real patient data
- GDPR compliance for EU users
- Clear terms of service and privacy policy
- Medical disclaimer prominently displayed

## Performance Optimization

### 1. Feedback Submission
- Asynchronous feedback submission (non-blocking)
- Batch multiple feedback items if needed
- Retry logic with exponential backoff
- Queue feedback locally if offline

### 2. Session Management
- Lazy load conversation history
- Implement pagination for long conversations
- Cache recent sessions in memory
- Compress conversation data in localStorage

### 3. Real-time Updates
- WebSocket connection for live updates (optional)
- Optimistic UI updates for feedback
- Debounce rapid feedback submissions

## Testing Requirements

### 1. Unit Tests
```typescript
// __tests__/UserFeedback.test.tsx
describe('UserFeedbackComponent', () => {
  it('submits thumbs up feedback to Langfuse');
  it('submits star rating with correct value');
  it('includes session ID in feedback');
  it('shows confirmation after submission');
  it('handles submission errors gracefully');
});
```

### 2. Integration Tests
```typescript
// __tests__/chat-integration.test.ts
describe('Chat Integration', () => {
  it('maintains session across multiple messages');
  it('associates feedback with correct trace');
  it('retrieves conversation history by session');
  it('starts new session when requested');
});
```

### 3. E2E Tests
```typescript
// e2e/feedback-flow.spec.ts
describe('Feedback Flow', () => {
  it('user can submit feedback after receiving response');
  it('feedback appears in Langfuse dashboard');
  it('session tracking persists across page refreshes');
});
```

## Implementation Phases

### Phase 3.1: Basic Chat Interface (Week 1)
- [ ] Set up Next.js project with TypeScript
- [ ] Create basic chat UI components
- [ ] Implement session management hooks
- [ ] Connect to existing Health Assistant API
- [ ] Display assistant responses with citations

### Phase 3.2: Feedback Integration (Week 2)
- [ ] Install and configure Langfuse Web SDK
- [ ] Create feedback UI components
- [ ] Implement feedback submission logic
- [ ] Add feedback confirmation UI
- [ ] Test feedback flow end-to-end

### Phase 3.3: Session Management (Week 3)
- [ ] Implement conversation history retrieval
- [ ] Add new conversation functionality
- [ ] Create session sidebar/dropdown
- [ ] Add conversation export feature
- [ ] Implement local storage management

### Phase 3.4: Polish & Testing (Week 4)
- [ ] Add loading and error states
- [ ] Implement responsive design
- [ ] Write comprehensive tests
- [ ] Performance optimization
- [ ] Documentation and deployment

## Success Metrics

### User Engagement
- **Target**: >50% of users provide feedback
- **Measurement**: Feedback submission rate per session

### Feedback Quality
- **Target**: >30% of feedback includes comments
- **Measurement**: Comment rate on feedback submissions

### Session Continuity
- **Target**: Average 5+ messages per session
- **Measurement**: Messages per session in Langfuse

### Performance
- **Target**: <100ms feedback submission time
- **Measurement**: Client-side performance monitoring

### Error Rate
- **Target**: <1% feedback submission failures
- **Measurement**: Error logs and retry metrics

## Monitoring & Analytics

### Langfuse Dashboard Metrics
- Session duration and message count
- Feedback distribution (positive/negative)
- Most common feedback categories
- User engagement patterns
- Response quality scores over time

### Custom Analytics
- Conversation topic clustering
- Peak usage times
- Drop-off points in conversations
- Feedback sentiment analysis
- Citation click-through rates

## Troubleshooting Guide

### Common Issues

1. **Feedback not appearing in Langfuse**
   - Verify public key is correct
   - Check network tab for API errors
   - Ensure trace ID is valid
   - Verify Langfuse SDK version compatibility

2. **Session not persisting**
   - Check localStorage permissions
   - Verify session ID format
   - Clear browser cache and retry
   - Check for conflicting session management

3. **Slow feedback submission**
   - Implement client-side queuing
   - Check network latency
   - Consider batch submissions
   - Use async submission pattern

## References

- [Langfuse Web SDK Documentation](https://langfuse.com/docs/sdk/typescript)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)
- [React Hooks for State Management](https://react.dev/reference/react)
- [Health Assistant API Documentation](../api_specification.md)
- [Langfuse Scoring API](https://langfuse.com/docs/scores)

## Appendix: Example Implementation Files

### A. Complete Feedback Component
See implementation in `/examples/UserFeedbackComponent.tsx`

### B. Session Management Hook
See implementation in `/examples/useSessionTracking.ts`

### C. Chat Interface Component
See implementation in `/examples/ChatInterface.tsx`

### D. API Route Handler
See implementation in `/examples/api-chat-route.ts`

---

**Document Version**: 1.0.0
**Last Updated**: September 2025
**Phase**: 3 - Web Application