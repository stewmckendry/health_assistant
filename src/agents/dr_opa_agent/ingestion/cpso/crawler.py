"""
CPSO Document Crawler with Parallel Processing

Automates extraction and ingestion of all CPSO documents using concurrent processing.
"""

import os
import time
import json
import hashlib
import logging
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue

from .extractor import CPSOExtractor
from .ingestion import CPSOIngester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPSOCrawlerParallel:
    """Crawls CPSO website with parallel processing support."""
    
    LANDING_PAGES = {
        'policies': 'https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies',
        'advice': 'https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Advice-to-the-Profession',
        'statements': 'https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Statements-Positions'
    }
    
    def __init__(self, 
                 output_dir: str = "data/dr_opa_agent",
                 max_workers: int = 5,
                 delay_seconds: float = 0.5,
                 resume_from_checkpoint: bool = True):
        """
        Initialize the parallel CPSO crawler.
        
        Args:
            output_dir: Root directory for saving extracted documents
            max_workers: Maximum number of parallel workers
            delay_seconds: Base delay between requests (will be multiplied by workers)
            resume_from_checkpoint: Whether to resume from last checkpoint
        """
        self.output_dir = output_dir
        self.raw_dir = os.path.join(output_dir, "raw", "cpso")
        self.processed_dir = os.path.join(output_dir, "processed", "cpso")
        self.checkpoint_file = os.path.join(output_dir, ".cpso_crawler_checkpoint.json")
        
        # Create directories
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.max_workers = max_workers
        self.delay_seconds = delay_seconds
        
        # Thread-safe components
        self.processed_urls_lock = Lock()
        self.processed_urls = self._load_checkpoint() if resume_from_checkpoint else set()
        
        # Rate limiting queue for polite crawling
        self.rate_limiter = queue.Queue()
        self._init_rate_limiter()
        
        # Statistics tracking
        self.stats_lock = Lock()
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def _init_rate_limiter(self):
        """Initialize rate limiting tokens."""
        for _ in range(self.max_workers):
            self.rate_limiter.put(None)
    
    def _load_checkpoint(self) -> Set[str]:
        """Load checkpoint file to resume from previous run."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_urls', []))
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        return set()
    
    def _save_checkpoint(self):
        """Save current progress to checkpoint file."""
        try:
            with self.processed_urls_lock:
                with open(self.checkpoint_file, 'w') as f:
                    json.dump({
                        'processed_urls': list(self.processed_urls),
                        'last_updated': datetime.now().isoformat(),
                        'stats': self.stats
                    }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save checkpoint: {e}")
    
    def _fetch_page_with_rate_limit(self, url: str) -> Optional[str]:
        """Fetch HTML content with rate limiting."""
        # Get rate limit token
        token = self.rate_limiter.get()
        
        try:
            time.sleep(self.delay_seconds)
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (research bot; educational purposes)'
            })
            
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
            
        finally:
            # Return rate limit token
            self.rate_limiter.put(token)
    
    def _extract_document_links(self, landing_url: str, doc_type: str) -> List[Dict[str, str]]:
        """Extract all document links from a landing page."""
        logger.info(f"Extracting links from {doc_type} landing page...")
        
        html = self._fetch_page_with_rate_limit(landing_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        documents = []
        
        # Find links based on document type
        if doc_type == 'policies':
            policy_links = soup.find_all('a', href=lambda x: x and '/Policies/' in x)
            
            for link in policy_links:
                if 'Advice-to-the-Profession' in link.get('href', ''):
                    continue
                    
                title = link.get_text(strip=True)
                if title and not title.startswith('View all'):
                    url = urljoin(landing_url, link['href'])
                    documents.append({
                        'title': title,
                        'url': url,
                        'type': doc_type
                    })
        
        elif doc_type == 'advice':
            # Advice documents are nested under Policies
            # They follow pattern: /Policies/{policy-name}/Advice-to-the-Profession-{topic}
            advice_links = soup.find_all('a', href=lambda x: x and 'Advice-to-the-Profession' in x and '/Policies/' in x)
            
            for link in advice_links:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # Skip the main landing page links
                if title and 'Advice to the Profession' in title and href.endswith('Advice-to-the-Profession'):
                    continue
                    
                if title:
                    url = urljoin(landing_url, href)
                    # Clean up the title if it's truncated
                    if '...' in title:
                        # Extract from URL instead
                        parts = href.split('/')
                        if parts:
                            title = parts[-1].replace('Advice-to-the-Profession-', '').replace('-', ' ')
                    
                    documents.append({
                        'title': f"Advice: {title}",
                        'url': url,
                        'type': doc_type
                    })
        
        elif doc_type == 'statements':
            statement_links = soup.find_all('a', href=lambda x: x and ('/Statements-Positions/' in x or '/Position-Statements/' in x))
            
            for link in statement_links:
                title = link.get_text(strip=True)
                if title and not title.startswith('View all'):
                    url = urljoin(landing_url, link['href'])
                    documents.append({
                        'title': title,
                        'url': url,
                        'type': doc_type
                    })
        
        # Remove duplicates
        seen_urls = set()
        unique_documents = []
        for doc in documents:
            if doc['url'] not in seen_urls:
                seen_urls.add(doc['url'])
                unique_documents.append(doc)
        
        logger.info(f"Found {len(unique_documents)} {doc_type} documents")
        return unique_documents
    
    def _process_document_worker(self, doc_info: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Worker function to process a single document.
        Returns (success, error_message)
        """
        url = doc_info['url']
        
        # Check if already processed (thread-safe)
        with self.processed_urls_lock:
            if url in self.processed_urls:
                logger.debug(f"Skipping already processed: {url}")
                with self.stats_lock:
                    self.stats['skipped'] += 1
                return (True, None)
        
        logger.info(f"Processing: {doc_info['title']}")
        
        try:
            # Fetch HTML with rate limiting
            html = self._fetch_page_with_rate_limit(url)
            if not html:
                return (False, f"Failed to fetch HTML for {url}")
            
            # Generate filename
            parsed_url = urlparse(url)
            filename_base = parsed_url.path.strip('/').replace('/', '_').lower()
            if not filename_base:
                filename_base = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Save raw HTML
            raw_file = os.path.join(self.raw_dir, f"{filename_base}.html")
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            # Extract structured data
            extractor = CPSOExtractor()
            extracted = extractor.extract_from_html(html, url)
            
            if extracted:
                # Save processed JSON
                processed_file = os.path.join(self.processed_dir, f"{filename_base}.json")
                with open(processed_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted, f, indent=2, ensure_ascii=False)
                
                # Save chunks separately (the ingester will do its own extraction)
                chunks_file = os.path.join(self.processed_dir, f"{filename_base}_chunks.json")
                
                # The CPSOIngester expects a URL and does its own extraction
                # Since we've already extracted, let's just save the chunks
                # We'll need to manually create the chunks since ingester won't work with pre-extracted data
                
                # Create a simple chunk representation
                chunks = [{
                    'chunk_id': hashlib.md5(f"{url}_full".encode()).hexdigest(),
                    'chunk_type': 'full_document',
                    'section_heading': extracted.get('title', ''),
                    'text_preview': extracted['content'][:200] + '...',
                    'text_length': len(extracted['content']),
                    'source_url': url,
                    'source_org': 'cpso',
                    'document_type': doc_info['type'],
                    'title': extracted.get('title', doc_info['title'])
                }]
                
                # Add section chunks
                for section in extracted.get('sections', []):
                    chunk_id = hashlib.md5(f"{url}_{section['heading']}".encode()).hexdigest()
                    chunks.append({
                        'chunk_id': chunk_id,
                        'chunk_type': 'section',
                        'section_heading': section['heading'],
                        'text_preview': section['content'][:200] + '...' if section['content'] else '',
                        'text_length': len(section['content']),
                        'source_url': url,
                        'source_org': 'cpso',
                        'document_type': doc_info['type'],
                        'title': extracted.get('title', doc_info['title'])
                    })
                
                with open(chunks_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✓ {doc_info['title']} ({len(chunks)} chunks)")
                
                # Mark as processed (thread-safe)
                with self.processed_urls_lock:
                    self.processed_urls.add(url)
                
                # Update stats
                with self.stats_lock:
                    self.stats['success'] += 1
                
                # Periodic checkpoint save
                if self.stats['success'] % 10 == 0:
                    self._save_checkpoint()
                
                return (True, None)
            
            else:
                error_msg = f"No content extracted from: {url}"
                logger.warning(error_msg)
                return (False, error_msg)
                
        except Exception as e:
            error_msg = f"Error processing {url}: {e}"
            logger.error(error_msg)
            return (False, error_msg)
    
    def crawl_all(self, doc_types: Optional[List[str]] = None):
        """
        Crawl all CPSO documents in parallel.
        
        Args:
            doc_types: List of document types to crawl ('policies', 'advice', 'statements')
                      If None, crawls all types.
        """
        if doc_types is None:
            doc_types = list(self.LANDING_PAGES.keys())
        
        all_documents = []
        
        # Collect all document links (sequential to be polite to server)
        for doc_type in doc_types:
            if doc_type not in self.LANDING_PAGES:
                logger.warning(f"Unknown document type: {doc_type}")
                continue
            
            landing_url = self.LANDING_PAGES[doc_type]
            documents = self._extract_document_links(landing_url, doc_type)
            all_documents.extend(documents)
        
        logger.info(f"Total documents to process: {len(all_documents)}")
        logger.info(f"Using {self.max_workers} parallel workers")
        
        # Process documents in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_doc = {
                executor.submit(self._process_document_worker, doc): doc 
                for doc in all_documents
            }
            
            # Process completed tasks
            for future in as_completed(future_to_doc):
                doc_info = future_to_doc[future]
                
                try:
                    success, error = future.result()
                    
                    if not success and error:
                        with self.stats_lock:
                            self.stats['failed'] += 1
                            self.stats['errors'].append({
                                'url': doc_info['url'],
                                'title': doc_info['title'],
                                'error': error
                            })
                            
                except Exception as e:
                    logger.error(f"Worker exception for {doc_info['title']}: {e}")
                    with self.stats_lock:
                        self.stats['failed'] += 1
                        self.stats['errors'].append({
                            'url': doc_info['url'],
                            'title': doc_info['title'],
                            'error': str(e)
                        })
        
        # Final checkpoint save
        self._save_checkpoint()
        
        # Print summary
        logger.info("="*60)
        logger.info("CRAWLING COMPLETE")
        logger.info(f"  Total documents: {len(all_documents)}")
        logger.info(f"  Successfully processed: {self.stats['success']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  Skipped (already processed): {self.stats['skipped']}")
        
        if self.stats['errors']:
            logger.info("\nErrors encountered:")
            for err in self.stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"  - {err['title']}: {err['error']}")
            if len(self.stats['errors']) > 5:
                logger.info(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        return {
            'total': len(all_documents),
            'success': self.stats['success'],
            'failed': self.stats['failed'],
            'skipped': self.stats['skipped'],
            'processed_urls': list(self.processed_urls),
            'errors': self.stats['errors']
        }


def main():
    """Run the parallel CPSO crawler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crawl CPSO documents in parallel')
    parser.add_argument('--types', nargs='+', 
                       choices=['policies', 'advice', 'statements'],
                       help='Document types to crawl (default: all)')
    parser.add_argument('--output-dir', default='data/dr_opa_agent',
                       help='Output directory for documents')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of parallel workers (default: 5)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Base delay between requests in seconds')
    parser.add_argument('--no-resume', action='store_true',
                       help='Start fresh, ignore checkpoint')
    
    args = parser.parse_args()
    
    crawler = CPSOCrawlerParallel(
        output_dir=args.output_dir,
        max_workers=args.workers,
        delay_seconds=args.delay,
        resume_from_checkpoint=not args.no_resume
    )
    
    result = crawler.crawl_all(args.types)
    
    # Save final report
    report_file = os.path.join(args.output_dir, f"cpso_crawl_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()