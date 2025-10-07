# Handover Note: Issue #6 - Parent/Child Chunking + Metadata Enrichment

**Date:** 2025-10-06
**From:** Previous Claude Code session (Issue #3 completion)
**To:** New Claude Code session
**Status:** Ready to start
**Priority:** P0 - IMMEDIATE (fixes critical failures + improves answer synthesis)

---

## Executive Summary

Implement parent/child chunking with enriched metadata to:
1. **Fix CEP Tools 0% Recall** - Current chunking breaks clinical tool descriptions
2. **Fix CPSO Policies 10% Faithfulness** - Better chunks reduce agent hallucination
3. **Improve answer synthesis** - Richer metadata helps agent understand context

**Why Issue #6 Over Issue #5:**
- Issue #5 (Answer Planner) requires good retrieval context to work
- Current chunking is breaking retrieval for CEP (0% recall) and CPSO (hallucinations)
- Fix the foundation (chunks + metadata) before building answer synthesis on top

---

## Context from Issues #2 and #3

### What We Learned:

**❌ Hybrid Retrieval (Issue #2):**
- Recall@50 already at 75-80% for most domains
- BM25 didn't help semantic medical queries
- RRF fusion degraded ranking quality
- **Verdict:** Dense-only retrieval works well for Dr. OPA

**❌ Cross-Encoder Reranking (Issue #3):**
- General models (bge-reranker-v2-m3) lack domain understanding
- MRR dropped 68%, nDCG@10 dropped 57%
- Domain-specific dense embeddings outperform general cross-encoders
- **Verdict:** Stick with dense-only baseline

**✅ Dense-only retrieval is working well:**
- Dr. OPA: 62% Recall@50, 0.335 MRR, 0.444 nDCG@10
- Dr. OFF: 87% Recall@50, 0.822 MRR, 0.963 nDCG@10
- **Real bottleneck:** Answer synthesis (19% Coverage, 25% Helpfulness)

### Critical Failures Identified:

1. **CEP Clinical Tools: 0% Recall**
   - Gold dataset expects full tool descriptions
   - Corpus has chunked text that doesn't match keywords
   - **Root cause:** Chunking strategy breaks semantic coherence of tool descriptions

2. **CPSO Policies: 10% Faithfulness**
   - Agent generates claims NOT supported by retrieved chunks
   - Despite 80% recall, chunks lack sufficient context
   - **Root cause:** Chunks too small or missing parent context → agent infers incorrectly

3. **Low Coverage/Helpfulness Across All Domains (19%/25%)**
   - Agent receives raw chunks without structure
   - Missing metadata: section hierarchy, document type, effective dates, authority
   - **Impact:** Agent can't determine what information is important for each intent

---

## Technical Approach

### Current Chunking Issues

**Example from PHO IPAC corpus:**
```
pho_chunk_1df57a_parent_0: 41 words (table of contents)
pho_chunk_17fab2_parent_1: 1,165 words (full preamble + introduction)
pho_chunk_0afbd7_child_2_2: 294 words (section on hand hygiene)
```

**Problems:**
1. **Variable chunk sizes:** 34-1,165 words → inconsistent retrieval quality
2. **Missing parent context:** Child chunks lack section titles, hierarchical position
3. **Sparse metadata:** No effective_date, authority, section_path, setting applicability
4. **CEP tools broken:** Clinical tool descriptions split across chunks, keywords don't match

### Parent/Child Chunking Strategy

**Implementation:**

```
Document (e.g., PHO IPAC Guidance)
├── Parent Chunk 1: "Hand Hygiene" section (400-800 words)
│   ├── Child 1.1: "4 Moments for Hand Hygiene" (150-300 words)
│   ├── Child 1.2: "Hand Hygiene Products" (150-300 words)
│   └── Child 1.3: "Surgical Hand Prep" (150-300 words)
├── Parent Chunk 2: "Personal Protective Equipment" section
│   ├── Child 2.1: "Gloves" (150-300 words)
│   ├── Child 2.2: "Masks and Respirators" (150-300 words)
│   └── Child 2.3: "Gowns and Eye Protection" (150-300 words)
```

**Metadata Schema:**
```python
{
    "chunk_id": "pho_chunk_hand_hygiene_parent_1",
    "chunk_type": "parent",  # or "child"
    "parent_id": null,  # for parent chunks
    "child_ids": ["pho_chunk_hand_hygiene_child_1_1", ...],  # for parent chunks

    # Hierarchical context
    "section_title": "Hand Hygiene",
    "section_path": "Infection Prevention > Hand Hygiene",
    "subsection_title": "4 Moments for Hand Hygiene",  # for child chunks

    # Document metadata
    "document_title": "Infection Prevention and Control for Clinical Office Practice",
    "document_type": "ipac-guidance",  # or "policy", "clinical_tool", "quality_standard"
    "source_org": "pho",  # or "cpso", "cep", "ontario_health"
    "authority": "Provincial Infectious Diseases Advisory Committee (PIDAC)",
    "effective_date": "2015-04",
    "last_updated": "2015-04",

    # Applicability
    "setting": ["clinical_office", "ambulatory_care"],  # clinical contexts
    "population": ["general"],  # or "immunocompromised", "pediatric"
    "topics": ["infection-prevention", "ipac", "hand-hygiene"],

    # Content flags
    "is_mandatory": true,  # legislated requirement
    "citation_ready": true,  # can be cited as authoritative source
    "requires_clinical_judgment": false  # clear directive vs recommendation
}
```

---

## Implementation Steps

### 1. Analyze Current Chunking

```bash
# Check current chunk statistics
python3 <<'EOF'
import chromadb

client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")

for coll_name in ["opa_pho_corpus", "opa_cpso_corpus", "opa_cep_corpus"]:
    coll = client.get_collection(coll_name)
    results = coll.get(limit=100, include=["documents", "metadatas"])

    word_counts = [len(doc.split()) for doc in results['documents']]
    print(f"\n{coll_name}:")
    print(f"  Chunks: {len(word_counts)}")
    print(f"  Avg words: {sum(word_counts)/len(word_counts):.0f}")
    print(f"  Min: {min(word_counts)}, Max: {max(word_counts)}")
    print(f"  Metadata fields: {set(results['metadatas'][0].keys())}")
EOF
```

### 2. Design Parent/Child Chunking Logic

**File:** `src/ingestion/parent_child_chunker.py`

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Chunk:
    """Represents a parent or child chunk with metadata."""
    chunk_id: str
    chunk_type: str  # "parent" or "child"
    text: str
    parent_id: Optional[str]
    child_ids: List[str]
    section_title: str
    section_path: str
    document_metadata: dict
    applicability_metadata: dict

class ParentChildChunker:
    """Chunk documents into parent/child hierarchy with rich metadata."""

    def __init__(
        self,
        parent_size: int = 600,  # words
        child_size: int = 200,   # words
        overlap: int = 50        # words
    ):
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap

    def chunk_document(self, document: dict) -> List[Chunk]:
        """
        Chunk a document into parent/child hierarchy.

        Args:
            document: Dict with 'text', 'metadata', 'sections'

        Returns:
            List of Chunk objects (parents + children)
        """
        # 1. Split document into sections (by headings)
        # 2. Create parent chunks (400-800 words per section)
        # 3. Create child chunks (150-300 words, subdividing parents)
        # 4. Add metadata to each chunk
        # 5. Return flat list of parents + children
        pass
```

### 3. Re-ingest Dr. OPA Collections

**Priority order:**
1. **CEP Corpus** (fixes 0% recall) - 57 documents
2. **CPSO Corpus** (fixes 10% faithfulness) - 366 documents
3. **PHO IPAC Corpus** (improves baseline) - 132 documents
4. **Quality Standards Corpus** - 340 documents
5. **Choosing Wisely Corpus** - 544 documents

**Steps per corpus:**
```bash
# 1. Backup existing collection
python scripts/backup_collection.py --collection opa_cep_corpus

# 2. Re-chunk with parent/child strategy
python src/ingestion/rechunk_opa_collections.py \
    --collection cep \
    --strategy parent_child \
    --parent_size 600 \
    --child_size 200

# 3. Validate new chunks
python scripts/validate_chunks.py --collection opa_cep_corpus_v2

# 4. Re-run evaluation to compare
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl \
    --output eval/results/04_parent_child/dr_opa_cep_tools.json
```

### 4. Update Retrieval to Use Parent/Child

**File:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py`

```python
async def _enrich_with_parent_context(
    self,
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    For child chunks, fetch parent chunk text to provide context.

    Args:
        chunks: Retrieved chunks (may include children)

    Returns:
        Chunks enriched with parent context where applicable
    """
    enriched = []
    for chunk in chunks:
        metadata = chunk.get('metadata', {})

        if metadata.get('chunk_type') == 'child' and metadata.get('parent_id'):
            # Fetch parent chunk
            parent = await self.vector_client.get_chunk_by_id(metadata['parent_id'])

            # Combine child + parent context
            chunk['enriched_text'] = f"""
Section: {metadata.get('section_title')}
Context: {parent['text'][:300]}...

Specific Content:
{chunk['text']}
"""
        else:
            chunk['enriched_text'] = chunk['text']

        enriched.append(chunk)

    return enriched
```

### 5. Add Metadata-Aware Response Formatting

**File:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/utils/response_formatter.py`

```python
def format_with_metadata(chunks: List[Dict]) -> str:
    """
    Format chunks with metadata for agent consumption.

    Returns structured text that helps agent understand:
    - Authority/credibility of source
    - Recency/effective date
    - Applicability to query context
    """
    formatted = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get('metadata', {})

        formatted.append(f"""
[Document {i+1}]
Source: {meta.get('source_org', 'unknown')} - {meta.get('document_title', 'Unknown')}
Authority: {meta.get('authority', 'N/A')}
Effective Date: {meta.get('effective_date', 'N/A')}
Section: {meta.get('section_path', 'N/A')}
Type: {meta.get('document_type', 'unknown')}
{'[MANDATORY REQUIREMENT]' if meta.get('is_mandatory') else ''}

Content:
{chunk.get('enriched_text', chunk['text'])}

---
""")

    return "\n".join(formatted)
```

---

## Acceptance Criteria

### Critical Fixes

1. **CEP Tools Recall:**
   - ✅ Recall@50: 0% → 75%+ (find clinical tool descriptions)
   - ✅ Chunking preserves tool name, purpose, and usage instructions together
   - ✅ Gold dataset keywords match new chunk structure

2. **CPSO Policies Faithfulness:**
   - ✅ Faithfulness: 10% → 95%+ (agent stops hallucinating)
   - ✅ Parent context available when child chunk retrieved
   - ✅ Section hierarchy visible to agent

### Improvements

3. **Metadata Enrichment:**
   - ✅ All chunks have: section_title, section_path, document_type, source_org, effective_date
   - ✅ IPAC chunks have: setting[], population[], is_mandatory flag
   - ✅ CPSO chunks have: policy_level, authority, citation_ready flag

4. **Parent/Child Structure:**
   - ✅ Parent chunks: 400-800 words (section-level)
   - ✅ Child chunks: 150-300 words (subsection-level)
   - ✅ 10% overlap between adjacent chunks
   - ✅ parent_id/child_ids properly linked

5. **Evaluation Improvements:**
   - ✅ CEP Tools: Recall@50 0% → 75%+
   - ✅ CPSO Policies: Faithfulness 10% → 95%+
   - ✅ PHO IPAC: Coverage 54.7% → 70%+ (better context for agent)
   - ✅ Quality Standards: Coverage 44% → 60%+ (section hierarchy helps)

---

## Expected Impact

### Retrieval Metrics

| Domain | Metric | Baseline | Expected | Improvement |
|--------|--------|----------|----------|-------------|
| CEP Tools | Recall@50 | 0% | 75%+ | +75% |
| CPSO Policies | Faithfulness | 10% | 95%+ | +85% |
| PHO IPAC | Coverage | 54.7% | 70%+ | +15% |
| Quality Standards | Coverage | 44% | 60%+ | +16% |

### Why This Works

1. **Better chunk boundaries:** Preserve semantic coherence (tool descriptions, policy sections)
2. **Parent context:** Agent understands hierarchical position → less hallucination
3. **Rich metadata:** Agent knows source authority, recency, applicability → better synthesis
4. **Foundation for Issue #5:** Structured chunks enable intent-specific answer schemas

---

## Known Challenges

### 1. Re-ingestion Downtime
- **Issue:** Need to rebuild ChromaDB collections (5 collections, ~1,400 total documents)
- **Mitigation:**
  - Backup existing collections first
  - Use versioned collection names (opa_cep_corpus_v2)
  - Test on CEP first (57 docs), then roll out to others

### 2. Increased Storage
- **Issue:** Parent + children = more chunks than current flat chunking
- **Estimation:** ~2x chunks (1 parent + 2-3 children per current chunk)
- **Impact:** ChromaDB size: ~50MB → ~100MB (acceptable)

### 3. Retrieval Latency
- **Issue:** Enriching with parent context adds extra DB lookups
- **Mitigation:**
  - Batch fetch parent chunks (1 DB call for all parents)
  - Cache parent chunks during session
  - Only enrich top-10 results, not all 50

### 4. Gold Dataset Updates
- **Issue:** CEP gold dataset keywords may need adjustment
- **Solution:** Update gold dataset to match new chunk structure OR adjust chunking to preserve keywords

---

## Files to Create/Modify

### New Files
- `src/ingestion/parent_child_chunker.py` - Chunking logic
- `src/ingestion/rechunk_opa_collections.py` - Re-ingestion script
- `scripts/backup_collection.py` - Backup utility
- `scripts/validate_chunks.py` - Validation script
- `tests/ingestion/test_parent_child_chunker.py` - Unit tests

### Files to Update
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py` - Add parent enrichment
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/utils/response_formatter.py` - Add metadata formatting
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/vector_client.py` - Add get_chunk_by_id()
- `eval/gold/dr_opa/cep_tools.jsonl` - Update keywords if needed

---

## Evaluation Instructions

### Step 1: Re-chunk and Re-ingest CEP Corpus

```bash
source /Users/liammckendry/spacy_env/bin/activate
source .env

# Backup current CEP collection
python scripts/backup_collection.py --collection opa_cep_corpus

# Re-chunk with parent/child strategy
python src/ingestion/rechunk_opa_collections.py --collection cep

# Validate new chunks
python scripts/validate_chunks.py --collection opa_cep_corpus_v2
```

### Step 2: Run CEP Evaluation

```bash
# Compare old vs new chunking
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl \
    --output eval/results/04_parent_child/dr_opa_cep_tools_new.json

# Compare results
python3 <<'EOF'
import json

with open("eval/results/01_baseline/dr_opa_cep_tools.json") as f:
    baseline = json.load(f)
with open("eval/results/04_parent_child/dr_opa_cep_tools_new.json") as f:
    new = json.load(f)

print(f"CEP Tools - Parent/Child Chunking:")
print(f"  Recall@50: {baseline['summary']['avg_recall@50']*100:.0f}% → {new['summary']['avg_recall@50']*100:.0f}%")
print(f"  MRR: {baseline['summary']['avg_mrr']:.3f} → {new['summary']['avg_mrr']:.3f}")
print(f"  Faithfulness: {baseline['summary']['avg_faithfulness']*100:.0f}% → {new['summary']['avg_faithfulness']*100:.0f}%")
EOF
```

### Step 3: Roll Out to Other Collections

If CEP shows improvement:
1. Re-chunk CPSO (fixes 10% faithfulness)
2. Re-chunk PHO IPAC (improves coverage)
3. Re-chunk Quality Standards
4. Re-chunk Choosing Wisely

---

## Success Criteria Summary

**Must Have:**
- ✅ CEP Tools Recall@50: 0% → 75%+
- ✅ CPSO Policies Faithfulness: 10% → 95%+
- ✅ All chunks have rich metadata (section_title, section_path, etc.)
- ✅ Parent/child structure properly linked
- ✅ Unit tests pass

**Nice to Have:**
- ✅ PHO IPAC Coverage: 54.7% → 70%+
- ✅ Quality Standards Coverage: 44% → 60%+
- ✅ Retrieval latency <500ms with parent enrichment
- ✅ Documentation of new chunk schema

---

## Next Steps After Issue #6

After completing parent/child chunking, **Issue #5 (Answer Planner + Self-Check)** becomes viable:
- Structured chunks enable intent-specific schemas
- Rich metadata helps agent understand what info is important
- Parent context provides sufficient detail for complete answers
- Expected: Coverage 19% → 85%+, Helpfulness 25% → 70%+

---

**Good luck with Issue #6! This will fix critical failures and provide the foundation for high-quality answer synthesis.**
