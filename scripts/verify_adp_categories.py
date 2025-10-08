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
