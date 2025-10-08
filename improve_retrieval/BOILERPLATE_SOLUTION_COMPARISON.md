# Boilerplate Removal: 3 Approaches Compared

**Problem:** 22.2% of chunks (143/644) are boilerplate (References, Acknowledgments, Legal)

## Current State

**Boilerplate sections:**
- References: 109 chunks (17%)
- Acknowledgments/Legal: 34 chunks (5%)

**Content in boilerplate:**
```
[1]Statistics Canada. The Daily – Study: Insomnia. 2005. [cited 2016 October 16]...
[2]Toward Optimized Practice. Assessment to management of adult insomnia...
[3]Qaseem A, Kansagara D, Forciea M, Cooke M, Denberg T. Management of chronic insomnia...
```

```
This Tool was developed as part of the Knowledge Translation in Primary Care Initiative,
led by Centre for Effective Practice with collaboration from the Ontario College of
Family Physicians...
```

---

## Approach 1: Filter at Ingestion Time (BeautifulSoup)

### Method
Skip sections with boilerplate titles during extraction:

```python
# In ingester_v2.py _extract_full_sections()

BOILERPLATE_SECTIONS = [
    'references', 'referencesnew',
    'acknowledgment', 'acknowledgement', 'acknowledgments',
    'legal', 'permission to use'
]

def _should_skip_section(heading: str) -> bool:
    """Check if section is boilerplate."""
    heading_lower = heading.lower()
    return any(kw in heading_lower for kw in BOILERPLATE_SECTIONS)

# In main loop:
if element.name == 'h2':
    heading_text = element.get_text(strip=True)

    # Skip boilerplate sections entirely
    if _should_skip_section(heading_text):
        logger.debug(f"Skipping boilerplate section: {heading_text}")
        current_section = None  # Don't track this section
        continue
```

### Pros
- ✅ **Simple**: 10 lines of code
- ✅ **Fast**: No LLM calls
- ✅ **Reduces collection size**: 644 → ~501 chunks (-22%)
- ✅ **Precise**: H2 section titles are reliable indicators
- ✅ **Reduces storage/query costs**: Smaller collection

### Cons
- ❌ **Loses citation metadata**: Can't answer "what evidence supports X?"
- ❌ **May miss edge cases**: If boilerplate has non-standard heading
- ❌ **Requires re-ingestion**: Can't fix existing collection

### Effort
- **Implementation**: 30 minutes
- **Testing**: 1 hour
- **Re-ingestion**: 10 minutes (46 tools)

---

## Approach 2: Filter at Query Time (Retrieval Filter)

### Method
Let boilerplate into collection, but filter it out during search:

```python
# In semantic_search.py _apply_filters()

BOILERPLATE_SECTIONS = [
    'references', 'referencesnew',
    'acknowledgment', 'acknowledgement', 'acknowledgments',
    'legal', 'permission to use'
]

def _is_boilerplate(metadata: Dict) -> bool:
    """Check if chunk is boilerplate."""
    section = metadata.get('section_title', '').lower()
    return any(kw in section for kw in BOILERPLATE_SECTIONS)

# In _apply_filters():
for doc in documents:
    metadata = doc.get('metadata', {})

    # Filter out boilerplate
    if _is_boilerplate(metadata):
        logger.debug(f"Filtered out boilerplate: {metadata.get('section_title')}")
        continue

    # ... rest of filtering logic
```

### Pros
- ✅ **No re-ingestion needed**: Works on existing collection
- ✅ **Flexible**: Can toggle filtering on/off per query
- ✅ **Preserves data**: References still available if needed
- ✅ **Fast**: No LLM calls
- ✅ **Easy to test**: Just run eval again

### Cons
- ❌ **Wastes storage**: Boilerplate still in collection (143 chunks, ~100K tokens)
- ❌ **Wastes embedding cost**: Already paid to embed boilerplate
- ❌ **Top-K pollution**: If k=20, might retrieve 5 boilerplate chunks, then filter to k=15
- ⚠️ **Requires careful top-k handling**: Need to retrieve k+buffer to account for filtering

### Effort
- **Implementation**: 1 hour (add filtering + adjust top-k buffer)
- **Testing**: 1 hour
- **No re-ingestion needed**

---

## Approach 3: LLM-Based Extraction (Replace BeautifulSoup)

### Method
Use LLM to extract ONLY clinical content from HTML:

