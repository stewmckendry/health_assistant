"""ODB (Ontario Drug Benefit) data ingestion module."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Generator, Optional
import logging
from datetime import datetime
from collections import defaultdict
import PyPDF2
from tqdm import tqdm

from ..base_ingester import BaseIngester

logger = logging.getLogger(__name__)


class ODBIngester(BaseIngester):
    """Ingester for Ontario Drug Benefit formulary data."""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize ODB ingester."""
        super().__init__("odb", db_path, chroma_path, openai_api_key)
        self.interchangeable_groups = {}
        self.lowest_cost_dins = {}
    
    def ingest(self, source_file: str) -> Dict[str, Any]:
        """Ingest ODB data from XML file and PDF documents.
        
        Args:
            source_file: Path to ODB XML file
            
        Returns:
            Ingestion statistics
        """
        self.log_ingestion(source_file, 'started')
        
        try:
            # Process XML data
            logger.info(f"Processing ODB XML: {source_file}")
            self._ingest_xml(source_file)
            
            # Process PDF documents for vector store
            pdf_dir = Path(source_file).parent
            pdf_files = list(pdf_dir.glob("*.pdf"))
            
            for pdf_file in pdf_files:
                logger.info(f"Processing ODB PDF: {pdf_file}")
                self._ingest_pdf(str(pdf_file))
            
            # Validate ingestion
            if self.validate_ingestion():
                self.log_ingestion(source_file, 'completed')
            else:
                self.log_ingestion(source_file, 'failed', 'Validation failed')
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            self.log_ingestion(source_file, 'failed', str(e))
            raise
        
        return self.ingestion_stats
    
    def parse_source(self, source_file: str) -> Generator[Dict[str, Any], None, None]:
        """Parse ODB XML file and yield drug records.
        
        Args:
            source_file: Path to ODB XML file
            
        Yields:
            Drug record dictionaries
        """
        tree = ET.parse(source_file)
        root = tree.getroot()
        
        # Parse manufacturers first
        manufacturers = {}
        for mfr in root.findall('.//manufacturer'):
            mfr_id = mfr.get('id')
            mfr_name = mfr.text
            if mfr_id:
                manufacturers[mfr_id] = mfr_name
        
        # Parse formulary drugs
        formulary = root.find('formulary')
        if not formulary:
            logger.error("No formulary section found in XML")
            return
        
        for pcg2 in formulary:  # Therapeutic classes
            therapeutic_class = self._get_element_text(pcg2, 'name')
            
            for pcg6 in pcg2.findall('pcg6'):  # Categories
                category = self._get_element_text(pcg6, 'name')
                
                for gen_name_elem in pcg6.findall('genericName'):
                    generic_name = self._get_element_text(gen_name_elem, 'name')
                    
                    for pcg_group in gen_name_elem.findall('pcgGroup'):
                        # This is an interchangeable group
                        for pcg9 in pcg_group.findall('pcg9'):
                            item_number = self._get_element_text(pcg9, 'itemNumber')
                            strength = self._get_element_text(pcg9, 'strength')
                            dosage_form = self._get_element_text(pcg9, 'dosageForm')
                            daily_cost = self._get_element_text(pcg9, 'dailyCost')
                            
                            # Create group ID
                            group_id = f"{generic_name}_{strength}_{dosage_form}".replace(' ', '_')
                            
                            # Process each drug in the group
                            drugs_in_group = []
                            for drug_elem in pcg9.findall('drug'):
                                drug = self._parse_drug_element(
                                    drug_elem,
                                    therapeutic_class,
                                    category,
                                    generic_name,
                                    strength,
                                    dosage_form,
                                    item_number,
                                    group_id,
                                    manufacturers
                                )
                                drugs_in_group.append(drug)
                                yield drug
                            
                            # Track interchangeable group
                            self._update_interchangeable_group(
                                group_id,
                                generic_name,
                                therapeutic_class,
                                category,
                                strength,
                                dosage_form,
                                item_number,
                                daily_cost,
                                drugs_in_group
                            )
    
    def _parse_drug_element(
        self,
        drug_elem: ET.Element,
        therapeutic_class: str,
        category: str,
        generic_name: str,
        strength: str,
        dosage_form: str,
        item_number: str,
        group_id: str,
        manufacturers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Parse individual drug element.
        
        Returns:
            Drug record dictionary
        """
        # Get DIN from id attribute or generate one
        din = drug_elem.get('id', '')
        
        # Parse drug attributes
        drug_data = {
            'din': din,
            'name': self._get_element_text(drug_elem, 'name'),
            'generic_name': generic_name,
            'manufacturer_id': self._get_element_text(drug_elem, 'manufacturerId'),
            'strength': strength,
            'dosage_form': dosage_form,
            'item_number': item_number,
            'therapeutic_class': therapeutic_class,
            'category': category,
            'interchangeable_group_id': group_id,
            'individual_price': self._parse_float(
                self._get_element_text(drug_elem, 'individualPrice')
            ),
            'daily_cost': self._parse_float(
                self._get_element_text(drug_elem, 'dailyCost')
            ),
            'amount_mohltc_pays': self._parse_float(
                self._get_element_text(drug_elem, 'amountMOHLTCPays')
            ),
            'listing_date': self._get_element_text(drug_elem, 'listingDate'),
            'notes': self._get_element_text(drug_elem, 'note'),
            
            # Parse attributes as boolean flags
            'is_benefit': drug_elem.get('notABenefit') != 'Y',
            'is_chronic_use': drug_elem.get('chronicUseMed') == 'Y',
            'is_section_3': drug_elem.get('sec3') == 'Y',
            'is_section_3b': drug_elem.get('sec3b') == 'Y',
            'is_section_3c': drug_elem.get('sec3c') == 'Y',
            'is_section_9': drug_elem.get('sec9') == 'Y',
            'is_section_12': drug_elem.get('sec12') == 'Y',
            'additional_benefit_type': drug_elem.get('additionalBenefitType'),
            'status': drug_elem.get('dinStatus', 'active')
        }
        
        return drug_data
    
    def _update_interchangeable_group(
        self,
        group_id: str,
        generic_name: str,
        therapeutic_class: str,
        category: str,
        strength: str,
        dosage_form: str,
        item_number: str,
        daily_cost: str,
        drugs: List[Dict[str, Any]]
    ):
        """Update interchangeable group tracking.
        
        Identifies lowest cost drug in each group.
        """
        if group_id not in self.interchangeable_groups:
            self.interchangeable_groups[group_id] = {
                'group_id': group_id,
                'generic_name': generic_name,
                'therapeutic_class': therapeutic_class,
                'category': category,
                'strength': strength,
                'dosage_form': dosage_form,
                'item_number': item_number,
                'daily_cost': daily_cost,
                'member_count': 0,
                'lowest_cost_din': None,
                'lowest_cost_price': float('inf'),
                'notes': None
            }
        
        group = self.interchangeable_groups[group_id]
        group['member_count'] += len(drugs)
        
        # Find lowest cost drug
        for drug in drugs:
            price = drug.get('individual_price')
            if price and price < group['lowest_cost_price']:
                group['lowest_cost_price'] = price
                group['lowest_cost_din'] = drug['din']
                self.lowest_cost_dins[drug['din']] = True
    
    def _ingest_xml(self, xml_file: str):
        """Ingest XML data into database and create embeddings.
        
        Args:
            xml_file: Path to ODB XML file
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Process drugs
        logger.info("Processing ODB drugs...")
        drug_count = 0
        drug_chunks = []  # Collect chunks for batch embedding
        
        for drug in tqdm(self.parse_source(xml_file), desc="Ingesting drugs"):
            try:
                # Mark if this is the lowest cost drug
                drug['is_lowest_cost'] = self.lowest_cost_dins.get(drug['din'], False)
                
                # Insert drug record
                cursor.execute("""
                    INSERT OR REPLACE INTO odb_drugs (
                        din, name, generic_name, manufacturer_id, strength,
                        dosage_form, item_number, therapeutic_class, category,
                        interchangeable_group_id, individual_price, daily_cost,
                        amount_mohltc_pays, listing_date, status, is_lowest_cost,
                        is_benefit, is_chronic_use, is_section_3, is_section_3b,
                        is_section_3c, is_section_9, is_section_12,
                        additional_benefit_type, notes
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    drug['din'], drug['name'], drug['generic_name'],
                    drug['manufacturer_id'], drug['strength'], drug['dosage_form'],
                    drug['item_number'], drug['therapeutic_class'], drug['category'],
                    drug['interchangeable_group_id'], drug['individual_price'],
                    drug['daily_cost'], drug['amount_mohltc_pays'],
                    drug['listing_date'], drug['status'], drug['is_lowest_cost'],
                    drug['is_benefit'], drug['is_chronic_use'], drug['is_section_3'],
                    drug['is_section_3b'], drug['is_section_3c'], drug['is_section_9'],
                    drug['is_section_12'], drug['additional_benefit_type'], drug['notes']
                ))
                
                # Create embedding text for this drug
                sections = []
                if drug.get('is_section_3'): sections.append('Section 3')
                if drug.get('is_section_3b'): sections.append('Section 3B')
                if drug.get('is_section_3c'): sections.append('Section 3C')
                if drug.get('is_section_9'): sections.append('Section 9')
                if drug.get('is_section_12'): sections.append('Section 12')
                
                drug_text = f"""Drug: {drug.get('name', 'Unknown')} ({drug.get('generic_name', 'Unknown')})
DIN: {drug.get('din', 'N/A')}
Strength: {drug.get('strength', 'N/A')} {drug.get('dosage_form', 'N/A')}
Therapeutic Class: {drug.get('therapeutic_class', 'N/A')}
Category: {drug.get('category') or 'General'}
Price: ${drug.get('individual_price') or 'N/A'} per unit
Daily Cost: ${drug.get('daily_cost') or 'N/A'}
Coverage: {'General Benefit' if drug.get('is_benefit') else 'Not a Benefit'}
{' '.join(sections)}
{'Chronic Use' if drug.get('is_chronic_use') else ''}
{'LOWEST COST OPTION' if drug.get('is_lowest_cost') else ''}
Manufacturer: {drug.get('manufacturer_id', 'N/A')}"""
                
                # Add notes if present
                if drug.get('notes'):
                    drug_text += f"\nClinical Notes: {drug['notes']}"
                
                # Create chunks for this drug
                chunks = self.chunk_text(
                    drug_text,
                    chunk_size=500,  # Smaller chunks for drug records
                    chunk_overlap=50,
                    metadata={
                        'din': drug.get('din'),
                        'generic_name': drug.get('generic_name'),
                        'brand_name': drug.get('name'),
                        'source_type': 'odb_drug',
                        'therapeutic_class': drug.get('therapeutic_class'),
                        'is_lowest_cost': str(drug.get('is_lowest_cost', False)),
                        'document_type': 'formulary_drug'
                    }
                )
                drug_chunks.extend(chunks)
                
                drug_count += 1
                self.ingestion_stats['records_processed'] += 1
                
                # Store chunks in batches to avoid memory issues
                if len(drug_chunks) >= 1000:
                    logger.info(f"Storing batch of {len(drug_chunks)} drug chunks...")
                    self.store_chunks_with_embeddings(drug_chunks, f"odb_drugs_batch_{drug_count}")
                    drug_chunks = []
                
            except Exception as e:
                logger.error(f"Error inserting drug {drug.get('din')}: {e}")
                self.ingestion_stats['records_failed'] += 1
                self.ingestion_stats['errors'].append(str(e))
        
        # Store remaining drug chunks
        if drug_chunks:
            logger.info(f"Storing final batch of {len(drug_chunks)} drug chunks...")
            self.store_chunks_with_embeddings(drug_chunks, f"odb_drugs_final")
        
        # Insert interchangeable groups and create embeddings
        logger.info("Processing interchangeable groups...")
        group_chunks = []
        
        for group in self.interchangeable_groups.values():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO odb_interchangeable_groups (
                        group_id, generic_name, therapeutic_class, category,
                        strength, dosage_form, item_number, member_count,
                        lowest_cost_din, lowest_cost_price, daily_cost, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    group['group_id'], group['generic_name'],
                    group['therapeutic_class'], group['category'],
                    group['strength'], group['dosage_form'],
                    group['item_number'], group['member_count'],
                    group['lowest_cost_din'], group['lowest_cost_price'],
                    group['daily_cost'], group['notes']
                ))
                
                # Create embedding for interchangeable group
                group_text = f"""Interchangeable Drug Group: {group['generic_name']} {group['strength']} {group['dosage_form']}
Therapeutic Class: {group['therapeutic_class']}
Category: {group.get('category') or 'General'}
Number of alternatives: {group['member_count']}
Lowest cost option: DIN {group['lowest_cost_din']} at ${group['lowest_cost_price']}
Daily cost: ${group.get('daily_cost') or 'N/A'}
Item Number: {group['item_number']}"""
                
                chunks = self.chunk_text(
                    group_text,
                    chunk_size=500,
                    chunk_overlap=50,
                    metadata={
                        'group_id': group['group_id'],
                        'generic_name': group['generic_name'],
                        'source_type': 'odb_interchangeable_group',
                        'therapeutic_class': group['therapeutic_class'],
                        'document_type': 'formulary_group'
                    }
                )
                group_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Error inserting group {group['group_id']}: {e}")
        
        # Store interchangeable group embeddings
        if group_chunks:
            logger.info(f"Storing {len(group_chunks)} interchangeable group chunks...")
            self.store_chunks_with_embeddings(group_chunks, "odb_interchangeable_groups")
        
        conn.commit()
        logger.info(f"Ingested {drug_count} drugs and {len(self.interchangeable_groups)} groups with embeddings")
    
    def _ingest_pdf(self, pdf_file: str):
        """Extract text from PDF and create embeddings.
        
        Args:
            pdf_file: Path to PDF file
        """
        try:
            # Extract text from PDF
            text_content = self._extract_pdf_text(pdf_file)
            
            if not text_content:
                logger.warning(f"No text extracted from {pdf_file}")
                return
            
            # Create chunks
            chunks = self.chunk_text(
                text_content,
                metadata={
                    'source_file': Path(pdf_file).name,
                    'document_type': 'odb_formulary_pdf'
                }
            )
            
            # Store chunks with embeddings
            self.store_chunks_with_embeddings(chunks, Path(pdf_file).name)
            
            logger.info(f"Created {len(chunks)} chunks from {Path(pdf_file).name}")
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_file}: {e}")
            self.ingestion_stats['errors'].append(str(e))
    
    def _extract_pdf_text(self, pdf_file: str) -> str:
        """Extract text from PDF file.
        
        Args:
            pdf_file: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text = []
        
        try:
            with open(pdf_file, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Add page marker for reference
                        text.append(f"\n[Page {page_num + 1}]\n")
                        text.append(page_text)
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
        
        return ''.join(text)
    
    def _get_element_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Safely get text from XML element.
        
        Args:
            parent: Parent XML element
            tag: Child tag name
            
        Returns:
            Text content or None
        """
        elem = parent.find(tag)
        return elem.text if elem is not None else None
    
    def _parse_float(self, value: Optional[str]) -> Optional[float]:
        """Parse string to float, handling None and invalid values.
        
        Args:
            value: String value to parse
            
        Returns:
            Float value or None
        """
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    from ..database import init_database
    db = init_database()
    
    # Run ingestion
    ingester = ODBIngester(
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    xml_file = "data/ontario/odb/moh-ontario-drug-benefit-odb-formulary-edition-43-data-extract-en-2025-08-29.xml"
    
    with ingester:
        stats = ingester.ingest(xml_file)
        print(f"\nIngestion complete: {stats}")