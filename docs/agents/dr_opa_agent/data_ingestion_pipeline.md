# Dr. OPA Data Ingestion Pipeline

## Overview

The Dr. OPA agent uses a sophisticated data ingestion pipeline to extract, process, and store Ontario practice guidance documents from multiple authoritative sources. The pipeline implements a parent-child chunking strategy with dual-path retrieval (SQL + vector search) for optimal information retrieval.

**Current Status**: 
- ✅ CPSO fully implemented (366 vectors)
- ✅ CEP clinical tools implemented (57 vectors, 6 tools)
- ✅ PHO IPAC guidance implemented (132 vectors)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Data Sources                              │
│  ┌──────┐  ┌──────────┐  ┌─────┐  ┌─────┐  ┌─────────────┐ │
│  │ CPSO │  │ Ontario  │  │ CEP │  │ PHO │  │ MOH/Ontario │ │
│  │  ✅  │  │  Health  │  │ ✅  │  │ ✅  │  │   Guidance  │ │
│  └──┬───┘  └────┬─────┘  └──┬──┘  └──┬──┘  └──────┬──────┘ │
└─────┼───────────┼───────────┼────────┼─────────────┼────────┘
      │           │           │        │             │
      └───────────┴───────────┴────────┴─────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Web Crawlers     │
                    │  (Parallel, 5      │
                    │   workers, rate    │
                    │   limited)         │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  HTML Extractors   │
                    │  (BeautifulSoup,   │
                    │   structured data) │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Parent-Child      │
                    │  Chunking          │
                    │  (2500/500 tokens) │
                    └─────────┬──────────┘
                              │
                  ┌───────────┴───────────┐
                  │                       │
        ┌─────────▼──────────┐ ┌─────────▼──────────┐
        │   SQLite Database  │ │  Chroma Vector DB  │
        │  (Structured data, │ │  (Embeddings with  │
        │   metadata, full   │ │   OpenAI ada-002)  │
        │   text search)     │ │                    │
        └────────────────────┘ └────────────────────┘
```

## File Structure

```
src/agents/dr_opa_agent/ingestion/
├── __init__.py
├── base_ingester.py          # Abstract base class for all ingesters
├── database.py               # SQLite database management
├── run_extraction.py         # Master extraction script
├── run_ingestion.py          # Master ingestion script
├── cpso/                     # CPSO-specific implementation
│   ├── __init__.py
│   ├── extractor.py          # HTML extraction logic
│   ├── crawler.py            # Parallel web crawler
│   ├── ingestion.py          # CPSO ingestion logic
│   └── batch_ingest.py       # Batch processing for extracted docs
├── cep/                      # CEP clinical tools implementation
│   ├── __init__.py
│   ├── crawler.py            # CEP tools crawler
│   ├── extractor.py          # Tool navigation extractor
│   ├── ingester.py           # CEP ingestion with lightweight indexing
│   └── run_full_pipeline.py  # Complete CEP pipeline
└── pho/                      # PHO IPAC implementation ✅
    ├── __init__.py
    ├── pho_extractor.py      # PDF extraction logic
    └── pho_ingester.py       # PHO ingestion with parent-child chunking

data/dr_opa_agent/
├── chroma/                   # Vector embeddings (consolidated)
│   ├── opa_cpso_corpus       # CPSO documents (366 vectors)
│   ├── opa_cep_corpus        # CEP tools (57 vectors)
│   └── opa_pho_corpus        # PHO IPAC guidance (132 vectors)
├── raw/                      # Raw source files
│   ├── cpso/                 # CPSO HTML files
│   └── pho/                  # PHO PDF files
└── processed/                # Extracted JSON documents
    ├── cpso/                 # CPSO structured data
    └── pho/                  # PHO structured data

