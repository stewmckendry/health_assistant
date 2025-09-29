# Task 3: OpenAI Agent & Web Integration

## 🎯 Objective
Build the Dr. OFF agent using OpenAI Agents SDK and integrate it into the Health Assistant web application for clinician access.

## 📋 Checklist

### Agent Configuration
- [ ] Create `configs/agents/dr_off.yaml`:
  ```yaml
  name: Dr. OFF
  full_name: Ontario Finance & Formulary Assistant
  description: AI assistant for Ontario drug coverage, OHIP billing, and assistive device funding
  model: gpt-4o
  temperature: 0.1
  
  capabilities:
    - ODB formulary lookups
    - Drug interchangeability checks
    - OHIP fee schedule queries
    - ADP device coverage verification
  
  tools:
    - formulary_lookup
    - interchangeability_context
    - ohip_fee_lookup
    - coverage_rule_lookup
    - adp_device_lookup
    - adp_forms
  
  system_prompt: |
    You are Dr. OFF (Ontario Finance & Formulary), an AI assistant specializing in Ontario healthcare coverage.
    
    Your role:
    - Answer questions about ODB drug coverage
    - Identify interchangeable medications and lowest-cost options
    - Provide OHIP billing codes and fee information
    - Explain ADP device funding and eligibility
    
    Important guidelines:
    - ALWAYS cite specific pages/sections from official documents
    - Never provide medical advice or diagnosis
    - Focus on coverage and financial aspects only
    - Clearly state when information may be outdated
    - Direct users to official sources for final verification
  
  guardrails:
    - no_medical_diagnosis
    - require_citations
    - ontario_scope_only
  ```

### Agent Implementation
- [ ] Create `src/agents/clinical/dr_off/__init__.py`
- [ ] Create `src/agents/clinical/dr_off/agent.py`:
  ```python
  from openai import OpenAI
  from typing import Optional, Dict, Any
  import yaml
  
  class DrOFFAgent:
      def __init__(self):
          self.client = OpenAI()
          self.config = self._load_config()
          self.tools = self._register_tools()
          self.agent = self._create_agent()
      
      def _load_config(self):
          with open("configs/agents/dr_off.yaml") as f:
              return yaml.safe_load(f)
      
      def _register_tools(self):
          from .tools import TOOLS
          return TOOLS
      
      def _create_agent(self):
          # Create agent with OpenAI Agents SDK
          pass
      
      async def query(self, 
                     message: str, 
                     session_id: str,
                     context: Optional[Dict] = None) -> Dict[str, Any]:
          # Process query through agent
          # Apply guardrails
          # Format response with citations
          pass
  ```

### Prompts & Guardrails
- [ ] Create `src/agents/clinical/dr_off/prompts.py`:
  ```python
  QUERY_ENHANCEMENT_PROMPT = """
  Enhance this Ontario healthcare query for better results:
  - Identify if it's about drugs (ODB), billing (OHIP), or devices (ADP)
  - Extract key entities (DINs, drug names, fee codes, device types)
  - Clarify ambiguous terms
  Query: {query}
  """
  
  CITATION_PROMPT = """
  Format the response with proper citations:
  - Include document name and page/section
  - Use inline citations [1], [2], etc.
  - List full citations at end
  """
  
  GUARDRAIL_PROMPTS = {
      "no_diagnosis": "This appears to be seeking medical diagnosis. Redirect to coverage information only.",
      "out_of_scope": "This query is outside Ontario healthcare coverage. Focus on ODB/OHIP/ADP only.",
      "needs_verification": "Add disclaimer that information should be verified with official sources."
  }
  ```

### Web API Integration
- [ ] Create API route `web/app/api/agents/dr-off/route.ts`:
  ```typescript
  import { NextRequest, NextResponse } from 'next/server';
  
  export async function POST(req: NextRequest) {
    const { message, sessionId } = await req.json();
    
    try {
      // Call Python backend
      const response = await fetch(`${BACKEND_URL}/agents/dr-off`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
      });
      
      const data = await response.json();
      return NextResponse.json(data);
    } catch (error) {
      return NextResponse.json({ error }, { status: 500 });
    }
  }
  ```

### UI Components
- [ ] Create `web/app/components/agents/DrOffCard.tsx`:
  ```typescript
  export function DrOffCard() {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Dr. OFF</CardTitle>
          <CardDescription>
            Ontario Finance & Formulary Assistant
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul>
            <li>✓ ODB Drug Coverage</li>
            <li>✓ OHIP Billing Codes</li>
            <li>✓ ADP Device Funding</li>
            <li>✓ Interchangeable Medications</li>
          </ul>
        </CardContent>
      </Card>
    );
  }
  ```

- [ ] Add to agent selector in `web/app/components/agents/AgentSelector.tsx`:
  ```typescript
  const CLINICAL_AGENTS = [
    // ... existing agents
    {
      id: 'dr-off',
      name: 'Dr. OFF',
      description: 'Ontario Finance & Formulary',
      icon: '💊',
      endpoint: '/api/agents/dr-off'
    }
  ];
  ```

### Backend FastAPI Integration
- [ ] Add endpoint to `src/web/api/main.py`:
  ```python
  @app.post("/agents/dr-off")
  async def dr_off_query(request: AgentRequest):
      agent = DrOFFAgent()
      response = await agent.query(
          message=request.message,
          session_id=request.session_id
      )
      return response
  ```

### Session Management
- [ ] Implement session tracking:
  - Store conversation history
  - Track tool calls
  - Log citations used
  - Monitor response times
- [ ] Add to session logger configuration

### Testing
- [ ] Create `tests/integration/dr_off/test_agent_integration.py`:
  ```python
  def test_drug_coverage_query():
      agent = DrOFFAgent()
      response = agent.query("Is atorvastatin covered by ODB?")
      assert response.decision == "Yes"
      assert len(response.citations) > 0
  
  def test_ohip_billing_query():
      agent = DrOFFAgent()
      response = agent.query("What is the OHIP code for a consultation?")
      assert "A005" in response.key_data
  
  def test_adp_device_query():
      agent = DrOFFAgent()
      response = agent.query("Is a manual wheelchair covered by ADP?")
      assert response.key_data["funding_pct"] == 75
  ```

- [ ] Create E2E test through web UI
- [ ] Test agent selection and switching
- [ ] Validate response formatting

### Documentation
- [ ] Document agent capabilities in `docs/agents/dr_off/README.md`
- [ ] Add example queries and responses
- [ ] Document tool usage patterns
- [ ] Create troubleshooting guide

## 📁 Deliverables

1. **Configuration**:
   - `configs/agents/dr_off.yaml`

2. **Agent Implementation**:
   - `src/agents/clinical/dr_off/__init__.py`
   - `src/agents/clinical/dr_off/agent.py`
   - `src/agents/clinical/dr_off/prompts.py`

3. **Web Integration**:
   - `web/app/api/agents/dr-off/route.ts`
   - `web/app/components/agents/DrOffCard.tsx`
   - Updates to `AgentSelector.tsx`

4. **Backend API**:
   - Updates to `src/web/api/main.py`

5. **Tests**:
   - `tests/integration/dr_off/test_agent_integration.py`

## 🔗 Dependencies
- **Input from Session 2**: MCP tools to register
- **Input from Session 1**: Database for queries
- **Output to Web App**: Working agent endpoint

## 💡 Tips
- Keep temperature low (0.1) for factual accuracy
- Use structured output mode for consistent responses
- Implement request caching for common queries
- Add request rate limiting
- Monitor token usage for cost control