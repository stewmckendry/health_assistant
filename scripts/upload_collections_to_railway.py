#!/usr/bin/env python3
"""Upload all local ChromaDB collections to Railway."""
import asyncio
import aiohttp
import chromadb
from chromadb.config import Settings
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAILWAY_URL = "https://healthassistant-production-3613.up.railway.app"

async def upload_collection(collection_name: str, source_path: str):
    """Upload a single collection to Railway."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Uploading {collection_name}...")
    logger.info(f"{'='*80}")

    # Get collection from local ChromaDB
    client = chromadb.PersistentClient(
        path=source_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False,
            is_persistent=True
        )
    )

    collection = client.get_collection(collection_name)

    # Get all data
    results = collection.get(include=['documents', 'metadatas', 'embeddings'])

    logger.info(f"  Local chunks: {len(results['ids'])}")

    # Convert embeddings to lists (from numpy arrays)
    embeddings = []
    raw_embeddings = results.get('embeddings')
    if raw_embeddings is not None and len(raw_embeddings) > 0:
        for emb in raw_embeddings:
            if hasattr(emb, 'tolist'):
                embeddings.append(emb.tolist())
            elif isinstance(emb, list):
                embeddings.append(emb)
            else:
                embeddings.append(list(emb))

    # Prepare payload for Railway
    payload = {
        "collection_name": collection_name,
        "documents": results['documents'],
        "metadatas": results['metadatas'],
        "ids": results['ids'],
        "embeddings": embeddings,
        "metadata": {
            "source": "local_chroma",
            "uploaded_at": datetime.now().isoformat(),
            "chunk_count": len(results['ids'])
        }
    }

    # Send to Railway
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{RAILWAY_URL}/admin/load-chroma",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=600)
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"  ✅ Success: {result.get('message', 'Uploaded')}")
                logger.info(f"  Documents loaded: {result.get('documents_loaded', 0)}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"  ❌ Failed: HTTP {response.status}")
                logger.error(f"  Error: {error_text[:500]}")
                return False

async def main():
    logger.info("🚂 Uploading Collections to Railway")
    logger.info(f"Railway URL: {RAILWAY_URL}\n")

    # Dr. OPA collections
    opa_collections = [
        'opa_cep_corpus',
        'opa_quality_standards_corpus',
        'opa_choosing_wisely_corpus',
        'opa_cpso_corpus',
        'opa_pho_corpus'
    ]

    # Dr. OFF collections
    off_collections = [
        'ohip_documents',
        'adp_documents',
        'odb_documents'
    ]

    opa_path = 'data/dr_opa_agent/chroma'
    off_path = 'data/dr_off_agent/processed/dr_off/chroma'

    success_count = 0
    fail_count = 0

    # Upload OPA collections
    logger.info("=" * 80)
    logger.info("Dr. OPA Collections")
    logger.info("=" * 80)
    for coll_name in opa_collections:
        success = await upload_collection(coll_name, opa_path)
        if success:
            success_count += 1
        else:
            fail_count += 1

    # Upload Dr. OFF collections
    logger.info("\n" + "=" * 80)
    logger.info("Dr. OFF Collections")
    logger.info("=" * 80)
    for coll_name in off_collections:
        success = await upload_collection(coll_name, off_path)
        if success:
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"\n{'='*80}")
    logger.info(f"📊 Upload Summary")
    logger.info(f"{'='*80}")
    logger.info(f"  ✅ Successful: {success_count}")
    logger.info(f"  ❌ Failed: {fail_count}")
    logger.info(f"\n✨ Upload complete!")

if __name__ == "__main__":
    asyncio.run(main())
