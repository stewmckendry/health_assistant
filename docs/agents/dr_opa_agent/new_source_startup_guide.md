# Dr. OPA Agent - New Data Source Integration Guide

## 🚀 Quick Start for New Claude Code Sessions

**Your Mission**: Integrate a new data source into the Dr. OPA (Ontario Practice Advice) Agent, which provides Ontario-specific primary care and practice guidance for clinicians.

---

## 📋 Context & Background

### What is Dr. OPA?
Dr. OPA is an AI agent that helps Ontario clinicians access practice guidance from multiple authoritative sources:
- **CPSO**: College of Physicians and Surgeons of Ontario (✅ Already integrated - 69 documents)
- **Ontario Health**: Cancer screening programs (⏳ Your task)
- **CEP**: Centre for Effective Practice clinical tools (⏳ Your task)
- **PHO**: Public Health Ontario IPAC guidance (⏳ Your task)
- **MOH**: Ministry of Health InfoBulletins (⏳ Your task)

### Architecture Overview
```
Data Flow: Web → Extract → Process → Store → Retrieve via MCP Tools
           ↓        ↓         ↓        ↓              ↓
        Crawler  Extractor  Chunker  SQL+Vector   FastMCP Server
```

---

## 🏗️ What's Already Built

### Core Infrastructure (Reuse These!)

1. **Base Ingestion Pipeline** (`src/agents/dr_opa_agent/ingestion/`)
   - `base_ingester.py` - Abstract base class with chunking logic
   - `database.py` - SQLite database handler
   - `run_extraction.py` - Master extraction script
   - `run_ingestion.py` - Master ingestion script

2. **MCP Tools** (`src/agents/dr_opa_agent/mcp/`)
   - `server.py` - FastMCP server with 6 working tools
   - `models/request.py` - Request schemas
   - `models/response.py` - Response schemas
   - `retrieval/sql_client.py` - SQL query handler
   - `retrieval/vector_client.py` - Chroma vector search
   - `utils/confidence.py` - Confidence scoring
   - `utils/citations.py` - Citation formatting

3. **CPSO Implementation** (`src/agents/dr_opa_agent/ingestion/cpso/`)
   - `cpso_crawler.py` - Web crawler example
   - `cpso_extractor.py` - HTML extraction example
   - `cpso_ingester.py` - Document ingestion example

### Database Schema
```sql
-- opa_documents table
document_id TEXT PRIMARY KEY
title TEXT
source_org TEXT  -- 'ontario_health', 'cep', 'pho', 'moh'
source_url TEXT
document_type TEXT  -- 'guideline', 'tool', 'bulletin', etc.
effective_date TEXT
topics TEXT  -- JSON array as string
is_superseded BOOLEAN

-- opa_sections table  
section_id TEXT PRIMARY KEY
document_id TEXT FOREIGN KEY
chunk_type TEXT  -- 'parent' or 'child'
section_text TEXT  -- The actual content
section_heading TEXT
metadata TEXT  -- JSON string
```

---

## 📁 File Organization

### Where to Create Your Files

```
src/agents/dr_opa_agent/ingestion/
├── ontario_health/  # For Ontario Health sources
│   ├── __init__.py
│   ├── oh_crawler.py      # Your crawler
│   ├── oh_extractor.py    # Your extractor
│   └── oh_ingester.py     # Your ingester
├── cep/            # For CEP sources
│   ├── __init__.py
│   ├── cep_crawler.py
│   ├── cep_extractor.py
│   └── cep_ingester.py
├── pho/            # For PHO sources
│   └── ...
└── moh/            # For MOH sources
    └── ...

data/dr_opa_agent/
├── raw/
│   ├── ontario_health/     # Your raw downloads
│   ├── cep/
│   ├── pho/
│   └── moh/
└── processed/
    ├── ontario_health/     # Your extracted JSON
    ├── cep/
    ├── pho/
    └── moh/
```

### Test Files Location
```
tests/dr_opa_agent/test_scripts/
├── test_ontario_health_ingestion.py
├── test_cep_tools.py
└── test_outputs/
    └── oh_test_results.json
```

---

## 🔧 Implementation Steps

### Step 1: Explore Target Website
```python
# First, understand the site structure
import requests
from bs4 import BeautifulSoup

# Example for Ontario Health
url = "https://www.cancercareontario.ca/en/guidelines-advice"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find patterns in URLs, document types, navigation
```

### Step 2: Create Crawler (Based on CPSO Example)
```python
# src/agents/dr_opa_agent/ingestion/ontario_health/oh_crawler.py
import asyncio
import aiohttp
from pathlib import Path
import json

class OntarioHealthCrawler:
    def __init__(self):
        self.base_url = "https://www.cancercareontario.ca"
        self.output_dir = Path("data/dr_opa_agent/raw/ontario_health")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def crawl_screening_programs(self):
        """Crawl screening program pages."""
        programs = [
            "cervical-screening",
            "breast-screening", 
            "colorectal-screening",
            "lung-screening"
        ]
        # Implementation here
```

