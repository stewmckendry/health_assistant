# Task 2: MCP Tools & Query Interface

## 🎯 Objective
Implement MCP (Model Context Protocol) tools that provide structured access to Ontario healthcare data for the Dr. OFF agent.

## 📋 Checklist

### Setup
- [ ] Create directory structure under `src/agents/clinical/dr_off/tools/`
- [ ] Review existing MCP tool patterns in codebase
- [ ] Set up base tool class following project conventions

### Response Models
- [ ] Create `src/agents/clinical/dr_off/response_models.py`
  - [ ] Define `Citation` model:
    ```python
    class Citation(BaseModel):
        source: str  # "ODB Ed. 43", "OHIP Schedule", "ADP Manual"
        page: Optional[int]
        section: Optional[str]
        url: Optional[str]
    ```
  - [ ] Define `AnswerCard` model:
    ```python
    class AnswerCard(BaseModel):
        decision: Literal["Yes", "No", "Conditional"]
        key_data: dict  # price, coverage_pct, fee_amount
        options: list  # DIN list, codes, device types
        citations: list[Citation]
        confidence: float
        notes: Optional[str]
    ```
  - [ ] Define specific response types:
    - `DrugCoverageResponse`
    - `OHIPFeeResponse`
    - `ADPDeviceResponse`

### ODB Formulary Tools (`formulary_tools.py`)
- [ ] Implement `formulary_lookup()`:
  ```python
  def formulary_lookup(
      din: Optional[str] = None,
      ingredient: Optional[str] = None,
      brand: Optional[str] = None
  ) -> DrugCoverageResponse:
      # Query odb_drugs table
      # Include interchangeable group info
      # Return structured response with lowest-cost flag
  ```
- [ ] Implement `interchangeability_context()`:
  ```python
  def interchangeability_context(
      group_id: str
  ) -> InterchangeabilityResponse:
      # Get all drugs in group
      # Retrieve PDF chunks for citation
      # Highlight lowest-cost option
  ```
- [ ] Add batch lookup support for multiple DINs
- [ ] Include LU code handling

### OHIP Tools (`ohip_tools.py`)
- [ ] Implement `ohip_fee_lookup()`:
  ```python
  def ohip_fee_lookup(
      code: Optional[str] = None,
      term: Optional[str] = None,
      specialty: Optional[str] = None
  ) -> OHIPFeeResponse:
      # Query ohip_fees table
      # Return fee schedule details
      # Include page reference from PDF
  ```
- [ ] Implement `coverage_rule_lookup()`:
  ```python
  def coverage_rule_lookup(
      section: Optional[str] = None,
      keyword: Optional[str] = None
  ) -> CoverageRuleResponse:
      # Search Regulation 552
      # Return relevant sections
      # Include regulatory citations
  ```
- [ ] Add support for fee modifiers and premiums
- [ ] Handle specialty-specific billing rules

### ADP Tools (`adp_tools.py`)
- [ ] Implement `adp_device_lookup()`:
  ```python
  def adp_device_lookup(
      category: Optional[str] = None,
      device: Optional[str] = None
  ) -> ADPDeviceResponse:
      # Query adp_device_rules
      # Return funding percentage
      # Include eligibility criteria
      # List required forms
  ```
- [ ] Implement `adp_forms()`:
  ```python
  def adp_forms(
      category: str
  ) -> ADPFormsResponse:
      # Return form URLs/names
      # Include submission instructions
      # Note processing timelines
  ```
- [ ] Add vendor search capability
- [ ] Include replacement interval logic

### Query Router (`router.py`)
- [ ] Create intelligent routing logic:
  ```python
  class QueryRouter:
      def route_query(self, query: str) -> list[str]:
          # Analyze query intent
          # Determine which tools to call
          # Return tool names in order
  ```
- [ ] Implement query classification:
  - Drug/medication queries → ODB tools
  - Billing/fee queries → OHIP tools
  - Device/equipment queries → ADP tools
  - Complex queries → Multiple tools
- [ ] Add confidence scoring for routing decisions
- [ ] Handle ambiguous queries with clarification

### Tool Registration
- [ ] Create `__init__.py` with tool exports
- [ ] Follow MCP tool registration pattern:
  ```python
  TOOLS = {
      "formulary_lookup": formulary_lookup,
      "interchangeability_context": interchangeability_context,
      "ohip_fee_lookup": ohip_fee_lookup,
      "coverage_rule_lookup": coverage_rule_lookup,
      "adp_device_lookup": adp_device_lookup,
      "adp_forms": adp_forms
  }
  ```
- [ ] Add tool descriptions for agent understanding
- [ ] Include parameter validation

### Error Handling
- [ ] Implement graceful fallbacks for missing data
- [ ] Add retry logic for database queries
- [ ] Create informative error messages
- [ ] Log all tool calls for debugging

### Testing
- [ ] Write unit tests for each tool
- [ ] Create mock database for testing
- [ ] Test edge cases:
  - [ ] Non-existent DINs
  - [ ] Ambiguous drug names
  - [ ] Invalid OHIP codes
  - [ ] Unsupported ADP devices
- [ ] Validate response formats
- [ ] Test router accuracy

## 📁 Deliverables

1. **Tools Implementation**:
   - `src/agents/clinical/dr_off/tools/__init__.py`
   - `src/agents/clinical/dr_off/tools/formulary_tools.py`
   - `src/agents/clinical/dr_off/tools/ohip_tools.py`
   - `src/agents/clinical/dr_off/tools/adp_tools.py`
   - `src/agents/clinical/dr_off/tools/router.py`

2. **Response Models**:
   - `src/agents/clinical/dr_off/response_models.py`

3. **Tests**:
   - `tests/unit/agents/dr_off/test_tools.py`
   - `tests/unit/agents/dr_off/test_router.py`

## 🔗 Dependencies
- **Input from Session 1**: Database schema and tables
- **Output to Session 3**: Tool functions for agent registration

## 💡 Tips
- Use SQL prepared statements for security
- Cache frequently requested items (common drugs, fee codes)
- Include fuzzy matching for drug name searches
- Return structured data that's easy for LLM to interpret
- Always include citations for auditability