# AI Health Assistant - Project Plan

## Executive Summary
A comprehensive AI-powered health assistant system designed to provide personalized medical education and information to both patients and physicians, with strict guardrails to ensure responses are grounded in trusted knowledge bases while explicitly avoiding medical diagnosis.

## Project Objectives

### Primary Goals
1. Deliver accurate, trustworthy medical information from validated sources
2. Provide personalized health education tailored to user context
3. Support physicians with evidence-based information and decision support
4. Maintain strict ethical boundaries (no diagnosis, only education/information)
5. Ensure transparency through comprehensive evaluation and testing

### Success Metrics
- Accuracy: >95% factually correct responses (validated against medical literature)
- User satisfaction: >4.5/5 rating on usefulness
- Safety: 100% compliance with no-diagnosis guardrails
- Response quality: Appropriate tone for target audience (patient vs physician)
- Source reliability: 100% responses cite trusted medical sources

## User Journeys

### Patient Journey
1. **Discovery**: Patient seeks health information about symptoms/conditions
2. **Query**: Submits natural language question through web interface
3. **Processing**: System validates query, fetches trusted sources
4. **Response**: Receives educational content with clear disclaimers
5. **Follow-up**: Can ask clarifying questions or explore related topics
6. **Action**: Encouraged to consult healthcare provider for diagnosis/treatment

### Physician Journey
1. **Access**: Physician accesses system (demo mode, no auth)
2. **Mode Selection**: Chooses physician mode for technical responses
3. **Query**: Asks clinical questions or requests evidence summaries
4. **Response**: Receives detailed, evidence-based information with citations
5. **Decision Support**: For complex cases, accesses orchestrated multi-agent system
6. **Documentation**: Exports findings for patient records/further review

## Core Features

### Phase 1: Basic Patient Assistant ✅ COMPLETE
- ✅ Natural language query processing
- ✅ System prompt for medical education focus
- ✅ Integration with Anthropic web_search and web_fetch tools
- ✅ Three-layer guardrail system (LLM, regex, hybrid modes)
- ✅ Citation of sources with deduplication
- ✅ Comprehensive session logging with viewer utility
- ✅ Test-driven development (72 tests passing)
- ✅ Emergency and mental health crisis detection
- ✅ 97 trusted medical domains
- ✅ Complete API documentation

### Phase 2: Evaluation Framework ✅ COMPLETE
- ✅ Integration with Langfuse evaluation platform (SDK v3)
- ✅ LLM-as-judge evaluation criteria (6 metrics):
  - ✅ Safety Compliance (30% weight, 0.99 threshold)
  - ✅ Medical Accuracy (25% weight, 0.90 threshold)
  - ✅ Citation Quality (20% weight, 0.80 threshold)
  - ✅ Response Helpfulness (15% weight, 0.70 threshold)
  - ✅ Emergency Handling (5% weight, 0.99 threshold)
  - ✅ Disclaimer Presence (5% weight, 0.95 threshold)
- ✅ Granular observation tracking (LLM calls, tool usage)
- ✅ Session and user tracking for multi-turn conversations
- ✅ 91 test cases in evaluation dataset
- ✅ Helper functions for trace/session/user analysis
- ✅ Batch prompt testing via DatasetEvaluator
- ✅ Performance metrics dashboard in Langfuse UI
- ✅ Test validation suite with comprehensive metrics

### Phase 3: Web Application ✅ COMPLETE
- ✅ Next.js 14 with TypeScript and App Router
- ✅ Responsive design with shadcn/ui components
- ✅ No authentication (demo mode)
- ✅ Multi-turn conversation support with Anthropic native features
- ✅ Session persistence (24-hour localStorage)
- ✅ User ID persistence across sessions
- ✅ Feedback collection with Langfuse integration
- ✅ Real-time chat interface with markdown support
- ✅ Citation display with deduplication
- ✅ Guardrail status indicators
- ✅ Langfuse observability (single trace per turn)
- ✅ Comprehensive API endpoints (chat, feedback, sessions)
- ✅ Error handling and loading states