data/processed/dr_opa/
└── opa.db                    # SQLite database (structured metadata & full-text search)
```

## Database Schema

### SQLite Tables

#### opa_documents
```sql
CREATE TABLE opa_documents (
    document_id TEXT PRIMARY KEY,
    source_url TEXT,
    source_org TEXT,           -- 'cpso', 'ontario_health', etc.
    document_type TEXT,         -- 'policy', 'advice', 'guideline'
    title TEXT,
    effective_date TEXT,
    updated_date TEXT,
    published_date TEXT,
    topics TEXT,                -- JSON array of topics
    policy_level TEXT,          -- 'expectation', 'advice', 'general'
    content_hash TEXT,
    metadata_json TEXT,
    is_superseded BOOLEAN,
    ingested_at TIMESTAMP
);
```

#### opa_sections
```sql
CREATE TABLE opa_sections (
    section_id TEXT PRIMARY KEY,
    document_id TEXT,
    chunk_type TEXT,            -- 'parent' or 'child'
    parent_id TEXT,             -- References parent chunk
    section_heading TEXT,
    section_text TEXT,          -- Actual content
    section_idx INTEGER,
    chunk_idx INTEGER,
    embedding_model TEXT,
    embedding_id TEXT,
    metadata_json TEXT,
    FOREIGN KEY (document_id) REFERENCES opa_documents(document_id)
);
```

### Chroma Vector Database
- **Collection**: `opa_cpso_corpus`
- **Embedding Model**: OpenAI text-embedding-3-small
- **Metadata**: Flattened (lists → comma-separated strings)

## Chunking Strategy

### Parent-Child Hierarchical Chunking

1. **Parent Chunks** (2500 tokens)
   - Complete sections or logical units
   - Control tokens: `[ORG={org}] [TOPIC={topic}] [DATE={date}] [TYPE={doc_type}]`
   - Provide retrieval context

2. **Child Chunks** (500 tokens)
   - Granular segments for precise matching
   - 100 token overlap
   - Reference parent ID for context

### Benefits
- **Better context**: Parents maintain coherence
- **Precise retrieval**: Children enable fine matching
- **Reduced hallucination**: Clear boundaries
- **Flexible**: Return parents, children, or both

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install beautifulsoup4 requests chromadb openai python-dotenv tqdm

# Set up environment
echo "OPENAI_API_KEY=sk-..." > .env
```

### Extract & Ingest CPSO Documents
```bash
# 1. Extract all CPSO documents (parallel)
python src/agents/dr_opa_agent/ingestion/run_extraction.py \
    --source cpso \
    --workers 5

# 2. Ingest into databases
python src/agents/dr_opa_agent/ingestion/run_ingestion.py \
    --source cpso
```

## Adding New Sources

To add a new source (e.g., Ontario Health), follow the CPSO pattern:

### 1. Create Source Module
```bash
mkdir src/agents/dr_opa_agent/ingestion/ontario_health
touch src/agents/dr_opa_agent/ingestion/ontario_health/__init__.py
```

### 2. Implement Extractor (`ontario_health/extractor.py`)
```python
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import hashlib

class OntarioHealthExtractor:
    """Extract structured data from Ontario Health pages."""
    
    def extract_from_html(self, html: str, url: str) -> Dict[str, Any]:
        """Extract document content and metadata."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Custom extraction logic based on site structure
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        sections = self._extract_sections(soup)
        
        return {
            'title': title,
            'content': content,
            'sections': sections,
            'source_url': url,
            'source_org': 'ontario_health',
            'content_hash': hashlib.sha256(content.encode()).hexdigest(),
            'extracted_at': datetime.now().isoformat()
        }
```

### 3. Implement Crawler (`ontario_health/crawler.py`)
```python
from concurrent.futures import ThreadPoolExecutor
from .extractor import OntarioHealthExtractor

class OntarioHealthCrawler:
    """Parallel crawler for Ontario Health documents."""
    
    LANDING_PAGES = {
        'clinical': 'https://www.ontariohealth.ca/clinical-guidance',
        'quality': 'https://www.hqontario.ca/quality-standards'
    }
    
    def __init__(self, output_dir: str, max_workers: int = 5):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.extractor = OntarioHealthExtractor()
    
    def crawl_all(self, doc_types: List[str] = None):
        """Crawl documents in parallel."""
        # Follow CPSO crawler pattern
        pass
```

### 4. Implement Batch Ingester (`ontario_health/batch_ingest.py`)
```python
from ..base_ingester import BaseOPAIngester

class OntarioHealthBatchIngester(BaseOPAIngester):
    """Batch ingest Ontario Health documents."""
    
    def __init__(self, db_path: str, chroma_path: str, openai_api_key: str = None):
        super().__init__(
            source_org='ontario_health',
            db_path=db_path,
            chroma_path=chroma_path,
            openai_api_key=openai_api_key
        )
```

