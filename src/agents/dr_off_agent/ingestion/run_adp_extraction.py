#!/usr/bin/env python3
"""
Authoritative ADP extraction script with LLM enhancement.
Extracts clinically relevant sections from ADP PDFs with focused page ranges.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.dr_off_agent.ingestion.extractors.adp_extractor import EnhancedADPExtractor, ADPSection


class FocusedADPExtractor(EnhancedADPExtractor):
    """Extended extractor that handles page range filtering"""
    
    def extract_page_range(self, path: str, start_page: int, end_page: int, adp_doc: Optional[str] = None) -> List[ADPSection]:
        """Extract only specific page range from PDF"""
        
        if adp_doc is None:
            adp_doc = self.infer_doc_kind(path)
            
        logger.info(f"Extracting pages {start_page}-{end_page} from {path} as {adp_doc}")
        
        # Load only the specified page range
        import pdfplumber
        
        page_text_parts = []
        page_texts = {}
        
        try:
            with pdfplumber.open(path) as pdf:
                for i in range(start_page - 1, min(end_page, len(pdf.pages))):
                    if i < len(pdf.pages):
                        text = pdf.pages[i].extract_text() or ""
                        page_texts[i + 1] = text
                        page_text_parts.append(f"\n--- Page {i + 1} ---\n{text}")
                        
            full_text = "\n".join(page_text_parts)
            
        except Exception as e:
            logger.error(f"Error loading PDF pages {start_page}-{end_page} from {path}: {e}")
            raise
        
        # Find all sections in the extracted text
        sections = []
        section_matches = list(self.SECTION_RE.finditer(full_text))
        
        logger.info(f"Found {len(section_matches)} sections in pages {start_page}-{end_page}")
        
        for i, match in enumerate(section_matches):
            # Get section details
            section_id = match.group('section')
            title = match.group('title').strip()
            
            # Find section boundaries
            start = match.end()
            end = section_matches[i + 1].start() if i + 1 < len(section_matches) else None
            
            # Extract body
            body = self.extract_section_body(full_text, start, end)
            
            # Find current part
            part = self.find_current_part(full_text, match.start())
            
            # Create policy UID
            policy_uid = f"adp:{adp_doc}:{section_id}"
            
            # Detect topics
            topics = self.detect_topics(body)
            
            # Harvest structured data with LLM enhancement
            funding = self.harvest_funding(body, section_id, title)
            exclusions = self.harvest_exclusions(body, section_id, title)
            
            # Find page number (approximate)
            page_num = None
            for pnum, ptext in page_texts.items():
                if section_id in ptext and title[:30] in ptext:
                    page_num = pnum
                    break
            
            # Create section object
            section = ADPSection(
                adp_doc=adp_doc,
                part=part,
                section_id=section_id,
                title=title,
                raw_text=body,
                policy_uid=policy_uid,
                topics=topics,
                funding=funding,
                exclusions=exclusions,
                page_num=page_num
            )
            
            sections.append(section)
            
        logger.info(f"Extracted {len(sections)} sections from pages {start_page}-{end_page}")
        return sections


def process_single_document(doc_info: Dict, worker_id: int = 0) -> Dict:
    """Process a single document - designed for parallel execution"""
    
    # Create new event loop for this thread (needed for async LLM calls)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Each worker needs its own extractor instance
    extractor = FocusedADPExtractor(use_llm=True)
    
    extraction = doc_info.get('extraction_recommended', {})
    if not extraction or 'start_page' not in extraction:
        print(f"[Worker {worker_id}] ⏭️  Skipping {doc_info['filename']} (no extraction range)")
        return None
    
    pdf_path = Path(doc_info['path'])
    
    if not pdf_path.exists():
        print(f"[Worker {worker_id}] ❌ File not found: {pdf_path}")
        return None
    
    start_page = extraction['start_page']
    end_page = extraction['end_page'] 
    total_pages = extraction['total_pages']
    
    # Fix invalid page ranges
    if start_page <= 0:
        print(f"[Worker {worker_id}]    ⚠️  Invalid start page {start_page}, using page 1")
        start_page = 1
    if end_page <= start_page:
        print(f"[Worker {worker_id}]    ⚠️  Invalid end page {end_page}, using start+10")
        end_page = start_page + 10
        total_pages = end_page - start_page + 1
    
    # Infer document type from filename
    doc_type = extractor.infer_doc_kind(pdf_path)
    
    print(f"\n[Worker {worker_id}] 📄 {doc_info['filename']}")
    print(f"[Worker {worker_id}]    Pages {start_page}-{end_page} ({total_pages} pages) as '{doc_type}'")
    
    try:
        # Extract focused sections with LLM
        sections = extractor.extract_page_range(
            str(pdf_path), start_page, end_page, doc_type
        )
        
        doc_exclusions = sum(len(s.exclusions) for s in sections)
        doc_funding = sum(len(s.funding) for s in sections)
        
        print(f"[Worker {worker_id}]    ✅ {len(sections)} sections, {doc_exclusions} exclusions, {doc_funding} funding rules")
        
        # Check for battery exclusions
        battery_found = any(
            'batter' in str(exc).lower() 
            for s in sections 
            for exc in s.exclusions
        )
        if battery_found:
            print(f"[Worker {worker_id}]    🔋 Battery exclusions detected!")
        
        return {
            'filename': doc_info['filename'],
            'sections': sections,
            'section_count': len(sections),
            'exclusion_count': doc_exclusions,
            'funding_count': doc_funding,
            'battery_found': battery_found
        }
        
    except Exception as e:
        print(f"[Worker {worker_id}]    ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up event loop
        loop.close()


def main():
    """Main extraction function"""
    
    # Load analysis results
    analysis_file = Path(__file__).parent.parent.parent.parent.parent / "tests/dr_off_agent/test_outputs/adp_toc_analysis.json"
    
    if not analysis_file.exists():
        print("❌ TOC analysis file not found. Please run TOC analysis first.")
        print(f"   Expected location: {analysis_file}")
        return
    
    with open(analysis_file) as f:
        analysis = json.load(f)
    
    print("Focused ADP Extraction with LLM Enhancement")
    print("=" * 60)
    print(f"Processing {analysis['total_documents']} documents")
    print(f"Total clinical pages: {sum(doc.get('extraction_recommended', {}).get('total_pages', 0) for doc in analysis['documents'])}")
    
    # Determine number of workers (use 3 for API rate limit safety)
    max_workers = min(3, os.cpu_count() or 1)
    print(f"Using {max_workers} parallel workers")
    print()
    
    # Filter documents that have extraction ranges
    docs_to_process = [
        doc for doc in analysis['documents']
        if doc.get('extraction_recommended') and 'start_page' in doc.get('extraction_recommended', {})
    ]
    
    print(f"Found {len(docs_to_process)} documents to process")
    print("-" * 60)
    
    # Process documents in parallel
    all_sections = []
    doc_count = 0
    total_sections = 0
    total_exclusions = 0
    total_funding = 0
    battery_docs = []
    
    # Use ThreadPoolExecutor for I/O bound LLM calls
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create tasks with worker IDs
        tasks = []
        for i, doc in enumerate(docs_to_process):
            worker_id = i % max_workers
            task = executor.submit(process_single_document, doc, worker_id)
            tasks.append(task)
        
        # Collect results as they complete
        for future in tasks:
            result = future.result()
            if result:
                doc_count += 1
                all_sections.extend(result['sections'])
                total_sections += result['section_count']
                total_exclusions += result['exclusion_count']
                total_funding += result['funding_count']
                if result['battery_found']:
                    battery_docs.append(result['filename'])
    
    # Save all extracted sections
    output_dir = Path(__file__).parent.parent.parent.parent.parent / "data/processed/dr_off/adp"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "adp_focused_extraction_llm.json"
    
    result_data = {
        "extraction_date": "2025-09-24",
        "documents_processed": doc_count,
        "total_sections": total_sections,
        "total_exclusions": total_exclusions,
        "total_funding_rules": total_funding,
        "sections": [s.to_dict() for s in all_sections]
    }
    
    with open(output_file, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("FOCUSED EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Documents processed: {doc_count}")
    print(f"Total sections: {total_sections}")
    print(f"Total exclusions: {total_exclusions}")
    print(f"Total funding rules: {total_funding}")
    print(f"Results saved to: {output_file}")
    
    # Check for battery exclusions across all docs
    battery_sections = [
        s for s in all_sections 
        for exc in s.exclusions
        if 'batter' in str(exc).lower()
    ]
    
    print(f"\n🔋 Battery exclusions found in {len(set(s.section_id for s in battery_sections))} sections")
    
    if len(set(s.section_id for s in battery_sections)) > 0:
        print("✅ SUCCESS: Battery exclusions properly detected with LLM enhancement!")
    else:
        print("⚠️  WARNING: No battery exclusions found - may need regex pattern updates")


if __name__ == "__main__":
    main()