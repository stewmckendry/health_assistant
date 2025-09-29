#!/usr/bin/env python3
"""
Test script to preview the new vector document format
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import our modified ingester
from src.agents.dr_off_agent.ingestion.ingesters.ohip_ingester import EnhancedOHIPIngester

def test_document_creation():
    """Test the new document creation methods with sample data"""
    
    # Sample fee code data (based on actual extraction)
    sample_fee_code = {
        "code": "C122",
        "description": "Subsequent visit by the Most Responsible Physician (MRP) - day following the hospital admission assessment",
        "fee": 61.15,
        "conditions": "Limited to a maximum of one each per hospital admission. Only payable for visits rendered by the MRP.",
        "units": None
    }
    
    sample_subsection = {
        "parent_section": "A",
        "subsection_title": "Neurosurgery (04)",
        "page_ref": "A136",
        "rules": [
            "Services rendered by physicians other than the MRP are not eligible for payment under this fee code.",
            "This code is payable only when the patient is admitted to hospital."
        ],
        "notes": [
            "The MRP must be the physician primarily responsible for the patient's care during the admission."
        ]
    }
    
    # Create ingester instance
    ingester = EnhancedOHIPIngester()
    
    # Test fee code document creation
    print("=== TESTING FEE CODE DOCUMENT ===")
    fee_doc = ingester._create_fee_code_document(sample_fee_code, sample_subsection)
    print(fee_doc)
    print()
    
    # Test subsection context document creation
    print("=== TESTING SUBSECTION CONTEXT DOCUMENT ===")
    context_doc = ingester._create_subsection_context_document(sample_subsection)
    print(context_doc)
    print()
    
    # Test with another admission-related code
    discharge_fee_code = {
        "code": "C124",
        "description": "Day of discharge",
        "fee": 61.15,
        "conditions": "Payable to the MRP on the day the patient is discharged from hospital."
    }
    
    print("=== TESTING DISCHARGE CODE DOCUMENT ===")
    discharge_doc = ingester._create_fee_code_document(discharge_fee_code, sample_subsection)
    print(discharge_doc)

if __name__ == "__main__":
    test_document_creation()