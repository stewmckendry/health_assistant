"""
Choosing Wisely Canada PDF Extractor

Extracts structured recommendations from Choosing Wisely Canada PDF documents
using LLM-based extraction with GPT-4o-mini.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import PyPDF2
from openai import OpenAI
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """Represents a single Choosing Wisely recommendation."""
    number: int
    title: str
    description: str
    references: List[str]  # Changed from pmids to references
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpecialtySection:
    """Represents a medical specialty section with all recommendations."""
    specialty: str
    organization: str
    last_updated: str
    recommendations: List[Recommendation]
    methodology: str
    all_sources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialty": self.specialty,
            "organization": self.organization,
            "last_updated": self.last_updated,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "methodology": self.methodology,
            "all_sources": self.all_sources
        }


class ChoosingWiselyExtractor:
    """Extracts Choosing Wisely recommendations from PDF using LLM."""
    
    def __init__(self, pdf_path: str, mapping_csv_path: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize the extractor.
        
        Args:
            pdf_path: Path to the Choosing Wisely PDF file
            mapping_csv_path: Path to CSV file with section mappings (specialty,start_page,end_page)
            openai_api_key: OpenAI API key (uses environment variable if not provided)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Load section mappings from CSV
        self.specialty_pages = {}
        if mapping_csv_path:
            self.load_mappings_from_csv(mapping_csv_path)
        else:
            # Use default path if not provided
            default_csv = Path(__file__).parent.parent.parent.parent.parent / "data" / "dr_opa_agent" / "raw" / "choosing_wisely" / "section_map.csv"
            if default_csv.exists():
                self.load_mappings_from_csv(str(default_csv))
            else:
                logger.warning("No section mapping CSV found. Extraction may fail.")
        
        # Configure synchronous client with timeout
        self.client = OpenAI(
            api_key=openai_api_key,
            timeout=90.0  # 90 second timeout to handle sections with many references
        )
        
        self.extraction_prompt = """Extract the following information from this Choosing Wisely Canada specialty section:

1. **Specialty name**: The medical specialty or field
2. **Organization/Society name**: The organization that created these recommendations  
3. **Last updated date**: When these recommendations were last updated
4. **Recommendations**: For each numbered recommendation extract:
   - Number (1-7)
   - Title (the bold text that summarizes the recommendation)
   - Description (the detailed explanation)
   - References cited (brief format like "Smith et al. 2020 - Title" or "Jones 2019 - Journal Name")
5. **Methodology**: The "How the list was created" section content
6. **All references**: List of references in brief citation format

Return as JSON with this exact structure:
{
    "specialty": "string",
    "organization": "string", 
    "last_updated": "string",
    "recommendations": [
        {
            "number": 1,
            "title": "string",
            "description": "string",
            "references": ["Smith 2020 - Brief title", ...]
        }
    ],
    "methodology": "string",
    "all_sources": ["Author Year - Title/Journal", ...]
}

