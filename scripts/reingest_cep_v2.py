#!/usr/bin/env python3
"""Re-run CEP ingestion v2 with parent/child chunking."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_agents.dr_opa_agent.ingestion.cep.ingester_v2 import CEPIngesterV2
import chromadb

def main():
    # Delete existing collection using SAME settings as ingester
    from chromadb.config import Settings
    print("Deleting existing opa_cep_corpus collection...")
    client = chromadb.PersistentClient(
        path='data/dr_opa_agent/chroma',
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False,
            is_persistent=True
        )
    )
    try:
        client.delete_collection('opa_cep_corpus')
        print('✓ Deleted existing collection')
    except Exception as e:
        print(f'No existing collection to delete: {e}')

    # Close client to avoid settings conflict
    del client

    # Run ingestion
    print("\nInitializing CEP Ingester V2...")
    ingester = CEPIngesterV2()

    print("Starting full ingestion...")
    result = ingester.ingest_all_tools()

    print(f"\n✅ CEP Ingestion Complete!")
    print(f"Tools ingested: {result.get('total_tools', 0)}")
    print(f"Total chunks: {result.get('total_chunks', 0)}")
    print(f"Parent chunks: {result.get('parent_chunks', 0)}")
    print(f"Child chunks: {result.get('child_chunks', 0)}")

if __name__ == "__main__":
    main()
