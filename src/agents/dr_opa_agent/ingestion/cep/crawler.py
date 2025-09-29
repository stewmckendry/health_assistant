"""CEP clinical tools crawler.

Fetches clinical tool pages from the Centre for Effective Practice website.
"""

import asyncio
import aiohttp
import logging
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class CEPCrawler:
    """Crawler for CEP clinical tools."""
    
    BASE_URL = "https://tools.cep.health"
    TOOLS_LIST_URL = "https://tools.cep.health"
    
    # Complete list of CEP tools scraped from https://tools.cep.health (Jan 2025)
    KNOWN_TOOLS = [
        # Mental Health & Neurology
        {"slug": "dementia-diagnosis", "name": "Dementia Diagnosis", "category": "mental_health"},
        {"slug": "anxiety-and-depression", "name": "Anxiety and Depression", "category": "mental_health"},
        {"slug": "attention-deficit-hyperactivity-disorder-in-adults", "name": "Attention Deficit Hyperactivity Disorder (ADHD) in Adults", "category": "mental_health"},
        {"slug": "behavioural-andpsychological-symptoms-of-dementia-bpsd", "name": "Behavioural and Psychological Symptoms of Dementia (BPSD)", "category": "mental_health"},
        {"slug": "management-of-chronic-insomnia", "name": "Management of Chronic Insomnia", "category": "mental_health"},
        {"slug": "youth-mental-health-anxiety-and-depression", "name": "Youth Mental Health Anxiety and Depression", "category": "mental_health"},
        {"slug": "core-neck-and-headache-navigator", "name": "CORE Neck and Headache Navigator", "category": "neurology"},
        
        # Substance Use & Addiction
        {"slug": "alcohol-use-disorder-aud-tool", "name": "Alcohol Use Disorder (AUD)", "category": "substance_use"},
        {"slug": "opioid-use-disorder-oud-tool", "name": "Opioid Use Disorder (OUD)", "category": "substance_use"},
        {"slug": "opioid-tapering-template", "name": "Opioid Tapering Template", "category": "substance_use"},
        {"slug": "non-medical-cannabis-resource", "name": "Non-Medical Cannabis Resource", "category": "substance_use"},
        {"slug": "managing-benzodiazepine-use-in-older-adults", "name": "Benzodiazepine Use in Older Adults", "category": "substance_use"},
        
        # Chronic Disease Management
        {"slug": "chronic-obstructive-pulmonary-disease-copd", "name": "Chronic obstructive pulmonary disease (COPD)", "category": "chronic_disease"},
        {"slug": "managing-patients-with-heart-failure-in-primary-care", "name": "Managing Heart Failure in Primary Care", "category": "chronic_disease"},
        {"slug": "type-2-diabetes-insulin-therapy", "name": "Type 2 diabetes: insulin therapy", "category": "chronic_disease"},
        {"slug": "type-2-diabetes-non-insulin-pharmacotherapy-2", "name": "Type 2 diabetes: non-insulin pharmacotherapy", "category": "chronic_disease"},
        {"slug": "local-services-patients-living-with-type-2-diabetes", "name": "Local Services for Patients Living With Type 2 Diabetes", "category": "chronic_disease"},
        
        # Pain & Musculoskeletal
        {"slug": "management-of-chronic-non-cancer-pain", "name": "Management of Chronic Non-Cancer Pain", "category": "pain_msk"},
        {"slug": "clinically-organized-relevant-exam-core-back-tool", "name": "Clinically Organized Relevant Exam (CORE) Back Tool", "category": "pain_msk"},
        {"slug": "fibromyalgia", "name": "Fibromyalgia (FM)", "category": "pain_msk"},
        {"slug": "manual-therapy-as-an-evidence-based-referral-for-musculoskeletal-pain", "name": "Manual Therapy as an Evidence-Based Referral for Musculoskeletal Pain", "category": "pain_msk"},
        {"slug": "myalgic-encephalomyelitis-chronic-fatigue-syndrome-me-cfs", "name": "Myalgic Encephalomyelitis/Chronic Fatigue Syndrome (ME/CFS)", "category": "pain_msk"},
        
        # Women's Health
        {"slug": "menopause-management", "name": "Menopause Management", "category": "womens_health"},
        {"slug": "preconception-health-care-tool", "name": "Preconception Health Care Tool", "category": "womens_health"},
        {"slug": "managing-urinary-incontinence-in-women", "name": "Urinary Incontinence in Women", "category": "womens_health"},
        
        # Geriatrics & Preventive Care
        {"slug": "falls-prevention-and-management", "name": "Fall Prevention and Management", "category": "preventive_care"},
        {"slug": "managing-proton-pump-inhibitor-use-in-older-adults", "name": "Managing Proton Pump Inhibitor Use in Older Adults", "category": "preventive_care"},
        {"slug": "preventing-childhood-obesity", "name": "Preventing Childhood Obesity", "category": "preventive_care"},
        
        # Metabolic & Obesity
        {"slug": "pharmacotherapy-obesity-management", "name": "Pharmacotherapy for Obesity Management", "category": "metabolic"},
        
        # Infectious Disease & Special Populations
        {"slug": "access-study-clinical-education-tool-supporting-anal-cancer-screening-in-primary-care-for-people-living-with-hiv", "name": "Supporting Anal Cancer Screening in Primary Care for People Living with HIV", "category": "infectious_disease"},
        {"slug": "rsv-prevention-program-for-infants", "name": "2025-2026 RSV Prevention Program for infants in Ontario", "category": "infectious_disease"},
        {"slug": "covid-19", "name": "COVID-19 in 2024: Care and Operations Guidance", "category": "infectious_disease"},
        
        # Specialized Conditions
        {"slug": "pots", "name": "Postural Orthostatic Tachycardia Syndrome (POTS)", "category": "neurology"},
        
        # End of Life Care
        {"slug": "medical-assistance-in-dying-maid-in-ontario-track-one-natural-death-is-reasonably-foreseeable", "name": "Medical Assistance in Dying (MAID) in Ontario Track One: Natural Death is Reasonably Foreseeable", "category": "end_of_life"},
        {"slug": "medical-assistance-in-dying-maid-in-ontario-track-two-natural-death-is-not-reasonably-foreseeable-2", "name": "Medical Assistance in Dying (MAID) in Ontario Track Two: Natural Death is NOT Reasonably Foreseeable", "category": "end_of_life"},
        
        # Digital Health & Innovation
        {"slug": "artificial-intelligence-ai-learning-centre", "name": "Artificial Intelligence (AI) Learning Centre", "category": "digital_health"},
        {"slug": "secure-messaging-content", "name": "Secure Messaging", "category": "digital_health"},
        
        # Social & Community Care
        {"slug": "social-prescribing", "name": "Social Prescribing: a Resource for Health Professionals", "category": "social_care"},
        {"slug": "adaptive-mentoring-to-build-primary-care-capacity-caring-for-canadians-living-with-mental-illness-chronic-pain-and-addictions-implementation-toolkit", "name": "Adaptive Mentoring to Build Primary Care Capacity: Caring for Canadians Living with Mental Illness, Chronic Pain and Addictions Implementation Toolkit", "category": "social_care"},
        {"slug": "a-guide-to-primary-care-management-of-mental-health-and-addictions-related-risks-and-functional-impairments", "name": "Keeping Your Patients Safe: A Guide to Primary Care Management of Mental Health and Addictions-related Risks and Functional Impairments", "category": "social_care"},
        
        # Operational & Administrative
        {"slug": "seasonal-preparedness-guide-for-primary-care", "name": "Seasonal Preparedness Guide", "category": "operational"},
        {"slug": "sp-drafting", "name": "SP drafting", "category": "operational"},
        {"slug": "maid-forms", "name": "MAID Forms Staging*", "category": "operational"},
        
        # Test/Development (exclude from production)
        # {"slug": "test", "name": "Playground for CEP", "category": "development"},
        # {"slug": "test-2", "name": "Test", "category": "development"},
    ]
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize CEP crawler.
        
        Args:
            output_dir: Directory to save crawled data
        """
        self.output_dir = Path(output_dir or "data/dr_opa_agent/raw/cep")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.processed_dir = Path("data/dr_opa_agent/processed/cep")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Load checkpoint if exists
        self.checkpoint_file = self.output_dir / "crawler_checkpoint.json"
        self.checkpoint = self._load_checkpoint()
        
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load crawler checkpoint."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {"crawled_tools": [], "last_crawl": None}
    
    def _save_checkpoint(self):
        """Save crawler checkpoint."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a single page.
        
        Args:
            session: aiohttp session
            url: URL to fetch
            
        Returns:
            HTML content
        """
        headers = {
            'User-Agent': 'Dr-OPA-Agent/1.0 (Ontario Practice Advice; Medical Education)'
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
    
    async def crawl_tool(self, session: aiohttp.ClientSession, tool_info: Dict[str, str]) -> Dict[str, Any]:
        """Crawl a single clinical tool.
        
        Args:
            session: aiohttp session
            tool_info: Tool information (slug, name, category)
            
        Returns:
            Tool data including HTML and metadata
        """
        tool_url = f"{self.BASE_URL}/tool/{tool_info['slug']}/"
        
        logger.info(f"Crawling tool: {tool_info['name']} ({tool_url})")
        
        # Fetch HTML
        html = await self.fetch_page(session, tool_url)
        
        # Generate content hash
        content_hash = hashlib.sha256(html.encode()).hexdigest()
        
        # Prepare tool data
        tool_data = {
            "tool_id": f"cep_{tool_info['slug'].replace('-', '_')}",
            "slug": tool_info['slug'],
            "name": tool_info['name'],
            "category": tool_info['category'],
            "url": tool_url,
            "html": html,
            "content_hash": content_hash,
            "crawled_at": datetime.now().isoformat()
        }
        
        # Save raw HTML
        html_file = self.output_dir / f"{tool_info['slug']}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Save metadata
        meta_file = self.output_dir / f"{tool_info['slug']}_meta.json"
        meta_data = {k: v for k, v in tool_data.items() if k != 'html'}
        with open(meta_file, 'w') as f:
            json.dump(meta_data, f, indent=2)
        
        logger.info(f"Saved tool: {tool_info['name']} to {html_file}")
        
        return tool_data
    
    async def crawl_single(self, tool_slug: str) -> Dict[str, Any]:
        """Crawl a single tool by slug.
        
        Args:
            tool_slug: Tool slug (e.g., 'dementia-diagnosis')
            
        Returns:
            Tool data
        """
        # Find tool info
        tool_info = None
        for tool in self.KNOWN_TOOLS:
            if tool['slug'] == tool_slug:
                tool_info = tool
                break
        
        if not tool_info:
            raise ValueError(f"Unknown tool slug: {tool_slug}")
        
        async with aiohttp.ClientSession() as session:
            # Add delay to be respectful
            await asyncio.sleep(0.5)
            return await self.crawl_tool(session, tool_info)
    
    async def crawl_all(self, max_concurrent: int = 3, resume: bool = True):
        """Crawl all CEP clinical tools.
        
        Args:
            max_concurrent: Maximum concurrent requests
            resume: Resume from checkpoint if available
        """
        # Determine which tools to crawl
        if resume and self.checkpoint['crawled_tools']:
            crawled_slugs = set(self.checkpoint['crawled_tools'])
            tools_to_crawl = [t for t in self.KNOWN_TOOLS if t['slug'] not in crawled_slugs]
            logger.info(f"Resuming crawl. {len(crawled_slugs)} already done, {len(tools_to_crawl)} remaining")
        else:
            tools_to_crawl = self.KNOWN_TOOLS
            logger.info(f"Starting fresh crawl of {len(tools_to_crawl)} tools")
        
        if not tools_to_crawl:
            logger.info("All tools already crawled")
            return
        
        async with aiohttp.ClientSession() as session:
            # Process in batches
            for i in range(0, len(tools_to_crawl), max_concurrent):
                batch = tools_to_crawl[i:i+max_concurrent]
                
                # Crawl batch
                tasks = []
                for tool_info in batch:
                    # Add delay between requests
                    await asyncio.sleep(0.5)
                    tasks.append(self.crawl_tool(session, tool_info))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update checkpoint
                for tool_info, result in zip(batch, results):
                    if not isinstance(result, Exception):
                        self.checkpoint['crawled_tools'].append(tool_info['slug'])
                    else:
                        logger.error(f"Failed to crawl {tool_info['slug']}: {result}")
                
                self.checkpoint['last_crawl'] = datetime.now().isoformat()
                self._save_checkpoint()
                
                logger.info(f"Progress: {len(self.checkpoint['crawled_tools'])}/{len(self.KNOWN_TOOLS)} tools crawled")
        
        logger.info(f"Crawl complete. {len(self.checkpoint['crawled_tools'])} tools crawled")
        
        # Generate summary
        summary = {
            "total_tools": len(self.KNOWN_TOOLS),
            "crawled_tools": len(self.checkpoint['crawled_tools']),
            "categories": {},
            "last_crawl": self.checkpoint['last_crawl']
        }
        
        for tool in self.KNOWN_TOOLS:
            category = tool['category']
            if category not in summary['categories']:
                summary['categories'][category] = []
            summary['categories'][category].append(tool['name'])
        
        summary_file = self.output_dir / "crawl_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Crawl summary saved to {summary_file}")


async def main():
    """Test crawler with single tool."""
    crawler = CEPCrawler()
    
    # Test with dementia tool
    result = await crawler.crawl_single('dementia-diagnosis')
    print(f"Crawled: {result['name']}")
    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Hash: {result['content_hash']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())