"""
Ontario Health Clinical Programs tool using Claude with web_search.
Provides access to all Ontario Health clinical programs via LLM-powered web search.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import json

logger = logging.getLogger(__name__)

# Ontario Health and related domains for clinical programs
ONTARIO_HEALTH_DOMAINS = [
    # Core Ontario Health domains
    "ontariohealth.ca",
    "health811.ontario.ca",

    # Cancer Care
    "cancercareontario.ca",
    "ccohealth.ca",
    "mycanceriq.ca",

    # Renal/Kidney
    "ontariorenalnetwork.ca",
    "renalnetwork.on.ca",

    # Critical Care
    "criticalcareontario.ca",

    # Cardiac/Stroke/Vascular
    "corhealthontario.ca",  # CorHealth Ontario
    "strokenetworkontario.ca",

    # Quality and Standards
    "hqontario.ca",
    "qualitystandards.hqontario.ca",

    # Palliative Care
    "ontariopalliativecarenetwork.ca",

    # Mental Health and Addictions
    "mentalhealthandaddictions.ca",
    "connex.ontariohealth.ca",  # ConnexOntario

    # Maternal and Child Health
    "pcmch.on.ca",  # Provincial Council for Maternal and Child Health
    "bornontario.ca",  # Better Outcomes Registry & Network

    # Health Technology
    "ohtac.ca",  # Ontario Health Technology Advisory Committee

    # Other Programs
    "thehealthline.ca",
    "health.gov.on.ca",  # Ministry of Health
    "ontariohealthprofiles.ca",
    "tobaccowise.com",  # Tobacco cessation
    "ontario.ca/health",  # Ontario government health portal

    # Regional programs
    "ccpnr.ca",  # Champlain Cardiovascular Disease Prevention Network
    "organtissuedonation.on.ca",  # Trillium Gift of Life

    # Public Health
    "publichealthontario.ca",  # Public Health Ontario
    "health.gov.on.ca/en/common/system/services/phu/locations.aspx",  # Public Health Units

    # National/Federal health resources (applicable to Ontario)
    "canada.ca",  # Health Canada
    "phac-aspc.gc.ca",  # Public Health Agency of Canada

    # Major health charities and organizations
    "cmha.ca",  # Canadian Mental Health Association
    "diabetes.ca",  # Diabetes Canada
    "heartandstroke.ca",  # Heart & Stroke Foundation
    "cancer.ca",  # Canadian Cancer Society
    "alzheimer.ca",  # Alzheimer Society
    "arthritis.ca",  # Arthritis Society
    "copd.ca",  # COPD Canada
    "kidney.ca",  # Kidney Foundation of Canada
    "osteoporosis.ca",  # Osteoporosis Canada
    "parkinson.ca",  # Parkinson Canada
]


class OntarioHealthProgramsClient:
    """Client for Ontario Health Clinical Programs using Claude with web_search."""

    def __init__(self):
        """Initialize the Ontario Health Programs client."""
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-latest"
        self.max_tokens = 2000
        self.timeout = 60.0  # 60 second timeout
        self.max_retries = 2  # Retry once on failure

        logger.info(f"Ontario Health Programs client initialized with {len(ONTARIO_HEALTH_DOMAINS)} domains")
    
    async def search_program(
        self,
        program: str,
        patient_age: Optional[int] = None,
        risk_factors: Optional[List[str]] = None,
        info_needed: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for Ontario Health clinical program information using Claude with web_search.
        
        Args:
            program: Clinical program name (e.g., "cancer screening", "kidney care", "cardiac", "stroke")
            patient_age: Optional patient age for eligibility checks
            risk_factors: Optional risk factors for personalized recommendations
            info_needed: Specific information types to retrieve (e.g., ["eligibility", "locations", "referral"])
        
        Returns:
            Program information including eligibility, procedures, locations, and resources
        """
        # Build the search query
        query_parts = [f"Ontario Health {program} program"]
        
        if patient_age:
            query_parts.append(f"age {patient_age} eligibility")
        
        if risk_factors:
            query_parts.append(" ".join(risk_factors))
        
        if info_needed:
            query_parts.append(" ".join(info_needed))
        
        search_query = " ".join(query_parts)
        
        # Build the system prompt
        system_prompt = """You are an Ontario Health clinical programs specialist. 
Your role is to search for and provide accurate information about Ontario Health clinical programs.
Focus on official Ontario Health sources and provide structured information about:
- Program eligibility and enrollment
- Clinical pathways and procedures
- Referral processes
- Resource locations and contact information
- Patient education materials

Always cite your sources and indicate if information may be outdated."""

        # Build user prompt with specific instructions
        user_prompt = f"""Search for information about: {search_query}

Please provide:
1. Program overview and purpose
2. Eligibility criteria
3. How to access the program (referral process)
4. Key services and procedures offered
5. Locations and contact information
6. Patient resources and education materials

Focus on the most current and relevant information from official Ontario Health sources."""

        if patient_age:
            user_prompt += f"\n\nPatient is {patient_age} years old - include age-specific eligibility."
        
        if risk_factors:
            user_prompt += f"\n\nPatient has these risk factors: {', '.join(risk_factors)}"

        # Retry logic with timeout handling
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Make the API call with web_search tool (with timeout)
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.messages.create,
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=0.3,  # Lower temperature for factual information
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        tools=[
                            {
                                "type": "web_search_20250305",
                                "name": "web_search",
                                "max_uses": 1,  # Single search to avoid hangs
                                "allowed_domains": ONTARIO_HEALTH_DOMAINS
                            }
                        ],
                        extra_headers={
                            "anthropic-beta": "web-search-2025-03-05"
                        }
                    ),
                    timeout=self.timeout
                )
            
                # Extract the response content
                content = ""
                citations = []

                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
                    if hasattr(block, 'citations') and block.citations:
                        for citation in block.citations:
                            if isinstance(citation, dict):
                                citations.append({
                                    "url": citation.get("url", ""),
                                    "title": citation.get("title", "Source")
                                })
                            elif hasattr(citation, 'url'):
                                citations.append({
                                    "url": getattr(citation, 'url', ''),
                                    "title": getattr(citation, 'title', 'Source')
                                })

                # Check if we got meaningful results
                if not content.strip():
                    raise ValueError("Empty response from web search")

                # Parse the structured response
                result = self._parse_program_response(content, program)
                result["citations"] = citations
                result["raw_response"] = content

                logger.info(f"Successfully retrieved {program} program information with {len(citations)} citations (attempt {attempt + 1})")

                return result

            except asyncio.TimeoutError:
                last_error = f"Web search timed out after {self.timeout} seconds"
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries}: {last_error} for program: {program}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
                continue

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries}: Error searching for {program} program: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
                continue

        # All retries failed
        logger.error(f"Failed to retrieve {program} program information after {self.max_retries} attempts. Last error: {last_error}")
        return {
            "error": last_error,
            "program": program,
            "message": f"Failed to retrieve program information after {self.max_retries} attempts",
            "items": [],
            "citations": [],
            "eligibility": {},
            "access": {},
            "services": [],
            "locations": [],
            "resources": []
        }
    
    def _parse_program_response(self, content: str, program: str) -> Dict[str, Any]:
        """
        Parse the LLM response into structured program information.
        
        Args:
            content: Raw response content from Claude
            program: Program name
        
        Returns:
            Structured program information
        """
        # Initialize result structure
        result = {
            "program": program,
            "overview": "",
            "eligibility": {},
            "access": {},
            "services": [],
            "locations": [],
            "resources": [],
            "patient_specific": None
        }
        
        # Simple parsing based on content sections
        # In production, this could use more sophisticated NLP or structured extraction
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect sections
            if 'overview' in line_lower or 'purpose' in line_lower:
                current_section = 'overview'
            elif 'eligibility' in line_lower or 'eligible' in line_lower:
                current_section = 'eligibility'
            elif 'access' in line_lower or 'referral' in line_lower or 'how to' in line_lower:
                current_section = 'access'
            elif 'service' in line_lower or 'procedure' in line_lower:
                current_section = 'services'
            elif 'location' in line_lower or 'contact' in line_lower:
                current_section = 'locations'
            elif 'resource' in line_lower or 'education' in line_lower:
                current_section = 'resources'
            elif line.strip() and current_section:
                # Add content to current section
                if current_section == 'overview':
                    result['overview'] += line + '\n'
                elif current_section == 'eligibility':
                    # Extract key eligibility criteria
                    if 'age' in line_lower:
                        result['eligibility']['age_criteria'] = line.strip()
                    elif 'risk' in line_lower:
                        result['eligibility']['risk_criteria'] = line.strip()
                    else:
                        result['eligibility'].setdefault('general', []).append(line.strip())
                elif current_section == 'access':
                    if 'referral' in line_lower:
                        result['access']['referral_process'] = line.strip()
                    elif 'self' in line_lower:
                        result['access']['self_referral'] = line.strip()
                    else:
                        result['access'].setdefault('steps', []).append(line.strip())
                elif current_section == 'services' and line.strip():
                    result['services'].append(line.strip())
                elif current_section == 'locations' and line.strip():
                    result['locations'].append(line.strip())
                elif current_section == 'resources' and line.strip():
                    result['resources'].append(line.strip())
        
        # Clean up empty sections
        result['overview'] = result['overview'].strip()
        result['services'] = [s for s in result['services'] if s][:10]  # Limit to 10
        result['locations'] = [l for l in result['locations'] if l][:5]  # Limit to 5
        result['resources'] = [r for r in result['resources'] if r][:5]  # Limit to 5
        
        return result
    
    def list_available_programs(self) -> List[str]:
        """
        List known Ontario Health clinical programs.
        
        Returns:
            List of available program names
        """
        return [
            "Cancer Screening",
            "Cancer Care",
            "Renal/Kidney Care",
            "Cardiac Care",
            "Stroke Care",
            "Critical Care",
            "Palliative Care",
            "Mental Health and Addictions",
            "Maternal and Child Health",
            "Diabetes Management",
            "Chronic Disease Management",
            "Surgical Care",
            "Emergency Care",
            "Primary Care",
            "Home and Community Care",
            "Long-Term Care",
            "Indigenous Health",
            "Francophone Health",
            "Transplant",
            "Genetics and Genomics"
        ]


# Singleton instance
_client = None

def get_client() -> OntarioHealthProgramsClient:
    """Get or create the Ontario Health Programs client singleton."""
    global _client
    if _client is None:
        _client = OntarioHealthProgramsClient()
    return _client