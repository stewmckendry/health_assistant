#!/usr/bin/env python3
"""
Script to run OHIP ingestion with the new vector approach
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_off_agent.ingestion.ingesters.ohip_ingester import EnhancedOHIPIngester

def run_ingestion():
    """Run OHIP ingestion processing all JSON files"""
    
    input_dir = Path("data/dr_off_agent/processed/subsection_chunks_enhanced")
    output_db = "data/dr_off_agent/processed/ohip_processed_data.db"
    chroma_path = "data/dr_off_agent/processed/dr_off/chroma"
    
    print(f"Starting OHIP ingestion...")
    print(f"Input directory: {input_dir}")
    print(f"Output database: {output_db}")
    print(f"Vector database: {chroma_path}")
    
    # Verify environment variables are loaded
    import os
    print(f"OpenAI API Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    # Create ingester instance with OpenAI API key
    ingester = EnhancedOHIPIngester(
        db_path=output_db,
        chroma_path=chroma_path, 
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Collect all JSON files
    json_files = list(input_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to process")
    
    # Create combined extraction data
    all_subsections = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Convert to expected format
            subsection = {
                'parent_section': data.get('parent_section'),
                'page_ref': data.get('page_ref'),
                'subsection_title': data.get('subsection_title'),
                'pages_processed': data.get('pages_processed'),
                'fee_codes': data.get('fee_codes', []),
                'referenced_codes': data.get('referenced_codes', []),
                'rules': data.get('rules', []),
                'notes': data.get('notes', []),
                'table_structures_detected': data.get('table_structures_detected', {})
            }
            all_subsections.append(subsection)
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue
    
    print(f"Successfully loaded {len(all_subsections)} subsections")
    
    # Create combined extraction data
    extraction_data = {
        'subsections': all_subsections
    }
    
    # Process the data
    ingester._process_extraction_data(extraction_data)
    
    # Store in ChromaDB
    ingester._store_chunks_chroma("combined_subsections.json")
    
    print("✓ Ingestion completed successfully!")
    return True

if __name__ == "__main__":
    success = run_ingestion()
    sys.exit(0 if success else 1)