### Step 3: Create Extractor
```python
# src/agents/dr_opa_agent/ingestion/ontario_health/oh_extractor.py
from bs4 import BeautifulSoup
from datetime import datetime
import json

class OntarioHealthExtractor:
    def extract_document(self, html_path: Path) -> dict:
        """Extract structured data from HTML."""
        with open(html_path, 'r') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        return {
            "title": self.extract_title(soup),
            "content": self.extract_content(soup),
            "sections": self.extract_sections(soup),
            "metadata": {
                "source_org": "ontario_health",
                "document_type": "guideline",
                "topics": ["screening", "cancer"],
                "effective_date": "2025-03-01"
            }
        }
```

### Step 4: Create Ingester (Inherit from Base!)
```python
# src/agents/dr_opa_agent/ingestion/ontario_health/oh_ingester.py
from ..base_ingester import BaseOPAIngester
from ..database import OPADatabase

class OntarioHealthIngester(BaseOPAIngester):
    def __init__(self):
        super().__init__()
        self.source_org = "ontario_health"
        
    def ingest_document(self, doc_path: Path):
        """Ingest a single document."""
        # Load extracted JSON
        with open(doc_path) as f:
            doc = json.load(f)
        
        # Create parent-child chunks (use inherited method!)
        chunks = self.create_chunks(
            doc['content'],
            metadata={
                "source_org": self.source_org,
                "document_type": doc['metadata']['document_type']
            }
        )
        
        # Store in database and vector store
        self.store_document(doc, chunks)
```

### Step 5: Test Your Integration
```python
# tests/dr_opa_agent/test_scripts/test_ontario_health_ingestion.py
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.dr_opa_agent.ingestion.ontario_health.oh_crawler import OntarioHealthCrawler
from src.agents.dr_opa_agent.ingestion.ontario_health.oh_extractor import OntarioHealthExtractor
from src.agents.dr_opa_agent.ingestion.ontario_health.oh_ingester import OntarioHealthIngester

async def test_full_pipeline():
    # 1. Crawl
    crawler = OntarioHealthCrawler()
    await crawler.crawl_screening_programs()
    
    # 2. Extract
    extractor = OntarioHealthExtractor()
    # ... extract documents
    
    # 3. Ingest
    ingester = OntarioHealthIngester()
    # ... ingest documents
    
    print("✅ Pipeline complete!")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
```

### Step 6: Test with MCP Tools
```python
# Test that your data is accessible via MCP tools
from src.agents.dr_opa_agent.mcp.tools.search import search_sections

result = await search_sections(
    query="cervical screening guidelines",
    source_org="ontario_health"
)
print(f"Found {result['total_matches']} results")
```

---

## 🔑 Key Technical Decisions (Follow These!)

### Chunking Strategy
- **Parent chunks**: 2500 tokens (10k characters) for context
- **Child chunks**: 500 tokens (2k characters) for precision  
- **Overlap**: 100 tokens between chunks
- **Control tokens**: `[ORG=ontario_health] [TOPIC=screening] [DATE=2025-03-01]`

### Metadata Requirements
```python
# Every document MUST have:
metadata = {
    "source_org": "ontario_health",  # Your org identifier
    "source_url": "https://...",     # Original URL
    "document_type": "guideline",    # guideline/tool/bulletin/policy
    "document_title": "...",         # Full title
    "effective_date": "2025-03-01",  # When guidance takes effect
    "topics": ["screening", "hpv"],  # Relevant topics (as list)
}

# Sections also need:
section_metadata = {
    "section_heading": "Eligibility Criteria",
    "section_idx": 3,
    "chunk_idx": 0  # For child chunks
}
```

### Vector Embeddings
- **Model**: OpenAI text-embedding-3-small (1536 dimensions)
- **API Key**: Load from `/Users/liammckendry/health_assistant_dr_off_worktree/.env`
- **Collection naming**: `opa_{source_org}_corpus` (e.g., `opa_ontario_health_corpus`)

### Important Constraints
1. **Chroma metadata**: Must be strings! Convert lists to comma-separated
2. **Database column**: Use `section_text` not `content`
3. **Environment**: Always activate `~/spacy_env/bin/activate`
4. **Rate limiting**: 0.5s delay between web requests minimum

---

## 🐛 Known Issues & Solutions

### Issue 1: Vector Dimension Mismatch
```python
# WRONG - Don't use default embeddings
from chromadb.utils import embedding_functions
ef = embedding_functions.DefaultEmbeddingFunction()  # 384 dims

# CORRECT - Use OpenAI
ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"  # 1536 dims
)
```

### Issue 2: Chroma Metadata Lists
```python
# WRONG
metadata = {"topics": ["screening", "cancer"]}  # Lists not allowed!

# CORRECT
metadata = {"topics": "screening,cancer"}  # Comma-separated string
```

### Issue 3: Database Schema
```python
# WRONG
cursor.execute("INSERT INTO opa_sections (content) ...")

# CORRECT  
cursor.execute("INSERT INTO opa_sections (section_text) ...")
```

---

## 📊 Expected Outputs

### After Successful Ingestion
```
✅ Crawled 15 documents from Ontario Health
✅ Extracted 15 documents (120 sections)
✅ Stored in SQLite: data/processed/dr_opa/opa.db
✅ Embedded in Chroma: 120 vectors in opa_ontario_health_corpus
✅ MCP tools returning results for "screening" queries
```

