#!/usr/bin/env python3
"""
Comprehensive test script for Dr. OPA MCP tools.
Tests all 6 tools with various scenarios.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import MCP components
from src.agents.dr_opa_agent.mcp.server import (
    search_sections_handler,
    get_section_handler,
    policy_check_handler,
    program_lookup_handler,
    ipac_guidance_handler,
    freshness_probe_handler
)


class OPAMCPTester:
    """Test harness for OPA MCP tools."""
    
    def __init__(self, output_dir: str = "tests/dr_opa_agent/test_outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_result(self, test_name: str, result: Dict[str, Any], error: str = None):
        """Save test result to file."""
        output = {
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
            'success': error is None,
            'error': error,
            'result': result
        }
        
        self.results.append(output)
        
        # Save individual result
        filename = self.output_dir / f"{test_name}_{self.timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"✓ Saved {test_name} to {filename}")
    
    async def test_search_sections(self):
        """Test opa.search_sections tool."""
        print("\n" + "="*50)
        print("Testing opa.search_sections")
        print("="*50)
        
        test_cases = [
            {
                'name': 'search_prescribing',
                'params': {
                    'query': 'prescribing controlled substances',
                    'sources': ['cpso'],
                    'top_k': 5
                }
            },
            {
                'name': 'search_telemedicine',
                'params': {
                    'query': 'telemedicine virtual care requirements',
                    'doc_types': ['policy', 'advice'],
                    'top_k': 3
                }
            },
            {
                'name': 'search_consent',
                'params': {
                    'query': 'informed consent documentation',
                    'topics': ['consent'],
                    'include_superseded': False,
                    'top_k': 5
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                print(f"\nTest: {test_case['name']}")
                print(f"Query: {test_case['params'].get('query')}")
                
                result = await search_sections_handler(**test_case['params'])
                
                # Display summary
                if result and not result.get('error'):
                    sections = result.get('sections', [])
                    documents = result.get('documents', [])
                    confidence = result.get('confidence', 0)
                    
                    print(f"  Found {len(sections)} sections from {len(documents)} documents")
                    print(f"  Confidence: {confidence:.2f}")
                    print(f"  Provenance: {result.get('provenance', [])}")
                    
                    if sections:
                        print(f"  Top result: {sections[0].get('heading', 'No heading')}")
                
                self.save_result(f"search_{test_case['name']}", result)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.save_result(f"search_{test_case['name']}", {}, error_msg)
    
    async def test_get_section(self):
        """Test opa.get_section tool."""
        print("\n" + "="*50)
        print("Testing opa.get_section")
        print("="*50)
        
        # First, get a section ID from search
        print("Getting a section ID via search...")
        search_result = await search_sections_handler(
            query="medical records",
            sources=['cpso'],
            top_k=1
        )
        
        if search_result and search_result.get('sections'):
            section_id = search_result['sections'][0].get('section_id')
            
            if section_id:
                print(f"Found section ID: {section_id}")
                
                test_cases = [
                    {
                        'name': 'get_with_children',
                        'params': {
                            'section_id': section_id,
                            'include_children': True,
                            'include_context': False
                        }
                    },
                    {
                        'name': 'get_with_context',
                        'params': {
                            'section_id': section_id,
                            'include_children': False,
                            'include_context': True
                        }
                    }
                ]
                
                for test_case in test_cases:
                    try:
                        print(f"\nTest: {test_case['name']}")
                        
                        result = await get_section_handler(**test_case['params'])
                        
                        if result and not result.get('error'):
                            section = result.get('section', {})
                            document = result.get('document', {})
                            children = result.get('children', [])
                            context = result.get('context', [])
                            
                            print(f"  Section: {section.get('heading', 'No heading')}")
                            print(f"  Document: {document.get('title', 'No title')}")
                            print(f"  Children: {len(children)}")
                            print(f"  Context sections: {len(context)}")
                        
                        self.save_result(f"get_section_{test_case['name']}", result)
                        
                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        print(f"  ✗ {error_msg}")
                        self.save_result(f"get_section_{test_case['name']}", {}, error_msg)
            else:
                print("  No section ID found in search results")
        else:
            print("  No search results to get section ID from")
    
    async def test_policy_check(self):
        """Test opa.policy_check tool."""
        print("\n" + "="*50)
        print("Testing opa.policy_check")
        print("="*50)
        
        test_cases = [
            {
                'name': 'prescribing_policy',
                'params': {
                    'topic': 'prescribing opioids',
                    'situation': 'chronic pain management',
                    'policy_level': 'both',
                    'include_related': True
                }
            },
            {
                'name': 'consent_expectations',
                'params': {
                    'topic': 'informed consent',
                    'policy_level': 'expectation',
                    'include_related': False
                }
            },
            {
                'name': 'telemedicine_advice',
                'params': {
                    'topic': 'virtual care telemedicine',
                    'policy_level': 'advice',
                    'include_related': True
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                print(f"\nTest: {test_case['name']}")
                print(f"Topic: {test_case['params'].get('topic')}")
                
                result = await policy_check_handler(**test_case['params'])
                
                if result:
                    policies = result.get('policies', [])
                    expectations = result.get('expectations', [])
                    advice = result.get('advice', [])
                    confidence = result.get('confidence', 0)
                    
                    print(f"  Found {len(policies)} policies")
                    print(f"  Expectations: {len(expectations)}")
                    print(f"  Advice items: {len(advice)}")
                    print(f"  Confidence: {confidence:.2f}")
                    print(f"  Summary: {result.get('summary', '')[:100]}...")
                
                self.save_result(f"policy_{test_case['name']}", result)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.save_result(f"policy_{test_case['name']}", {}, error_msg)
    
    async def test_program_lookup(self):
        """Test opa.program_lookup tool."""
        print("\n" + "="*50)
        print("Testing opa.program_lookup")
        print("="*50)
        
        test_cases = [
            {
                'name': 'breast_screening_age_55',
                'params': {
                    'program': 'breast',
                    'patient_age': 55,
                    'info_needed': ['eligibility', 'intervals', 'procedures']
                }
            },
            {
                'name': 'cervical_with_risk',
                'params': {
                    'program': 'cervical',
                    'patient_age': 30,
                    'risk_factors': ['family_history'],
                    'info_needed': ['eligibility', 'intervals', 'followup']
                }
            },
            {
                'name': 'colorectal_general',
                'params': {
                    'program': 'colorectal',
                    'info_needed': ['eligibility', 'procedures']
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                print(f"\nTest: {test_case['name']}")
                print(f"Program: {test_case['params'].get('program')}")
                
                result = await program_lookup_handler(**test_case['params'])
                
                if result and not result.get('error'):
                    eligibility = result.get('eligibility', {})
                    intervals = result.get('intervals', {})
                    procedures = result.get('procedures', [])
                    patient_specific = result.get('patient_specific', {})
                    
                    print(f"  Eligibility: {eligibility}")
                    print(f"  Intervals: {intervals}")
                    print(f"  Procedures: {procedures}")
                    if patient_specific:
                        print(f"  Patient recommendation: {patient_specific.get('recommendation', 'None')}")
                
                self.save_result(f"program_{test_case['name']}", result)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.save_result(f"program_{test_case['name']}", {}, error_msg)
    
    async def test_ipac_guidance(self):
        """Test opa.ipac_guidance tool."""
        print("\n" + "="*50)
        print("Testing opa.ipac_guidance")
        print("="*50)
        
        test_cases = [
            {
                'name': 'clinic_hand_hygiene',
                'params': {
                    'setting': 'clinic',
                    'topic': 'hand hygiene',
                    'include_checklists': True
                }
            },
            {
                'name': 'hospital_ppe_covid',
                'params': {
                    'setting': 'hospital',
                    'topic': 'PPE personal protective equipment',
                    'pathogen': 'COVID-19',
                    'include_checklists': True
                }
            },
            {
                'name': 'ltc_infection_control',
                'params': {
                    'setting': 'ltc',
                    'topic': 'infection prevention control',
                    'include_checklists': False
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                print(f"\nTest: {test_case['name']}")
                print(f"Setting: {test_case['params'].get('setting')}")
                print(f"Topic: {test_case['params'].get('topic')}")
                
                result = await ipac_guidance_handler(**test_case['params'])
                
                if result:
                    guidelines = result.get('guidelines', [])
                    procedures = result.get('procedures', [])
                    checklists = result.get('checklists', [])
                    pathogen_specific = result.get('pathogen_specific')
                    
                    print(f"  Guidelines: {len(guidelines)}")
                    print(f"  Procedures: {len(procedures)}")
                    print(f"  Checklists: {len(checklists)}")
                    if pathogen_specific:
                        print(f"  Pathogen-specific: Yes")
                
                self.save_result(f"ipac_{test_case['name']}", result)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.save_result(f"ipac_{test_case['name']}", {}, error_msg)
    
    async def test_freshness_probe(self):
        """Test opa.freshness_probe tool."""
        print("\n" + "="*50)
        print("Testing opa.freshness_probe")
        print("="*50)
        
        test_cases = [
            {
                'name': 'telemedicine_freshness',
                'params': {
                    'topic': 'telemedicine',
                    'sources': ['cpso'],
                    'check_web': False
                }
            },
            {
                'name': 'opioid_guidelines_check',
                'params': {
                    'topic': 'opioid prescribing guidelines',
                    'check_web': True
                }
            },
            {
                'name': 'screening_updates',
                'params': {
                    'topic': 'cancer screening',
                    'sources': ['ontario_health'],
                    'check_web': False
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                print(f"\nTest: {test_case['name']}")
                print(f"Topic: {test_case['params'].get('topic')}")
                
                result = await freshness_probe_handler(**test_case['params'])
                
                if result:
                    current = result.get('current_guidance', {})
                    last_updated = result.get('last_updated')
                    updates_found = result.get('updates_found')
                    recommended_action = result.get('recommended_action')
                    
                    print(f"  Current: {current.get('title', 'None')}")
                    print(f"  Last updated: {last_updated}")
                    print(f"  Updates found: {updates_found}")
                    print(f"  Recommendation: {recommended_action}")
                
                self.save_result(f"freshness_{test_case['name']}", result)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.save_result(f"freshness_{test_case['name']}", {}, error_msg)
    
    async def run_all_tests(self):
        """Run all MCP tool tests."""
        print("\n" + "="*60)
        print("Dr. OPA MCP Tools Test Suite")
        print("="*60)
        print(f"Output directory: {self.output_dir}")
        print(f"Timestamp: {self.timestamp}")
        
        # Run all tests
        await self.test_search_sections()
        await self.test_get_section()
        await self.test_policy_check()
        await self.test_program_lookup()
        await self.test_ipac_guidance()
        await self.test_freshness_probe()
        
        # Save summary
        summary = {
            'timestamp': self.timestamp,
            'total_tests': len(self.results),
            'successful': sum(1 for r in self.results if r['success']),
            'failed': sum(1 for r in self.results if not r['success']),
            'results': self.results
        }
        
        summary_file = self.output_dir / f"test_summary_{self.timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Total tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Summary saved to: {summary_file}")
        
        return summary


async def main():
    """Main test entry point."""
    tester = OPAMCPTester()
    summary = await tester.run_all_tests()
    
    # Return non-zero exit code if any tests failed
    sys.exit(0 if summary['failed'] == 0 else 1)


if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault('PYTHONPATH', str(Path(__file__).parent.parent.parent.parent))
    
    # Run tests
    asyncio.run(main())