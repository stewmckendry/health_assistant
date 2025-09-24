# Dr. OPA Data Model Documentation

## Overview

The Dr. OPA data model is designed to support efficient storage, retrieval, and management of Ontario practice guidance documents. It implements a hierarchical chunking strategy with comprehensive metadata tracking and automatic supersession management.

## Database Schema

### 1. opa_documents

Primary table for document metadata and versioning.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| document_id | TEXT | Unique identifier (hash of URL) | PRIMARY KEY |
| source_org | TEXT | Source organization identifier | NOT NULL |
| source_url | TEXT | Original document URL | UNIQUE, NOT NULL |
| title | TEXT | Document title | - |
| document_type | TEXT | Type classification | - |
| effective_date | TEXT | When guidance becomes effective | ISO format |
| updated_date | TEXT | Last update date | ISO format |
| published_date | TEXT | Original publication date | ISO format |
| topics | TEXT | JSON array of topic tags | JSON format |
| policy_level | TEXT | CPSO: expectation/advice/general | - |
| content_hash | TEXT | SHA-256 hash of content | - |
| metadata_json | TEXT | Additional metadata | JSON format |
| is_superseded | BOOLEAN | Supersession flag | DEFAULT 0 |
| superseded_by | TEXT | Reference to newer document | FOREIGN KEY |
| superseded_date | TEXT | When marked as superseded | ISO format |
| ingested_at | TEXT | Ingestion timestamp | NOT NULL, ISO format |

**Indexes:**
- `idx_documents_org` on `source_org`
- `idx_documents_type` on `document_type`
- `idx_documents_effective` on `effective_date`
- `idx_documents_superseded` on `is_superseded`

**Example Record:**
```json
{
  "document_id": "a7f3b2c9d8e4f1a6",
  "source_org": "cpso",
  "source_url": "https://www.cpso.on.ca/policies/continuity-care",
  "title": "Continuity of Care",
  "document_type": "policy",
  "effective_date": "2023-06-01",
  "updated_date": "2023-05-15",
  "published_date": "2019-03-01",
  "topics": ["continuity_care", "transfer", "referral"],
  "policy_level": "expectation",
  "content_hash": "3f2b8a9c7d6e5f4a3b2c1d0e9f8a7b6c",
  "is_superseded": false,
  "superseded_by": null,
  "ingested_at": "2024-01-15T10:30:00Z"
}
```

### 2. opa_sections

Stores document sections with parent-child chunk hierarchy.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| section_id | TEXT | Unique chunk identifier | PRIMARY KEY |
| document_id | TEXT | Parent document reference | FOREIGN KEY, NOT NULL |
| chunk_type | TEXT | 'parent' or 'child' | NOT NULL |
| parent_id | TEXT | Parent chunk reference | FOREIGN KEY (self) |
| section_heading | TEXT | Section title/heading | - |
| section_text | TEXT | Actual text content | NOT NULL |
| section_idx | INTEGER | Section order in document | - |
| chunk_idx | INTEGER | Chunk order within section | - |
| embedding_model | TEXT | Model used for embedding | - |
| embedding_id | TEXT | Reference to vector store | - |
| metadata_json | TEXT | Additional metadata | JSON format |
| created_at | TEXT | Creation timestamp | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `idx_sections_document` on `document_id`
- `idx_sections_type` on `chunk_type`
- `idx_sections_parent` on `parent_id`

**Example Parent Chunk:**
```json
{
  "section_id": "p_a7f3b2c9_0",
  "document_id": "a7f3b2c9d8e4f1a6",
  "chunk_type": "parent",
  "parent_id": null,
  "section_heading": "Patient Transfers",
  "section_text": "[ORG=cpso] [TOPIC=transfer] [DATE=2023-06-01] [TYPE=policy]\n\n## Patient Transfers\n\nPhysicians must ensure continuity of care when transferring patients...",
  "section_idx": 0,
  "chunk_idx": null,
  "embedding_model": "text-embedding-3-small",
  "embedding_id": "p_a7f3b2c9_0",
  "metadata_json": "{\"word_count\": 623, \"has_expectations\": true}"
}
```

