#!/usr/bin/env python3
"""
Build BM25 index from existing ChromaDB collections for Dr. OPA agent.
This is a one-time setup script that creates the Whoosh BM25 index for hybrid retrieval.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.vector_client import VectorClient
from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.bm25_client import BM25Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Build BM25 index from ChromaDB."""

    logger.info("=" * 60)
    logger.info("BM25 Index Builder for Dr. OPA Hybrid Retrieval")
    logger.info("=" * 60)

    # Step 1: Initialize ChromaDB vector client
    logger.info("\n[1/3] Initializing ChromaDB vector client...")
    try:
        # Use default Dr. OPA path (data/dr_opa_agent/chroma)
        vector_client = VectorClient()  # Will use default path
        logger.info("✓ ChromaDB client initialized")

        # Log collection info
        logger.info("\nChromaDB Collections Found:")
        for name, collection in vector_client._collections.items():
            count = collection.count()
            logger.info(f"  • {name}: {count} documents")

    except Exception as e:
        logger.error(f"✗ Failed to initialize ChromaDB: {e}")
        return 1

    # Step 2: Initialize BM25 client
    logger.info("\n[2/3] Initializing BM25 client...")
    try:
        # Use default BM25 path
        bm25_client = BM25Client()  # Will use default path
        logger.info("✓ BM25 client initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize BM25 client: {e}")
        return 1

    # Step 3: Build BM25 index from ChromaDB
    logger.info("\n[3/3] Building BM25 index from ChromaDB collections...")
    try:
        await bm25_client.build_index_from_chroma(vector_client)

        # Verify index
        doc_count = bm25_client.index.doc_count_all()
        logger.info(f"\n✓ BM25 index build complete!")
        logger.info(f"  Total documents indexed: {doc_count}")
        logger.info(f"  Index location: data/processed/dr_opa/bm25_index/")

        # Test search
        logger.info("\n[TEST] Running test BM25 search...")
        test_results = await bm25_client.search("IPAC hand hygiene", sources=['pho'], n_results=5)
        logger.info(f"  Test search returned {len(test_results)} results")
        if test_results:
            title = test_results[0].get('metadata', {}).get('document_title', 'No title')
            logger.info(f"  Top result: {title[:60]}...")

    except Exception as e:
        logger.error(f"✗ Failed to build BM25 index: {e}")
        import traceback
        traceback.print_exc()
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("SUCCESS: BM25 index ready for hybrid retrieval!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("  1. Run evaluation: python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl")
    logger.info("  2. Compare to baseline in eval/results/RESULTS.md")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