### Phase 4: Cloud Deployment ✅ COMPLETE
- ✅ **Frontend (Vercel)**:
  - ✅ Deployed Next.js app
  - ✅ Environment variable for backend URL configured
  - ✅ GitHub integration for auto-deploy
- ✅ **Backend (Railway)**:
  - ✅ Deployed FastAPI Python app at healthassistant-production-3613.up.railway.app
  - ✅ Environment variables (API keys) configured
  - ✅ Public URL for frontend connection established
- ✅ **Minimal Changes**:
  - ✅ Kept in-memory session storage
  - ✅ Using existing Langfuse cloud
  - ✅ No additional infrastructure needed

### Phase 5: Performance Optimization ✅ COMPLETE
- ✅ **Streaming Responses**:
  - ✅ Server-Sent Events (SSE) implementation
  - ✅ StreamingMixin for assistant classes
  - ✅ <1 second time to first token
  - ✅ Progressive text rendering in UI
- ✅ **Session Settings System**:
  - ✅ Per-session configuration storage
  - ✅ Settings API endpoints
  - ✅ Comprehensive settings UI panel
  - ✅ Guardrails toggle (input/output)
  - ✅ Domain management (block/add)
  - ✅ Model and parameter configuration
- ✅ **Performance Metrics**:
  - ✅ Time to first token tracking
  - ✅ API duration monitoring
  - ✅ Langfuse performance observations
  - ✅ Streaming vs non-streaming comparison
- ✅ **Guardrails Optimization**:
  - ✅ Input guardrails: ON by default
  - ✅ Output guardrails: OFF by default for streaming
  - ✅ Automatic fallback to non-streaming when output guardrails enabled
  - ✅ Strengthened system prompts to reduce need for output checks

### Phase 6: Provider Assistant ✅ COMPLETE
- ✅ Technical language adaptation for healthcare professionals
- ✅ Extended source access configuration (169 trusted domains)
- ✅ Relaxed guardrails for professional medical context
- ✅ Mode switching capability in web application
- ✅ Specialized test suite for provider queries
- ✅ Enhanced markdown formatting for clinical communication
- ✅ Langfuse observability with mode-specific tagging
- ✅ Professional system prompts with clinical standards

### Phase 7: Medical Decision Support (MAI-DxO Pattern)
- Orchestrator agent architecture using OpenAI Agents Python SDK
- Specialized sub-agents:
  - Best Evidence Agent
  - Clinical Guidelines Agent
  - Drug Interaction Agent
  - Social Determinants Agent
  - Specialty-specific Agents
- Consensus building mechanism
- Disagreement reporting
- Audit trail generation via logging

### Phase 8: Configuration System
- **Configurable AI Models**:
  - Model selection (Anthropic, OpenAI, Gemini)
  - Model parameters (temperature, max tokens)
- **Configurable Trusted Sources**:
  - Domain whitelist management
  - Organization-specific source lists
  - Source priority/weighting
- **Configurable Response Parameters**:
  - Disclaimer templates
  - Response length limits
  - Technical level adjustment
- Configuration via JSON/YAML files
- Runtime configuration switching

## Technical Specification

### Technology Stack

#### Backend
- **Language**: Python 3.11+
- **Frameworks**: 
  - FastAPI (API server)
  - OpenAI Agents SDK (Phase 6 orchestration)
  - Anthropic SDK
  - ref-tools SDK (documentation retrieval)
  - Exa SDK (web search)
- **Testing**: pytest, unittest (TDD approach)
- **Evaluation**: Langfuse SDK
- **Logging**: Python logging module with file handlers
- **Configuration**: python-dotenv, pydantic settings

#### Frontend (Phase 3+)
- **Framework**: React/Next.js
- **UI Library**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand or Context API

#### Infrastructure
- **Environment**: Local development / Demo deployment
- **Database**: SQLite for session/user data (demo)
- **Caching**: In-memory caching for responses
- **Logs**: Rotating file logs with timestamps

