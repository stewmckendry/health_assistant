# ChromaDB Collections Changelog

This file tracks all changes to ChromaDB vector collections (both local and Railway).

Format:
```
## YYYY-MM-DD - Collection Name
**Environment:** [Local | Railway | Both]
**Action:** [Created | Updated | Deleted | Uploaded]
**Reason:** Brief description
**Details:**
- Document count before: X
- Document count after: Y
- Tools/Sources: List
- Commit: git hash (if applicable)
```

---

## 2025-10-14 - opa_cep_corpus

**Environment:** Both (Local + Railway)
**Action:** Updated and Uploaded
**Reason:** Fix ChromaDB `$or` filter bug causing empty tool results

**Details:**
- **Document count:** 639 (312 parent + 327 child chunks)
- **Tools:** 46 CEP clinical tools from tools.cep.health
- **Changes made:**
  - Fixed `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_helpers.py:167-179`
  - ChromaDB `$or` operator requires ≥2 items; added conditional logic for single-tool queries
  - Local collection last updated: 2025-10-14 12:24
  - Uploaded to Railway: 2025-10-14
- **Railway Collection ID:** `5739b3a8-a9b3-4f86-9a6d-e8c563ce94c5` (new)
- **Previous Railway Collection ID:** `4a762d92-9dac-4ae2-a30e-449c3d3c835a` (deleted)
- **Metadata fields verified:** 10 fields including `chunk_type`, `is_overview`, `section_path`, `source_url`, `topics`
- **Upload method:** `python scripts/upload_collections_to_railway.py --single opa_cep_corpus`
- **Git commits:**
  - `a8229f3` - "fix: Resolve orchestrator empty tool results through ChromaDB metadata and filter fixes"
  - Script enhancement: Added `--single` flag for individual collection uploads

**Sample tools included:**
- Managing Heart Failure in Primary Care
- Anxiety and Depression
- Type 2 Diabetes (insulin therapy)
- Opioid Use Disorder (OUD)
- MAID (Medical Assistance in Dying) - Tracks 1 & 2
- Mental Health, COPD, Falls Prevention, Menopause Management, etc.

**Verification:**
- ✅ All 46 tool URLs present
- ✅ Parent/child chunking structure intact
- ✅ Section paths and titles preserved
- ✅ Topics taxonomy applied
- ✅ Overview chunks flagged correctly
- ✅ Railway upload successful (639 docs loaded)

---

## Collection Inventory (as of 2025-10-14)

### Dr. OPA Collections (Local + Railway)
| Collection | Documents | Status | Last Updated |
|------------|-----------|--------|--------------|
| opa_cep_corpus | 639 | ✅ Synced | 2025-10-14 |
| opa_cpso_corpus | 366 (local) / 325 (railway) | ⚠️ Out of sync | Unknown |
| opa_quality_standards_corpus | 340 | ✅ Synced | Unknown |
| opa_choosing_wisely_corpus | 544 (local) / 295 (railway) | ⚠️ Out of sync | Unknown |
| opa_pho_corpus | 132 | ✅ Synced | Unknown |

### Dr. OFF Collections (Local + Railway)
| Collection | Documents | Status | Last Updated |
|------------|-----------|--------|--------------|
| ohip_documents | 379 | ✅ Synced | Unknown |
| adp_documents | 214 | ✅ Synced | Unknown |
| odb_documents | 3358 | ✅ Synced | Unknown |

**Note:** Collections marked "Out of sync" have different document counts between local and Railway.

---

## Template for Future Entries

```markdown
## YYYY-MM-DD - collection_name

**Environment:** [Local | Railway | Both]
**Action:** [Created | Updated | Deleted | Uploaded]
**Reason:** Brief description

**Details:**
- Document count before: X
- Document count after: Y
- Changes made: List of changes
- Railway Collection ID: UUID (if applicable)
- Upload method: Command or script used
- Git commit: hash - "message"
- Verification: What was checked

---
```
