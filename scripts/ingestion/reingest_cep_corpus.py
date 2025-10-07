#!/usr/bin/env python3
"""Delete and re-ingest CEP corpus with updated extractor."""
import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_agents.dr_opa_agent.ingestion.cep.ingester_v2 import CEPIngesterV2

def delete_cep_collection():
    """Delete existing CEP collection."""
    print("="*80)
    print("STEP 1: DELETE EXISTING CEP COLLECTION")
    print("="*80)

    chroma_path = "data/dr_opa_agent/chroma"
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False)
    )

    collection_name = "opa_cep_corpus"

    try:
        # Check if collection exists
        existing = client.get_collection(collection_name)
        count = existing.count()
        print(f"\n✓ Found existing collection: {collection_name}")
        print(f"  Current document count: {count}")

        # Delete it
        print(f"\n🗑️  Deleting collection...")
        client.delete_collection(collection_name)
        print(f"✅ Collection deleted successfully")

        return True

    except Exception as e:
        if "does not exist" in str(e):
            print(f"\n⚠️  Collection {collection_name} does not exist (already clean)")
            return True
        else:
            print(f"\n❌ Error deleting collection: {e}")
            return False


def reingest_cep_corpus():
    """Re-ingest CEP corpus with updated extractor."""
    print("\n" + "="*80)
    print("STEP 2: RE-INGEST CEP CORPUS")
    print("="*80)

    raw_dir = Path("data/dr_opa_agent/raw/cep")

    # Find all HTML files
    html_files = list(raw_dir.glob("*.html"))
    print(f"\nFound {len(html_files)} HTML files to ingest")

    # Create ingester
    print("\n🔧 Initializing ingester...")
    ingester = CEPIngesterV2(chroma_path="data/dr_opa_agent/chroma")

    # Ingest each file
    success_count = 0
    error_count = 0

    print("\n📥 Starting ingestion...\n")

    for i, html_file in enumerate(html_files, 1):
        tool_slug = html_file.stem

        try:
            print(f"  [{i}/{len(html_files)}] Ingesting: {tool_slug}...", end=" ")
            result = ingester.ingest_tool_from_html(tool_slug)

            chunks_created = result.get('chunks_created', 0)
            print(f"✓ ({chunks_created} chunks)")
            success_count += 1

        except Exception as e:
            print(f"✗ Error: {e}")
            error_count += 1

    print(f"\n{'='*80}")
    print(f"INGESTION COMPLETE")
    print(f"{'='*80}")
    print(f"  Success: {success_count}/{len(html_files)} tools")
    print(f"  Errors:  {error_count}/{len(html_files)} tools")

    return success_count, error_count