### 5. Register in Master Scripts

Update `run_extraction.py`:
```python
def run_ontario_health_extraction(args):
    from ontario_health.crawler import OntarioHealthCrawler
    crawler = OntarioHealthCrawler(args.output_dir, args.workers)
    return crawler.crawl_all(args.types)
```

Update `run_ingestion.py`:
```python
def run_ontario_health_ingestion(args):
    from ontario_health.batch_ingest import OntarioHealthBatchIngester
    ingester = OntarioHealthBatchIngester(
        args.db_path, args.chroma_path, args.openai_key
    )
    return ingester.ingest_directory(args.input_dir)
```

### 6. Run Pipeline
```bash
# Extract
python src/agents/dr_opa_agent/ingestion/run_extraction.py \
    --source ontario_health

# Ingest
python src/agents/dr_opa_agent/ingestion/run_ingestion.py \
    --source ontario_health
```

## Performance Metrics

### CPSO Implementation Results
- **Documents**: 69 total (35 policies, 29 advice, 5 statements)
- **Extraction Time**: ~10 minutes (5 parallel workers)
- **Ingestion Time**: ~1 minute
- **Storage**:
  - SQLite: 65 documents, 373 sections
  - Chroma: 366 embeddings (with OpenAI API)
- **Chunks**: 74 parents, 299 children

### PHO IPAC Implementation Results
- **Documents**: 1 comprehensive PDF (116 pages)
- **Extraction Time**: ~2 seconds (PDF processing)
- **Ingestion Time**: ~8 seconds (including embeddings)
- **Storage**:
  - SQLite: 1 document, 132 sections
  - Chroma: 132 embeddings (with OpenAI API)
- **Chunks**: 26 parents, 136 children
- **Topics**: infection-prevention, IPAC, clinical-office, sterilization, PPE, hand-hygiene

### CEP Clinical Tools Results
- **Documents**: 46 clinical tools and algorithms
- **Storage**:
  - Chroma: 57 embeddings (with OpenAI API)
- **Topics**: clinical-pathways, evidence-based-care, primary-care-tools

## Advanced Features

### Automatic Supersession Detection
```python
def check_and_mark_superseded(self, topic: str, effective_date: str):
    """Mark older documents on same topic as superseded."""
    # Implemented in BaseOPAIngester
```

### Control Tokens for Enhanced Retrieval
```python
control_tokens = "[ORG=cpso] [TOPIC=prescribing] [DATE=2024] [TYPE=policy]"
```

### Checkpoint System for Resumable Extraction
```json
{
    "processed_urls": [...],
    "last_updated": "2025-09-24T12:00:00",
    "stats": {...}
}
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No OpenAI API key" | Add `OPENAI_API_KEY` to `.env` |
| "Chroma metadata error" | Fixed - lists auto-converted to strings |
| "Document already exists" | Normal - deduplication by content hash |
| "Rate limiting" | Reduce workers: `--workers 2` |
| "Import errors" | Ensure proper module structure |

### Debug Commands
```bash
# Check database status
sqlite3 data/dr_opa_agent/opa.db "SELECT COUNT(*) FROM opa_documents;"

# Verify Chroma embeddings
python -c "import chromadb; client = chromadb.PersistentClient('data/dr_opa_agent/chroma'); print(client.get_collection('opa_cpso_corpus').count())"

# Test single document
python src/agents/dr_opa_agent/ingestion/cpso/batch_ingest.py \
    --test-file data/dr_opa_agent/processed/cpso/sample.json
```

## Future Roadmap

### Phase 1 (Completed)
- ✅ CPSO policies and advice (366 vectors)
- ✅ CEP clinical tools (57 vectors) 
- ✅ PHO IPAC guidance (132 vectors)
- ✅ Parent-child chunking
- ✅ Dual-path storage (SQL + vector)

### Phase 2 (Next)
- ⏳ Ontario Health screening guidelines
- ⏳ MOH InfoBulletins and fee schedules

### Phase 3 (Future)
- ⏸️ Incremental updates via RSS
- ⏸️ Cross-source deduplication
- ⏸️ French language support
- ⏸️ PDF extraction support