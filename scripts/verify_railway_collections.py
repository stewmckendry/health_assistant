#!/usr/bin/env python3
"""Verify Railway ChromaDB collections after upload."""
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAILWAY_URL = "https://healthassistant-production-3613.up.railway.app"

async def check_collections():
    """Check Railway ChromaDB collections."""
    logger.info("🔍 Checking Railway ChromaDB Collections")
    logger.info(f"Railway URL: {RAILWAY_URL}\n")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{RAILWAY_URL}/admin/chroma-collections") as response:
            if response.status == 200:
                result = await response.json()

                logger.info(f"Total collections: {result.get('total_collections', 0)}\n")

                for coll in result.get('collections', []):
                    logger.info(f"  📦 {coll['name']}: {coll['count']} chunks")

                return result
            else:
                error = await response.text()
                logger.error(f"Failed to get collections: {error}")
                return None

if __name__ == "__main__":
    asyncio.run(check_collections())
