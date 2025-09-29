# Database and Vector Store Migration to Railway

## Overview
This document describes the migration of SQLite databases and ChromaDB vector stores from local development to Railway cloud platform for the Ontario Healthcare AI Agents Registry.

**Migration Date**: September 29, 2025  
**Target Platform**: Railway (https://healthassistant-production-3613.up.railway.app)

## Migration Summary

### Databases Migrated

#### SQLite Databases (5 total)
1. **OHIP Database** (`data/ohip.db` → `/app/data/ohip.db`)
   - 14 tables, 25,482 rows
   - Contains OHIP fee schedules and billing rules
   
2. **Dr. OFF Conversations** (`data/dr_off_conversations.db` → `/app/data/dr_off_conversations.db`)
   - 2 tables, 55 rows
   - Agent session tracking
   
3. **Dr. OPA Conversations** (`data/dr_opa_conversations.db` → `/app/data/dr_opa_conversations.db`)
   - 2 tables, 5 rows
   - Agent session tracking
   
4. **Orchestrator Conversations** (`data/orchestrator_conversations.db` → `/app/data/orchestrator_conversations.db`)
   - 2 tables, 171 rows
   - Multi-agent orchestration logs
   
5. **Dr. OPA Agent Database** (`data/dr_opa_agent/opa.db` → `/app/data/dr_opa_agent/opa.db`)
   - 3 tables, 506 rows
   - OPA documents and sections

#### ChromaDB Vector Stores (6 collections, 18,963 documents)

**Dr. OFF Collections** (Source: `data/dr_off_agent/processed/dr_off/chroma/`)
1. **ohip_documents**: 6,983 documents - OHIP fee codes and billing information
2. **odb_documents**: 10,815 documents - Ontario Drug Benefit formulary data  
3. **adp_documents**: 610 documents - Assistive Devices Program policies

**Dr. OPA Collections** (Source: `data/dr_opa_agent/chroma/`)
4. **opa_cpso_corpus**: 366 documents - CPSO policies and advice
5. **opa_pho_corpus**: 132 documents - Public Health Ontario IPAC guidance
6. **opa_cep_corpus**: 57 documents - Centre for Effective Practice clinical tools

## Migration Approach

### Phase 1: Admin Endpoints Setup
Created admin endpoints on Railway to receive migrated data:
- `/admin/load-database` - SQLite database import
- `/admin/direct-chroma-upload` - ChromaDB collection import
- `/admin/chroma-collections` - List collections
- `/admin/database-status` - Check database status

**Implementation Files**:
- `src/web/api/admin_endpoints.py` - Main admin endpoints
- `src/web/api/simple_chroma_endpoint.py` - Simplified ChromaDB upload (bypasses complex ingesters)

### Phase 2: Database Migration Script
**Script**: `scripts/migrate_chroma_collections.py`

Key features:
- Exports local ChromaDB collections with metadata preservation
- Handles large collections (10K+ documents) with proper timeouts
- Provides detailed logging to `chroma_migration.log`
- Includes retry logic and error handling

### Phase 3: Quality Verification
**Script**: `scripts/verify_local_chroma.py`

Verified:
- Document content integrity (no empty documents)
- Metadata structure consistency
- ID uniqueness (no duplicates)
- Proper field population

## Technical Implementation

### ChromaDB Migration Process
```python
# Extract from local ChromaDB
client = chromadb.PersistentClient(path=source_path)
collection = client.get_collection(collection_name)
results = collection.get(include=["documents", "metadatas", "embeddings"])

# Upload to Railway
response = requests.post(
    f"{railway_url}/admin/direct-chroma-upload",
    json={
        "collection_name": collection_name,
        "documents": documents,
        "metadatas": metadatas,
        "ids": ids
    }
)
```

### Key Design Decisions

1. **Direct Upload Approach**: Created simplified endpoints to bypass complex ingester classes with import issues
2. **Delete and Recreate**: Collections are deleted and recreated on Railway to avoid duplicates
3. **Embedding Regeneration**: Railway regenerates embeddings using OpenAI API for consistency
4. **Batch Processing**: Documents uploaded in batches to handle large collections

## Migration Results

### Performance Metrics
- **Total Migration Time**: ~4 minutes 6 seconds
- **Average Speed**: 77 documents/second
- **Largest Collection** (odb_documents): 114.5 seconds

### Data Integrity
- ✅ All 18,963 documents successfully migrated
- ✅ Metadata structure preserved
- ✅ No data loss or corruption
- ✅ IDs maintained for reference consistency

## Railway Deployment Configuration

### Environment Variables Required
```bash
OPENAI_API_KEY=<key>           # For embedding generation
ANTHROPIC_API_KEY=<key>        # For Claude API
LANGFUSE_PUBLIC_KEY=<key>      # For observability
LANGFUSE_SECRET_KEY=<key>      # For observability
```

### Volume Mounts
- `/app/data/` - Persistent storage for SQLite databases
- `/app/data/chroma/` - ChromaDB vector store persistence

## Verification Commands

Check migration status:
```bash
# List ChromaDB collections
curl https://healthassistant-production-3613.up.railway.app/admin/chroma-collections

# Check database status  
curl https://healthassistant-production-3613.up.railway.app/admin/database-status
```

## Files to Maintain

### Migration Scripts (kept for reference)
- `scripts/migrate_chroma_collections.py` - Main migration script
- `scripts/verify_local_chroma.py` - Quality verification script
- `chroma_migration.log` - Migration execution log

### Admin Endpoints
- `src/web/api/admin_endpoints.py` - Database/ChromaDB admin endpoints
- `src/web/api/simple_chroma_endpoint.py` - Direct ChromaDB upload endpoint

## Cleanup Performed

Removed temporary directories and files:
- `upload_dbs_only/`, `upload_to_railway/`, `railway_upload/`, `data_exports/`, `upload_minimal/`
- Various test migration scripts (`migrate_to_railway*.py`, `direct_chroma_upload.py`, etc.)
- Temporary Dockerfiles and test scripts

## Troubleshooting

### Common Issues and Solutions

1. **Import Errors**: Use simple_chroma_endpoint.py which bypasses complex ingester imports
2. **Timeout Errors**: Increase timeout to 1200s for large collections
3. **Duplicate IDs**: Use hash-based ID generation for uniqueness
4. **Empty Metadata Fields**: These are optional fields, not critical for search/retrieval

## Next Steps

1. Monitor Railway application performance with migrated data
2. Set up automated backups for Railway databases
3. Implement health checks for data integrity
4. Consider incremental sync for future updates