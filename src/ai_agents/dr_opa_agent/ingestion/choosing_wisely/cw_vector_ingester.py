"""Choosing Wisely vector ingestion module.

This module handles ingestion of Choosing Wisely Canada recommendations
into Chroma vector database for semantic search and retrieval.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChoosingWiselyVectorIngester:
    """Ingester for Choosing Wisely recommendations into Chroma vector store."""
    
    # Chunking parameters optimized for recommendations
    CHUNK_SIZE = 1000  # Characters per chunk
    CHUNK_OVERLAP = 200  # Overlap between chunks
    BATCH_SIZE = 100  # Embeddings per batch
    
    def __init__(
        self,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        collection_name: str = "choosing_wisely_recommendations",
        use_railway: bool = False,
        railway_url: Optional[str] = None
    ):
        """Initialize Choosing Wisely vector ingester.
        
        Args:
            chroma_path: Path to local Chroma database
            openai_api_key: OpenAI API key for embeddings
            collection_name: Name of Chroma collection
            use_railway: Whether to use Railway HTTP client
            railway_url: Railway Chroma server URL
        """
        self.collection_name = collection_name
        self.use_railway = use_railway
        
        # Initialize OpenAI client for embeddings
        self.openai_client = None
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        elif os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI()
        else:
            logger.warning("No OpenAI API key provided - embeddings will not be generated")
        
        # Initialize Chroma client
        if use_railway and railway_url:
            # Railway HTTP client
            self.chroma_client = chromadb.HttpClient(
                host=railway_url.replace("http://", "").replace("https://", "").split(":")[0],
                port=int(railway_url.split(":")[-1]) if ":" in railway_url else 8000
            )
            logger.info(f"Connected to Railway Chroma at {railway_url}")
        else:
            # Local persistent client
            chroma_path = chroma_path or "data/dr_opa_agent/chroma"
            Path(chroma_path).mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Using local Chroma at {chroma_path}")
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )
        logger.info(f"Using collection: {self.collection_name}")
    
    def create_chunks_from_recommendation(
        self, 
        recommendation: Dict[str, Any], 
        specialty_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create chunks from a single recommendation.
        
        Args:
            recommendation: Recommendation data with title, description, references
            specialty_metadata: Document-level metadata (specialty, organization, etc.)
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Create recommendation text
        rec_text = f"Recommendation #{recommendation.get('number', 'N/A')}: {recommendation.get('title', '')}\n\n"
        rec_text += f"{recommendation.get('description', '')}"
        
        # Add references if present
        references = recommendation.get('references', [])
        if references:
            rec_text += f"\n\nReferences:\n"
            for ref in references:
                rec_text += f"- {ref}\n"
        
        # Create metadata for this recommendation
        metadata = {
            **specialty_metadata,  # Include all specialty-level metadata
            'recommendation_number': recommendation.get('number'),
            'recommendation_title': recommendation.get('title', ''),
            'has_references': len(references) > 0,
            'reference_count': len(references),
            'chunk_type': 'recommendation',
            'text_length': len(rec_text)
        }
        
        # If text is short enough, create single chunk
        if len(rec_text) <= self.CHUNK_SIZE:
            chunk_id = self._generate_chunk_id(
                specialty_metadata['specialty'],
                recommendation.get('number', 0)
            )
            chunks.append({
                'id': chunk_id,
                'text': rec_text,
                'metadata': metadata
            })
        else:
            # Split into overlapping chunks
            for i, chunk_text in enumerate(self._split_text(rec_text)):
                chunk_id = self._generate_chunk_id(
                    specialty_metadata['specialty'],
                    recommendation.get('number', 0),
                    chunk_index=i
                )
                chunk_metadata = {
                    **metadata,
                    'chunk_index': i,
                    'is_partial': True
                }
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
        
        return chunks
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                for sep in ['. ', '.\n', '? ', '! ']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep != -1:
                        end = last_sep + len(sep) - 1
                        break
            
            chunks.append(text[start:end])
            start = end - self.CHUNK_OVERLAP
            
            # Avoid infinite loop
            if start >= len(text) - 10:
                break
        
        return chunks
    
    def _generate_chunk_id(
        self, 
        specialty: str, 
        rec_number: int, 
        chunk_index: int = 0
    ) -> str:
        """Generate unique chunk ID."""
        specialty_clean = specialty.lower().replace(' ', '_').replace('-', '_')
        return f"cw_{specialty_clean}_rec{rec_number}_chunk{chunk_index}"
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.openai_client:
            logger.warning("No OpenAI client - returning empty embeddings")
            return [[0.0] * 1536 for _ in texts]  # Return zero vectors
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [[0.0] * 1536 for _ in texts]
    
    def ingest_specialty(self, json_path: str) -> Dict[str, Any]:
        """Ingest a single specialty JSON file.
        
        Args:
            json_path: Path to specialty JSON file
            
        Returns:
            Ingestion statistics
        """
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            specialty = data.get('specialty', 'Unknown')
            logger.info(f"Ingesting {specialty} with {len(data.get('recommendations', []))} recommendations")
            
            # Prepare specialty-level metadata
            specialty_metadata = {
                'source': 'choosing_wisely',
                'source_org': 'choosing_wisely_canada',
                'specialty': specialty,
                'organization': data.get('organization', ''),
                'last_updated': data.get('last_updated', ''),
                'has_methodology': bool(data.get('methodology')),
                'total_sources': len(data.get('all_sources', [])),
                'ingested_at': datetime.now().isoformat()
            }
            
            # Create chunks for each recommendation
            all_chunks = []
            for rec in data.get('recommendations', []):
                chunks = self.create_chunks_from_recommendation(rec, specialty_metadata)
                all_chunks.extend(chunks)
            
            # Process chunks in batches
            for i in range(0, len(all_chunks), self.BATCH_SIZE):
                batch = all_chunks[i:i + self.BATCH_SIZE]
                
                # Extract components
                ids = [c['id'] for c in batch]
                texts = [c['text'] for c in batch]
                metadatas = [c['metadata'] for c in batch]
                
                # Generate embeddings
                embeddings = self.generate_embeddings(texts)
                
                # Add to Chroma
                self.collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings if embeddings[0] != [0.0] * 1536 else None
                )
                
                logger.info(f"  Added batch {i//self.BATCH_SIZE + 1} ({len(batch)} chunks)")
            
            logger.info(f"✓ Successfully ingested {specialty}: {len(all_chunks)} chunks")
            
            return {
                'success': True,
                'specialty': specialty,
                'recommendations': len(data.get('recommendations', [])),
                'chunks_created': len(all_chunks),
                'json_path': json_path
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {json_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'json_path': json_path
            }
    
    def ingest_all(self, json_dir: str = None) -> Dict[str, Any]:
        """Ingest all Choosing Wisely JSON files.
        
        Args:
            json_dir: Directory containing JSON files
            
        Returns:
            Overall ingestion statistics
        """
        if not json_dir:
            # Default to current directory where extractions are saved
            json_dir = "."
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter to only choosing wisely files (exclude other JSON)
        cw_files = [
            f for f in json_files 
            if not any(skip in f.name.lower() for skip in [
                'section_map', 'test', 'config', 'package'
            ])
        ]
        
        logger.info(f"Found {len(cw_files)} Choosing Wisely JSON files to ingest")
        
        results = []
        total_chunks = 0
        total_recommendations = 0
        
        for json_file in cw_files:
            result = self.ingest_specialty(str(json_file))
            results.append(result)
            
            if result['success']:
                total_chunks += result['chunks_created']
                total_recommendations += result['recommendations']
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        # Print summary
        print("\n" + "=" * 60)
        print("CHOOSING WISELY INGESTION SUMMARY")
        print("=" * 60)
        print(f"Files processed: {len(cw_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total recommendations: {total_recommendations}")
        print(f"Total chunks created: {total_chunks}")
        print(f"Collection: {self.collection_name}")
        print(f"Storage: {'Railway' if self.use_railway else 'Local'}")
        
        if failed > 0:
            print("\n❌ Failed files:")
            for r in results:
                if not r['success']:
                    print(f"  - {Path(r['json_path']).name}: {r.get('error')}")
        
        return {
            'success': successful > 0,
            'files_processed': len(cw_files),
            'successful': successful,
            'failed': failed,
            'total_recommendations': total_recommendations,
            'total_chunks': total_chunks,
            'results': results
        }


def main():
    """Main entry point for Choosing Wisely vector ingestion."""
    import argparse
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(
        description='Ingest Choosing Wisely recommendations into Chroma'
    )
    parser.add_argument(
        '--json-dir',
        default='.',
        help='Directory containing JSON files'
    )
    parser.add_argument(
        '--chroma-path',
        default='data/dr_opa_agent/chroma',
        help='Path to local Chroma database'
    )
    parser.add_argument(
        '--collection',
        default='choosing_wisely_recommendations',
        help='Chroma collection name'
    )
    parser.add_argument(
        '--use-railway',
        action='store_true',
        help='Use Railway Chroma server instead of local'
    )
    parser.add_argument(
        '--railway-url',
        default='http://localhost:8000',
        help='Railway Chroma server URL'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key for embeddings'
    )
    parser.add_argument(
        '--specialty',
        help='Ingest only a specific specialty JSON file'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Initialize ingester
    ingester = ChoosingWiselyVectorIngester(
        chroma_path=args.chroma_path,
        openai_api_key=args.api_key,
        collection_name=args.collection,
        use_railway=args.use_railway,
        railway_url=args.railway_url
    )
    
    # Ingest files
    if args.specialty:
        # Single specialty
        json_file = Path(args.json_dir) / f"{args.specialty}.json"
        if json_file.exists():
            result = ingester.ingest_specialty(str(json_file))
            if result['success']:
                print(f"\n✅ Successfully ingested {args.specialty}")
            else:
                print(f"\n❌ Failed to ingest {args.specialty}: {result['error']}")
        else:
            print(f"\n❌ File not found: {json_file}")
    else:
        # All specialties
        result = ingester.ingest_all(args.json_dir)
        
        if result['success']:
            print("\n✅ Ingestion completed successfully!")
        else:
            print("\n❌ Ingestion completed with errors")


if __name__ == "__main__":
    main()