### API Design
```
POST /api/chat
  - Model selection
  - User type (patient/physician)
  - Query text
  - Session ID
  - Config override (optional)

GET /api/config
  - Returns current configuration
  - Includes allowed domains list

POST /api/config
  - Update configuration at runtime

POST /api/evaluate
  - Submit responses for evaluation

GET /api/metrics
  - Retrieve evaluation metrics
```

### Development Principles
- **Test-Driven Development**: Write tests first, then implementation
- **Comprehensive Logging**: All requests, responses, and decisions logged
- **Configuration First**: Make everything configurable
- **SDK Priority**: Use existing SDKs (ref-tools, Exa) before custom solutions

## Implementation Phases

### Phase 1: Basic Patient Assistant ✅ COMPLETE
**Test-Driven Development Approach**

**Completed Tasks:**
- [x] Write test suite for basic assistant functionality (72 tests)
- [x] Set up environment with API keys
- [x] Integrate Anthropic web_search and web_fetch tools
- [x] Define comprehensive system prompts
- [x] Implement Anthropic API wrapper with logging
- [x] Build three-layer guardrail system (LLM + regex + hybrid)
- [x] Add emergency and crisis detection
- [x] Implement session-based logging
- [x] Create citation deduplication
- [x] Build CLI testing interface
- [x] Write comprehensive documentation
- [ ] Create disclaimer templates
- [ ] Set up file-based logging system
- [ ] Run tests to validate implementation
- [ ] Document API usage and configuration

### Phase 2: Evaluation Framework ✅ COMPLETE (Weeks 3-4)
**Successfully Built on Phase 1 Foundation:**
- ✅ Extended LLMGuardrails for evaluation scoring
- ✅ Leveraged SessionLogger for evaluation data collection
- ✅ Used existing test suite (72 tests) as baseline

**Completed Tasks:**
- [x] Write test suite for evaluation framework
- [x] Set up Langfuse account and SDK (v3)
- [x] Define evaluation criteria and rubrics:
  - [x] Extend LLMGuardrails prompts for scoring (6 metrics)
  - [x] Reuse guardrail detection logic for safety metrics
  - [x] Build on citation tracking for source quality
- [x] Create prompt test dataset (91 queries):
  - [x] Include Phase 1 test cases as foundation
  - [x] Add adversarial and edge cases
- [x] Implement LLM-as-judge evaluation:
  - [x] Integrate with existing SessionLogger
  - [x] Reuse LLM guardrail infrastructure
  - [x] Track all evaluations in session logs
- [x] Native Langfuse dashboard for annotation/review
- [x] Generate evaluation reports from Langfuse traces
- [x] Validate evaluation accuracy with comprehensive tests
- [x] System achieves all success metrics (>99% safety, >90% accuracy)

### Phase 3: Web Application ✅ COMPLETE (Weeks 5-7)
**Successfully Built on Phase 1-2 Foundation:**
- ✅ Direct integration with PatientAssistant class
- ✅ Session tracking matches Langfuse sessions
- ✅ Citations displayed from web_search/web_fetch
- ✅ Guardrail status shown in responses

**Completed Tasks:**
- [x] Write integration tests for web app
- [x] Design UI/UX mockups:
  - [x] Include guardrail status indicators
  - [x] Show citation sources inline
  - [x] Display emergency/crisis redirects
- [x] Set up Next.js 14 project with TypeScript
- [x] Implement chat interface:
  - [x] Direct integration with PatientAssistant
  - [x] Real-time session tracking
  - [x] Display tool usage (web_search/web_fetch)
- [x] Add session management (no auth):
  - [x] Use existing session_id infrastructure
  - [x] LocalStorage persistence (24 hours)
  - [x] User ID tracking across sessions
- [x] Implement multi-turn conversations:
  - [x] Native Anthropic message history
  - [x] Context preservation across turns
  - [x] Single trace per turn in Langfuse
- [x] Create landing page with disclaimers:
  - [x] Use existing disclaimer templates
  - [x] Include emergency resources
