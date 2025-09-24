# Task 4: Evaluation & Testing Framework

## 🎯 Objective
Create comprehensive evaluation suite for Dr. OFF using existing Langfuse integration, build golden test sets, and implement E2E testing.

## 📋 Checklist

### Langfuse Integration
- [ ] Review existing Langfuse setup in codebase
- [ ] Create Dr. OFF specific traces:
  ```python
  from langfuse import Langfuse
  
  class DrOFFTracer:
      def __init__(self):
          self.langfuse = Langfuse()
      
      def trace_query(self, 
                     query: str, 
                     query_type: str,
                     tools_called: list,
                     response: dict,
                     latency_ms: float):
          trace = self.langfuse.trace(
              name="dr_off_query",
              input={"query": query, "type": query_type},
              output=response,
              metadata={
                  "tools_called": tools_called,
                  "latency_ms": latency_ms,
                  "citations_count": len(response.get("citations", []))
              }
          )
          return trace
  ```

### Golden Test Dataset
- [ ] Create `data/evaluation/dr_off_golden_set.json`:
  ```json
  {
    "test_cases": {
      "odb_coverage": [
        {
          "id": "odb_001",
          "query": "Is atorvastatin 20mg covered by ODB?",
          "expected": {
            "decision": "Yes",
            "din": "02247521",
            "covered": true,
            "interchangeable_count": 8,
            "has_lowest_cost_option": true
          },
          "langfuse_tags": ["drug_coverage", "interchangeability"]
        },
        {
          "id": "odb_002", 
          "query": "What is the lowest cost alternative to Lipitor 20mg?",
          "expected": {
            "has_alternatives": true,
            "lowest_cost_brand": "Apo-Atorvastatin",
            "savings_potential": true
          },
          "langfuse_tags": ["cost_optimization", "generic_substitution"]
        }
        // ... 18 more ODB test cases
      ],
      "ohip_billing": [
        {
          "id": "ohip_001",
          "query": "What is the OHIP billing code for a general consultation?",
          "expected": {
            "codes": ["A005"],
            "has_fee_amount": true,
            "specialty_specific": false
          },
          "langfuse_tags": ["billing_code", "consultation"]
        },
        {
          "id": "ohip_002",
          "query": "Can I bill OHIP for telephone consultation?",
          "expected": {
            "decision": "Conditional",
            "has_specific_codes": true,
            "requires_context": true
          },
          "langfuse_tags": ["virtual_care", "billing_eligibility"]
        }
        // ... 18 more OHIP test cases
      ],
      "adp_devices": [
        {
          "id": "adp_001",
          "query": "Is a manual wheelchair covered by ADP?",
          "expected": {
            "decision": "Yes",
            "funding_percentage": 75,
            "has_eligibility_criteria": true,
            "requires_authorization": true
          },
          "langfuse_tags": ["mobility_device", "funding"]
        }
        // ... 4 more ADP test cases
      ]
    }
  }
  ```

### Langfuse Evaluation Scores
- [ ] Define custom scoring functions:
  ```python
  # src/agents/clinical/dr_off/evaluation/scores.py
  
  def score_coverage_decision(trace_id: str, expected: dict, actual: dict) -> float:
      """Score accuracy of coverage decision (Yes/No/Conditional)"""
      score = 1.0 if actual.get("decision") == expected.get("decision") else 0.0
      
      langfuse.score(
          trace_id=trace_id,
          name="coverage_decision_accuracy",
          value=score
      )
      return score
  
  def score_citation_quality(trace_id: str, response: dict) -> float:
      """Score presence and quality of citations"""
      citations = response.get("citations", [])
      
      # Check for citations
      has_citations = len(citations) > 0
      # Check for page numbers
      has_page_nums = any(c.get("page") for c in citations)
      # Check for official sources
      has_official_source = any(
          c.get("source") in ["ODB Formulary", "OHIP Schedule", "ADP Manual"] 
          for c in citations
      )
      
      score = (has_citations * 0.4 + has_page_nums * 0.3 + has_official_source * 0.3)
      
      langfuse.score(
          trace_id=trace_id,
          name="citation_quality",
          value=score
      )
      return score
  
  def score_response_completeness(trace_id: str, expected: dict, actual: dict) -> float:
      """Score if response contains all expected elements"""
      required_fields = expected.keys()
      present_fields = sum(1 for f in required_fields if f in actual and actual[f])
      score = present_fields / len(required_fields) if required_fields else 0
      
      langfuse.score(
          trace_id=trace_id,
          name="response_completeness",
          value=score
      )
      return score
  ```

### Automated Test Runner
- [ ] Create test execution framework:
  ```python
  # src/agents/clinical/dr_off/evaluation/runner.py
  
  class DrOFFTestRunner:
      def __init__(self, agent: DrOFFAgent):
          self.agent = agent
          self.langfuse = Langfuse()
          self.results = []
      
      async def run_golden_tests(self):
          with open("data/evaluation/dr_off_golden_set.json") as f:
              test_cases = json.load(f)
          
          for category, cases in test_cases["test_cases"].items():
              for test_case in cases:
                  result = await self._run_single_test(test_case, category)
                  self.results.append(result)
          
          return self._generate_report()
      
      async def _run_single_test(self, test_case: dict, category: str):
          # Create Langfuse trace
          trace = self.langfuse.trace(
              name=f"golden_test_{test_case['id']}",
              tags=test_case['langfuse_tags'] + [category, "golden_test"]
          )
          
          # Run query
          response = await self.agent.query(
              test_case["query"],
              session_id=f"test_{test_case['id']}"
          )
          
          # Score response
          scores = {
              "decision": score_coverage_decision(trace.id, test_case["expected"], response),
              "citations": score_citation_quality(trace.id, response),
              "completeness": score_response_completeness(trace.id, test_case["expected"], response)
          }
          
          return {
              "test_id": test_case["id"],
              "category": category,
              "passed": all(s >= 0.8 for s in scores.values()),
              "scores": scores,
              "trace_id": trace.id
          }
  ```

