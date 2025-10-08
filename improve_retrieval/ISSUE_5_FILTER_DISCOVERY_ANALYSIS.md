# Issue #5: Filter Discovery Analysis

**Date:** 2025-10-07
**Raised By:** User during implementation review
**Concern:** Agents may not discover available filters, leading to either missed retrievals or bloated retrievals

---

## Problem Statement

The MCP tools expose a `filters` parameter with various criteria specific to each tool. **Without explicit guidance in the system prompt, agents may not discover or use these filters**, leading to:

1. **Inadvertently Filtered Out Retrievals:** Agent doesn't know filters exist, can't access specific subsets
2. **Bloated Retrievals:** Agent retrieves everything, gets irrelevant results mixed in
3. **Suboptimal Tool Usage:** Agent doesn't leverage domain-specific filtering capabilities

---

## Current Filter Inventory

### Dr. OFF Tools (schedule.py)

**`schedule_get` Filters:**
```python
filters: {
    "codes": List[str],           # Specific OHIP fee codes to look up
    "include": List[str]           # What to include: ["codes", "fee", "limits", "documentation"]
}
```

**Examples:**
- `filters={"codes": ["E083A", "E083B"]}` → Direct code lookup (SQL-only strategy)
- `filters={"include": ["codes", "fee"]}` → Only return codes and fees, not documentation

**Current Agent Awareness:** ❌ NOT mentioned in prompt

---

### Dr. OPA Tools

#### 1. `opa_search_sections` (General Search)

**Filters:**
```python
filters: {
    "sources": List[str],         # ["pho", "cpso", "cep", "quality_standards", "choosing_wisely", "ontario_health"]
    "doc_types": List[str],       # ["guideline", "policy", "standard", "recommendation", "tool"]
    "topics": List[str],          # ["infection_prevention", "clinical_programs", "quality_improvement"]
    "date_range": {
        "start": str,             # ISO date (e.g., "2023-01-01")
        "end": str
    },
    "include_superseded": bool    # Include old/superseded documents
}
```

**Examples:**
- `filters={"sources": ["pho", "cpso"]}` → Only PHO and CPSO sources
- `filters={"doc_types": ["guideline"]}` → Only guidelines, not tools or standards
- `filters={"date_range": {"start": "2024-01-01"}}` → Only docs from 2024+

**Current Agent Awareness:** ❌ NOT mentioned in prompt

---

#### 2. `opa_policy_check` (CPSO Policies)

**Filters:**
```python
filters: {
    "policy_level": str,         # "expectation" | "advice" | "both" (default: "both")
    "include_related": bool      # Include related policies (default: True)
}
```

**Examples:**
- `filters={"policy_level": "expectation"}` → Only mandatory requirements, not advice
- `filters={"include_related": False}` → Only exact matches, no related policies

**Current Agent Awareness:** ❌ NOT mentioned in prompt

---

#### 3. `opa_program_lookup` (Ontario Health Programs)

**Filters:**
```python
filters: {
    "patient_age": int,           # Patient age for eligibility filtering
    "risk_factors": List[str],    # Risk factors to consider
    "info_needed": List[str]      # ["eligibility", "referral", "coverage", "access"]
}
```

**Examples:**
- `filters={"patient_age": 52, "risk_factors": ["smoker", "family_history"]}` → Age and risk-specific results
- `filters={"info_needed": ["eligibility", "referral"]}` → Only eligibility and referral info, skip coverage/access

**Current Agent Awareness:** ❌ NOT mentioned in prompt

---

#### 4. `opa_ipac_guidance` (Infection Prevention)

**Filters:**
```python
filters: {
    "setting": str,              # "hospital" | "clinic" | "ltc" | "community" | ""
    "pathogen": str,             # Specific pathogen (e.g., "MRSA", "C. difficile")
    "include_checklists": bool,  # Include implementation checklists (default: True)
    "search_web": bool          # Fallback to PHO web search (default: True)
}
```