Keep reference format concise: first author, year, and abbreviated title or journal.
If any field is not found, use an empty string or empty array as appropriate."""
    
    def load_mappings_from_csv(self, csv_path: str):
        """
        Load section mappings from CSV file.
        
        Args:
            csv_path: Path to CSV file with format: specialty,start_page,end_page
        """
        import csv
        
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    specialty = row[0].strip()
                    start_page = int(row[1].strip())
                    end_page = int(row[2].strip())
                    self.specialty_pages[specialty] = (start_page, end_page)
        
        logger.info(f"Loaded {len(self.specialty_pages)} specialty mappings from CSV")
    
    def extract_pdf_pages(self, start_page: int, end_page: int) -> List[str]:
        """
        Extract text from specific pages of the PDF.
        
        Args:
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (inclusive)
            
        Returns:
            List of page texts
        """
        pages = []
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Adjust for 0-indexed pages
            for page_num in range(start_page - 1, min(end_page, len(pdf_reader.pages))):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                pages.append(text)
        
        return pages
    
    def extract_specialty(self, specialty_name: str, pages: List[str]) -> SpecialtySection:
        """
        Extract one specialty section using LLM.
        
        Args:
            specialty_name: Name of the specialty
            pages: List of page texts for this specialty
            
        Returns:
            Extracted specialty section
        """
        combined_text = "\n".join(pages)
        
        # Log extraction details
        char_count = len(combined_text)
        token_estimate = char_count // 4
        logger.info(f"Extracting {specialty_name}: {char_count} chars (~{token_estimate} tokens)")
        
        # Retry logic for API calls
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.extraction_prompt},
                        {"role": "user", "content": f"Extract information for {specialty_name}:\n\n{combined_text}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=4000
                    # Timeout is now handled at client level
                )
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API call failed for {specialty_name}, attempt {attempt + 1}/{max_retries}: {e}")
                    import time
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise on final attempt
        
        try:
            
            data = json.loads(response.choices[0].message.content)
            
            # Convert to dataclass
            recommendations = [
                Recommendation(
                    number=rec["number"],
                    title=rec["title"],
                    description=rec["description"],
                    references=rec.get("references", [])  # Changed from pmids to references
                )
                for rec in data.get("recommendations", [])
            ]
            
            return SpecialtySection(
                specialty=data.get("specialty", specialty_name),
                organization=data.get("organization", ""),
                last_updated=data.get("last_updated", ""),
                recommendations=recommendations,
                methodology=data.get("methodology", ""),
                all_sources=data.get("all_sources", [])
            )
            
        except Exception as e:
            logger.error(f"Error extracting {specialty_name}: {e}")
            # Return empty section on error
            return SpecialtySection(
                specialty=specialty_name,
                organization="",
                last_updated="",
                recommendations=[],
                methodology="",
                all_sources=[]
            )
    
    def extract_all_specialties(self, 
                                     batch_size: int = 3,
                                     output_dir: Optional[Path] = None,
                                     skip_existing: bool = True) -> List[SpecialtySection]:
        """
        Extract all specialties using parallel workers.
        
        Args:
            batch_size: Number of parallel extractions
            output_dir: Directory to save individual JSON files (optional)
            skip_existing: Skip extraction if output file already exists
            
        Returns:
            List of all extracted specialty sections
        """
        if not self.specialty_pages:
            raise ValueError("No specialty mappings loaded. Please provide section_map.csv")
        
        results = []
        
        # Create output directory if specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter out already extracted specialties if skip_existing is True
        specialty_items = list(self.specialty_pages.items())
        
        if skip_existing and output_dir:
            # Check which files already exist
            remaining_items = []
            skipped = 0
            for specialty_name, page_range in specialty_items:
                filename = output_dir / f"{specialty_name.lower().replace(' ', '_').replace('&', 'and')}.json"
                if filename.exists():
                    logger.info(f"Skipping {specialty_name} - already extracted")
                    skipped += 1
                    # Load existing file for results
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        results.append(SpecialtySection(
                            specialty=data["specialty"],
                            organization=data["organization"],
                            last_updated=data["last_updated"],
                            recommendations=[Recommendation(**rec) for rec in data["recommendations"]],
                            methodology=data.get("methodology", ""),
                            all_sources=data.get("all_sources", [])
                        ))
                else:
                    remaining_items.append((specialty_name, page_range))
            
            if skipped > 0:
                logger.info(f"Skipped {skipped} already extracted specialties")
            specialty_items = remaining_items
        
        total_specialties = len(specialty_items)
        
        if total_specialties == 0:
            logger.info("All specialties already extracted!")
            return results
        
        logger.info(f"Extracting {total_specialties} specialties...")
        
        for i in range(0, total_specialties, batch_size):
            batch = specialty_items[i:i+batch_size]
            
            # Process each specialty in the batch
            for specialty_name, (start_page, end_page) in batch:
                pages = self.extract_pdf_pages(start_page, end_page)
                section = self.extract_specialty(specialty_name, pages)
                results.append(section)
            
            # Save individual files if output directory specified
            if output_dir:
                # Save each section in the batch
                for section in results[-(len(batch)):]:  # Get all sections from this batch
                    if section.recommendations:  # Only save non-empty sections
                        filename = output_dir / f"{section.specialty.lower().replace(' ', '_').replace('&', 'and')}.json"
                        with open(filename, 'w') as f:
                            json.dump(section.to_dict(), f, indent=2)
            
            # Log progress
            processed = min(i + batch_size, total_specialties)
            logger.info(f"Processed {processed}/{total_specialties} specialties")
            
            # Add delay between batches to avoid rate limits (except for last batch)
            if i + batch_size < total_specialties:
                delay = 2  # 2 second delay between batches
                logger.info(f"Waiting {delay} seconds before next batch...")
                import time
                time.sleep(delay)
        
        return results
    
    def validate_extraction(self, sections: List[SpecialtySection]) -> Dict[str, Any]:
        """
        Validate extraction completeness and quality.
        
        Args:
            sections: List of extracted sections
            
        Returns:
            Validation report
        """
        report = {
            "total_specialties_expected": len(self.specialty_pages),
            "total_specialties_extracted": len(sections),
            "specialties_with_recommendations": 0,
            "total_recommendations": 0,
            "specialties_missing_data": [],
            "extraction_rate": 0.0,
            "average_recommendations_per_specialty": 0.0
        }
        
        for section in sections:
            if section.recommendations:
                report["specialties_with_recommendations"] += 1
                report["total_recommendations"] += len(section.recommendations)
            else:
                report["specialties_missing_data"].append(section.specialty)
        
        if report["total_specialties_extracted"] > 0:
            report["extraction_rate"] = (
                report["specialties_with_recommendations"] / 
                report["total_specialties_extracted"] * 100
            )
            report["average_recommendations_per_specialty"] = (
                report["total_recommendations"] / 
                report["specialties_with_recommendations"]
                if report["specialties_with_recommendations"] > 0 else 0
            )
        
        return report
    
    def save_extraction_report(self, sections: List[SpecialtySection], output_path: str):
        """
        Save extraction report and combined data.
        
        Args:
            sections: List of extracted sections
            output_path: Path to save the report
        """
        report = self.validate_extraction(sections)
        
        # Add the full data to report
        report["extracted_data"] = [section.to_dict() for section in sections]
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Extraction report saved to {output_path}")
        logger.info(f"Extraction stats: {report['specialties_with_recommendations']}/{report['total_specialties_expected']} specialties extracted successfully")