**Example Child Chunk:**
```json
{
  "section_id": "c_a7f3b2c9_0_1",
  "document_id": "a7f3b2c9d8e4f1a6",
  "chunk_type": "child",
  "parent_id": "p_a7f3b2c9_0",
  "section_heading": "Patient Transfers",
  "section_text": "When transferring care, physicians must provide a written summary including current medications, active problems, and recent investigations...",
  "section_idx": 0,
  "chunk_idx": 1,
  "embedding_model": "text-embedding-3-small",
  "embedding_id": "c_a7f3b2c9_0_1",
  "metadata_json": "{\"word_count\": 127}"
}
```

### 3. ingestion_log

Tracks document ingestion history and errors.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| log_id | INTEGER | Auto-incrementing ID | PRIMARY KEY AUTOINCREMENT |
| source_type | TEXT | Source identifier | NOT NULL |
| source_file | TEXT | URL or file path | NOT NULL |
| status | TEXT | 'started', 'completed', 'failed' | NOT NULL |
| started_at | TEXT | Start timestamp | ISO format |
| completed_at | TEXT | Completion timestamp | ISO format |
| records_processed | INTEGER | Documents processed | DEFAULT 0 |
| records_failed | INTEGER | Documents failed | DEFAULT 0 |
| error_message | TEXT | Error details if failed | - |

**Example Record:**
```json
{
  "log_id": 42,
  "source_type": "opa_cpso",
  "source_file": "https://www.cpso.on.ca/policies/continuity-care",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:31:45Z",
  "records_processed": 1,
  "records_failed": 0,
  "error_message": null
}
```

### 4. query_cache

Caches frequent queries for performance optimization.

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| cache_id | INTEGER | Auto-incrementing ID | PRIMARY KEY AUTOINCREMENT |
| query_hash | TEXT | MD5 hash of query | UNIQUE, NOT NULL |
| query_text | TEXT | Original query | NOT NULL |
| result_json | TEXT | Cached results | NOT NULL, JSON format |
| created_at | TEXT | Cache creation time | DEFAULT CURRENT_TIMESTAMP |
| accessed_at | TEXT | Last access time | DEFAULT CURRENT_TIMESTAMP |
| access_count | INTEGER | Number of cache hits | DEFAULT 1 |

**Indexes:**
- `idx_cache_hash` on `query_hash`

**Example Record:**
```json
{
  "cache_id": 123,
  "query_hash": "5d41402abc4b2a76b9719d911017c592",
  "query_text": "cervical screening intervals",
  "result_json": "[{\"section_id\": \"c_b8g4c3d0_2_1\", \"score\": 0.92, ...}]",
  "created_at": "2024-01-15T11:00:00Z",
  "accessed_at": "2024-01-15T14:30:00Z",
  "access_count": 7
}
```

## Vector Store Schema (Chroma)

### Collection Structure

Collections are organized by source organization:

- `opa_cpso_corpus`
- `opa_ontario_health_corpus`
- `opa_cep_corpus`
- `opa_pho_corpus`
- `opa_moh_corpus`

### Metadata Fields

Each vector in Chroma includes:

```python
{
    "chunk_id": str,              # Unique identifier
    "document_id": str,           # Parent document
    "chunk_type": str,            # "parent" or "child"
    "parent_id": Optional[str],   # Parent chunk reference
    "source_org": str,            # Organization
    "source_url": str,            # Original URL
    "document_type": str,         # Classification
    "effective_date": str,        # ISO date
    "topics": List[str],          # Topic tags
    "policy_level": Optional[str], # CPSO specific
    "section_heading": str,       # Section title
    "section_idx": int,           # Section order
    "chunk_idx": Optional[int]    # Chunk order
}
```

## Data Relationships

### Document Hierarchy

```
opa_documents (1)
    ↓
opa_sections (many)
    ├── parent chunks
    └── child chunks → parent chunks
```

### Supersession Chain

```
Document A (old)
    ↓ superseded_by
Document B (current)
    ↓ superseded_by
Document C (latest)
```

### Embedding Relationships

```
opa_sections.embedding_id
    ↓
Chroma Collection.ids
    ↓
Vector Embeddings
```

## Data Patterns

### 1. Control Token Format

Control tokens prepended to parent chunks:

```
[ORG={organization}] [TOPIC={topic_list}] [DATE={effective_date}] [TYPE={document_type}]
```

Example:
```
[ORG=cpso] [TOPIC=privacy,consent,virtual_care] [DATE=2024-01-01] [TYPE=policy]
```

### 2. Chunk ID Generation

Chunk IDs follow a consistent pattern:

- Parent chunks: `p_{doc_id_prefix}_{section_idx}`
- Child chunks: `c_{doc_id_prefix}_{section_idx}_{chunk_idx}`

