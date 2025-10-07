"""Backup ChromaDB collection before re-ingestion.

Usage:
    python scripts/backup_collection.py --collection opa_cep_corpus
"""

import argparse
import shutil
from pathlib import Path
from datetime import datetime
import chromadb
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_collection(collection_name: str, chroma_path: str = "data/dr_opa_agent/chroma"):
    """Backup a ChromaDB collection to disk.

    Args:
        collection_name: Name of collection to backup
        chroma_path: Path to ChromaDB directory
    """
    # Create backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"data/dr_opa_agent/backups/{collection_name}_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Backing up collection: {collection_name}")
    logger.info(f"Backup directory: {backup_dir}")

    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(collection_name)

        # Get all chunks
        logger.info("Fetching all chunks...")
        results = collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        chunk_count = len(results['ids'])
        logger.info(f"Found {chunk_count} chunks to backup")

        # Convert embeddings to lists for JSON serialization
        embeddings_as_lists = [emb.tolist() if hasattr(emb, 'tolist') else emb
                               for emb in results['embeddings']]

        # Save chunks to JSON
        backup_data = {
            'collection_name': collection_name,
            'timestamp': timestamp,
            'chunk_count': chunk_count,
            'ids': results['ids'],
            'documents': results['documents'],
            'metadatas': results['metadatas'],
            'embeddings': embeddings_as_lists
        }

        backup_file = backup_dir / "collection_backup.json"
        logger.info(f"Saving backup to: {backup_file}")

        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        # Also save metadata separately for easy inspection
        metadata_file = backup_dir / "metadata_summary.json"
        metadata_summary = {
            'collection_name': collection_name,
            'timestamp': timestamp,
            'chunk_count': chunk_count,
            'sample_metadata': results['metadatas'][0] if results['metadatas'] else {},
            'metadata_fields': sorted(set(results['metadatas'][0].keys())) if results['metadatas'] else []
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata_summary, f, indent=2)

        logger.info(f"✓ Backup complete!")
        logger.info(f"  Chunks backed up: {chunk_count}")
        logger.info(f"  Backup location: {backup_dir}")
        logger.info(f"  Files created:")
        logger.info(f"    - collection_backup.json (full data)")
        logger.info(f"    - metadata_summary.json (metadata info)")

        return str(backup_dir)

    except Exception as e:
        logger.error(f"Error backing up collection: {e}")
        raise


def restore_collection(backup_dir: str, chroma_path: str = "data/dr_opa_agent/chroma"):
    """Restore a collection from backup.

    Args:
        backup_dir: Path to backup directory
        chroma_path: Path to ChromaDB directory
    """
    backup_dir = Path(backup_dir)
    backup_file = backup_dir / "collection_backup.json"

    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    logger.info(f"Restoring collection from: {backup_dir}")

    # Load backup data
    with open(backup_file) as f:
        backup_data = json.load(f)

    collection_name = backup_data['collection_name']
    chunk_count = backup_data['chunk_count']

    logger.info(f"Collection: {collection_name}")
    logger.info(f"Chunks: {chunk_count}")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path)

    # Delete existing collection if it exists
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except:
        pass

    # Create new collection
    collection = client.create_collection(
        name=collection_name,
        metadata={"restored_from": str(backup_dir)}
    )

    # Restore chunks in batches
    batch_size = 100
    for i in range(0, chunk_count, batch_size):
        batch_end = min(i + batch_size, chunk_count)

        collection.add(
            ids=backup_data['ids'][i:batch_end],
            documents=backup_data['documents'][i:batch_end],
            metadatas=backup_data['metadatas'][i:batch_end],
            embeddings=backup_data['embeddings'][i:batch_end]
        )

        logger.info(f"Restored {batch_end}/{chunk_count} chunks")

    logger.info(f"✓ Restore complete!")
    logger.info(f"  Collection: {collection_name}")
    logger.info(f"  Chunks restored: {chunk_count}")


def main():
    parser = argparse.ArgumentParser(description="Backup/restore ChromaDB collections")
    parser.add_argument('--collection', required=True, help='Collection name to backup')
    parser.add_argument('--action', choices=['backup', 'restore'], default='backup', help='Action to perform')
    parser.add_argument('--backup-dir', help='Backup directory (for restore action)')
    parser.add_argument('--chroma-path', default='data/dr_opa_agent/chroma', help='Path to ChromaDB')

    args = parser.parse_args()

    if args.action == 'backup':
        backup_dir = backup_collection(args.collection, args.chroma_path)
        print(f"\nBackup saved to: {backup_dir}")

    elif args.action == 'restore':
        if not args.backup_dir:
            parser.error("--backup-dir required for restore action")
        restore_collection(args.backup_dir, args.chroma_path)
        print(f"\nCollection restored: {args.collection}")


if __name__ == "__main__":
    main()
