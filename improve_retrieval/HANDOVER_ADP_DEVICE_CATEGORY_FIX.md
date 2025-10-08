# Handover: Fix ADP device_category Metadata

**Date:** October 8, 2025
**Priority:** High
**Estimated Effort:** 30 minutes
**Type:** Metadata Update (No Re-ingestion Required)

---

## Problem Statement

The ADP (Assistive Devices Program) collection has **214 documents** in ChromaDB, but all have `device_category: 'None'`. This breaks device-specific queries in the `adp_get` tool.

**Current state:**
```python
device_category = metadata.get('device_category')  # Returns None
# Causes TypeError: 'in <string>' requires string as left operand, not NoneType
```

**Impact:** Users cannot filter or search by device category (mobility devices, hearing aids, insulin pumps, etc.)

---

## Good News: Data Already Exists!

The category information is **already captured** in the `adp_doc` metadata field:

```
Distribution of adp_doc values (214 total documents):
  core_manual:       74 docs
  grants:            32 docs
  maxillofacial:     20 docs
  mobility:          16 docs
  respiratory:       16 docs
  prosthesis:        13 docs
  glucose_monitoring: 12 docs
  insulin_pump:      10 docs
  visual_aids:        9 docs
  hearing_devices:    7 docs
  comm_aids:          5 docs
```

**We just need to map these to human-readable device_category values!**

---

## Solution: Update Metadata In-Place

Create a script to:
1. Load the ADP collection from ChromaDB
2. Map `adp_doc` values to proper `device_category` strings
3. Update each document's metadata with the new field
4. Verify the update

**No re-ingestion needed** - ChromaDB supports metadata updates.

---

## Implementation

### Step 1: Create the Update Script

**File:** `scripts/update_adp_device_categories.py`

