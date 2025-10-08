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