- [x] Implement feedback system:
  - [x] Thumbs up/down quick feedback
  - [x] 5-star rating with comments
  - [x] Direct Langfuse score attachment
- [x] Run end-to-end tests
- [x] Deploy locally for demo (ports 3000/8000)

### Phase 4: Cloud Deployment ✅ COMPLETE (Week 8)
**Successfully Deployed to Production:**
- ✅ App accessible to external testers
- ✅ Minimal infrastructure changes
- ✅ All existing functionality intact

**Completed Tasks:**
- [x] Frontend (Vercel):
  - [x] Created Vercel project as "health-assistant"
  - [x] Added NEXT_PUBLIC_BACKEND_URL environment variable
  - [x] Connected GitHub repository for auto-deploy
  - [x] Deployed and tested frontend
- [x] Backend (Railway):
  - [x] Created Railway project
  - [x] Added environment variables (ANTHROPIC_API_KEY, LANGFUSE keys)
  - [x] Deployed FastAPI app
  - [x] Public URL: healthassistant-production-3613.up.railway.app
- [x] Integration:
  - [x] Updated frontend to use Railway backend URL
  - [x] Tested end-to-end functionality
  - [x] Updated CORS settings for production domains
- [x] Documentation:
  - [x] Created .env.example files
  - [x] Fixed TypeScript build issues
  - [x] Added vercel.json configuration

### Phase 6: Provider Assistant ✅ COMPLETE (Week 9)
**Successfully Built on Phase 1-3 Foundation:**
- ✅ Created ProviderAssistant extending BaseAssistant
- ✅ Reused guardrail infrastructure with relaxed provider rules
- ✅ Leveraged existing web_search/web_fetch tools
- ✅ Extended session logging for provider context
- ✅ Integrated with web app for seamless mode switching

**Completed Tasks:**
- [x] Write provider-specific test cases
- [x] Create ProviderAssistant class:
  - [x] Inherit from BaseAssistant (src/assistants/provider.py)
  - [x] Adapt guardrail thresholds for clinical use
  - [x] Allow technical/medical terminology
- [x] Adapt system prompts for healthcare providers:
  - [x] Create provider-specific prompts in prompts.yaml
  - [x] Adjust disclaimer language for professional use
  - [x] Enable evidence-based information retrieval
- [x] Configure extended source access:
  - [x] Add 76 additional medical domains (total 169)
  - [x] Include medical journals (NEJM, JAMA, Lancet, BMJ)
  - [x] Enable clinical databases (UpToDate, DynaMed, ClinicalKey)
  - [x] Add drug information resources (Lexicomp, Micromedex)
- [x] Implement mode switching in web app:
  - [x] Add provider/patient toggle in UI (ModeToggle component)
  - [x] Update API to handle mode parameter
  - [x] Maintain session continuity across modes
  - [x] Persistent mode selection in localStorage
- [x] Add provider-specific logging:
  - [x] Track evidence quality with extended domains
  - [x] Log source credibility with domain categorization
- [x] Integrate with Langfuse infrastructure:
  - [x] Use same trace/session/user patterns
  - [x] Add mode-specific tags (mode:provider, provider_assistant)
  - [x] Fixed tag consolidation issue for proper observability
- [x] Enhanced markdown formatting:
  - [x] Professional formatting guidelines in system prompts
  - [x] Clinical communication standards
  - [x] Improved ReactMarkdown styling for provider responses
- [x] Run evaluation on provider responses
- [x] Validate against healthcare provider requirements
- [x] Document professional use guidelines (docs/provider_assistant.md)

### Phase 7: Medical Decision Support (Weeks 10-12)
**Build on Phase 1-5 Foundation:**
- Orchestrate multiple assistant instances
- Aggregate session logs for consensus building
- Use LLMGuardrails for agent output validation
- Leverage all previous phases' infrastructure