### Integration Tests
- [ ] Create `tests/integration/dr_off/test_dr_off_integration.py`:
  ```python
  import pytest
  from src.agents.clinical.dr_off import DrOFFAgent
  
  @pytest.fixture
  async def agent():
      return DrOFFAgent()
  
  @pytest.mark.asyncio
  async def test_odb_interchangeability(agent):
      """Test drug interchangeability lookup"""
      response = await agent.query("What drugs are interchangeable with Lipitor?")
      
      assert response["decision"] in ["Yes", "Conditional"]
      assert "citations" in response
      assert len(response.get("options", [])) > 0
  
  @pytest.mark.asyncio
  async def test_ohip_fee_lookup(agent):
      """Test OHIP fee code retrieval"""
      response = await agent.query("What is the OHIP code for A005?")
      
      assert "key_data" in response
      assert "amount" in response["key_data"]
      assert response["key_data"]["code"] == "A005"
  
  @pytest.mark.asyncio
  async def test_adp_eligibility(agent):
      """Test ADP device eligibility check"""
      response = await agent.query("Who is eligible for ADP wheelchair funding?")
      
      assert "eligibility" in response["key_data"]
      assert response["citations"]
  ```

### E2E Web Tests
- [ ] Create `tests/e2e/dr_off/test_web_interface.py`:
  ```python
  from playwright.sync_api import Page, expect
  
  def test_dr_off_agent_selection(page: Page):
      """Test selecting Dr. OFF from agent dropdown"""
      page.goto("/clinical-agents")
      
      # Select Dr. OFF
      page.click("[data-testid='agent-selector']")
      page.click("text=Dr. OFF")
      
      # Verify agent loaded
      expect(page.locator("[data-testid='agent-name']")).to_have_text("Dr. OFF")
  
  def test_dr_off_query_flow(page: Page):
      """Test complete query flow through web UI"""
      page.goto("/clinical-agents")
      
      # Select agent and submit query
      page.click("[data-testid='agent-selector']")
      page.click("text=Dr. OFF")
      page.fill("[data-testid='query-input']", "Is metformin covered by ODB?")
      page.click("[data-testid='submit-query']")
      
      # Wait for response
      response = page.locator("[data-testid='agent-response']")
      expect(response).to_contain_text("covered")
      expect(response).to_contain_text("ODB")
  
  def test_citation_display(page: Page):
      """Test that citations are properly displayed"""
      # ... test citation rendering in UI
  ```

### Performance Benchmarks
- [ ] Create performance test suite:
  ```python
  # tests/performance/dr_off/test_latency.py
  
  async def test_response_latency():
      """Ensure p95 < 1.5s, p50 < 0.8s"""
      agent = DrOFFAgent()
      latencies = []
      
      test_queries = [
          "Is atorvastatin covered?",
          "OHIP code for consultation",
          "ADP wheelchair coverage"
      ]
      
      for _ in range(100):
          for query in test_queries:
              start = time.time()
              await agent.query(query, session_id="perf_test")
              latencies.append(time.time() - start)
      
      p50 = np.percentile(latencies, 50)
      p95 = np.percentile(latencies, 95)
      
      assert p50 < 0.8, f"p50 latency {p50}s exceeds 0.8s target"
      assert p95 < 1.5, f"p95 latency {p95}s exceeds 1.5s target"
  ```

### Monitoring Dashboard
- [ ] Set up Langfuse dashboard views:
  - Average accuracy by category (ODB/OHIP/ADP)
  - Citation quality scores over time
  - Response latency trends
  - Tool call patterns
  - Error rate monitoring

### CI/CD Integration
- [ ] Add to GitHub Actions:
  ```yaml
  # .github/workflows/dr_off_tests.yml
  name: Dr. OFF Tests
  
  on:
    push:
      paths:
        - 'src/agents/clinical/dr_off/**'
        - 'tests/**/dr_off/**'
  
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v2
        - name: Run Dr. OFF Tests
          run: |
            pytest tests/unit/agents/dr_off/
            pytest tests/integration/dr_off/
        - name: Run Golden Test Suite
          run: |
            python -m src.agents.clinical.dr_off.evaluation.runner
  ```

## 📁 Deliverables

1. **Evaluation Framework**:
   - `src/agents/clinical/dr_off/evaluation/scores.py`
   - `src/agents/clinical/dr_off/evaluation/runner.py`
   - `data/evaluation/dr_off_golden_set.json`

2. **Tests**:
   - `tests/integration/dr_off/test_dr_off_integration.py`
   - `tests/e2e/dr_off/test_web_interface.py`
   - `tests/performance/dr_off/test_latency.py`

3. **Monitoring**:
   - Langfuse dashboard configuration
   - Performance tracking setup

## 🔗 Dependencies
- **Input from Session 2**: Expected response formats
- **Input from Session 3**: Agent implementation to test
- **Uses existing**: Langfuse integration from health assistant

## 💡 Tips
- Run golden tests nightly in CI
- Use Langfuse tags to segment test vs production
- Set up alerts for accuracy drops below 90%
- Keep test data updated with formulary changes
- Archive Langfuse traces for compliance