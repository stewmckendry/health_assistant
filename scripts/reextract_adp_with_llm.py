#!/usr/bin/env python3
"""
Re-extract all ADP PDFs using the enhanced LLM-based extractor
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the enhanced extractor and ingester
from src.agents.dr_off_agent.ingestion.extractors.adp_extractor import EnhancedADPExtractor, ADPSection
from src.agents.dr_off_agent.ingestion.ingesters.adp_ingester import EnhancedADPIngester


def infer_doc_type(pdf_path: str) -> str:
    """Infer document type from filename"""
    path_lower = str(pdf_path).lower()
    
    # Map filenames to document types
    if 'communication' in path_lower:
        return 'comm_aids'
    elif 'mobility' in path_lower:
        return 'mobility'
    elif 'respiratory' in path_lower:
        return 'respiratory'
    elif 'oxygen' in path_lower:
        return 'oxygen'
    elif 'hearing' in path_lower:
        return 'hearing'
    elif 'visual' in path_lower:
        return 'visual'
    elif 'prosthesis' in path_lower or 'prosthetic' in path_lower:
        return 'prosthetics'
    elif 'orthotic' in path_lower:
        return 'orthotics'
    elif 'insulin' in path_lower or 'glucose' in path_lower:
        return 'diabetes'
    elif 'pressure' in path_lower:
        return 'pressure_mod'
    elif 'policies-and-procedures' in path_lower:
        return 'core_manual'
    else:
        return 'general'


def main():
    # Find all ADP PDFs
    pdf_dir = Path("data/dr_off_agent/ontario/adp")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} ADP PDFs to process")
    print("=" * 60)
    
    # Initialize extractor with LLM support
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Initialize ingester
    ingester = EnhancedADPIngester(
        db_path="data/ohip.db",
        chroma_path="data/dr_off_agent/processed/dr_off/chroma",
        collection_name="adp_documents"
    )
    
    # Track statistics
    total_sections = 0
    total_exclusions = 0
    total_funding_rules = 0
    files_with_battery_exclusions = []
    
    # Process each PDF
    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        print("-" * 50)
        
        # Infer document type
        doc_type = infer_doc_type(pdf_path)
        print(f"  Document type: {doc_type}")
        
        try:
            # Extract sections with LLM enhancement
            sections = extractor.extract(str(pdf_path), adp_doc=doc_type)
            print(f"  Extracted {len(sections)} sections")
            
            # Count exclusions and funding rules
            file_exclusions = sum(len(s.exclusions) for s in sections)
            file_funding = sum(len(s.funding) for s in sections)
            
            print(f"  Found {file_exclusions} exclusions")
            print(f"  Found {file_funding} funding rules")
            
            # Check for battery exclusions
            battery_found = False
            for section in sections:
                for exc in section.exclusions:
                    if 'batter' in str(exc).lower():
                        battery_found = True
                        break
                if battery_found:
                    break
            
            if battery_found:
                print(f"  ✅ Battery exclusions detected!")
                files_with_battery_exclusions.append(pdf_path.name)
            
            # Save extracted data to file
            output_dir = Path("data/dr_off_agent/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{doc_type}_extracted_llm.json"
            extractor.save_results(sections, str(output_file))
            print(f"  Saved to: {output_file.name}")
            
            # Ingest into database and vector store
            print(f"  Ingesting into database...")
            for section in sections:
                ingester.ingest_section(section)
            ingester.conn.commit()
            print(f"  ✅ Ingested {len(sections)} sections")
            
            # Update totals
            total_sections += len(sections)
            total_exclusions += file_exclusions
            total_funding_rules += file_funding
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total sections extracted: {total_sections}")
    print(f"Total exclusions found: {total_exclusions}")
    print(f"Total funding rules found: {total_funding_rules}")
    print(f"Files with battery exclusions: {len(files_with_battery_exclusions)}")
    
    if files_with_battery_exclusions:
        print("\nFiles containing battery exclusions:")
        for filename in files_with_battery_exclusions:
            print(f"  - {filename}")
    
    # Get final database stats
    stats = ingester.get_stats()
    print("\nDatabase Statistics:")
    print(f"  Funding rules in DB: {stats['funding_rules']}")
    print(f"  Exclusions in DB: {stats['exclusions']}")
    print(f"  Embeddings in vector store: {stats['embeddings']}")
    
    # Close connections
    ingester.close()
    
    print("\n✅ Re-extraction complete!")


if __name__ == "__main__":
    main()