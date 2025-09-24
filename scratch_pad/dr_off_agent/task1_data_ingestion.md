# Task 1: Data Ingestion & Storage Layer

## 🎯 Objective
Set up the data foundation for Dr. OFF by ingesting Ontario healthcare data (ODB, OHIP, ADP) into structured SQL tables and vector embeddings.

## 📋 Checklist

### Setup
- [ ] Create directory structure under `src/agents/clinical/dr_off/ingestion/`
- [ ] Create directory structure under `data/ontario/` and `data/processed/dr_off/`
- [ ] Set up SQLite database at `data/processed/dr_off/dr_off.db`

### ODB (Ontario Drug Benefit) Ingestion
- [ ] Download ODB Formulary Data Extract (XML)
- [ ] Download ODB Formulary Edition 43 PDF
- [ ] Create `ingest_odb.py` script
  - [ ] Parse XML into structured format
  - [ ] Create `odb_drugs` table schema:
    ```sql
    CREATE TABLE odb_drugs (
        din TEXT PRIMARY KEY,
        ingredient TEXT,
        brand TEXT,
        strength TEXT,
        form TEXT,
        group_id TEXT,
        price REAL,
        lowest_cost BOOLEAN,
        status TEXT,
        updated_date DATE
    );
    ```
  - [ ] Create `interchangeable_groups` table:
    ```sql
    CREATE TABLE interchangeable_groups (
        group_id TEXT PRIMARY KEY,
        name TEXT,
        member_count INTEGER,
        lowest_din TEXT
    );
    ```
  - [ ] Compute lowest-cost flag per interchangeable group
  - [ ] Chunk ODB PDF (900-1200 tokens, 20% overlap)
  - [ ] Generate embeddings using `text-embedding-3-small`
  - [ ] Store in Chroma with metadata

### OHIP (Ontario Health Insurance Plan) Ingestion
- [ ] Download Schedule of Benefits PDF
- [ ] Download Regulation 552 HTML
- [ ] Create `ingest_ohip.py` script
  - [ ] Parse Schedule PDF using PyPDF2 or pdfplumber
  - [ ] Create `ohip_fees` table:
    ```sql
    CREATE TABLE ohip_fees (
        code TEXT PRIMARY KEY,
        description TEXT,
        amount REAL,
        specialty TEXT,
        page_num INTEGER,
        section TEXT,
        effective_date DATE
    );
    ```
  - [ ] Parse Regulation 552 by section
  - [ ] Chunk both documents appropriately
  - [ ] Generate embeddings
  - [ ] Store in Chroma with source metadata

### ADP (Assistive Devices Program) Ingestion
- [ ] Download ADP Policies & Procedures Manual
- [ ] Download Mobility Devices Category Manual
- [ ] Create `ingest_adp.py` script
  - [ ] Create `adp_device_rules` table:
    ```sql
    CREATE TABLE adp_device_rules (
        device_id TEXT PRIMARY KEY,
        category TEXT,
        device TEXT,
        funding_pct REAL,
        max_funding REAL,
        eligibility TEXT,
        replacement_interval TEXT,
        forms_required TEXT
    );
    ```
  - [ ] Extract funding percentages and rules
  - [ ] Parse eligibility criteria
  - [ ] Chunk manuals for embedding
  - [ ] Generate embeddings
  - [ ] Store in Chroma with metadata

### Vector Store Setup
- [ ] Initialize Chroma persistent client
- [ ] Create collections:
  - `odb_documents`
  - `ohip_documents`
  - `adp_documents`
- [ ] Configure metadata fields:
  - source_type (odb/ohip/adp)
  - document_name
  - page_number
  - section
  - last_updated

### Testing & Validation
- [ ] Write unit tests for each ingestion script
- [ ] Validate data integrity:
  - [ ] Check all DINs have group assignments
  - [ ] Verify lowest-cost calculations
  - [ ] Ensure all OHIP codes have descriptions
  - [ ] Validate ADP funding percentages
- [ ] Test vector search retrieval quality
- [ ] Document ingestion pipeline

## 📁 Deliverables

1. **Scripts**:
   - `src/agents/clinical/dr_off/ingestion/__init__.py`
   - `src/agents/clinical/dr_off/ingestion/ingest_odb.py`
   - `src/agents/clinical/dr_off/ingestion/ingest_ohip.py`
   - `src/agents/clinical/dr_off/ingestion/ingest_adp.py`
   - `src/agents/clinical/dr_off/ingestion/base_ingester.py`

2. **Database**:
   - `data/processed/dr_off/dr_off.db` with populated tables

3. **Vector Store**:
   - `data/processed/dr_off/chroma/` with embedded documents

4. **Tests**:
   - `tests/unit/agents/dr_off/test_ingestion.py`

## 🔗 Dependencies
- **Output to Session 2**: Database schema and table structure
- **Output to Session 4**: Vector store configuration and collections

## 📚 Resources
- [ODB Formulary Downloads](https://www.ontario.ca/page/check-medication-coverage/)
- [OHIP Schedule of Benefits](https://www.health.gov.on.ca/en/pro/programs/ohip/sob/)
- [ADP Program Manuals](https://www.ontario.ca/page/assistive-devices-program)

## 💡 Tips
- Use batch processing for large XML files
- Implement retry logic for PDF parsing
- Add progress bars for long-running ingestion
- Log all parsing errors for manual review
- Keep original source files for re-ingestion