#!/usr/bin/env python3
"""Enhanced OHIP data ingestion using improved extraction and proper SQL/ChromaDB storage."""

import os
import logging
import json
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from tqdm import tqdm
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Import enhanced extractor
from ..extractors.ohip_extractor import EnhancedSubsectionExtractor

# Import database components
from ..database import Database, init_database
from ..base_ingester import BaseIngester

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedOHIPIngester(BaseIngester):
    """Enhanced OHIP ingester using subsection extraction."""
    
    def __init__(
        self,
        db_path: str = None,
        chroma_path: str = None,
        openai_api_key: str = None
    ):
        """Initialize enhanced OHIP ingester."""
        super().__init__("ohip", db_path, chroma_path, openai_api_key)
        self.fee_codes_to_store = []
        self.subsection_texts = []
    
    def ingest(self, source_file: str) -> Dict[str, Any]:
        """Implementation of abstract method - delegates to ingest_enhanced."""
        # This is handled by ingest_enhanced for our use case
        return {}
    
    def parse_source(self, source_file: str):
        """Implementation of abstract method - not used in enhanced workflow."""
        # This is handled by the extraction process
        yield from []
    
    async def ingest_enhanced(
        self,
        pdf_file: str,
        toc_file: str,
        extracted_data_file: str = None,
        max_subsections: int = None
    ) -> Dict[str, Any]:
        """Ingest OHIP data using enhanced extraction.
        
        Args:
            pdf_file: Path to OHIP PDF
            toc_file: Path to TOC JSON file
            extracted_data_file: Optional path to pre-extracted data
            max_subsections: Maximum number of subsections to process
            
        Returns:
            Ingestion statistics
        """
        self.log_ingestion(pdf_file, 'started')
        
        try:
            # Step 1: Extract or load subsection data
            if extracted_data_file and Path(extracted_data_file).exists():
                logger.info(f"Loading pre-extracted data from {extracted_data_file}")
                with open(extracted_data_file) as f:
                    extraction_data = json.load(f)
            else:
                logger.info("Running enhanced extraction...")
                extraction_data = await self._run_extraction(
                    pdf_file, toc_file, max_subsections
                )
                
                # Save extraction for reuse
                output_file = Path('data/processed/ohip_extracted_enhanced.json')
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(extraction_data, f, indent=2)
                logger.info(f"Saved extraction to {output_file}")
            
            # Step 2: Process extracted data
            self._process_extraction_data(extraction_data)
            
            # Step 3: Store in SQL database
            self._store_fee_codes_sql()
            
            # Step 4: Store in ChromaDB vector store
            self._store_chunks_chroma(pdf_file)
            
            # Step 5: Validate ingestion
            if self.validate_ingestion():
                self.log_ingestion(pdf_file, 'completed')
                logger.info("✓ Ingestion validated successfully")
            else:
                self.log_ingestion(pdf_file, 'failed', 'Validation failed')
                logger.error("✗ Ingestion validation failed")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            self.log_ingestion(pdf_file, 'failed', str(e))
            raise
        
        return self.ingestion_stats
    
    async def _run_extraction(
        self,
        pdf_file: str,
        toc_file: str,
        max_subsections: int = None
    ) -> Dict[str, Any]:
        """Run enhanced subsection extraction."""
        
        extractor = EnhancedSubsectionExtractor(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            max_concurrent=3
        )
        
        # Process all sections or specified maximum
        await extractor.process_subsections(
            toc_file,
            pdf_file,
            max_subsections=max_subsections,
            target_sections=None  # Process all sections
        )
        
        # Load and return results
        results_file = Path('data/processed/subsections_enhanced.json')
        with open(results_file) as f:
            return json.load(f)
    
    def _process_extraction_data(self, extraction_data: Dict[str, Any]):
        """Process extracted data into SQL records and text chunks."""
        
        subsections = extraction_data.get('subsections', [])
        logger.info(f"Processing {len(subsections)} subsections...")
        
        for sub in tqdm(subsections, desc="Processing subsections"):
            if 'error' in sub:
                continue
            
            parent = sub.get('parent_section', '')
            page_ref = sub.get('page_ref', '')
            title = sub.get('subsection_title', '')
            pages = sub.get('pages_processed', '')
            
            # Process fee codes for SQL storage
            for fc in sub.get('fee_codes', []):
                # Map enhanced extraction to SQL schema
                fee_record = {
                    'fee_code': fc.get('code'),
                    'description': fc.get('description', ''),
                    'amount': self._parse_fee_amount(fc),
                    'units': fc.get('units'),
                    'specialty': parent,  # Use parent section as specialty
                    'category': title,    # Use subsection title as category
                    'subcategory': fc.get('subcategory'),
                    'requirements': fc.get('conditions'),
                    'notes': fc.get('notes'),
                    'effective_date': '2024-03-04',  # From PDF filename
                    'end_date': None,
                    'page_number': self._extract_page_number(pages),
                    'section': f"{parent}/{page_ref}",
                    # Store additional fee columns in notes
                    'h_fee': fc.get('h_fee'),
                    'p_fee': fc.get('p_fee'),
                    't_fee': fc.get('t_fee'),
                    'asst_fee': fc.get('asst_fee'),
                    'surg_fee': fc.get('surg_fee'),
                    'anae_fee': fc.get('anae_fee')
                }
                
                self.fee_codes_to_store.append(fee_record)
            
            # Prepare text for ChromaDB embeddings
            # Create a searchable text representation of the subsection
            subsection_text = self._create_subsection_text(sub)
            if subsection_text:
                # Extract referenced codes for metadata
                referenced_codes = sub.get('referenced_codes', [])
                referenced_code_list = [rc.get('code') for rc in referenced_codes if rc.get('code')]
                
                self.subsection_texts.append({
                    'text': subsection_text,
                    'fee_codes': sub.get('fee_codes', []),  # Include fee codes for junction table
                    'metadata': {
                        'source_type': 'ohip',
                        'parent_section': parent,
                        'subsection': title,
                        'page_ref': page_ref,
                        'pages': pages,
                        'fee_code_count': len(sub.get('fee_codes', [])),
                        'referenced_codes': json.dumps(referenced_code_list) if referenced_code_list else '',  # Convert list to JSON string
                        'referenced_code_count': len(referenced_code_list),
                        'has_tables': sub.get('table_structures_detected', {}).get('multi_column', False)
                    }
                })
    
    def _parse_fee_amount(self, fee_code: Dict) -> float:
        """Parse fee amount from various fee fields."""
        
        # Try single fee first
        if fee_code.get('fee'):
            try:
                # Handle percentage increases
                if '%' in str(fee_code['fee']):
                    return None  # Store as note instead
                # Parse dollar amount
                cleaned = str(fee_code['fee']).replace('$', '').replace(',', '').strip()
                return float(cleaned)
            except:
                pass
        
        # Try H/P fees (use professional fee as primary)
        if fee_code.get('p_fee'):
            try:
                cleaned = str(fee_code['p_fee']).replace('$', '').replace(',', '').strip()
                return float(cleaned)
            except:
                pass
        
        return None
    
    def _extract_page_number(self, pages_str: str) -> int:
        """Extract first page number from pages string like '35-53'."""
        if '-' in pages_str:
            try:
                return int(pages_str.split('-')[0])
            except:
                pass
        return None
    
    def _create_subsection_text(self, subsection: Dict) -> str:
        """Create searchable text representation of subsection."""
        
        parts = []
        
        # Header
        parts.append(f"Section: {subsection.get('parent_section', '')}")
        parts.append(f"Subsection: {subsection.get('subsection_title', '')}")
        parts.append(f"Page Reference: {subsection.get('page_ref', '')}")
        parts.append("")
        
        # Fee codes
        fee_codes = subsection.get('fee_codes', [])
        if fee_codes:
            parts.append(f"Fee Codes ({len(fee_codes)} codes):")
            for fc in fee_codes[:20]:  # Limit to avoid huge texts
                code = fc.get('code', '')
                desc = fc.get('description', '')
                fee = fc.get('fee', '')
                
                if code:
                    fee_str = f" - ${fee}" if fee else ""
                    parts.append(f"  {code}: {desc}{fee_str}")
        
        # Referenced codes (codes mentioned without fee amounts)
        referenced_codes = subsection.get('referenced_codes', [])
        if referenced_codes:
            parts.append("")
            parts.append(f"Referenced Codes ({len(referenced_codes)} references):")
            for rc in referenced_codes[:20]:  # Limit to avoid huge texts
                code = rc.get('code', '')
                context = rc.get('context', '')
                
                if code:
                    context_str = f" (in {context})" if context else ""
                    parts.append(f"  {code}{context_str}")
        
        # Rules and notes
        if subsection.get('rules'):
            parts.append("")
            parts.append("Rules:")
            for rule in subsection['rules']:
                parts.append(f"  - {rule}")
        
        if subsection.get('notes'):
            parts.append("")
            parts.append("Notes:")
            for note in subsection['notes']:
                parts.append(f"  - {note}")
        
        return '\n'.join(parts)
    
    def _store_fee_codes_sql(self):
        """Store fee codes in SQL database."""
        
        if not self.fee_codes_to_store:
            logger.warning("No fee codes to store in SQL")
            return
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        logger.info(f"Storing {len(self.fee_codes_to_store)} fee codes in SQL...")
        
        stored_count = 0
        for code in tqdm(self.fee_codes_to_store, desc="Storing in SQL"):
            try:
                # Combine multi-column fees into notes
                multi_fees = []
                if code.get('h_fee'):
                    multi_fees.append(f"H: ${code['h_fee']}")
                if code.get('p_fee'):
                    multi_fees.append(f"P: ${code['p_fee']}")
                if code.get('asst_fee'):
                    multi_fees.append(f"Asst: {code['asst_fee']}")
                if code.get('surg_fee'):
                    multi_fees.append(f"Surg: {code['surg_fee']}")
                if code.get('anae_fee'):
                    multi_fees.append(f"Anae: {code['anae_fee']}")
                
                # Append multi-column fees to notes
                if multi_fees:
                    fee_info = "Fee structure: " + ", ".join(multi_fees)
                    if code['notes']:
                        code['notes'] = code['notes'] + ". " + fee_info
                    else:
                        code['notes'] = fee_info
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ohip_fee_schedule (
                        fee_code, description, amount, units, specialty,
                        category, subcategory, requirements, notes,
                        effective_date, end_date, page_number, section
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    code['fee_code'],
                    code['description'],
                    code['amount'],
                    code['units'],
                    code['specialty'],
                    code['category'],
                    code['subcategory'],
                    code['requirements'],
                    code['notes'],
                    code['effective_date'],
                    code['end_date'],
                    code['page_number'],
                    code['section']
                ))
                
                stored_count += 1
                self.ingestion_stats['records_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error storing fee code {code.get('fee_code')}: {e}")
                self.ingestion_stats['records_failed'] += 1
                self.ingestion_stats['errors'].append(str(e))
        
        conn.commit()
        logger.info(f"✓ Stored {stored_count} fee codes in SQL database")
    
    def _store_chunks_chroma(self, source_file: str):
        """Store subsection texts in ChromaDB for vector search."""
        
        if not self.subsection_texts:
            logger.warning("No subsection texts to store in ChromaDB")
            return
        
        logger.info(f"Creating chunks for {len(self.subsection_texts)} subsections...")
        
        all_chunks = []
        chunk_to_fees = {}  # Map chunk_id to list of fee codes
        
        for sub_text in self.subsection_texts:
            # Extract fee codes from metadata
            fee_codes_in_section = []
            if 'fee_codes' in sub_text:
                fee_codes_in_section = [fc['code'] for fc in sub_text.get('fee_codes', []) if fc.get('code')]
            
            # Create chunks from subsection text
            chunks = self.chunk_text(
                sub_text['text'],
                chunk_size=1000,
                chunk_overlap=200,
                metadata=sub_text['metadata']
            )
            
            # Track fee codes for each chunk
            for chunk in chunks:
                chunk_to_fees[chunk['chunk_id']] = fee_codes_in_section
                # Add fee codes to chunk metadata
                chunk['metadata']['fee_codes_list'] = ','.join(fee_codes_in_section[:20])  # Limit for metadata
            
            all_chunks.extend(chunks)
        
        logger.info(f"Storing {len(all_chunks)} chunks in ChromaDB...")
        
        # Store chunks with embeddings
        stored = self.store_chunks_with_embeddings(
            all_chunks,
            Path(source_file).name
        )
        
        # Populate junction table
        self._populate_chunk_fee_junction(chunk_to_fees)
        
        # Update fee_codes_list column in document_chunks
        self._update_chunk_fee_lists(chunk_to_fees)
        
        logger.info(f"✓ Stored {stored} chunks in ChromaDB vector store")
    
    def _populate_chunk_fee_junction(self, chunk_to_fees: Dict[str, List[str]]):
        """Populate the chunk_fee_codes junction table."""
        
        if not chunk_to_fees:
            return
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        junction_count = 0
        for chunk_id, fee_codes in chunk_to_fees.items():
            for fee_code in fee_codes:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO chunk_fee_codes (chunk_id, fee_code, relevance_score)
                        VALUES (?, ?, ?)
                    """, (chunk_id, fee_code, 1.0))
                    junction_count += 1
                except Exception as e:
                    logger.warning(f"Could not link chunk {chunk_id} to fee {fee_code}: {e}")
        
        conn.commit()
        logger.info(f"  Created {junction_count} chunk-fee relationships in junction table")
    
    def _update_chunk_fee_lists(self, chunk_to_fees: Dict[str, List[str]]):
        """Update fee_codes_list column in document_chunks table."""
        
        if not chunk_to_fees:
            return
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        for chunk_id, fee_codes in chunk_to_fees.items():
            if fee_codes:
                fee_list_str = ','.join(fee_codes[:50])  # Limit to 50 codes
                try:
                    cursor.execute("""
                        UPDATE document_chunks 
                        SET fee_codes_list = ? 
                        WHERE chunk_id = ?
                    """, (fee_list_str, chunk_id))
                except Exception as e:
                    logger.warning(f"Could not update fee list for chunk {chunk_id}: {e}")
        
        conn.commit()
        logger.info(f"  Updated fee_codes_list for {len(chunk_to_fees)} chunks")
    
    def validate_ingestion(self) -> bool:
        """Validate ingestion completed successfully."""
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Check SQL fee schedule
        cursor.execute("SELECT COUNT(*) FROM ohip_fee_schedule")
        fee_count = cursor.fetchone()[0]
        logger.info(f"  SQL: {fee_count} fee codes in ohip_fee_schedule")
        
        # Check SQL chunks
        cursor.execute(
            "SELECT COUNT(*) FROM document_chunks WHERE source_type = ?",
            (self.source_type,)
        )
        chunk_count = cursor.fetchone()[0]
        logger.info(f"  SQL: {chunk_count} chunks in document_chunks")
        
        # Check ChromaDB
        try:
            chroma_count = self.collection.count()
            logger.info(f"  ChromaDB: {chroma_count} vectors in collection")
        except:
            chroma_count = 0
        
        # Show sample fee codes
        if fee_count > 0:
            cursor.execute("""
                SELECT fee_code, description, amount, category
                FROM ohip_fee_schedule
                WHERE amount IS NOT NULL
                LIMIT 3
            """)
            samples = cursor.fetchall()
            
            logger.info("\n  Sample fee codes in database:")
            for sample in samples:
                logger.info(f"    {sample[0]}: {sample[1][:50]}... ${sample[2]:.2f}" if sample[2] else f"    {sample[0]}: {sample[1][:50]}...")
        
        return fee_count > 0 and (chunk_count > 0 or chroma_count > 0)


async def main():
    """Run enhanced OHIP ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced OHIP data ingestion')
    parser.add_argument('--pdf', default='data/ontario/ohip/moh-schedule-benefit-2024-03-04.pdf',
                       help='Path to OHIP PDF')
    parser.add_argument('--toc', default='data/processed/toc_extracted.json',
                       help='Path to TOC JSON')
    parser.add_argument('--extracted', default=None,
                       help='Path to pre-extracted data (skip extraction)')
    parser.add_argument('--max-subsections', type=int, default=None,
                       help='Maximum subsections to process')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database before ingestion')
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        db = init_database()
        logger.info("✓ Database initialized")
    
    # Run ingestion
    ingester = EnhancedOHIPIngester(
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    with ingester:
        stats = await ingester.ingest_enhanced(
            args.pdf,
            args.toc,
            args.extracted,
            args.max_subsections
        )
    
    print("\n" + "="*60)
    print("ENHANCED INGESTION COMPLETE")
    print("="*60)
    print(f"Records processed: {stats['records_processed']}")
    print(f"Records failed: {stats['records_failed']}")
    print(f"Chunks created: {stats['chunks_created']}")
    print(f"Embeddings created: {stats['embeddings_created']}")
    if stats['errors']:
        print(f"Errors: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"  - {error}")

if __name__ == '__main__':
    asyncio.run(main())