```python
# New: llm_extractor.py

from openai import OpenAI

def extract_clinical_content_with_llm(html: str, tool_name: str) -> List[Dict]:
    """Use LLM to extract clinical sections, skip boilerplate."""

    # Convert HTML to clean text
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)

    # Prompt LLM to extract structured sections
    prompt = f"""
You are a medical content extractor. Extract ONLY the clinical sections from this CEP tool.

INCLUDE:
- Diagnosis criteria and procedures
- Screening guidelines
- Assessment tools and procedures
- Treatment options and protocols
- Management approaches
- Monitoring and follow-up
- Referral criteria
- Red flags and warnings

EXCLUDE:
- References and citations
- Acknowledgments
- Legal disclaimers
- Development methodology
- Funding information

Tool: {tool_name}

HTML Content:
{text[:15000]}  # Truncate to fit context window

Return a JSON array of sections:
[
  {{
    "heading": "Diagnosis",
    "content": "Full text of diagnosis section...",
    "subsections": ["Diagnostic criteria", "When to suspect"]
  }},
  ...
]
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    sections = json.loads(response.choices[0].message.content)
    return sections['sections']
```

### Pros
- ✅ **Intelligent filtering**: LLM understands context, not just keywords
- ✅ **Handles edge cases**: Can detect boilerplate even with unusual headings
- ✅ **Semantic chunking**: LLM can identify logical content boundaries
- ✅ **Potential for enhancement**: Could also clean up formatting, expand acronyms, etc.

### Cons
- ❌ **Expensive**: ~$0.01-0.05 per tool × 46 tools = $0.46-$2.30 per ingestion
- ❌ **Slow**: ~3-10s per tool × 46 tools = 2-8 minutes (vs 10s for BeautifulSoup)
- ❌ **Non-deterministic**: Different extractions on different runs
- ❌ **Token limits**: May need to chunk large tools (>15K tokens)
- ❌ **Potential for errors**: LLM might skip important content or hallucinate
- ❌ **Requires validation**: Need to verify LLM didn't drop critical sections
- ❌ **Overkill**: HTML structure is already reliable (H2 sections work well)

### Effort
- **Implementation**: 4-6 hours (LLM integration + error handling + validation)
- **Testing**: 3-4 hours (validate all 46 tools)
- **Cost**: ~$2-5 per test run
- **Re-ingestion**: 5-10 minutes (slower due to LLM calls)

---

## Recommendation: **Approach 1 + Approach 2 Hybrid**

### Best Solution: Filter at Ingestion, with Runtime Override

```python
# Step 1: Filter at ingestion (Approach 1)
# ingester_v2.py - skip boilerplate sections entirely

# Step 2: Add runtime toggle (Approach 2 - optional)
# semantic_search.py - allow including references if needed

def search(
    query: str,
    include_references: bool = False,  # Default: skip references
    include_acknowledgments: bool = False,  # Default: skip acknowledgments
    ...
):
    # If user specifically asks "what evidence supports X?", set include_references=True
```

### Why This Is Best:

1. **Reduces collection size** by 22% (143 chunks saved)
2. **Saves embedding costs** (~$0.02 per run × many runs = real savings)
3. **Improves retrieval quality** (no boilerplate in top-k)
4. **Preserves flexibility** (can toggle back on if needed)
5. **Simple and fast** (30 min implementation)
6. **Reliable** (H2 headings are consistent across all CEP tools)

### Implementation Steps:

**Step 1 - Add filter to ingester (30 min):**
```bash
# Edit src/ai_agents/dr_opa_agent/ingestion/cep/ingester_v2.py
# Add BOILERPLATE_SECTIONS and _should_skip_section()
# Skip in _extract_full_sections() loop
```

**Step 2 - Re-ingest corpus (10 min):**
```bash
python reingest_cep_corpus.py
# Expected: 644 → ~500 chunks
```

**Step 3 - Validate (30 min):**
```bash
# Check that References sections are gone
python analyze_boilerplate.py

# Re-run evaluation
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl ...
```

**Expected Impact:**
- Collection size: 644 → ~500 chunks (-22%)
- Boilerplate in results: 26% → 0%
- MRR: 0.051 → ~0.25-0.35 (5-7x improvement)
- Recall@50: 50% → 50% (same - test queries still broken)

---

## When To Use LLM Extraction (Approach 3)

LLM extraction would be worth it if:

1. **HTML is messy/inconsistent** (not the case - CEP uses consistent Gravity Forms)
2. **Need semantic understanding** (not needed - headings are reliable)
3. **Want content enhancement** (e.g., expand acronyms, add context) - could be valuable later
4. **Source documents vary widely** (not the case - all CEP tools follow same template)

For CEP specifically, **BeautifulSoup + filtering is sufficient and optimal**.

---

## Conclusion

**Recommended:** Implement Approach 1 (filter at ingestion)

- ✅ Simple (30 min)
- ✅ Effective (removes all boilerplate)
- ✅ Cost-efficient (no LLM calls)
- ✅ Reliable (H2 headings are consistent)
- ✅ Improves metrics (MRR 5-7x)

**Skip LLM extraction** - it's overkill for structured HTML with consistent section headings.