```python
"""
Update device_category metadata in ADP ChromaDB collection.

This script reads the existing adp_doc field and maps it to
human-readable device_category values.
"""
import chromadb
from datetime import datetime
from typing import Dict

# ChromaDB path
CHROMA_PATH = "data/dr_off_agent/processed/dr_off/chroma"
COLLECTION_NAME = "adp_documents"


def get_device_category_mapping() -> Dict[str, str]:
    """
    Map adp_doc internal names to human-readable device categories.

    Based on filename patterns from:
    data/dr_off_agent/ontario/adp/moh-adp-policy-and-administration-manual-*.pdf
    """
    return {
        'mobility': 'Mobility Devices',
        'hearing_devices': 'Hearing Devices',
        'insulin_pump': 'Insulin Pump',
        'comm_aids': 'Communication Aids',
        'grants': 'Grants',
        'maxillofacial': 'Maxillofacial Prosthetics',
        'respiratory': 'Respiratory Equipment',
        'prosthesis': 'Limb Prosthesis',
        'glucose_monitoring': 'Glucose Monitoring Systems',
        'visual_aids': 'Visual Aids',
        'core_manual': 'General ADP Policy',  # Core manual applies to all
        # Add more mappings as needed
    }


def update_device_categories(dry_run: bool = True):
    """
    Update device_category metadata for all ADP documents.

    Args:
        dry_run: If True, only print what would be updated without modifying data
    """
    print("="*80)
    print("ADP Device Category Metadata Update")
    print("="*80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Path: {CHROMA_PATH}")
    print()

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    print(f"✓ Connected to collection: {collection.name}")
    print(f"  Total documents: {collection.count()}")
    print()

    # Get all documents
    results = collection.get(include=['metadatas'])

    # Get mapping
    category_mapping = get_device_category_mapping()

    # Track statistics
    stats = {
        'total': len(results['ids']),
        'updated': 0,
        'skipped': 0,
        'unknown_types': set()
    }

    # Process each document
    updates_to_apply = []

    for doc_id, metadata in zip(results['ids'], results['metadatas']):
        adp_doc = metadata.get('adp_doc', '')
        current_category = metadata.get('device_category')

        # Map to device category
        device_category = category_mapping.get(adp_doc)

        if device_category:
            # Check if update needed
            if current_category != device_category:
                stats['updated'] += 1
                updates_to_apply.append({
                    'id': doc_id,
                    'adp_doc': adp_doc,
                    'old_category': current_category,
                    'new_category': device_category,
                    'metadata': metadata
                })
            else:
                stats['skipped'] += 1
        else:
            # Unknown adp_doc type
            stats['unknown_types'].add(adp_doc)
            print(f"⚠️  Unknown adp_doc type: '{adp_doc}' (document {doc_id})")

    # Print summary
    print("\n" + "="*80)
    print("Update Summary")
    print("="*80)
    print(f"Total documents:     {stats['total']}")
    print(f"To be updated:       {stats['updated']}")
    print(f"Already correct:     {stats['skipped']}")
    print(f"Unknown types:       {len(stats['unknown_types'])}")
    print()

    if stats['unknown_types']:
        print("Unknown adp_doc types found:")
        for unknown in sorted(stats['unknown_types']):
            print(f"  - {unknown}")
        print()

    # Show sample updates
    if updates_to_apply:
        print("Sample updates (first 5):")
        for update in updates_to_apply[:5]:
            print(f"  {update['id'][:20]}...")
            print(f"    adp_doc: {update['adp_doc']}")
            print(f"    device_category: {update['old_category']} → {update['new_category']}")
        print()

    # Apply updates if not dry run
    if not dry_run and updates_to_apply:
        print("="*80)
        print("Applying Updates...")
        print("="*80)

        for i, update in enumerate(updates_to_apply, 1):
            # Update metadata
            new_metadata = update['metadata'].copy()
            new_metadata['device_category'] = update['new_category']
            new_metadata['category_updated_at'] = datetime.now().isoformat()

            # Update in ChromaDB
            collection.update(
                ids=[update['id']],
                metadatas=[new_metadata]
            )

            if i % 50 == 0:
                print(f"  Updated {i}/{len(updates_to_apply)} documents...")

        print(f"\n✓ Successfully updated {len(updates_to_apply)} documents")
        print(f"  Timestamp: {datetime.now().isoformat()}")

        # Verify updates
        print("\n" + "="*80)
        print("Verification")
        print("="*80)

        # Check a few random updates
        verify_ids = [updates_to_apply[0]['id'], updates_to_apply[-1]['id']]
        verify_results = collection.get(
            ids=verify_ids,
            include=['metadatas']
        )

        print("Checking updated documents:")
        for doc_id, metadata in zip(verify_results['ids'], verify_results['metadatas']):
            category = metadata.get('device_category')
            adp_doc = metadata.get('adp_doc')
            print(f"  ✓ {doc_id[:20]}... → device_category: '{category}' (from adp_doc: '{adp_doc}')")

    elif dry_run:
        print("="*80)
        print("⚠️  DRY RUN MODE - No changes applied")
        print("="*80)
        print("To apply updates, run with --apply flag:")
        print("  python scripts/update_adp_device_categories.py --apply")
    else:
        print("\n✓ No updates needed - all documents already have correct device_category")

    print("\n" + "="*80)
    print("Update Complete")
    print("="*80)


if __name__ == '__main__':
    import sys

    # Check for --apply flag
    dry_run = '--apply' not in sys.argv

    if dry_run:
        print("\n⚠️  Running in DRY RUN mode - no changes will be made")
        print("To apply changes, add --apply flag\n")

    update_device_categories(dry_run=dry_run)
```

---

### Step 2: Run the Script

**First, dry run to preview changes:**
```bash
python scripts/update_adp_device_categories.py
```

**Then apply updates:**
```bash
python scripts/update_adp_device_categories.py --apply
```

---

### Step 3: Verify the Fix

Create test script: `scripts/verify_adp_categories.py`

