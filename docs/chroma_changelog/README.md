# ChromaDB Collections Changelog

## Purpose

This directory tracks all changes to ChromaDB vector collections across both local development and Railway production environments. This helps maintain data integrity, track updates, and debug issues.

## Files

- **CHANGELOG.md** - Chronological log of all collection updates
- **README.md** - This file (documentation)

## When to Update

Add an entry to CHANGELOG.md whenever you:

1. **Create** a new collection
2. **Update** an existing collection (reingest, add documents, fix metadata)
3. **Delete** a collection
4. **Upload** local changes to Railway
5. **Download** Railway data to local
6. **Fix** a data quality issue (missing metadata, corrupted chunks, etc.)

## How to Update

1. Copy the template from CHANGELOG.md
2. Fill in all required fields:
   - Date (YYYY-MM-DD)
   - Collection name
   - Environment (Local | Railway | Both)
   - Action (Created | Updated | Deleted | Uploaded)
   - Reason (brief description)
   - Details (counts, changes, verification)
3. Add verification steps taken
4. Include git commit hash if code changes were involved

## Collection Naming Convention

### Dr. OPA (Ontario Physicians Assistant)
- `opa_cep_corpus` - Centre for Effective Practice clinical tools
- `opa_cpso_corpus` - College of Physicians and Surgeons of Ontario policies
- `opa_quality_standards_corpus` - Ontario Health quality standards
- `opa_choosing_wisely_corpus` - Choosing Wisely recommendations
- `opa_pho_corpus` - Public Health Ontario documents

### Dr. OFF (Ontario Funding & Formulary)
- `ohip_documents` - OHIP schedule of benefits (billing codes)
- `adp_documents` - Assistive Devices Program documents
- `odb_documents` - Ontario Drug Benefit formulary

## Common Operations

### Check Local Collection Stats
```bash
source ~/spacy_env/bin/activate
python -c "
import chromadb
client = chromadb.PersistentClient(path='data/dr_opa_agent/chroma')
collections = client.list_collections()
for c in collections:
    print(f'{c.name}: {client.get_collection(c.name).count()} docs')
"
```

### Check Railway Collection Stats
```bash
source ~/spacy_env/bin/activate
python -c "
import requests
r = requests.get('https://healthassistant-production-3613.up.railway.app/admin/chroma-stats')
import json
print(json.dumps(r.json(), indent=2))
"
```

### Upload Single Collection to Railway
```bash
source ~/spacy_env/bin/activate
python scripts/upload_collections_to_railway.py --single <collection_name>
```

### Upload All Collections to Railway
```bash
source ~/spacy_env/bin/activate
python scripts/upload_collections_to_railway.py
```

## Sync Status Monitoring

The CHANGELOG.md file includes a "Collection Inventory" section that tracks:
- Current document counts (local vs Railway)
- Sync status (✅ Synced | ⚠️ Out of sync)
- Last updated date

**Update this section whenever:**
- You verify sync status
- You notice discrepancies between environments
- You complete a large update/upload

## Troubleshooting

### Collections Out of Sync
If local and Railway document counts differ:
1. Check CHANGELOG.md for recent updates
2. Verify which version has the correct data
3. Re-upload if Railway is outdated: `python scripts/upload_collections_to_railway.py --single <collection_name>`
4. Or re-download if local is outdated: Use download script

### Missing Metadata
If metadata is incomplete:
1. Check ingestion script that created the collection
2. Fix metadata in ingestion script
3. Re-run ingestion locally
4. Verify metadata with sample queries
5. Upload to Railway if verified
6. Document in CHANGELOG.md

### Empty Query Results
If queries return empty results:
1. Check collection exists and has documents
2. Verify metadata structure (nested vs flat)
3. Check where clause syntax (ChromaDB `$or` requires ≥2 items)
4. Test with direct ChromaDB queries
5. Document fix in CHANGELOG.md

## Best Practices

1. **Always verify before uploading** - Check local collection quality first
2. **Document all changes** - Even small fixes should be logged
3. **Include git commits** - Link code changes to data changes
4. **Track collection IDs** - Railway assigns new UUID on recreate
5. **Note verification steps** - What you checked to confirm success
6. **Update inventory table** - Keep sync status current