Example:
- Document: `a7f3b2c9d8e4f1a6`
- Parent: `p_a7f3b2c9_0`
- Child: `c_a7f3b2c9_0_1`

### 3. Topic Taxonomy

Standardized topics for consistent tagging:

```python
TOPIC_TAXONOMY = {
    "screening": ["cervical", "breast", "colorectal", "lung"],
    "privacy": ["consent", "disclosure", "records"],
    "continuity": ["transfer", "referral", "discharge"],
    "ipac": ["sterilization", "disinfection", "ppe"],
    "digital": ["emr", "ehr", "olis", "hrm"],
    "prescribing": ["opioids", "controlled", "narcotics"],
    "virtual": ["telemedicine", "remote", "video"]
}
```

### 4. Date Formats

All dates stored in ISO 8601 format:

- Full timestamp: `2024-01-15T10:30:00Z`
- Date only: `2024-01-15`
- Parsed formats:
  - "January 15, 2024" → `2024-01-15`
  - "15/01/2024" → `2024-01-15`
  - "2024-01-15" → `2024-01-15`

## Query Patterns

### 1. Find Active Documents by Organization

```sql
SELECT * FROM opa_documents
WHERE source_org = 'cpso'
  AND is_superseded = 0
ORDER BY effective_date DESC;
```

### 2. Get Document with Sections

```sql
SELECT d.*, s.*
FROM opa_documents d
LEFT JOIN opa_sections s ON d.document_id = s.document_id
WHERE d.document_id = ?
ORDER BY s.section_idx, s.chunk_idx;
```

### 3. Find Superseded Documents

```sql
SELECT 
    old.title AS old_title,
    old.effective_date AS old_date,
    new.title AS new_title,
    new.effective_date AS new_date
FROM opa_documents old
JOIN opa_documents new ON old.superseded_by = new.document_id
WHERE old.is_superseded = 1;
```

### 4. Get Parent with Children

```sql
SELECT * FROM opa_sections
WHERE parent_id = ? OR section_id = ?
ORDER BY chunk_idx;
```

### 5. Cache Hit Query

```sql
UPDATE query_cache
SET accessed_at = CURRENT_TIMESTAMP,
    access_count = access_count + 1
WHERE query_hash = ?
RETURNING result_json;
```

## Data Integrity Rules

### 1. Document Constraints

- `document_id` must be unique
- `source_url` must be unique and valid URL
- `source_org` must be from allowed list
- `effective_date` <= current date
- If `is_superseded` = true, `superseded_by` must reference valid document

### 2. Section Constraints

- `section_id` must be unique
- `document_id` must reference existing document
- `chunk_type` must be 'parent' or 'child'
- If `chunk_type` = 'child', `parent_id` must be set
- If `chunk_type` = 'parent', `parent_id` must be null
- `section_text` cannot be empty

### 3. Supersession Rules

- Document can only be superseded by newer document (by effective_date)
- Supersession is transitive (if A→B and B→C, then A is superseded by C)
- Only documents with same topic can supersede each other
- Superseded documents remain in database but excluded from default queries

### 4. Cache Management

- Cache entries expire after configurable TTL (default 1 hour)
- Cache cleared when new documents ingested for same organization
- Maximum cache size enforced (default 1000 entries)
- LRU eviction when size limit reached

## Migration Strategy

### Version Control

Database schema versioned in `migrations/` directory:

```
migrations/
├── 001_initial_schema.sql
├── 002_add_supersession.sql
├── 003_add_query_cache.sql
└── 004_add_indexes.sql
```

### Rollback Support

Each migration includes rollback statements:

```sql
-- Migrate up
CREATE TABLE opa_documents (...);

-- Migrate down
DROP TABLE IF EXISTS opa_documents;
```

### Data Validation

Post-migration validation queries:

```sql
-- Check referential integrity
SELECT COUNT(*) FROM opa_sections
WHERE document_id NOT IN (SELECT document_id FROM opa_documents);

-- Check supersession cycles
WITH RECURSIVE chain AS (
    SELECT document_id, superseded_by, 0 as depth
    FROM opa_documents
    WHERE is_superseded = 1
    UNION ALL
    SELECT c.document_id, d.superseded_by, c.depth + 1
    FROM chain c
    JOIN opa_documents d ON c.superseded_by = d.document_id
    WHERE c.depth < 10
)
SELECT * FROM chain WHERE depth >= 10;
```