```python
"""Verify device_category metadata is populated."""
import chromadb
from collections import Counter

CHROMA_PATH = "data/dr_off_agent/processed/dr_off/chroma"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection("adp_documents")

results = collection.get(include=['metadatas'])

print("="*80)
print("ADP device_category Verification")
print("="*80)

# Count device_category values
category_counts = Counter()
none_count = 0

for metadata in results['metadatas']:
    category = metadata.get('device_category')
    if category and category != 'None':
        category_counts[category] += 1
    else:
        none_count += 1

print(f"Total documents: {len(results['metadatas'])}")
print(f"\nDevice category distribution:")
for category, count in category_counts.most_common():
    print(f"  {category:35s} {count:3d} docs")

print(f"\n{'None/Empty:':35s} {none_count:3d} docs")

if none_count == 0:
    print("\n✅ SUCCESS: All documents have device_category populated!")
else:
    print(f"\n⚠️  WARNING: {none_count} documents still have empty device_category")
```

Run verification:
```bash
python scripts/verify_adp_categories.py
```

**Expected output:**
```
================================================================================
ADP device_category Verification
================================================================================
Total documents: 214

Device category distribution:
  General ADP Policy                   74 docs
  Grants                               32 docs
  Maxillofacial Prosthetics            20 docs
  Mobility Devices                     16 docs
  Respiratory Equipment                16 docs
  Limb Prosthesis                      13 docs
  Glucose Monitoring Systems           12 docs
  Insulin Pump                         10 docs
  Visual Aids                           9 docs
  Hearing Devices                       7 docs
  Communication Aids                    5 docs

None/Empty:                            0 docs

✅ SUCCESS: All documents have device_category populated!
```

---

### Step 4: Update adp.py to Handle Categories

The fix in `src/ai_agents/dr_off_agent/mcp/tools/adp.py:491,499` should now work correctly:

```python
device_category = device.get("category") or ""  # Now returns actual category

# This comparison will now work:
if device_type in scenario or (device_category and device_category in scenario):
    # Match found
```

**Test the tool:**
```python
# Test queries that should now work:
await adp_get.fn(query="power wheelchair")  # Mobility Devices
await adp_get.fn(query="hearing aid")       # Hearing Devices
await adp_get.fn(query="insulin pump")      # Insulin Pump
```

---

## Category Mapping Reference

| `adp_doc` (internal)      | `device_category` (display)     | Document Count |
|---------------------------|---------------------------------|----------------|
| `core_manual`             | General ADP Policy              | 74             |
| `grants`                  | Grants                          | 32             |
| `maxillofacial`           | Maxillofacial Prosthetics       | 20             |
| `mobility`                | Mobility Devices                | 16             |
| `respiratory`             | Respiratory Equipment           | 16             |
| `prosthesis`              | Limb Prosthesis                 | 13             |
| `glucose_monitoring`      | Glucose Monitoring Systems      | 12             |
| `insulin_pump`            | Insulin Pump                    | 10             |
| `visual_aids`             | Visual Aids                     | 9              |
| `hearing_devices`         | Hearing Devices                 | 7              |
| `comm_aids`               | Communication Aids              | 5              |

---

## Benefits of This Approach

✅ **No re-ingestion required** - Updates metadata in-place
✅ **Fast** - Updates 214 documents in <5 seconds
✅ **Reversible** - Original `adp_doc` field preserved
✅ **Dry run mode** - Preview changes before applying
✅ **Verification** - Built-in checks to confirm success
✅ **Timestamped** - Adds `category_updated_at` for audit trail

---

## Alternative: If You Prefer Re-ingestion

If you want to fix this at the source (ingestion script), find the ingestion script:

```bash
find . -name "*ingest*" -type f | grep -i adp
```

Then modify the ingestion to set `device_category` metadata from the `adp_doc` field during initial processing.

**But the update script is much faster for immediate fix!**

---

## Testing After Update

Run the direct MCP tool test:
```bash
pytest tests/test_mcp_handlers_direct.py::test_dr_off_tools -v
```

The `adp_get` tool should now:
- ✅ Not crash with TypeError
- ✅ Return results filtered by device_category
- ✅ Show proper category in metadata

---

## Success Criteria

✅ All 214 documents have `device_category` populated
✅ No documents have `device_category: 'None'`
✅ Categories map correctly to `adp_doc` values
✅ `adp_get` tool returns category-filtered results
✅ Tests pass without TypeError

---

**Status:** Ready to implement
**Time to complete:** ~30 minutes
**Risk level:** Low (dry run first, no data loss)
