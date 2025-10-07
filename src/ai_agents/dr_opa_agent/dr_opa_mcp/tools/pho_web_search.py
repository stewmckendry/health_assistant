"""
Public Health Ontario (PHO) web search tool using Claude with web_search.
Provides real-time access to PHO's extensive public health resources.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import json

logger = logging.getLogger(__name__)

# PHO and Canadian public health domains
PHO_DOMAINS = [
    # Core PHO domains
    "publichealthontario.ca",
    "oahpp.ca",  # Ontario Agency for Health Protection and Promotion (PHO's legal name)

    # Canadian public health authorities
    "canada.ca/en/public-health",
    "phac-aspc.gc.ca",  # Public Health Agency of Canada
    "nccid.ca",  # National Collaborating Centre for Infectious Diseases
    "ncceh.ca",  # National Collaborating Centre for Environmental Health
    "nccmt.ca",  # National Collaborating Centre for Methods and Tools

    # Provincial health authorities (for comparison/best practices)
    "bccdc.ca",  # BC Centre for Disease Control
    "albertahealthservices.ca/poph",  # Alberta Public Health
    "health.gov.on.ca/en/public",  # Ontario Ministry of Health - Public Health

    # Specific PHO program areas
    "ophea.net",  # Ontario Physical and Health Education Association
    "hpepractice.ca",  # Health Promotion and Education Practice
]

# PHO topic areas for focused search
PHO_TOPICS = {
    "infectious_disease": [
        "COVID-19", "influenza", "respiratory illness", "tuberculosis",
        "sexually transmitted infections", "STI", "HIV", "hepatitis",
        "vaccine-preventable diseases", "immunization"
    ],
    "ipac": [
        "infection prevention and control", "IPAC", "hand hygiene",
        "personal protective equipment", "PPE", "outbreak management",
        "environmental cleaning", "sterilization", "disinfection"
    ],
    "antimicrobial_stewardship": [
        "antimicrobial resistance", "AMR", "antibiotic stewardship",
        "antimicrobial use", "resistance surveillance"
    ],
    "environmental_health": [
        "water quality", "air quality", "food safety", "environmental hazards",
        "climate change and health", "vector-borne disease"
    ],
    "health_equity": [
        "health equity", "social determinants of health", "SDOH",
        "vulnerable populations", "health disparities"
    ],
    "emergency_preparedness": [
        "emergency preparedness", "pandemic planning", "outbreak response",
        "public health emergency", "mass vaccination"
    ],
    "chronic_disease": [
        "chronic disease prevention", "cancer prevention", "diabetes",
        "cardiovascular disease", "tobacco control", "healthy eating"
    ],
    "data_surveillance": [
        "public health surveillance", "reportable diseases", "outbreak investigation",
        "epidemiology", "health data", "OLIS"  # Ontario Laboratory Information System
    ]
}


class PHOWebSearchClient:
    """Client for Public Health Ontario resources using Claude with web_search."""

    def __init__(self):
        """Initialize the PHO web search client."""
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-latest"
        self.max_tokens = 2000

        logger.info(f"PHO web search client initialized with {len(PHO_DOMAINS)} domains")

    def search_pho_guidance(
        self,
        topic: str,
        subtopics: Optional[List[str]] = None,
        clinical_setting: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for PHO public health guidance using Claude with web_search.

        Args:
            topic: Main public health topic (e.g., "IPAC", "COVID-19", "immunization")
            subtopics: Optional list of specific subtopics (e.g., ["hand hygiene", "PPE"])
            clinical_setting: Optional clinical setting (e.g., "long-term care", "primary care", "hospital")
            resource_type: Optional resource type (e.g., "guidance document", "toolkit", "checklist", "factsheet")

        Returns:
            Dictionary with:
                - guidance: List of relevant PHO guidance documents
                - recommendations: Key recommendations extracted
                - links: Direct links to PHO resources
                - last_updated: When information was last updated
                - search_summary: Summary of search results
        """
        try:
            # Build search query
            query_parts = [f"Public Health Ontario {topic}"]

            if subtopics:
                query_parts.append(f"specifically about {', '.join(subtopics)}")

            if clinical_setting:
                query_parts.append(f"for {clinical_setting} setting")

            if resource_type:
                query_parts.append(f"{resource_type}")

            search_query = " ".join(query_parts)

            # Build prompt for Claude with JSON output request
            prompt = f"""Search for Public Health Ontario (PHO) guidance on: {search_query}

Focus on finding:
1. Official PHO guidance documents, toolkits, and recommendations
2. Most recent/updated information (check dates)
3. Practical implementation guidance for healthcare providers
4. Links to downloadable resources (PDFs, toolkits, checklists)
5. Evidence-based recommendations and best practices

Prioritize results from publichealthontario.ca and authoritative Canadian public health sources.

IMPORTANT: Return ONLY valid JSON with no additional text before or after. No preamble, no explanation, just the JSON object.

Required JSON structure:
{{
  "resources": [
    {{
      "title": "Resource title",
      "url": "https://publichealthontario.ca/...",
      "publication_date": "Month Year or null",
      "last_updated": "Month Year or null",
      "resource_type": "guidance|toolkit|checklist|factsheet|report",
      "summary": "Brief summary of the resource"
    }}
  ],
  "key_recommendations": [
    "Recommendation 1",
    "Recommendation 2"
  ],
  "summary": "Overall summary of findings"
}}

Only include resources you actually found URLs for. Be precise with URLs. Return only the JSON, nothing else."""

            # Make API call with web_search
            logger.info(f"Searching PHO for: {search_query}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "allowed_domains": PHO_DOMAINS,
                    "max_uses": 5  # Allow multiple searches for comprehensive results
                }]
            )

            # Extract text content from response
            search_results = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    search_results += block.text

            # Parse JSON response
            import re
            result = {
                "topic": topic,
                "search_query": search_query,
                "guidance": [],
                "recommendations": [],
                "links": [],
                "resources": [],
                "search_summary": "",
                "model_used": self.model,
                "domains_searched": PHO_DOMAINS[:5],
                "success": True
            }

            try:
                # Try to extract JSON from response (handle code blocks)
                json_match = re.search(r'```json\s*(\{.*\})\s*```', search_results, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON object directly (look for complete JSON with balanced braces)
                    # First try to find the start of JSON
                    start = search_results.find('{')
                    if start != -1:
                        # Find matching closing brace by counting
                        brace_count = 0
                        for i in range(start, len(search_results)):
                            if search_results[i] == '{':
                                brace_count += 1
                            elif search_results[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = search_results[start:i+1]
                                    break
                        else:
                            json_str = search_results
                    else:
                        json_str = search_results

                parsed_json = json.loads(json_str)

                # Extract structured data
                if 'resources' in parsed_json:
                    result['resources'] = parsed_json['resources']
                    result['links'] = [r.get('url') for r in parsed_json['resources'] if r.get('url')]
                    result['guidance'] = parsed_json['resources']

                if 'key_recommendations' in parsed_json:
                    result['recommendations'] = parsed_json['key_recommendations']

                if 'summary' in parsed_json:
                    result['search_summary'] = parsed_json['summary']
                else:
                    result['search_summary'] = search_results[:500]  # Fallback

                logger.info(f"Found {len(result['links'])} PHO resources for {topic}")

            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Could not parse JSON response, using fallback: {e}")
                # Fallback to regex extraction
                links = re.findall(r'https?://[^\s\)"\]]+', search_results)
                pho_links = [link for link in links if 'publichealthontario' in link]
                result["links"] = pho_links[:10]
                result["search_summary"] = search_results[:500]
                logger.info(f"Fallback: Found {len(pho_links)} PHO links for {topic}")

            return result

        except Exception as e:
            logger.error(f"Error searching PHO: {e}")
            return {
                "topic": topic,
                "search_query": search_query if 'search_query' in locals() else topic,
                "error": str(e),
                "success": False
            }

    def search_pho_data(
        self,
        data_topic: str,
        region: Optional[str] = None,
        time_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for PHO public health data and surveillance information.

        Args:
            data_topic: Type of data (e.g., "COVID-19 cases", "flu activity", "outbreak reports")
            region: Optional region/jurisdiction (e.g., "Toronto", "Ontario")
            time_period: Optional time period (e.g., "current", "2024", "past year")

        Returns:
            Dictionary with data sources and surveillance information
        """
        query_parts = [f"Public Health Ontario {data_topic} data surveillance"]

        if region:
            query_parts.append(f"in {region}")

        if time_period:
            query_parts.append(f"for {time_period}")

        search_query = " ".join(query_parts)

        # Specialized prompt for data/surveillance with JSON output
        prompt = f"""Find Public Health Ontario data and surveillance information on: {search_query}

Look for:
1. Current surveillance reports and data dashboards
2. Reportable disease data
3. Laboratory surveillance information
4. Outbreak reports and trends
5. Data visualization tools and interactive dashboards

IMPORTANT: Return ONLY valid JSON with no additional text before or after. No preamble, no explanation, just the JSON object.

Required JSON structure:
{{
  "data_sources": [
    {{
      "title": "Data source or dashboard name",
      "url": "https://publichealthontario.ca/...",
      "last_updated": "Date or null",
      "data_type": "surveillance|dashboard|report|outbreak",
      "description": "Brief description"
    }}
  ],
  "key_findings": [
    "Finding 1",
    "Finding 2"
  ],
  "summary": "Overall summary of data findings"
}}

Only include data sources you actually found URLs for. Be precise with URLs. Return only the JSON, nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "allowed_domains": PHO_DOMAINS,
                    "max_uses": 3
                }]
            )

            search_results = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    search_results += block.text

            # Parse JSON response
            import re
            result = {
                "data_topic": data_topic,
                "search_query": search_query,
                "data_sources": [],
                "key_findings": [],
                "links": [],
                "summary": "",
                "success": True
            }

            try:
                # Try to extract JSON from response (handle code blocks)
                json_match = re.search(r'```json\s*(\{.*\})\s*```', search_results, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON object directly (look for complete JSON with balanced braces)
                    start = search_results.find('{')
                    if start != -1:
                        # Find matching closing brace by counting
                        brace_count = 0
                        for i in range(start, len(search_results)):
                            if search_results[i] == '{':
                                brace_count += 1
                            elif search_results[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = search_results[start:i+1]
                                    break
                        else:
                            json_str = search_results
                    else:
                        json_str = search_results

                parsed_json = json.loads(json_str)

                if 'data_sources' in parsed_json:
                    result['data_sources'] = parsed_json['data_sources']
                    result['links'] = [ds.get('url') for ds in parsed_json['data_sources'] if ds.get('url')]

                if 'key_findings' in parsed_json:
                    result['key_findings'] = parsed_json['key_findings']

                if 'summary' in parsed_json:
                    result['summary'] = parsed_json['summary']
                else:
                    result['summary'] = search_results[:500]

                logger.info(f"Found {len(result['links'])} PHO data sources")

            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Could not parse JSON response, using fallback: {e}")
                result['summary'] = search_results[:500]
                # Extract any URLs as fallback
                links = re.findall(r'https?://[^\s\)"\]]+', search_results)
                result['links'] = [link for link in links if 'publichealthontario' in link][:10]

            return result

        except Exception as e:
            logger.error(f"Error searching PHO data: {e}")
            return {
                "data_topic": data_topic,
                "error": str(e),
                "success": False
            }


# MCP tool wrapper functions
def search_pho_guidance_tool(
    topic: str,
    subtopics: Optional[List[str]] = None,
    clinical_setting: Optional[str] = None,
    resource_type: Optional[str] = None
) -> str:
    """
    Search Public Health Ontario for clinical guidance and recommendations.

    Use this tool to find current PHO guidance on public health topics including:
    - Infection prevention and control (IPAC)
    - Infectious diseases (COVID-19, influenza, TB, STIs, etc.)
    - Immunization and vaccine-preventable diseases
    - Environmental health and safety
    - Chronic disease prevention
    - Emergency preparedness

    Args:
        topic: Main public health topic
        subtopics: Optional specific areas of interest
        clinical_setting: Optional clinical setting (e.g., "long-term care", "primary care")
        resource_type: Optional type of resource (e.g., "toolkit", "checklist", "guidance")

    Returns:
        JSON string with PHO guidance, recommendations, and resource links
    """
    client = PHOWebSearchClient()
    result = client.search_pho_guidance(topic, subtopics, clinical_setting, resource_type)
    return json.dumps(result, indent=2)


def search_pho_data_tool(
    data_topic: str,
    region: Optional[str] = None,
    time_period: Optional[str] = None
) -> str:
    """
    Search Public Health Ontario for surveillance data and public health statistics.

    Use this tool to find current PHO data on:
    - Disease surveillance and reportable diseases
    - Outbreak reports and trends
    - Laboratory surveillance data
    - Public health indicators

    Args:
        data_topic: Type of data needed
        region: Optional geographic region
        time_period: Optional time period

    Returns:
        JSON string with data sources and surveillance information
    """
    client = PHOWebSearchClient()
    result = client.search_pho_data(data_topic, region, time_period)
    return json.dumps(result, indent=2)
