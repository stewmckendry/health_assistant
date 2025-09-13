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

### Phase 2: Evaluation Framework
- Integration with Langfuse or similar evaluation platform
- LLM-as-judge evaluation criteria:
  - Medical accuracy
  - Appropriateness of response
  - Tone and clarity
  - Guardrail compliance
- Human review annotation system
- Batch prompt testing
- Performance metrics dashboard
- Test validation suite

### Phase 3: Web Application
- Responsive, accessible design
- No authentication (demo mode)
- Session history
- Feedback collection
- Terms of service and disclaimers
- Export/share functionality
- Comprehensive logging

### Phase 4: Configuration System
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

### Phase 5: Physician Mode
- Technical language adaptation
- Extended source access configuration
- Differential diagnosis support (information only)
- Clinical guideline integration
- Mode switching capability
- Specialized test suite for physician queries

### Phase 6: Medical Decision Support (MAI-DxO Pattern)
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

### Phase 2: Evaluation Framework (Weeks 3-4)
**Build on Phase 1 Foundation:**
- Extend existing LLMGuardrails for evaluation scoring
- Leverage SessionLogger for evaluation data collection
- Use existing test suite (72 tests) as baseline

**ToDos:**
- [ ] Write test suite for evaluation framework
- [ ] Set up Langfuse account and SDK
- [ ] Define evaluation criteria and rubrics:
  - [ ] Extend LLMGuardrails prompts for scoring
  - [ ] Reuse guardrail detection logic for safety metrics
  - [ ] Build on citation tracking for source quality
- [ ] Create prompt test dataset (50-100 queries)
  - [ ] Include Phase 1 test cases as foundation
  - [ ] Add adversarial and edge cases
- [ ] Implement LLM-as-judge evaluation:
  - [ ] Integrate with existing SessionLogger
  - [ ] Reuse LLM guardrail infrastructure
  - [ ] Track all evaluations in session logs
- [ ] Build human annotation interface
- [ ] Generate evaluation reports from session logs
- [ ] Validate evaluation accuracy with tests
- [ ] Fine-tune system based on results

### Phase 3: Web Application (Weeks 5-7)
**Build on Phase 1 Foundation:**
- Integrate with existing PatientAssistant class
- Stream session logs to web interface
- Display citations from Phase 1 implementation
- Show guardrail status in UI

**ToDos:**
- [ ] Write integration tests for web app
- [ ] Design UI/UX mockups:
  - [ ] Include guardrail status indicators
  - [ ] Show citation sources inline
  - [ ] Display emergency/crisis redirects
- [ ] Set up Next.js project
- [ ] Implement chat interface:
  - [ ] Direct integration with PatientAssistant
  - [ ] Real-time SessionLogger integration
  - [ ] Display tool usage (web_search/web_fetch)
- [ ] Add session management (no auth):
  - [ ] Use existing session_id infrastructure
  - [ ] Browse historical sessions from logs
- [ ] Create landing page with disclaimers:
  - [ ] Use existing disclaimer templates
  - [ ] Include emergency resources
- [ ] Implement feedback system
- [ ] Run end-to-end tests
- [ ] Deploy to demo environment

### Phase 4: Configuration System (Week 8)
**Build on Phase 1 Foundation:**
- Extend existing YAML configuration files
- Enhance AssistantConfig dataclass
- Build on 97 trusted domains list
- Extend guardrail mode configuration

**ToDos:**
- [ ] Write tests for configuration management
- [ ] Design configuration schema:
  - [ ] Extend existing prompts.yaml structure
  - [ ] Build on domains.yaml (97 domains)
  - [ ] Enhance guardrail_prompts.yaml
- [ ] Implement model configuration interface:
  - [ ] Extend AssistantConfig class
  - [ ] Add model fallback logic
  - [ ] Support temperature/token overrides
- [ ] Create trusted sources configuration:
  - [ ] Build UI for domains.yaml management
  - [ ] Organization-specific domain lists
  - [ ] Source priority/weighting system
- [ ] Build response parameter configuration:
  - [ ] Extend disclaimer templates
  - [ ] Configure guardrail sensitivity
  - [ ] Adjust citation formatting
- [ ] Implement runtime configuration API
- [ ] Create configuration validation
- [ ] Test configuration switching
- [ ] Document configuration options

### Phase 5: Physician Mode (Week 9)
**Build on Phase 1 Foundation:**
- Create PhysicianAssistant extending PatientAssistant
- Reuse guardrail infrastructure with physician-specific rules
- Leverage existing web_search/web_fetch tools
- Extend session logging for physician context

**ToDos:**
- [ ] Write physician-specific test cases
- [ ] Create PhysicianAssistant class:
  - [ ] Inherit from BaseAssistant
  - [ ] Adapt guardrail thresholds
  - [ ] Allow technical terminology
- [ ] Adapt system prompts for medical professionals:
  - [ ] Extend prompts.yaml with physician mode
  - [ ] Adjust disclaimer language
  - [ ] Enable differential information
- [ ] Configure extended source access:
  - [ ] Add medical journal domains
  - [ ] Include clinical trial databases
  - [ ] Enable UpToDate/DynaMed access
- [ ] Implement mode switching logic:
  - [ ] Reuse guardrail_mode pattern
  - [ ] Add physician verification stub
- [ ] Add physician-specific logging:
  - [ ] Track clinical reasoning steps
  - [ ] Log evidence quality scores
- [ ] Run evaluation on physician responses
- [ ] Validate against physician requirements
- [ ] Document clinical use guidelines

### Phase 6: Medical Decision Support (Weeks 10-12)
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