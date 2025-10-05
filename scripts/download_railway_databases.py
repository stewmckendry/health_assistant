#!/usr/bin/env python3
"""
Download databases from Railway for local evaluation.

This script uses the admin export endpoints to download:
1. ChromaDB collections (ohip_documents, adp_documents, odb_documents, etc.)
2. SQLite databases (ohip.db, opa.db)

Usage:
    python scripts/download_railway_databases.py [--collections NAMES] [--databases NAMES]

Examples:
    # Download everything
    python scripts/download_railway_databases.py

    # Download specific collections
    python scripts/download_railway_databases.py --collections ohip_documents,adp_documents

    # Download only databases
    python scripts/download_railway_databases.py --databases ohip.db,opa.db
"""

import asyncio
import aiohttp
import json
import sqlite3
import chromadb
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Railway URL from environment
RAILWAY_URL = os.getenv("NEXT_PUBLIC_API_URL", "https://healthassistant-production-3613.up.railway.app")


async def get_chroma_stats(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Get list of available ChromaDB collections."""
    logger.info("Fetching ChromaDB collection list...")

    async with session.get(f"{RAILWAY_URL}/admin/chroma-collections") as resp:
        if resp.status != 200:
            raise Exception(f"Failed to get Chroma collections: {resp.status}")
        data = await resp.json()

    # Convert /admin/chroma-collections format to stats format
    collections = {}
    for col_info in data.get("collections", []):
        collections[col_info["name"]] = {"count": col_info["count"]}

    stats = {
        "total_collections": data.get("total_collections", 0),
        "collections": collections
    }

    logger.info(f"Found {stats.get('total_collections', 0)} collections")
    return stats


async def download_chroma_collection(
    session: aiohttp.ClientSession,
    collection_name: str,
    output_dir: Path
) -> int:
    """
    Download a ChromaDB collection from Railway and save locally.

    Args:
        session: aiohttp session
        collection_name: Name of collection to download
        output_dir: Local ChromaDB directory path

    Returns:
        Number of documents downloaded
    """
    logger.info(f"Downloading collection: {collection_name}")

    async with session.get(f"{RAILWAY_URL}/admin/export-chroma/{collection_name}") as resp:
        if resp.status != 200:
            error_text = await resp.text()
            raise Exception(f"Failed to export {collection_name}: {resp.status} - {error_text}")

        data = await resp.json()

    count = data.get("count", 0)
    logger.info(f"  Downloaded {count} documents")

    # Save to local ChromaDB
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = chromadb.PersistentClient(path=str(output_dir))

        # Delete collection if it exists
        try:
            client.delete_collection(collection_name)
            logger.info(f"  Deleted existing collection: {collection_name}")
        except:
            pass

        # Create collection
        collection = client.create_collection(name=collection_name)

        # Add documents in batches
        batch_size = 100
        ids = data["ids"]
        documents = data["documents"]
        metadatas = data["metadatas"]
        embeddings = data.get("embeddings", [])

        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))

            batch_data = {
                "ids": ids[i:batch_end],
                "documents": documents[i:batch_end],
                "metadatas": metadatas[i:batch_end]
            }

            if embeddings:
                batch_data["embeddings"] = embeddings[i:batch_end]

            collection.add(**batch_data)
            logger.info(f"  Loaded batch {i//batch_size + 1}: {batch_end}/{len(ids)} documents")

        logger.info(f"  ✓ Collection {collection_name} saved locally")
        return count

    except Exception as e:
        logger.error(f"  ✗ Error saving collection {collection_name}: {e}")
        raise


async def download_sqlite_database(
    session: aiohttp.ClientSession,
    db_name: str,
    output_path: Path
) -> bool:
    """
    Download SQLite database from Railway and recreate locally.

    Args:
        session: aiohttp session
        db_name: Database filename (e.g., "ohip.db")
        output_path: Local path to save database

    Returns:
        True if successful
    """
    logger.info(f"Downloading database: {db_name}")

    async with session.get(f"{RAILWAY_URL}/admin/export-database/{db_name}") as resp:
        if resp.status != 200:
            error_text = await resp.text()
            raise Exception(f"Failed to export {db_name}: {resp.status} - {error_text}")

        data = await resp.json()

    # Create local database
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if output_path.exists():
        output_path.unlink()
        logger.info(f"  Removed existing database: {output_path}")

    conn = sqlite3.connect(str(output_path))

    total_rows = 0
    tables = data.get("tables", {})

    for table_name, rows in tables.items():
        if not rows:
            logger.info(f"  Skipping empty table: {table_name}")
            continue

        logger.info(f"  Creating table: {table_name} ({len(rows)} rows)")

        # Get column names and types from first row
        columns = list(rows[0].keys())

        # Create table
        column_defs = []
        for col in columns:
            sample_val = rows[0].get(col)
            if isinstance(sample_val, int):
                col_type = "INTEGER"
            elif isinstance(sample_val, float):
                col_type = "REAL"
            else:
                col_type = "TEXT"
            column_defs.append(f'"{col}" {col_type}')

        create_sql = f'CREATE TABLE "{table_name}" ({", ".join(column_defs)})'
        conn.execute(create_sql)

        # Insert data
        placeholders = ", ".join(["?" for _ in columns])
        quoted_columns = ", ".join([f'"{col}"' for col in columns])
        insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'

        for row in rows:
            values = [row.get(col) for col in columns]
            conn.execute(insert_sql, values)

        total_rows += len(rows)

    conn.commit()
    conn.close()

    logger.info(f"  ✓ Database {db_name} saved: {len(tables)} tables, {total_rows} rows")
    return True


async def main():
    """Main download orchestration."""
    parser = argparse.ArgumentParser(description="Download databases from Railway")
    parser.add_argument(
        "--collections",
        type=str,
        help="Comma-separated list of ChromaDB collections to download (default: all)"
    )
    parser.add_argument(
        "--databases",
        type=str,
        help="Comma-separated list of SQLite databases to download (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Output directory for downloaded data (default: data/)"
    )

    args = parser.parse_args()

    logger.info("🚂 Railway Database Download Script")
    logger.info(f"Railway URL: {RAILWAY_URL}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info("")

    # Parse collection and database filters
    collection_filter = args.collections.split(",") if args.collections else None
    database_filter = args.databases.split(",") if args.databases else None

    output_dir = Path(args.output_dir)
    chroma_dir = output_dir / "dr_off_agent" / "processed" / "dr_off" / "chroma"
    chroma_dir_opa = output_dir / "dr_opa_agent" / "chroma"

    async with aiohttp.ClientSession() as session:
        try:
            # Get available collections
            stats = await get_chroma_stats(session)
            available_collections = list(stats.get("collections", {}).keys())

            logger.info(f"\n📦 Available collections: {', '.join(available_collections)}")

            # Download ChromaDB collections
            collections_to_download = collection_filter if collection_filter else available_collections

            logger.info(f"\n⬇️  Downloading {len(collections_to_download)} ChromaDB collections...")
            total_docs = 0

            for collection_name in collections_to_download:
                if collection_name not in available_collections:
                    logger.warning(f"  ⚠️  Collection {collection_name} not found, skipping")
                    continue

                try:
                    # Use appropriate directory based on agent
                    if "opa" in collection_name:
                        target_dir = chroma_dir_opa
                    else:
                        target_dir = chroma_dir

                    count = await download_chroma_collection(session, collection_name, target_dir)
                    total_docs += count
                except Exception as e:
                    logger.error(f"  ✗ Failed to download {collection_name}: {e}")

            logger.info(f"\n✓ Downloaded {total_docs} total documents")

            # Download SQLite databases only if explicitly requested
            if database_filter is not None or (collection_filter is None and args.databases is None):
                databases_to_download = database_filter if database_filter else ["ohip.db", "opa.db"]

                logger.info(f"\n⬇️  Downloading {len(databases_to_download)} SQLite databases...")

                for db_name in databases_to_download:
                    try:
                        db_path = output_dir / db_name
                        await download_sqlite_database(session, db_name, db_path)
                    except Exception as e:
                        logger.error(f"  ✗ Failed to download {db_name}: {e}")
            else:
                logger.info(f"\n⏭️  Skipping SQLite database download (use --databases to download)")

            logger.info(f"\n✅ Download complete!")
            logger.info(f"Data saved to: {output_dir.absolute()}")

        except Exception as e:
            logger.error(f"\n❌ Error: {e}")
            logger.info("\n💡 Troubleshooting:")
            logger.info("1. Verify Railway URL is correct in .env")
            logger.info("2. Check that admin endpoints are deployed on Railway")
            logger.info("3. Ensure Railway app is running")
            logger.info(f"   Test: curl {RAILWAY_URL}/admin/database-status")
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