**Examples:**
- `filters={"setting": "ltc"}` → Long-term care specific guidance
- `filters={"pathogen": "MRSA"}` → MRSA-specific protocols
- `filters={"include_checklists": False}` → Only guidance, no checklists

**Current Agent Awareness:** ❌ NOT mentioned in prompt

---

## Impact Analysis

### Scenario 1: Agent Doesn't Use Filters (Current State)

**Query:** "What are CPSO expectations vs. advice for virtual care consent?"

**Agent Behavior (Without Filter Guidance):**
```python
# Agent calls:
opa_policy_check(query="virtual care consent", k=10)
# Gets: Mixed expectations + advice
```

**Problem:**
- Agent gets 10 results with both mandatory requirements AND optional advice mixed together
- Agent must sort through and categorize on its own (error-prone)
- Answer may conflate "must do" with "should do"

**With Filter Guidance:**
```python
# Agent could call twice:
opa_policy_check(query="virtual care consent", filters={"policy_level": "expectation"})  # Mandatory
opa_policy_check(query="virtual care consent", filters={"policy_level": "advice"})       # Optional
# Gets: Clear separation
```

**Benefit:**
- Clear distinction between mandatory vs. optional
- Agent can structure answer: "MUST: ... | SHOULD: ..."
- Higher faithfulness (no confusion about requirement level)

---

### Scenario 2: Bloated Retrievals

**Query:** "What are hand hygiene requirements for procedure rooms?"

**Agent Behavior (Without Filter Guidance):**
```python
# Agent calls:
opa_ipac_guidance(query="hand hygiene procedure rooms", k=10)
# Gets: Hospital, clinic, LTC, community settings all mixed
```

**Problem:**
- Gets 10 results across ALL settings (hospital, clinic, LTC, etc.)
- Only 2-3 are relevant to procedure rooms
- Agent must filter mentally → cognitive load → missed details

**With Filter Guidance:**
```python
# Agent calls with setting filter:
opa_ipac_guidance(query="hand hygiene", filters={"setting": "clinic"}, k=10)
# Gets: 10 results ALL relevant to clinic procedure rooms
```

**Benefit:**
- All 10 results are relevant
- Higher density of useful information
- Better coverage (10 clinic-specific vs 2-3 buried in mixed results)

---

### Scenario 3: Missing Critical Subsets

**Query:** "Is this 65-year-old patient eligible for colon cancer screening?"

**Agent Behavior (Without Filter Guidance):**
```python
# Agent calls:
opa_program_lookup(query="colon cancer screening eligibility", k=10)
# Gets: General eligibility info (50+, no age-specific guidance)
```

**Problem:**
- Gets general info about the program
- Misses age-specific nuances (e.g., "65+ qualifies for enhanced coverage")
- Agent can't provide precise answer for this patient

**With Filter Guidance:**
```python
# Agent calls with age filter:
opa_program_lookup(query="colon cancer screening", filters={"patient_age": 65}, k=10)
# Gets: Age-specific eligibility, enhanced coverage details
```

