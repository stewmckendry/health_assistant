#!/usr/bin/env python3
"""
Ingest the extracted ADP JSON data into SQLite and ChromaDB.
This script reads the output from run_adp_extraction.py and loads it into the databases.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path to import modules properly
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import from the proper path
from src.agents.dr_off_agent.ingestion.ingesters.adp_ingester import EnhancedADPIngester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main ingestion function"""
    
    # Path to extracted JSON file
    # Go up 5 levels to reach project root from src/agents/dr_off_agent/ingestion/run_adp_ingestion.py
    json_file = Path(__file__).parent.parent.parent.parent.parent / "data" / "processed" / "dr_off" / "adp" / "adp_focused_extraction_llm.json"
    
    if not json_file.exists():
        print(f"❌ Extracted JSON file not found: {json_file}")
        print("   Please run run_adp_extraction.py first")
        return
    
    print("ADP Ingestion to SQLite and ChromaDB")
    print("=" * 60)
    print(f"Input file: {json_file}")
    
    # Initialize ingester with proper paths
    # Use ohip.db as the central database for all OHIP, ODB, and ADP data
    project_root = Path(__file__).parent.parent.parent.parent.parent
    db_path = project_root / "data" / "ohip.db"
    chroma_path = project_root / "data" / "processed" / "dr_off" / "chroma"
    
    print(f"Database: {db_path}")
    print(f"Chroma: {chroma_path}")
    print()
    
    # Initialize ingester
    ingester = EnhancedADPIngester(
        db_path=str(db_path),
        chroma_path=str(chroma_path),
        collection_name="adp_v1"
    )
    
    # Ingest the JSON file
    try:
        count = ingester.ingest_json(str(json_file))
        print(f"\n✅ Successfully ingested {count} ADP sections")
        
        # Show statistics
        stats = ingester.get_stats()
        print("\n" + "=" * 60)
        print("DATABASE STATISTICS")
        print("=" * 60)
        print(f"Funding rules: {stats['funding_rules']}")
        print(f"Exclusions: {stats['exclusions']}")
        print(f"Unique documents: {stats['unique_docs']}")
        print(f"Embeddings in Chroma: {stats['embeddings']}")
        
        # Test search functionality
        print("\n" + "=" * 60)
        print("TESTING SEARCH")
        print("=" * 60)
        
        test_queries = [
            "battery exclusions",
            "wheelchair funding",
            "CEP eligibility"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = ingester.search_embeddings(query, n_results=2)
            for i, result in enumerate(results, 1):
                print(f"  {i}. Section {result['section']}: {result['title']}")
                print(f"     Distance: {result['distance']:.3f}")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        ingester.close()
    
    print("\n✅ Ingestion complete!")
    return 0


if __name__ == "__main__":
    exit(main())