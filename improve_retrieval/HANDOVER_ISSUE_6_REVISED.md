# Handover Note: Issue #6 - Systematic Chunk Quality Analysis & Remediation

**Date:** 2025-10-06
**From:** Previous Claude Code session (Issue #3 completion)
**To:** New Claude Code session
**Status:** Ready to start
**Priority:** P0 - IMMEDIATE (foundation for all retrieval improvements)

---

## Executive Summary

**DO NOT jump to implementation.** First, conduct a comprehensive analysis of chunking quality across ALL collections (Dr. OFF + Dr. OPA) to understand gaps, then design targeted fixes.

**Why This Approach:**
- Issues #2 and #3 failed because we reacted to symptoms without understanding root causes
- We have 8 vector collections with varying performance (0% to 100% recall)
- Need to understand: What makes good chunks work? What breaks bad chunks?
- **Goal:** Data-driven chunking strategy, not reactive fixes

---

## Phase 1: Comprehensive Chunk Analysis (DO THIS FIRST)

### Step 1: Extract All Chunks from All Collections

**Collections to analyze (8 total):**

**Dr. OFF (3 collections):**
1. `ohip_documents` - 6,983 chunks - **100% Recall@50, 1.000 MRR** ✅ EXCELLENT
2. `adp_documents` - 610 chunks - **100% Recall@50, 0.867 MRR** ✅ EXCELLENT
3. `odb_documents` - 10,815 chunks - **100% Recall@50, 1.000 MRR** ✅ EXCELLENT

**Dr. OPA (5 collections):**
4. `opa_pho_corpus` - 132 chunks - **80% Recall@50, 0.533 MRR** ⚠️ GOOD
5. `opa_cpso_corpus` - 366 chunks - **80% Recall@50, 0.567 MRR, 10% Faithfulness** ❌ HALLUCINATION ISSUE
6. `opa_cep_corpus` - 57 chunks - **0% Recall@50** ❌ COMPLETE FAILURE
7. `opa_quality_standards_corpus` - 340 chunks - **75% Recall@50, 0.350 MRR** ⚠️ MEDIOCRE
8. `opa_choosing_wisely_corpus` - 544 chunks - **75% Recall@50, 0.375 MRR** ⚠️ MEDIOCRE

**Create analysis script:**

```python
# scripts/analyze_all_chunks.py
"""
Comprehensive chunk quality analysis across all collections.

Outputs:
1. Chunk statistics (size, metadata completeness)
2. Sample chunks (best/worst/typical from each collection)
3. Metadata consistency report
4. Performance correlation analysis (chunk features vs metrics)
"""

import chromadb
import json
from pathlib import Path
from collections import defaultdict
import statistics

def analyze_collection(client, collection_name, performance_metrics):
    """Analyze a single collection's chunks."""
    coll = client.get_collection(collection_name)
    results = coll.get(limit=None, include=["documents", "metadatas", "embeddings"])

    analysis = {
        "name": collection_name,
        "total_chunks": len(results['ids']),
        "performance": performance_metrics,
        "chunk_stats": {},
        "metadata_stats": {},
        "samples": {}
    }

    # 1. Chunk size statistics
    word_counts = [len(doc.split()) for doc in results['documents']]
    char_counts = [len(doc) for doc in results['documents']]

    analysis["chunk_stats"] = {
        "word_count": {
            "min": min(word_counts),
            "max": max(word_counts),
            "mean": statistics.mean(word_counts),
            "median": statistics.median(word_counts),
            "stdev": statistics.stdev(word_counts) if len(word_counts) > 1 else 0,
            "distribution": {
                "<50 words": sum(1 for w in word_counts if w < 50),
                "50-200 words": sum(1 for w in word_counts if 50 <= w < 200),
                "200-500 words": sum(1 for w in word_counts if 200 <= w < 500),
                "500-1000 words": sum(1 for w in word_counts if 500 <= w < 1000),
                ">1000 words": sum(1 for w in word_counts if w >= 1000)
            }
        },
        "char_count": {
            "min": min(char_counts),
            "max": max(char_counts),
            "mean": statistics.mean(char_counts),
            "median": statistics.median(char_counts)
        }
    }

    # 2. Metadata completeness
    if results['metadatas']:
        all_keys = set()
        for meta in results['metadatas']:
            all_keys.update(meta.keys())

        metadata_completeness = {}
        for key in all_keys:
            completeness = sum(1 for meta in results['metadatas'] if key in meta and meta[key]) / len(results['metadatas'])
            metadata_completeness[key] = completeness

        analysis["metadata_stats"] = {
            "available_fields": sorted(all_keys),
            "completeness": metadata_completeness,
            "missing_critical_fields": [
                field for field in ["document_title", "source_org", "document_type"]
                if metadata_completeness.get(field, 0) < 1.0
            ]
        }

    # 3. Sample chunks (smallest, largest, median, with metadata)
    sorted_by_size = sorted(zip(word_counts, results['ids'], results['documents'], results['metadatas']))

    analysis["samples"] = {
        "smallest": {
            "word_count": sorted_by_size[0][0],
            "id": sorted_by_size[0][1],
            "text_preview": sorted_by_size[0][2][:300],
            "metadata": sorted_by_size[0][3]
        },
        "median": {
            "word_count": sorted_by_size[len(sorted_by_size)//2][0],
            "id": sorted_by_size[len(sorted_by_size)//2][1],
            "text_preview": sorted_by_size[len(sorted_by_size)//2][2][:300],
            "metadata": sorted_by_size[len(sorted_by_size)//2][3]
        },
        "largest": {
            "word_count": sorted_by_size[-1][0],
            "id": sorted_by_size[-1][1],
            "text_preview": sorted_by_size[-1][2][:300],
            "metadata": sorted_by_size[-1][3]
        }
    }

    return analysis


def main():
    # Performance metrics from baseline eval (eval/results/RESULTS.md)
    performance = {
        "ohip_documents": {"recall@50": 0.60, "mrr": 0.600, "faithfulness": 0.90},
        "adp_documents": {"recall@50": 1.00, "mrr": 0.867, "faithfulness": 1.00},
        "odb_documents": {"recall@50": 1.00, "mrr": 1.000, "faithfulness": 1.00},
        "opa_pho_corpus": {"recall@50": 0.80, "mrr": 0.533, "faithfulness": 1.00},
        "opa_cpso_corpus": {"recall@50": 0.80, "mrr": 0.567, "faithfulness": 0.10},
        "opa_cep_corpus": {"recall@50": 0.00, "mrr": 0.000, "faithfulness": 1.00},
        "opa_quality_standards_corpus": {"recall@50": 0.75, "mrr": 0.350, "faithfulness": 0.88},
        "opa_choosing_wisely_corpus": {"recall@50": 0.75, "mrr": 0.375, "faithfulness": 1.00}
    }

    # Connect to both ChromaDB instances
    dr_off_client = chromadb.PersistentClient(path="data/dr_off_agent/chroma")
    dr_opa_client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")

    all_analyses = []

    # Analyze Dr. OFF collections
    for coll_name in ["ohip_documents", "adp_documents", "odb_documents"]:
        print(f"Analyzing {coll_name}...")
        analysis = analyze_collection(dr_off_client, coll_name, performance[coll_name])
        all_analyses.append(analysis)

    # Analyze Dr. OPA collections
    for coll_name in ["opa_pho_corpus", "opa_cpso_corpus", "opa_cep_corpus",
                      "opa_quality_standards_corpus", "opa_choosing_wisely_corpus"]:
        print(f"Analyzing {coll_name}...")
        analysis = analyze_collection(dr_opa_client, coll_name, performance[coll_name])
        all_analyses.append(analysis)

    # Save comprehensive report
    output_path = Path("eval/chunk_analysis_report.json")
    with open(output_path, 'w') as f:
        json.dump(all_analyses, f, indent=2)

    print(f"\nAnalysis complete! Report saved to: {output_path}")

    # Print summary
    print("\n" + "="*80)
    print("CHUNK QUALITY SUMMARY")
    print("="*80)

    for analysis in all_analyses:
        perf = analysis['performance']
        stats = analysis['chunk_stats']['word_count']

        print(f"\n{analysis['name']}:")
        print(f"  Performance: R@50={perf['recall@50']*100:.0f}%, MRR={perf['mrr']:.3f}, Faith={perf['faithfulness']*100:.0f}%")
        print(f"  Chunks: {analysis['total_chunks']} total")
        print(f"  Size: {stats['mean']:.0f} ± {stats['stdev']:.0f} words (min={stats['min']}, max={stats['max']})")
        print(f"  Distribution: {stats['distribution']}")
        print(f"  Metadata fields: {len(analysis['metadata_stats']['available_fields'])}")
        print(f"  Missing critical: {analysis['metadata_stats']['missing_critical_fields']}")


if __name__ == "__main__":
    main()
```

**Run analysis:**
```bash
source /Users/liammckendry/spacy_env/bin/activate
source .env
PYTHONPATH=/Users/liammckendry/health_assistant_retrieval_improvements python scripts/analyze_all_chunks.py
```

---

### Step 2: Correlation Analysis - What Makes Good Chunks?

**Create correlation analysis script:**

```python
# scripts/correlate_chunk_quality_to_performance.py
"""
Analyze correlation between chunk characteristics and retrieval performance.

Questions to answer:
1. Do collections with consistent chunk sizes perform better?
2. Does metadata completeness correlate with Faithfulness?
3. What chunk size range performs best?
4. Do very large chunks (>1000 words) hurt recall?
5. Do very small chunks (<50 words) lack context?
"""

import json
import statistics

def analyze_correlations(report_path):
    with open(report_path) as f:
        analyses = json.load(f)

    print("="*80)
    print("CORRELATION ANALYSIS: Chunk Characteristics vs Performance")
    print("="*80)

    # Collect data points
    data_points = []
    for analysis in analyses:
        stats = analysis['chunk_stats']['word_count']
        perf = analysis['performance']
        meta = analysis['metadata_stats']

        data_points.append({
            "name": analysis['name'],
            "recall": perf['recall@50'],
            "mrr": perf['mrr'],
            "faithfulness": perf['faithfulness'],
            "mean_size": stats['mean'],
            "size_stdev": stats['stdev'],
            "size_cv": stats['stdev'] / stats['mean'] if stats['mean'] > 0 else 0,  # coefficient of variation
            "pct_small": analysis['chunk_stats']['word_count']['distribution'].get('<50 words', 0) / analysis['total_chunks'],
            "pct_large": analysis['chunk_stats']['word_count']['distribution'].get('>1000 words', 0) / analysis['total_chunks'],
            "metadata_completeness": statistics.mean(meta['completeness'].values())
        })

    # Hypothesis 1: Consistent chunk sizes (low CV) → better recall
    print("\n1. Size Consistency vs Recall:")
    for dp in sorted(data_points, key=lambda x: x['size_cv']):
        print(f"   {dp['name'][:30]:30} | CV={dp['size_cv']:.2f} | Recall={dp['recall']*100:.0f}%")

    # Hypothesis 2: Optimal chunk size range
    print("\n2. Mean Chunk Size vs MRR:")
    for dp in sorted(data_points, key=lambda x: x['mrr'], reverse=True):
        print(f"   {dp['name'][:30]:30} | Size={dp['mean_size']:.0f} words | MRR={dp['mrr']:.3f}")

    # Hypothesis 3: Very small chunks hurt performance
    print("\n3. Small Chunks (<50 words) vs Performance:")
    for dp in sorted(data_points, key=lambda x: x['pct_small'], reverse=True):
        print(f"   {dp['name'][:30]:30} | {dp['pct_small']*100:.1f}% small | R@50={dp['recall']*100:.0f}% MRR={dp['mrr']:.3f}")

    # Hypothesis 4: Very large chunks hurt performance
    print("\n4. Large Chunks (>1000 words) vs Performance:")
    for dp in sorted(data_points, key=lambda x: x['pct_large'], reverse=True):
        print(f"   {dp['name'][:30]:30} | {dp['pct_large']*100:.1f}% large | R@50={dp['recall']*100:.0f}% MRR={dp['mrr']:.3f}")

    # Hypothesis 5: Metadata completeness vs Faithfulness
    print("\n5. Metadata Completeness vs Faithfulness:")
    for dp in sorted(data_points, key=lambda x: x['faithfulness']):
        print(f"   {dp['name'][:30]:30} | Meta={dp['metadata_completeness']*100:.0f}% | Faith={dp['faithfulness']*100:.0f}%")

    # Identify patterns
    print("\n" + "="*80)
    print("PATTERNS IDENTIFIED:")
    print("="*80)

    high_performers = [dp for dp in data_points if dp['recall'] >= 0.75 and dp['mrr'] >= 0.5]
    low_performers = [dp for dp in data_points if dp['recall'] < 0.5 or dp['mrr'] < 0.3]

    if high_performers:
        avg_high_size = statistics.mean([dp['mean_size'] for dp in high_performers])
        avg_high_cv = statistics.mean([dp['size_cv'] for dp in high_performers])
        avg_high_meta = statistics.mean([dp['metadata_completeness'] for dp in high_performers])

        print(f"\nHigh Performers (R@50≥75%, MRR≥0.5): {len(high_performers)} collections")
        print(f"  Avg chunk size: {avg_high_size:.0f} words")
        print(f"  Avg size CV: {avg_high_cv:.2f}")
        print(f"  Avg metadata completeness: {avg_high_meta*100:.0f}%")

    if low_performers:
        avg_low_size = statistics.mean([dp['mean_size'] for dp in low_performers])
        avg_low_cv = statistics.mean([dp['size_cv'] for dp in low_performers])
        avg_low_meta = statistics.mean([dp['metadata_completeness'] for dp in low_performers])

        print(f"\nLow Performers (R@50<50% OR MRR<0.3): {len(low_performers)} collections")
        print(f"  Avg chunk size: {avg_low_size:.0f} words")
        print(f"  Avg size CV: {avg_low_cv:.2f}")
        print(f"  Avg metadata completeness: {avg_low_meta*100:.0f}%")


if __name__ == "__main__":
    analyze_correlations("eval/chunk_analysis_report.json")
```

---

### Step 3: Manual Inspection of Failure Cases

**Focus on collections with poor performance:**

1. **CEP Tools (0% Recall)** - Complete failure
   - Extract 10 sample chunks
   - Compare to gold dataset queries
   - Identify why keywords don't match

2. **CPSO Policies (10% Faithfulness)** - Hallucination issue
   - Extract chunks that led to hallucinations
   - Check if chunks lack parent context
   - Verify if chunks are too fragmented

3. **Quality Standards & Choosing Wisely (MRR <0.4)** - Poor ranking
   - Extract top-ranked vs should-be-top-ranked chunks
   - Identify why wrong chunks rank higher
   - Check for semantic coherence

**Create inspection script:**

```python
# scripts/inspect_failure_cases.py
"""
Deep dive into specific failure cases to understand chunking issues.
"""

import chromadb
import json

def inspect_cep_failure():
    """CEP: 0% Recall - why are keywords not matching?"""
    client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
    cep_coll = client.get_collection("opa_cep_corpus")

    # Get all CEP chunks
    results = cep_coll.get(limit=None, include=["documents", "metadatas"])

    print("="*80)
    print("CEP TOOLS FAILURE ANALYSIS")
    print("="*80)

    # Load gold dataset
    with open("eval/gold/dr_opa/cep_tools.jsonl") as f:
        gold = [json.loads(line) for line in f]

    print(f"\nGold dataset queries: {len(gold)}")
    print(f"CEP chunks in DB: {len(results['ids'])}")

    # Show sample query + expected sources
    sample_query = gold[0]
    print(f"\nSample Query: {sample_query['query']}")
    print(f"Expected sources: {sample_query.get('expected_sources', [])}")

    # Show sample CEP chunks
    print(f"\nSample CEP chunks:")
    for i in range(min(3, len(results['ids']))):
        print(f"\n--- Chunk {i+1} ---")
        print(f"ID: {results['ids'][i]}")
        print(f"Text ({len(results['documents'][i].split())} words):")
        print(results['documents'][i][:300] + "...")
        print(f"Metadata: {results['metadatas'][i]}")

    # Identify mismatch
    print("\n" + "="*80)
    print("HYPOTHESIS: Why 0% recall?")
    print("="*80)
    print("1. Check if gold dataset expects full tool names/descriptions")
    print("2. Check if chunks are too fragmented (tool names separated from descriptions)")
    print("3. Check if metadata doesn't match expected source identifiers")


def inspect_cpso_hallucination():
    """CPSO: 10% Faithfulness - why is agent hallucinating?"""
    client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
    cpso_coll = client.get_collection("opa_cpso_corpus")

    results = cpso_coll.get(limit=50, include=["documents", "metadatas"])

    print("\n" + "="*80)
    print("CPSO POLICIES HALLUCINATION ANALYSIS")
    print("="*80)

    # Check chunk sizes
    word_counts = [len(doc.split()) for doc in results['documents']]
    print(f"\nChunk sizes: min={min(word_counts)}, max={max(word_counts)}, avg={sum(word_counts)/len(word_counts):.0f}")

    # Show very small chunks (likely missing context)
    small_chunks = [(i, doc, len(doc.split())) for i, doc in enumerate(results['documents']) if len(doc.split()) < 50]
    if small_chunks:
        print(f"\nVery small chunks (<50 words): {len(small_chunks)}")
        print("Sample:")
        print(f"  {small_chunks[0][2]} words: {small_chunks[0][1][:200]}")

    # Check for parent/section context in metadata
    has_section = sum(1 for meta in results['metadatas'] if 'section_title' in meta or 'section_heading' in meta)
    print(f"\nChunks with section context: {has_section}/{len(results['metadatas'])} ({has_section/len(results['metadatas'])*100:.0f}%)")

    print("\n" + "="*80)
    print("HYPOTHESIS: Why hallucinations?")
    print("="*80)
    print("1. Check if chunks lack parent/section context")
    print("2. Check if very small chunks force agent to infer missing info")
    print("3. Check if chunks split mid-sentence or mid-paragraph")


if __name__ == "__main__":
    inspect_cep_failure()
    inspect_cpso_hallucination()
```

---

## Phase 2: Design Targeted Fixes (AFTER Analysis)

**ONLY after completing Phase 1 analysis, design fixes based on data.**

### Possible Fix Strategies (TBD based on analysis):

1. **If high performers have consistent chunk sizes:**
   - Standardize to 200-500 word range across all collections
   - Add overlap (10-20%) to prevent mid-concept splits

2. **If CEP failure is due to fragmented tool descriptions:**
   - Keep tool name + purpose + usage together in single chunk
   - Add parent/child hierarchy (tool overview → detailed steps)

3. **If CPSO hallucination is due to small chunks:**
   - Increase minimum chunk size to 150 words
   - Add parent context to metadata (section title, broader context)

4. **If metadata completeness correlates with Faithfulness:**
   - Enrich all chunks with: section_title, document_type, effective_date, authority
   - Add citation_ready flag to help agent know what's citable

5. **If Dr. OFF performs well due to structured data:**
   - Extract structural patterns from OHIP/ADP/ODB chunking
   - Apply similar structure to Dr. OPA chunks (normalize document_type, add codes/identifiers)

---

## Acceptance Criteria

### Phase 1 Deliverables:
- ✅ `eval/chunk_analysis_report.json` generated with statistics for all 8 collections
- ✅ Correlation analysis script run, patterns identified
- ✅ Manual inspection of CEP + CPSO failure cases documented
- ✅ Hypothesis document created: "Why does collection X perform poorly?"

### Phase 2 Deliverables (AFTER Phase 1):
- ✅ Data-driven chunking strategy document
- ✅ Remediation plan for each collection (if needed)
- ✅ Target chunk specifications per collection type
- ✅ Implementation plan with expected impact

---

## Success Metrics

**After analysis, we should know:**
1. What chunk size range performs best?
2. Does size consistency matter?
3. What metadata is critical for Faithfulness?
4. Why does CEP have 0% recall? (specific root cause)
5. Why does CPSO cause hallucinations? (specific root cause)
6. Can we apply Dr. OFF's chunking patterns to Dr. OPA?

**Expected outcomes:**
- Data-driven understanding of what makes good chunks
- Targeted fixes for specific collection failures
- Standard chunking strategy for future ingestion
- Foundation for better answer synthesis (Issue #5)

---

## Key Principle

**Don't fix symptoms - fix root causes.**
- Issues #2 and #3 failed because we guessed at solutions
- Phase 1 analysis ensures we understand the problem deeply
- Phase 2 fixes are targeted and evidence-based
- This approach prevents wasted effort on low-impact changes

---

**Start with Phase 1 analysis. Do NOT proceed to implementation until analysis is complete and reviewed.**
