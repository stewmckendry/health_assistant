#!/usr/bin/env python3
"""
Run ODB (Ontario Drug Benefit) formulary data ingestion
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_off_agent.ingestion.ingesters.odb_ingester import ODBIngester

def main():
    """Run ODB ingestion"""
    print("🚀 Starting ODB Formulary Data Ingestion...")
    
    # Path to ODB XML file
    xml_file = "data/dr_off_agent/ontario/odb/moh-ontario-drug-benefit-odb-formulary-edition-43-data-extract-en-2025-08-29.xml"
    
    if not Path(xml_file).exists():
        print(f"❌ XML file not found: {xml_file}")
        return 1
    
    # Get OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️ Warning: No OPENAI_API_KEY found - embeddings will be skipped")
    
    ingester = ODBIngester(
        db_path="data/dr_off_agent/processed/odb_processed_data.db",
        chroma_path="data/dr_off_agent/processed/dr_off/chroma",
        openai_api_key=openai_key
    )
    
    try:
        # Run ingestion
        stats = ingester.ingest(xml_file)
        print(f"✅ ODB ingestion complete!")
        print(f"   Statistics: {stats}")
        
    except Exception as e:
        print(f"❌ Error during ODB ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())