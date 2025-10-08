#!/usr/bin/env python3
"""Show status of local ChromaDB databases - collections and counts."""

import chromadb
from pathlib import Path
from datetime import datetime
import sys

def check_chroma_db(db_path: str, agent_name: str):
    """Check and display ChromaDB status for a given path."""
    db_path = Path(db_path)

    print(f"\n{'='*80}")
    print(f"🗄️  {agent_name}")
    print(f"{'='*80}")
    print(f"📂 Path: {db_path}")

    if not db_path.exists():
        print("❌ Directory does not exist")
        return

    # Check if chroma.sqlite3 exists
    sqlite_file = db_path / "chroma.sqlite3"
    if sqlite_file.exists():
        size_mb = sqlite_file.stat().st_size / (1024 * 1024)
        print(f"💾 Database size: {size_mb:.1f} MB")
    else:
        print("⚠️  No chroma.sqlite3 file found")
        return

    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=str(db_path))

        # List all collections
        collections = client.list_collections()

        if not collections:
            print("📦 Collections: None")
            return

        print(f"📦 Collections ({len(collections)}):\n")

        total_chunks = 0
        for coll in collections:
            count = coll.count()
            total_chunks += count

            # Try to get embedding dimension
            try:
                sample = coll.get(limit=1, include=['embeddings'])
                embeddings = sample.get('embeddings', [])
                if len(embeddings) > 0 and embeddings[0] is not None:
                    dim = len(embeddings[0])
                    print(f"   • {coll.name:40s} {count:>6,} chunks  [{dim} dim]")
                else:
                    print(f"   • {coll.name:40s} {count:>6,} chunks  [no embeddings]")
            except Exception as e:
                print(f"   • {coll.name:40s} {count:>6,} chunks  [error checking dim: {e}]")

        print(f"\n   Total chunks: {total_chunks:,}")

    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {e}")


def main():
    """Show status of all ChromaDB databases."""
    print(f"\n{'='*80}")
    print(f"📊 ChromaDB Status Report")
    print(f"{'='*80}")
    print(f"🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check Dr. OFF ChromaDB
    check_chroma_db(
        "data/dr_off_agent/processed/dr_off/chroma",
        "Dr. OFF Agent ChromaDB"
    )

    # Check Dr. OPA ChromaDB
    check_chroma_db(
        "data/dr_opa_agent/chroma",
        "Dr. OPA Agent ChromaDB"
    )

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