**Benefit:**
- Retrieval is tailored to patient demographics
- Agent gets precise, actionable information
- Higher helpfulness (specific to user's case)

---

## Root Cause: Filter Schema Not Visible to Agent

**OpenAI Agents SDK Tool Schema:**

When tools are registered via MCP, the agent sees:
```python
{
  "name": "opa_policy_check",
  "description": "Check CPSO policies for regulatory requirements",
  "parameters": {
    "query": {"type": "string", "description": "Policy question"},
    "k": {"type": "integer", "description": "Number of results"},
    "filters": {"type": "object", "description": "Optional filters"}  # ❌ NO DETAILS
  }
}
```

**Problem:** `filters` is just listed as "object" with no details about available keys!

**Agent's View:**
- Agent knows `filters` exists
- Agent doesn't know what keys are valid
- Agent doesn't know what values are allowed
- Agent must guess or ignore filters entirely

---

## Proposed Solutions

### Option 1: Add Filter Documentation to Step 2 (RETRIEVE) in System Prompt

**Implementation: Update system prompts with filter tables**

#### Dr. OFF Agent Prompt Addition (Step 2):

```markdown
STEP 2: RETRIEVE - Call Tools and Extract Facts
───────────────────────────────────────────────────

Call the appropriate MCP tools based on intent:
- schedule_get: For OHIP billing codes (Billing intent)
- odb_get: For drug coverage (Drug Coverage intent)
- adp_get: For device funding (Device Funding intent)

**Available Filters (Use to Refine Retrievals):**

**schedule_get filters:**
- `codes`: List[str] - Specific OHIP fee codes (e.g., ["E083A", "E083B"])
- `include`: List[str] - What to include (e.g., ["codes", "fee", "limits", "documentation"])

**Example:** For billing queries with known codes, use direct lookup:
```python
schedule_get(query="E083A details", filters={"codes": ["E083A"]})
```
```

#### Dr. OPA Agent Prompt Addition (Step 2):

```markdown
STEP 2: RETRIEVE - Call Tools and Extract Facts
───────────────────────────────────────────────────

Call the appropriate MCP tools based on intent:
- opa_policy_check: For CPSO policy questions
- opa_ipac_guidance: For infection control questions
- opa_program_lookup: For clinical programs
- [other tools...]

**Available Filters (Use to Refine Retrievals):**

**opa_policy_check filters:**
- `policy_level`: "expectation" | "advice" | "both" - Filter by requirement level
- `include_related`: bool - Include related policies

**opa_ipac_guidance filters:**
- `setting`: "hospital" | "clinic" | "ltc" | "community" - Filter by healthcare setting
- `pathogen`: str - Specific pathogen (e.g., "MRSA", "C. difficile")
- `include_checklists`: bool - Include implementation checklists
- `search_web`: bool - Enable PHO web search fallback

**opa_program_lookup filters:**
- `patient_age`: int - Patient age for eligibility filtering
- `risk_factors`: List[str] - Risk factors to consider
- `info_needed`: ["eligibility", "referral", "coverage", "access"] - What info to return

**opa_search_sections filters:**
- `sources`: ["pho", "cpso", "cep", "quality_standards", "choosing_wisely", "ontario_health"]
- `doc_types`: ["guideline", "policy", "standard", "recommendation", "tool"]
- `date_range`: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} - Filter by date
- `include_superseded`: bool - Include old/superseded documents

**When to Use Filters:**
- Use `policy_level="expectation"` when user asks about "mandatory" or "must" requirements
- Use `setting` filter when query mentions specific setting (hospital, clinic, LTC)
- Use `patient_age` filter when query includes patient demographics
- Use `sources` filter when user asks for specific organization (e.g., "PHO guidelines")
- Use `date_range` when user asks for "latest" or "recent" guidance
```

**Pros:**
- ✅ Agents discover available filters
- ✅ Agents understand when to use them
- ✅ No code changes required
- ✅ Easy to update as filters evolve

**Cons:**
- ❌ Adds ~100 lines to prompt (but still manageable)
- ❌ Agent must remember filter details while calling tools

**Estimated Effort:** 30 minutes

---

### Option 2: Create Filter Helper Tool

**Implementation: Add new MCP tool `get_tool_filters(tool_name: str)`**

```python
@mcp.tool(name="get_tool_filters")
async def get_tool_filters(tool_name: str) -> Dict[str, Any]:
    """
    Returns available filters for a specific tool.

    Args:
        tool_name: Name of the tool (e.g., "opa_policy_check")

    Returns:
        Dict with filter definitions and usage examples
    """
    FILTER_SCHEMAS = {
        "opa_policy_check": {
            "filters": {
                "policy_level": {
                    "type": "string",
                    "values": ["expectation", "advice", "both"],
                    "default": "both",
                    "description": "Filter by requirement level"
                },
                "include_related": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include related policies"
                }
            },
            "examples": [
                {"policy_level": "expectation"},  # Mandatory only
                {"include_related": False}        # Exact matches only
            ]
        },
        "opa_ipac_guidance": {
            "filters": {
                "setting": {
                    "type": "string",
                    "values": ["hospital", "clinic", "ltc", "community", ""],
                    "description": "Filter by healthcare setting"
                },
                "pathogen": {
                    "type": "string",
                    "description": "Specific pathogen name"
                },
                "include_checklists": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include implementation checklists"
                }
            },
            "examples": [
                {"setting": "ltc"},
                {"pathogen": "MRSA", "include_checklists": True}
            ]
        }
    }

    return FILTER_SCHEMAS.get(tool_name, {"error": f"Unknown tool: {tool_name}"})
```

**System Prompt Addition:**
```markdown
STEP 2: RETRIEVE - Call Tools and Extract Facts

Before calling a tool for the first time, you can call `get_tool_filters(tool_name)`
to see what filters are available. Use filters to refine retrievals.

Example workflow:
1. Call: get_tool_filters("opa_policy_check")
2. Learn: policy_level="expectation" filters to mandatory requirements
3. Call: opa_policy_check(query="...", filters={"policy_level": "expectation"})
```

**Pros:**
- ✅ Agent discovers filters programmatically
- ✅ Filter schemas are maintained in code (single source of truth)
- ✅ Can include examples and validation rules
- ✅ Shorter system prompt

**Cons:**
- ❌ Requires additional tool call (agent must learn to call it)
- ❌ More code to maintain
- ❌ Agent might forget to call helper tool

**Estimated Effort:** 2-3 hours

---

### Option 3: Enhanced Tool Descriptions (FastMCP Level)

**Implementation: Improve tool descriptions in FastMCP registration**

```python
@mcp.tool(
    name="opa_policy_check",
    description="""
    Check CPSO policies for regulatory requirements.

    Filters:
    - policy_level: "expectation" (mandatory) | "advice" (recommended) | "both"
    - include_related: bool (include related policies, default True)

    Examples:
    - Mandatory requirements only: filters={"policy_level": "expectation"}
    - Exact matches only: filters={"include_related": False}
    """
)
async def policy_check_handler(query: str, k: int = 10, filters: Dict[str, Any] = None):
    ...
```

**Pros:**
- ✅ Filters visible in tool schema sent to agent
- ✅ No prompt changes required
- ✅ Filters stay close to implementation

**Cons:**
- ❌ OpenAI Agents SDK may not show full descriptions to agent
- ❌ Unclear if agent will parse examples from description
- ❌ Need to verify agent actually sees this

**Estimated Effort:** 1 hour + verification

---

## Recommendation

**Implement Option 1 (Filter Documentation in Prompt) FIRST:**

### Rationale:
1. **Fastest:** 30 minutes vs 2-3 hours
2. **Most Reliable:** Agents definitely see system prompt content
3. **Easy to Iterate:** Prompt changes don't require code/testing
4. **Aligns with Issue #5 Approach:** We already added Step 2 (RETRIEVE) to prompt

### When to Consider Option 2/3:
- If prompt becomes too long (>250 lines total)
- If filters change frequently and prompt maintenance becomes burden
- If OpenAI Agents SDK adds better filter schema support

---

## Implementation Plan

### Phase 1: Add Filter Documentation to Existing Step 2

**Dr. OFF Agent** (`src/ai_agents/dr_off_agent/openai_agent.py`):

Add after line 470 (within Step 2 section):

```python
**Available Tool Filters:**

schedule_get filters:
- codes: List[str] - Direct OHIP code lookup (e.g., ["E083A"])
- include: List[str] - Fields to return ["codes", "fee", "limits", "documentation"]

odb_get filters:
- drug_class: str - Therapeutic class filter
- include_generic: bool - Include generic alternatives

adp_get filters:
- device_category: str - Device type filter
- funding_level: str - Coverage level filter
```

**Dr. OPA Agent** (`src/ai_agents/dr_opa_agent/openai_agent.py`):

Add after line 469 (within Step 2 section):

```python
**Available Tool Filters:**

opa_policy_check:
- policy_level: "expectation" | "advice" | "both" - Requirement level
- include_related: bool - Include related policies

opa_ipac_guidance:
- setting: "hospital" | "clinic" | "ltc" | "community"
- pathogen: str - Specific pathogen name
- include_checklists: bool - Include checklists

opa_program_lookup:
- patient_age: int - Age for eligibility
- risk_factors: List[str] - Risk factors
- info_needed: ["eligibility", "referral", "coverage", "access"]

opa_search_sections:
- sources: ["pho", "cpso", "cep", "quality_standards", "choosing_wisely", "ontario_health"]
- doc_types: ["guideline", "policy", "standard", "recommendation", "tool"]
- date_range: {"start": "YYYY-MM-DD"}
- include_superseded: bool

**When to Use Filters:**
- Use setting filter when query mentions specific setting
- Use policy_level="expectation" for mandatory requirements
- Use patient_age filter for eligibility queries
- Use sources filter when user asks for specific organization
```

---

### Phase 2: Validation (After Implementation)

**Test Queries:**

1. **Dr. OFF - Billing Filter Test:**
   - Query: "Get details for OHIP codes E083A and E083B"
   - Expected: Agent uses `filters={"codes": ["E083A", "E083B"]}`
   - Verify: Tool call logs show filter usage

2. **Dr. OPA - Setting Filter Test:**
   - Query: "What are hand hygiene requirements for long-term care facilities?"
   - Expected: Agent uses `filters={"setting": "ltc"}`
   - Verify: Tool call logs show filter usage

3. **Dr. OPA - Policy Level Filter Test:**
   - Query: "What MUST physicians do for virtual care consent?"
   - Expected: Agent uses `filters={"policy_level": "expectation"}`
   - Verify: Tool call logs show filter usage

**Success Criteria:**
- ≥70% of queries with implicit filter hints use appropriate filters
- Filter usage improves answer precision (fewer irrelevant results)
- No regression in Coverage/Helpfulness metrics

---

## Monitoring & Metrics

After implementing filter guidance, track:

1. **Filter Usage Rate:**
   - % of tool calls that include filters
   - Baseline: ~0% (current)
   - Target: ≥30% of calls where filters would help

2. **Filter Correctness:**
   - % of filter uses that are appropriate for the query
   - Target: ≥80% correct usage

3. **Retrieval Precision:**
   - Avg relevance score of top 10 results (with vs without filters)
   - Expected improvement: +10-20% relevance

4. **Answer Quality:**
   - Coverage/Helpfulness should maintain or improve
   - Target: No regression (<5% drop)

**Log Analysis:**
```bash
# Check filter usage in tool call logs
grep "filters=" logs/dr_opa_agent/mcp_session_*.log | wc -l
```

---

## Conclusion

**Status:** ✅ Issue identified, solution designed, ready to implement

**Next Steps:**
1. Add filter documentation to Step 2 of both agent prompts (~30 min)
2. Test with 5-10 queries that should use filters
3. Measure filter usage rate and answer quality
4. Consider Option 2 (helper tool) if adoption is low (<30%)

**Priority:** MEDIUM-HIGH
- Not blocking Issue #5 eval, but important for maximizing retrieval precision
- Should implement before declaring Issue #5 "complete"
- Quick win with low risk

---

**Related Documents:**
- `improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md` - Main Issue #5 implementation
- `src/ai_agents/dr_off_agent/openai_agent.py:397-559` - Dr. OFF system prompt
- `src/ai_agents/dr_opa_agent/openai_agent.py:380-558` - Dr. OPA system prompt
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:144-857` - Filter definitions