**ToDos:**
- [ ] Write tests for orchestrator patterns
- [ ] Research OpenAI Agents SDK patterns
- [ ] Design orchestrator architecture:
  - [ ] Base on existing assistant classes
  - [ ] Reuse session logging for audit trail
  - [ ] Apply guardrails to each agent
- [ ] Implement base orchestrator:
  - [ ] Instantiate multiple assistants
  - [ ] Coordinate web_search/web_fetch usage
  - [ ] Aggregate citations across agents
- [ ] Create specialized agent templates:
  - [ ] Evidence Agent (extends PhysicianAssistant)
  - [ ] Guidelines Agent (uses trusted domains)
  - [ ] Drug Interaction Agent (specific prompts)
  - [ ] Social Determinants Agent
- [ ] Build consensus mechanism:
  - [ ] Use LLMGuardrails for validation
  - [ ] Track agreement in session logs
  - [ ] Weight by source quality
- [ ] Implement disagreement detection:
  - [ ] Log conflicting recommendations
  - [ ] Flag for human review
- [ ] Create comprehensive audit trail:
  - [ ] Extend SessionLogger for multi-agent
  - [ ] Track decision rationale
- [ ] Test with NEJM-CPC cases
- [ ] Validate orchestration effectiveness
- [ ] Document clinical decision support workflow

## Testing Strategy

### Test Categories
1. **Unit Tests**: Individual components
2. **Integration Tests**: SDK integrations
3. **End-to-End Tests**: Full workflow validation
4. **Performance Tests**: Response time, throughput
5. **Safety Tests**: Guardrail effectiveness

### Test Data
- Medical query dataset
- Edge cases (emergency, mental health)
- Adversarial prompts
- Multi-turn conversations

### Success Criteria per Phase
- Phase 1: 100% test pass rate
- Phase 2: Evaluation accuracy >90%
- Phase 3: E2E tests passing
- Phase 4: Configuration switches work
- Phase 5: Physician tests passing
- Phase 6: Orchestration tests passing

## Logging Strategy

### Log Categories
- **Request Logs**: All incoming queries
- **API Logs**: External API calls and responses
- **Decision Logs**: Guardrail triggers, source selection
- **Error Logs**: Exceptions and failures
- **Evaluation Logs**: Test results and metrics
- **Audit Logs**: Configuration changes

### Log Format
```python
{
    "timestamp": "ISO-8601",
    "level": "INFO/WARNING/ERROR",
    "component": "assistant/evaluation/web",
    "session_id": "uuid",
    "message": "description",
    "data": {}
}
```

## Configuration Management

### Configuration Structure
```yaml
models:
  primary: "claude-3-opus"
  fallback: "gpt-4"
  parameters:
    temperature: 0.7
    max_tokens: 2000

sources:
  trusted_domains:
    medical:
      - "pubmed.ncbi.nlm.nih.gov"
      - "mayoclinic.org"
      - "cdc.gov"
    organization_specific:
      - "internal.hospital.org"
  
response:
  disclaimer_template: "templates/disclaimer.txt"
  max_length: 1500
  include_citations: true

logging:
  level: "INFO"
  file: "logs/health_assistant.log"
  rotation: "daily"
```

## Risk Mitigation

### Medical/Legal Risks
- Clear disclaimers about non-diagnostic nature
- Comprehensive logging for audit trails
- Configurable guardrails per organization

### Technical Risks
- API rate limiting with exponential backoff
- Fallback models in configuration
- Comprehensive error logging
- SDK-first approach for reliability

### User Safety
- Explicit emergency redirection (call 911)
- Mental health crisis resources
- Harmful content detection with logging

## Timeline
- **Total Duration**: 12 weeks
- **MVP (Phase 1-2)**: 4 weeks
- **User-Ready (Phase 3)**: 7 weeks
- **Full System (Phase 6)**: 12 weeks

## Resources Required
- API keys (stored in ~/thunder_playbook/.env)
- Cloud infrastructure (demo deployment)
- Evaluation platform subscription
- Medical expert reviewers (2-3 hours/week)
- UI/UX designer (Phase 3)