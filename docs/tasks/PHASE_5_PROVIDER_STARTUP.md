# Phase 5: Provider Assistant Development

## 🚀 Ready to Start!

Your development environment is set up:
- **GitHub Issue**: #7 - Phase 5: Provider Assistant with Web App Mode Switching
- **Branch**: `phase-5-provider-assistant`
- **Worktree**: `../health_assistant_phase5_provider`

## 📍 Current State

### Completed Phases
- ✅ **Phase 1**: Basic Patient Assistant with guardrails
- ✅ **Phase 2**: Langfuse evaluation framework
- ✅ **Phase 3**: Next.js web application with chat interface

### What's Built
- `PatientAssistant` extends `BaseAssistant` with patient-specific prompts
- FastAPI backend at `/chat` endpoint (hardcoded to PatientAssistant)
- Next.js frontend with multi-turn conversation support
- Langfuse integration throughout the stack

## 🎯 Phase 5 Objectives

Build a Provider Assistant that:
1. **Extends BaseAssistant** with provider-specific system prompts
2. **Uses technical medical terminology** appropriate for healthcare professionals
3. **Accesses extended trusted domains** (medical journals, clinical databases)
4. **Integrates with existing Langfuse** infrastructure
5. **Enables mode switching** in the web application

## 📝 Implementation Plan

### 1. Backend - Create ProviderAssistant
```bash
cd ../health_assistant_phase5_provider
```

Create `src/assistants/provider.py`:
- Extend `BaseAssistant` (not PatientAssistant)
- Provider-specific system prompt focusing on evidence-based information
- Adjusted guardrail thresholds for medical terminology
- Same Langfuse @observe pattern as PatientAssistant

### 2. Configuration Updates
Update `src/config/prompts.yaml`:
- Add `provider_prompt` section with technical language
- Focus on evidence-based medicine, clinical guidelines
- Remove "not a doctor" disclaimers, add professional use disclaimers

Update `src/config/domains.yaml`:
- Add medical journal domains (pubmed.ncbi.nlm.nih.gov, nejm.org, jamanetwork.com)
- Clinical trial databases (clinicaltrials.gov)
- Professional resources (uptodate.com, dynamed.com)

### 3. API Updates
Modify `src/web/api/main.py`:
- Add `mode` parameter to ChatRequest model
- Implement assistant factory: `get_assistant(mode='patient'|'provider')`
- Track mode in session metadata
- Ensure Langfuse tags include mode

### 4. Frontend Mode Switching
Update web app components:
- Add toggle component in header
- Store mode preference in localStorage
- Include mode in API requests
- Display current mode indicator
- Show appropriate disclaimers per mode

### 5. Testing
Create comprehensive tests:
- Unit tests for ProviderAssistant
- Integration tests for mode switching
- Provider-specific test queries
- Langfuse tracking validation

## 🛠️ Key Files to Modify

### Backend
- [ ] Create: `src/assistants/provider.py`
- [ ] Update: `src/web/api/main.py` (add mode handling)
- [ ] Update: `src/config/prompts.yaml` (provider prompts)
- [ ] Update: `src/config/domains.yaml` (medical journals)

### Frontend
- [ ] Update: `web/app/api/chat/route.ts` (pass mode)
- [ ] Update: `web/app/page.tsx` (add mode toggle)
- [ ] Update: `web/types/chat.ts` (add mode type)
- [ ] Create: `web/components/ModeToggle.tsx`

### Tests
- [ ] Create: `tests/unit/test_provider_assistant.py`
- [ ] Create: `tests/integration/test_mode_switching.py`
- [ ] Update: `tests/e2e/test_web_app.py`

## 💡 Implementation Notes

### Provider System Prompt Guidelines
- Use medical terminology naturally
- Reference clinical guidelines and evidence levels
- Include statistical information when available
- Cite primary sources and medical journals
- Avoid oversimplification

### Guardrail Adjustments
- Allow diagnostic terminology in educational context
- Permit discussion of treatment options with evidence
- Enable medication information with proper citations
- Maintain prohibition on personal medical advice

### Langfuse Tracking
- Add `mode:provider` tag to traces
- Track provider-specific metrics (evidence quality, source credibility)
- Maintain session continuity across mode switches

## 🔄 Git Workflow

```bash
# Switch to worktree
cd ../health_assistant_phase5_provider

# Verify you're on the right branch
git branch --show-current  # Should show: phase-5-provider-assistant

# Make changes and commit
git add .
git commit -m "feat: implement ProviderAssistant with mode switching"

# Push to remote
git push -u origin phase-5-provider-assistant

# Create PR when ready
gh pr create
```

## ✅ Success Criteria

- [ ] ProviderAssistant class implemented and tested
- [ ] API supports mode parameter
- [ ] Frontend has working mode toggle
- [ ] Sessions maintain continuity across modes
- [ ] Langfuse properly tracks provider interactions
- [ ] All tests pass
- [ ] Documentation updated

## 🚦 Ready to Start!

Your next Claude Code session should:
1. Open the worktree: `cd ../health_assistant_phase5_provider`
2. Start with creating `src/assistants/provider.py`
3. Follow the implementation plan above
4. Test frequently with both unit and integration tests

Good luck with Phase 5! 🎉