def validate_collection():
    """Validate the new collection quality."""
    print("\n" + "="*80)
    print("STEP 3: VALIDATE COLLECTION QUALITY")
    print("="*80)

    chroma_path = "data/dr_opa_agent/chroma"
    client = chromadb.PersistentClient(path=chroma_path)

    collection = client.get_collection("opa_cep_corpus")
    total_count = collection.count()

    print(f"\n📊 Collection Statistics:")
    print(f"  Total chunks: {total_count}")

    # Sample some chunks to check quality
    sample_size = min(100, total_count)
    results = collection.get(
        limit=sample_size,
        include=['metadatas', 'documents']
    )

    # Analyze chunk sizes
    word_counts = [len(doc.split()) for doc in results['documents']]
    char_counts = [len(doc) for doc in results['documents']]

    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    min_words = min(word_counts) if word_counts else 0
    max_words = max(word_counts) if word_counts else 0

    avg_chars = sum(char_counts) / len(char_counts) if char_counts else 0

    print(f"\n📝 Content Density (sample of {sample_size} chunks):")
    print(f"  Average words per chunk: {avg_words:.0f}")
    print(f"  Average chars per chunk: {avg_chars:.0f}")
    print(f"  Min words: {min_words}")
    print(f"  Max words: {max_words}")

    # Check chunk types
    from collections import Counter
    chunk_types = Counter()
    for metadata in results['metadatas']:
        chunk_type = metadata.get('chunk_type', 'unknown')
        chunk_types[chunk_type] += 1

    print(f"\n📦 Chunk Type Distribution:")
    for chunk_type, count in chunk_types.most_common():
        pct = count / len(results['metadatas']) * 100
        print(f"  {chunk_type}: {count} ({pct:.1f}%)")

    # Check section titles
    section_titles = Counter()
    for metadata in results['metadatas']:
        section = metadata.get('section_title', 'unknown')
        section_titles[section] += 1

    print(f"\n📋 Top 10 Section Titles:")
    for section, count in section_titles.most_common(10):
        print(f"  {section[:50]:50} {count:3d}")

    # Sample some content
    print(f"\n🔍 Sample Chunks:")
    for i in range(min(3, len(results['documents']))):
        doc = results['documents'][i]
        metadata = results['metadatas'][i]

        print(f"\n  Chunk {i+1}:")
        print(f"    Tool: {metadata.get('title', 'N/A')}")
        print(f"    Section: {metadata.get('section_title', 'N/A')}")
        print(f"    Type: {metadata.get('chunk_type', 'N/A')}")
        print(f"    Words: {len(doc.split())}")
        print(f"    Preview: {doc[:150]}...")

    # Quality checks
    print(f"\n✅ QUALITY CHECKS:")

    checks_passed = 0
    checks_total = 0

    # Check 1: Average chunk size should be substantial
    checks_total += 1
    if avg_words >= 200:
        print(f"  ✓ Chunk density: {avg_words:.0f} words (target: ≥200)")
        checks_passed += 1
    else:
        print(f"  ✗ Chunk density: {avg_words:.0f} words (target: ≥200) - TOO SMALL")

    # Check 2: Should have both parent and child chunks
    checks_total += 1
    if 'parent' in chunk_types and 'child' in chunk_types:
        print(f"  ✓ Both parent and child chunks present")
        checks_passed += 1
    else:
        print(f"  ✗ Missing chunk types (need both parent and child)")

    # Check 3: No empty chunks
    checks_total += 1
    empty_count = sum(1 for wc in word_counts if wc < 20)
    if empty_count == 0:
        print(f"  ✓ No empty/trivial chunks")
        checks_passed += 1
    else:
        print(f"  ✗ Found {empty_count} chunks with <20 words")

    # Check 4: Varied section titles (not all References/Acknowledgments)
    checks_total += 1
    boilerplate = sum(count for section, count in section_titles.items()
                     if any(term in section.lower() for term in ['reference', 'acknowledgment', 'legal']))
    boilerplate_pct = boilerplate / sum(section_titles.values()) * 100 if section_titles else 0

    if boilerplate_pct < 30:
        print(f"  ✓ Boilerplate content: {boilerplate_pct:.0f}% (target: <30%)")
        checks_passed += 1
    else:
        print(f"  ✗ Boilerplate content: {boilerplate_pct:.0f}% (target: <30%) - TOO HIGH")

    print(f"\n{'='*80}")
    print(f"Quality Score: {checks_passed}/{checks_total} checks passed")

    if checks_passed == checks_total:
        print("✅ EXCELLENT: Collection quality is high!")
    elif checks_passed >= checks_total * 0.75:
        print("✓ GOOD: Collection quality is acceptable")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Collection quality is low")

    return checks_passed, checks_total


def main():
    """Main workflow."""
    print("\n" + "="*80)
    print("CEP CORPUS RE-INGESTION")
    print("="*80)

    # Step 1: Delete old collection
    if not delete_cep_collection():
        print("\n❌ Failed to delete collection, aborting")
        return

    # Step 2: Re-ingest with updated extractor
    success, errors = reingest_cep_corpus()

    if errors > 0:
        print(f"\n⚠️  Some ingestion errors occurred ({errors} tools failed)")

    if success == 0:
        print("\n❌ No tools ingested successfully, aborting validation")
        return

    # Step 3: Validate quality
    checks_passed, checks_total = validate_collection()

    print("\n" + "="*80)
    print("ALL STEPS COMPLETE")
    print("="*80)
    print(f"  ✓ Collection deleted and recreated")
    print(f"  ✓ {success} tools ingested successfully")
    print(f"  ✓ Quality validation: {checks_passed}/{checks_total} checks passed")

    if checks_passed == checks_total:
        print("\n✅ Ready to run evaluations!")
    else:
        print("\n⚠️  Consider reviewing quality issues before evaluating")


if __name__ == "__main__":
    main()
