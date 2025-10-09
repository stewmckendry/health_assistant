#!/usr/bin/env python3
"""
Upload ohip.db to Railway persistent storage.

This script exports the local ohip.db and uploads it to Railway via the /admin/load-database endpoint.

Usage:
    python scripts/upload_ohip_to_railway.py
"""

import asyncio
import aiohttp
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAILWAY_URL = os.getenv("NEXT_PUBLIC_API_URL", "https://healthassistant-production-3613.up.railway.app")


def export_sqlite_database(db_path: Path) -> Dict[str, Any]:
    """
    Export SQLite database to JSON format.

    Args:
        db_path: Path to SQLite database

    Returns:
        Dictionary with tables and metadata
    """
    logger.info(f"Exporting database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")

    exported_data = {}
    total_rows = 0

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        # Convert sqlite3.Row to dict
        table_data = []
        for row in rows:
            table_data.append(dict(row))

        exported_data[table] = table_data
        total_rows += len(table_data)
        logger.info(f"  Exported {table}: {len(table_data)} rows")

    conn.close()

    logger.info(f"Total rows exported: {total_rows}")

    return {
        "tables": exported_data,
        "metadata": {
            "source": str(db_path),
            "exported_at": datetime.now().isoformat(),
            "total_rows": total_rows,
            "table_count": len(tables)
        }
    }


async def upload_database(
    session: aiohttp.ClientSession,
    db_name: str,
    db_path: Path
) -> bool:
    """
    Upload database to Railway.

    Args:
        session: aiohttp session
        db_name: Target database name (e.g., "ohip.db")
        db_path: Local path to source database

    Returns:
        True if successful
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Uploading {db_name} to Railway")
    logger.info(f"{'='*80}")

    # Export database
    export_data = export_sqlite_database(db_path)

    # Prepare payload
    payload = {
        "target_db": db_name,
        "tables": export_data["tables"],
        "metadata": export_data["metadata"]
    }

    # Calculate payload size
    payload_size_mb = len(json.dumps(payload)) / (1024 * 1024)
    logger.info(f"Payload size: {payload_size_mb:.2f} MB")

    # Upload to Railway
    logger.info(f"Uploading to {RAILWAY_URL}/admin/load-database...")

    try:
        async with session.post(
            f"{RAILWAY_URL}/admin/load-database",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"  ✅ Success!")
                logger.info(f"  Tables loaded: {result.get('tables_loaded', 0)}")
                logger.info(f"  Total rows: {result.get('total_rows', 0)}")
                logger.info(f"  Database path: {result.get('database_path', 'N/A')}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"  ❌ Failed: HTTP {response.status}")
                logger.error(f"  Error: {error_text[:1000]}")
                return False

    except asyncio.TimeoutError:
        logger.error("  ❌ Upload timed out (>10 minutes)")
        return False
    except Exception as e:
        logger.error(f"  ❌ Upload failed: {e}")
        return False


async def main():
    logger.info("🚂 Uploading OHIP Database to Railway")
    logger.info(f"Railway URL: {RAILWAY_URL}\n")

    # Database to upload
    db_path = Path("data/ohip.db")

    if not db_path.exists():
        logger.error(f"❌ Database not found: {db_path}")
        logger.error("Please ensure data/ohip.db exists before running this script.")
        return

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    logger.info(f"Database file: {db_path}")
    logger.info(f"Database size: {db_size_mb:.2f} MB\n")

    async with aiohttp.ClientSession() as session:
        success = await upload_database(session, "ohip.db", db_path)

    logger.info(f"\n{'='*80}")
    if success:
        logger.info("✨ Upload complete!")
        logger.info("The ohip.db database is now available at /app/data/ohip.db on Railway")
    else:
        logger.error("❌ Upload failed. Please check the logs above for details.")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