### Files You Should Generate
1. `data/dr_opa_agent/raw/ontario_health/*.html` - Raw HTML files
2. `data/dr_opa_agent/processed/ontario_health/*.json` - Extracted JSON
3. `tests/dr_opa_agent/test_outputs/oh_test_results.json` - Test results

---

## 🧪 Testing Checklist

- [ ] Crawler successfully downloads target documents
- [ ] Extractor properly parses HTML/PDF content
- [ ] Ingester creates correct parent-child chunks
- [ ] Documents stored in SQLite with proper metadata
- [ ] Vectors embedded in Chroma with correct dimensions
- [ ] MCP tool `opa.search_sections` returns your documents
- [ ] Source-specific tool works (e.g., `opa.program_lookup` for Ontario Health)

---

## 📞 Quick Reference

### Key Files to Read First
1. `src/agents/dr_opa_agent/ingestion/base_ingester.py` - Chunking logic
2. `src/agents/dr_opa_agent/ingestion/cpso/cpso_crawler.py` - Crawler example
3. `src/agents/dr_opa_agent/mcp/server.py` - MCP tools implementation
4. `docs/agents/dr_opa_agent/data_ingestion_pipeline.md` - Full pipeline docs

### Environment Setup
```bash
# Activate virtual environment
source ~/spacy_env/bin/activate

# Load environment variables
export $(cat /Users/liammckendry/health_assistant_dr_off_worktree/.env | xargs)

# Test database connection
sqlite3 data/processed/dr_opa/opa.db "SELECT COUNT(*) FROM opa_documents;"
```

### Running Your Code
```bash
# Run extraction for your source
python src/agents/dr_opa_agent/ingestion/run_extraction.py --source ontario_health

# Run ingestion
python src/agents/dr_opa_agent/ingestion/run_ingestion.py --source ontario_health

# Test MCP tools
python tests/dr_opa_agent/test_scripts/test_mcp_tools.py
```

---

## 🎯 Source-Specific Guidance

### Ontario Health (Cancer Care Ontario)
- **Focus**: Screening programs (cervical, breast, colorectal, lung)
- **Key URLs**: 
  - https://www.cancercareontario.ca/en/guidelines-advice/cancer-continuum/screening
  - HPV Hub: https://www.cancercareontario.ca/en/guidelines-advice/cancer-continuum/screening/hpv-hub
- **Document types**: Guidelines, pathways, algorithms, patient resources
- **Special attention**: March 2025 cervical screening changes

### Centre for Effective Practice (CEP)
- **Focus**: Clinical tools and point-of-care resources
- **Key URLs**: https://cep.health/clinical-products/
- **Document types**: Tools, algorithms, quick reference guides
- **Special handling**: Many PDFs, some interactive tools

### Public Health Ontario (PHO)
- **Focus**: IPAC (Infection Prevention and Control) for office practice
- **Key URLs**: 
  - https://www.publichealthontario.ca/en/health-topics/infection-prevention-control/clinical-office-practice
- **Document types**: Best practice documents, checklists, fact sheets
- **File types**: Mostly PDFs, need good PDF extraction

### Ministry of Health (MOH)
- **Focus**: OHIP InfoBulletins and policy updates
- **Key URLs**: https://www.ontario.ca/document/ohip-infobulletins-2025
- **Document types**: Bulletins, fee schedule updates, policy changes
- **Metadata**: Bulletin numbers, effective dates critical

---

## ⚠️ Important Reminders

1. **Always test with 1-2 documents first** before full crawl
2. **Check robots.txt** and respect rate limits
3. **Store checkpoint files** for resumable crawling
4. **Log everything** - Use the logging setup in base_ingester.py
5. **Validate embeddings** - Ensure 1536 dimensions
6. **Test MCP tools** after ingestion to verify accessibility

---

## 💡 Pro Tips

1. **Reuse CPSO code**: Most of the crawler/extractor logic can be adapted
2. **Parallel processing**: Use asyncio for crawling, max 3-5 workers
3. **Checkpointing**: Save progress frequently for large crawls
4. **PDF handling**: Use PyPDF2 for text PDFs, consider OCR for scanned
5. **Testing**: Write tests as you go, don't wait until the end

---

## 🆘 If You Get Stuck

1. **Check existing implementations**: CPSO code in `ingestion/cpso/`
2. **Review test results**: `scratch_pad/dr_opa_agent/test_results.md`
3. **Database issues**: Check schema in `ingestion/database.py`
4. **Vector issues**: See fix in `ingestion/fix_embeddings.py`
5. **MCP tool issues**: Ensure metadata matches what tools expect

---

## 🎉 Success Criteria

Your integration is complete when:
1. ✅ Documents successfully crawled and stored
2. ✅ All documents accessible via `opa.search_sections`
3. ✅ Source-specific tool returns relevant results
4. ✅ Test script demonstrates full pipeline working
5. ✅ Documentation updated with your source details

Good luck! The Dr. OPA Agent is counting on your contribution! 🏥🤖