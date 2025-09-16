# Phase 3: Web Application Development - Startup Guide

## 🚀 Welcome to Phase 3!

You're working on the **Web Application** phase of the Health Assistant project.

### 📍 Current Context

**Repository**: `/Users/liammckendry/health_assistant_phase3`  
**Branch**: `phase-3-web-application`  
**GitHub Issue**: [#5](https://github.com/stewmckendry/health_assistant/issues/5)

### ✅ What's Already Complete

#### Phase 1: Basic Patient Assistant
- PatientAssistant with 3-layer guardrails (LLM, regex, hybrid)
- Emergency and crisis detection
- 97 trusted medical domains
- Web search/fetch tools integration
- Session logging infrastructure

#### Phase 2: Evaluation Framework  
- Langfuse SDK integration with observability
- LLM-as-Judge evaluation (6 metrics)
- Granular tool tracking (nested spans)
- Session and user tracking
- 91 test cases in evaluation dataset
- DatasetEvaluator for batch testing

### 🎯 Phase 3 Objectives

Build a modern web interface that:
1. **Enables multi-turn conversations** with the PatientAssistant
2. **Integrates Langfuse** for observability and user feedback
3. **Displays citations and guardrail status** in the UI
4. **Collects user feedback** (ratings, comments) linked to traces
5. **Maintains session continuity** across interactions

### 🛠️ Technical Stack

- **Frontend**: Next.js 14+ with App Router
- **UI**: Tailwind CSS + shadcn/ui components  
- **Backend**: Next.js API Routes
- **Observability**: Langfuse Web SDK + Server SDK
- **State**: React Context or Zustand

### 📁 Project Structure

```
health_assistant_phase3/
├── web/                      # Next.js application
│   ├── app/                  # App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── api/
│   │       ├── chat/route.ts
│   │       ├── feedback/route.ts
│   │       └── sessions/route.ts
│   ├── components/
│   │   ├── chat/
│   │   ├── feedback/
│   │   └── ui/
│   ├── hooks/
│   └── lib/
├── src/                      # Existing Python backend
│   ├── assistants/
│   ├── evaluation/
│   └── utils/
└── tests/                    # Test suites
```

### 🔑 Key Integration Points

1. **PatientAssistant API**:
   ```python
   response = assistant.query(
       query="user question",
       session_id="session_123",
       user_id="user_456"
   )
   # Returns: content, citations, trace_id, tool_calls
   ```

2. **Langfuse Feedback**:
   ```typescript
   langfuse.score({
       traceId: response.traceId,
       name: 'user_feedback',
       value: rating,
       comment: userComment
   });
   ```

3. **Session Tracking**:
   - Session IDs persist across page refreshes
   - User IDs track anonymous users
   - All traces linked to sessions in Langfuse

### 📋 Development Checklist

#### Week 1: Setup & Backend
- [ ] Initialize Next.js 14 project
- [ ] Configure Tailwind CSS + shadcn/ui
- [ ] Create API routes for chat/feedback/sessions
- [ ] Integrate with PatientAssistant
- [ ] Set up Langfuse SDK

#### Week 2: Frontend Components
- [ ] Build ChatInterface component
- [ ] Create Message components with citations
- [ ] Add FeedbackButtons (thumbs/stars/comments)
- [ ] Implement SessionManager
- [ ] Add loading states and error handling

#### Week 3: Polish & Deploy
- [ ] Langfuse Web SDK integration
- [ ] Dark mode support
- [ ] Mobile responsiveness
- [ ] Accessibility (ARIA, keyboard nav)
- [ ] Testing (unit, integration, E2E)
- [ ] Deploy to Vercel/Netlify

### 🚦 Getting Started

1. **Install dependencies**:
   ```bash
   cd web
   npm install
   ```

2. **Set environment variables**:
   ```bash
   # .env.local
   ANTHROPIC_API_KEY=sk-ant-...
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY=pk-lf-...
   ```

3. **Run development server**:
   ```bash
   npm run dev
   # Visit http://localhost:3000
   ```

### 📝 Important Notes

- **No PHI**: This is a demo - no personal health information storage
- **Disclaimers**: Medical disclaimer must always be visible
- **Accessibility**: Target WCAG 2.1 AA compliance
- **Performance**: <3s initial load, <1s interaction response
- **Langfuse**: Use native features, avoid custom implementations

### 🔗 Resources

- [GitHub Issue #5](https://github.com/stewmckendry/health_assistant/issues/5)
- [Langfuse Web App Spec](../docs/langfuse-webApp-spec.md)
- [Langfuse Docs](https://langfuse.com/docs)
- [Next.js 14 Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)

### 💡 First Steps

1. Review the langfuse-webApp-spec.md for detailed requirements
2. Set up the Next.js project structure
3. Create the basic chat interface
4. Integrate with the Python backend via API routes
5. Add Langfuse tracking and feedback collection

Good luck with Phase 3! 🎉