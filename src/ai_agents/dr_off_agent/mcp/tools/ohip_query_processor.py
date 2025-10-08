"""
OHIP Schedule Query Processor - Flexible natural language billing query understanding.

Adapted from ODB query processor pattern for OHIP billing codes and fees.
Handles complex clinical billing questions like:
- "Can I bill C124 as MRP after 3 days?"
- "House call codes for elderly patient"
- "ER consultation as internist"
- "Discharge codes for Monday 2pm to Thursday 10am admission"

Architecture:
    Query → Understand (LLM) → Expand Terms → Retrieve (SQL+Vector) → Enrich (LLM) → Format
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from .ohip_query_models import (
    BillingQueryIntent,
    QueryModifiers,
    RetrievalResult,
    EnrichedBillingResult,
    BillingEligibility,
    YesNoAnswer,
    PremiumModifier
)
from ..retrieval import SQLClient, VectorClient

load_dotenv()
logger = logging.getLogger(__name__)


class OHIPQueryProcessor:
    """
    Flexible natural language query processor for OHIP Schedule of Benefits.
    Uses LLM for understanding billing intent and enrichment.
    """

    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize OHIP query processor.

        Args:
            sql_client: SQL client for OHIP fee codes
            vector_client: Vector client for OHIP documents
            model: OpenAI model for query understanding
        """
        self.sql_client = sql_client or SQLClient(
            db_path="data/ohip.db",
            timeout_ms=500
        )
        self.vector_client = vector_client or VectorClient(
            persist_directory=None,
            timeout_ms=5000
        )

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.llm = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"OHIP Query Processor initialized with model: {model}")

    # ========================================================================
    # STEP 1: Query Understanding
    # ========================================================================

    async def understand_query(self, raw_query: str) -> BillingQueryIntent:
        """
        Use LLM to understand clinician's billing intent from natural language.

        This handles the complexity of medical billing terminology:
        - "MRP" → Most Responsible Physician
        - "house call" → specific billing codes
        - "ER consultation as internist" → specialty + location context

        Args:
            raw_query: Natural language billing query

        Returns:
            BillingQueryIntent with structured understanding
        """
        logger.info(f"Understanding OHIP billing query: '{raw_query}'")

        prompt = f"""You are analyzing a query about OHIP (Ontario Health Insurance Plan) billing codes and fees.

Query: "{raw_query}"

Analyze this billing query and extract structured information. Return ONLY valid JSON:

{{
    "query_type": "<code_lookup|service_discovery|eligibility_check|fee_inquiry|specialty_search|premium_modifier|yes_no|general>",
    "billing_codes": ["list of OHIP codes mentioned like 'C124', 'K013', 'A007'"],
    "service_types": ["types of services mentioned like 'consultation', 'house call', 'discharge', 'assessment'"],
    "clinical_terms": ["billing/clinical terms like 'MRP', 'comprehensive geriatric assessment', 'surgical assist'"],
    "specialty": "<medical specialty like 'internist', 'family practice', 'surgery', or null>",
    "location": "<care location like 'ER', 'emergency', 'LTC', 'long-term care', 'office', 'hospital', or null>",
    "modifiers": {{
        "time_based": <true if query involves time/dates>,
        "eligibility_focused": <true if asking about billing eligibility>,
        "cost_focused": <true if asking about fees>,
        "location_specific": <true if location matters>
    }},
    "expects_yes_no": <true if expecting yes/no answer>,
    "time_context": {{"any time-related info like admission/discharge times, duration"}},
    "patient_context": {{"any patient info like age, condition, admission length"}}
}}

Query type definitions:
- "code_lookup": Asking about specific code (e.g., "What is K013?")
- "service_discovery": Looking for codes for a service (e.g., "house call codes")
- "eligibility_check": Can I bill this? (e.g., "Can I bill C124 as MRP?")
- "fee_inquiry": How much does this pay? (e.g., "fee for consultation")
- "specialty_search": Service + specialty (e.g., "internist ER consultation")
- "premium_modifier": Asking about premiums (e.g., "elderly patient premium")
- "yes_no": Expects yes/no (e.g., "Can I bill this?")
- "general": Doesn't fit other categories

IMPORTANT TERMINOLOGY:
- "MRP" = Most Responsible Physician
- "comprehensive geriatric assessment" = specific assessment type
- "house call" = physician visit to patient's home
- "ER" or "emergency" = emergency department
- "LTC" = long-term care facility
- "discharge" = patient leaving hospital

Examples:
- "Can I bill C124 as MRP?" → {{"query_type": "eligibility_check", "billing_codes": ["C124"], "clinical_terms": ["MRP"], "expects_yes_no": true}}
- "house call codes" → {{"query_type": "service_discovery", "service_types": ["house call"]}}
- "ER consultation as internist" → {{"query_type": "specialty_search", "service_types": ["consultation"], "specialty": "internal medicine", "location": "emergency"}}
- "discharge codes for 3-day admission" → {{"query_type": "service_discovery", "service_types": ["discharge"], "patient_context": {{"admission_days": 3}}}}

Return ONLY the JSON object, no other text."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM parsed billing intent: {result}")

            # Convert to BillingQueryIntent model
            intent = BillingQueryIntent(
                query_type=result.get("query_type", "general"),
                billing_codes=result.get("billing_codes", []),
                service_types=result.get("service_types", []),
                clinical_terms=result.get("clinical_terms", []),
                specialty=result.get("specialty"),
                location=result.get("location"),
                modifiers=QueryModifiers(**result.get("modifiers", {})),
                expects_yes_no=result.get("expects_yes_no", False),
                time_context=result.get("time_context"),
                patient_context=result.get("patient_context"),
                original_query=raw_query
            )

            # Enrich with clinical term expansion if needed
            if intent.clinical_terms or intent.service_types:
                logger.info(f"Expanding billing terms: {intent.clinical_terms + intent.service_types}")
                expanded_codes = await self._expand_billing_terms(
                    intent.clinical_terms + intent.service_types,
                    intent.specialty,
                    intent.location
                )
                intent.billing_codes.extend(expanded_codes)
                logger.info(f"Expanded to codes: {expanded_codes}")

            return intent

        except Exception as e:
            logger.error(f"Error understanding billing query: {e}")
            # Fallback to basic intent
            return BillingQueryIntent(
                query_type="general",
                billing_codes=[],
                service_types=[],
                clinical_terms=[],
                specialty=None,
                location=None,
                modifiers=QueryModifiers(),
                expects_yes_no=False,
                time_context=None,
                patient_context=None,
                original_query=raw_query
            )

    # ========================================================================
    # STEP 2: Clinical Term Expansion
    # ========================================================================

    async def _expand_billing_terms(
        self,
        clinical_terms: List[str],
        specialty: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[str]:
        """
        Map billing terminology to actual OHIP fee codes using vector search + LLM validation.

        Examples:
        - "MRP discharge" → ["C124", "C125", "C126"]
        - "house call" → ["K007", "K008", "K009"]
        - "comprehensive geriatric assessment" → ["K040", "K682"]

        Args:
            clinical_terms: List of billing/clinical terms
            specialty: Medical specialty context
            location: Care location context

        Returns:
            List of OHIP fee codes matching those terms
        """
        expanded_codes = []

        for term in clinical_terms:
            try:
                # Build context-aware search query
                query_parts = [f"OHIP billing code for {term}"]
                if specialty:
                    query_parts.append(f"specialty {specialty}")
                if location:
                    query_parts.append(f"location {location}")

                query = " ".join(query_parts)
                logger.debug(f"Vector search query: {query}")

                # Search OHIP documents
                results = await self.vector_client.search(
                    query=query,
                    collection="ohip_documents",
                    n_results=20  # Cast wide net
                )

                # Extract candidate codes from results
                candidates = []
                for result in results:
                    metadata = result.get('metadata', {})
                    text = result.get('text', '')

                    # Try to extract fee code from metadata
                    fee_code = metadata.get('fee_code')
                    if fee_code:
                        candidates.append({
                            'code': fee_code,
                            'description': metadata.get('description', text[:300]),
                            'specialty': metadata.get('specialty'),
                            'category': metadata.get('category')
                        })

                    # Also try to extract from text using pattern matching
                    import re
                    code_matches = re.findall(r'\b([A-Z]\d{3,4})\b', text)
                    for code in code_matches[:3]:  # Limit per result
                        if code not in [c['code'] for c in candidates]:
                            candidates.append({
                                'code': code,
                                'description': text[:300],
                                'specialty': metadata.get('specialty'),
                                'category': metadata.get('category')
                            })

                # Deduplicate by code
                unique_candidates = {c['code']: c for c in candidates}

                # Validate with LLM
                if unique_candidates:
                    validated = await self._validate_code_matches(
                        term,
                        list(unique_candidates.values())[:15],  # Top 15
                        specialty,
                        location
                    )
                    expanded_codes.extend(validated)

            except Exception as e:
                logger.error(f"Error expanding billing term '{term}': {e}")

        return list(set(expanded_codes))  # Deduplicate

    async def _validate_code_matches(
        self,
        billing_term: str,
        candidates: List[Dict[str, Any]],
        specialty: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[str]:
        """
        Validate which OHIP codes actually match the billing term using LLM.

        This prevents false positives (e.g., discharge codes vs discharge summary).

        Args:
            billing_term: Billing term to validate against
            candidates: List of candidate code dicts
            specialty: Specialty context
            location: Location context

        Returns:
            List of validated OHIP codes
        """
        if not candidates:
            return []

        # Build validation prompt
        candidate_list = "\n".join([
            f"- {c['code']}: {c['description'][:200]}"
            for c in candidates
        ])

        context_parts = []
        if specialty:
            context_parts.append(f"specialty: {specialty}")
        if location:
            context_parts.append(f"location: {location}")
        context_str = f" ({', '.join(context_parts)})" if context_parts else ""

        prompt = f"""Which OHIP billing codes match "{billing_term}"{context_str}?

Candidates:
{candidate_list}

Return ONLY valid JSON:
{{
    "matches": ["list of matching fee codes"],
    "reasoning": "brief explanation"
}}

Be strict - only include codes that actually relate to "{billing_term}"."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            matches = result.get("matches", [])
            logger.debug(f"Validated {len(matches)}/{len(candidates)} code matches for '{billing_term}'")

            return matches

        except Exception as e:
            logger.error(f"Error validating code matches: {e}")
            # Fallback: return top candidates
            return [c['code'] for c in candidates[:5]]

    # ========================================================================
    # STEP 3: Retrieval (SQL + Vector)
    # ========================================================================

    async def retrieve(self, intent: BillingQueryIntent) -> RetrievalResult:
        """
        Execute retrieval based on understood billing intent.

        Routes to appropriate retrieval strategy:
        - Direct code lookup: SQL-only (fast, exact)
        - Service discovery: hybrid (SQL + vector)
        - Eligibility: vector-focused (need policy text)

        Args:
            intent: Understood billing query intent

        Returns:
            RetrievalResult with SQL and vector results
        """
        logger.info(f"Retrieving billing data for query_type: {intent.query_type}")

        # Route based on query type
        if intent.query_type == "code_lookup" and intent.billing_codes:
            # SQL-only for direct code lookups
            logger.debug("Using SQL-only retrieval for code lookup")
            sql_results = await self._sql_retrieval(intent)
            return RetrievalResult(
                sql_results=sql_results,
                vector_results=[],
                sql_success=len(sql_results) > 0,
                vector_success=True  # Intentionally skipped
            )

        else:
            # Dual-path: run SQL and vector in parallel
            logger.debug("Using dual-path retrieval (SQL + vector)")
            sql_task = self._sql_retrieval(intent)
            vector_task = self._vector_retrieval(intent)

            sql_results, vector_results = await asyncio.gather(
                sql_task,
                vector_task,
                return_exceptions=True
            )

            # Handle exceptions
            sql_success = not isinstance(sql_results, Exception)
            vector_success = not isinstance(vector_results, Exception)

            if isinstance(sql_results, Exception):
                logger.warning(f"SQL retrieval failed: {sql_results}")
                sql_results = []

            if isinstance(vector_results, Exception):
                logger.warning(f"Vector retrieval failed: {vector_results}")
                vector_results = []

            return RetrievalResult(
                sql_results=sql_results,
                vector_results=vector_results,
                sql_success=sql_success,
                vector_success=vector_success
            )

    async def _sql_retrieval(self, intent: BillingQueryIntent) -> List[Dict[str, Any]]:
        """
        SQL query for OHIP fee codes.

        Args:
            intent: Query intent

        Returns:
            List of fee code records from SQL
        """
        if not intent.billing_codes:
            return []

        try:
            # Build SQL query for code lookup
            placeholders = ','.join(['?' for _ in intent.billing_codes])
            query = f"""
            SELECT
                fee_code as code,
                description,
                amount as fee,
                requirements,
                notes as limits,
                page_number as page_num
            FROM ohip_fee_schedule
            WHERE fee_code IN ({placeholders})
            LIMIT 50
            """

            results = await self.sql_client.query(query, tuple(intent.billing_codes))
            logger.debug(f"SQL retrieved {len(results)} codes")
            return results

        except Exception as e:
            logger.error(f"SQL retrieval error: {e}")
            raise

    async def _vector_retrieval(self, intent: BillingQueryIntent) -> List[Dict[str, Any]]:
        """
        Vector search for OHIP billing information.

        Builds context-aware query including service type, specialty, location.

        Args:
            intent: Query intent

        Returns:
            List of vector search results
        """
        try:
            # Build comprehensive search query
            query_parts = []

            if intent.service_types:
                query_parts.extend(intent.service_types)

            if intent.clinical_terms:
                query_parts.extend(intent.clinical_terms)

            if intent.specialty:
                query_parts.append(f"specialty {intent.specialty}")

            if intent.location:
                query_parts.append(f"location {intent.location}")

            if intent.billing_codes:
                query_parts.extend([f"code {code}" for code in intent.billing_codes])

            query = " ".join(query_parts) if query_parts else intent.original_query

            logger.debug(f"Vector search query: {query}")

            results = await self.vector_client.search(
                query=query,
                collection="ohip_documents",
                n_results=30
            )

            logger.debug(f"Vector retrieved {len(results)} documents")
            return results

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            raise

    # ========================================================================
    # STEP 4: LLM Enrichment
    # ========================================================================

    async def enrich_with_llm(
        self,
        intent: BillingQueryIntent,
        retrieval: RetrievalResult
    ) -> EnrichedBillingResult:
        """
        Enrich results with LLM extraction of structured billing information.

        Extracts:
        - Eligibility requirements
        - Yes/no answers to billing questions
        - Premium/modifier information
        - Clear billing explanations

        Args:
            intent: Original query intent
            retrieval: Retrieved data

        Returns:
            EnrichedBillingResult with structured information
        """
        logger.info(f"Enriching results for query type: {intent.query_type}")

        result = EnrichedBillingResult(
            intent=intent,
            retrieval=retrieval,
            enrichment_method="hybrid" if (retrieval.sql_results and retrieval.vector_results) else "sql_only" if retrieval.sql_results else "vector_only"
        )

        # Route enrichment based on query type
        if intent.query_type == "eligibility_check" and intent.billing_codes:
            result.eligibility = await self._extract_eligibility(intent, retrieval)

        elif intent.expects_yes_no or intent.query_type == "yes_no":
            result.yes_no_answer = await self._extract_yes_no(intent, retrieval)

        elif intent.query_type == "premium_modifier":
            result.premiums = await self._extract_premiums(intent, retrieval)

        # Always add general explanation
        result.billing_explanation = await self._generate_explanation(intent, retrieval)

        return result

    async def _extract_eligibility(
        self,
        intent: BillingQueryIntent,
        retrieval: RetrievalResult
    ) -> Optional[BillingEligibility]:
        """Extract structured eligibility information."""
        # Combine all context
        context_parts = []

        for sql_result in retrieval.sql_results[:3]:
            context_parts.append(f"Code {sql_result.get('code')}: {sql_result.get('description')}")
            if sql_result.get('requirements'):
                context_parts.append(f"Requirements: {sql_result.get('requirements')}")
            if sql_result.get('limits'):
                context_parts.append(f"Limits: {sql_result.get('limits')}")

        for vec_result in retrieval.vector_results[:5]:
            context_parts.append(vec_result.get('text', '')[:400])

        context = "\n\n".join(context_parts)

        if not context:
            return None

        prompt = f"""Based on this OHIP billing information, answer: "{intent.original_query}"

Information:
{context}

IMPORTANT NOTES:
- If fee is null/None BUT requirements mention "Add X%" or "premium", this is a MODIFIER CODE that adds to a base fee
- Premium codes like "Add 30%" are ADDITIONAL payments on top of the base service code
- Example: "Add 30%" means this code adds 30% to whatever base assessment code was billed

Return ONLY valid JSON:
{{
    "code": "<OHIP fee code>",
    "eligible": <true/false>,
    "explanation": "<clear explanation - if premium, explain it adds to base code>",
    "requirements": ["list of requirements to bill this code"],
    "exclusions": ["situations where billing is not allowed"],
    "documentation_required": ["documentation needed"],
    "specialty_restrictions": "<specialty restrictions or null>",
    "time_requirements": "<time-based requirements or null>"
}}"""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return BillingEligibility(**result)

        except Exception as e:
            logger.error(f"Error extracting eligibility: {e}")
            return None

    async def _extract_yes_no(
        self,
        intent: BillingQueryIntent,
        retrieval: RetrievalResult
    ) -> Optional[YesNoAnswer]:
        """Extract yes/no answer to billing question."""
        # Build context with emphasis on requirements
        context_parts = []

        for sql_result in retrieval.sql_results[:3]:
            code = sql_result.get('code')
            desc = sql_result.get('description')
            reqs = sql_result.get('requirements')

            context_parts.append(f"Code {code}: {desc}")
            if reqs:
                context_parts.append(f"  REQUIREMENTS: {reqs}")

        for vec_result in retrieval.vector_results[:5]:
            context_parts.append(vec_result.get('text', '')[:300])

        context = "\n".join(context_parts)

        if not context:
            return None

        prompt = f"""Answer this yes/no billing question: "{intent.original_query}"

OHIP Information:
{context}

CRITICAL RULES:
1. If REQUIREMENTS field contains "Not eligible for payment when", "Not payable with", or "Cannot be billed", you MUST answer "no"
2. NEVER contradict explicit SQL requirements - they are authoritative
3. If requirements say a condition prevents billing, the answer is "no" even if the code exists

Return ONLY valid JSON:
{{
    "answer": "<yes|no|conditional>",
    "explanation": "<brief explanation that respects requirements>",
    "conditions": ["conditions or restrictions from requirements field"],
    "applicable_codes": ["relevant OHIP codes"],
    "confidence": <0.0 to 1.0>
}}"""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return YesNoAnswer(**result)

        except Exception as e:
            logger.error(f"Error extracting yes/no answer: {e}")
            return None

    async def _extract_premiums(
        self,
        intent: BillingQueryIntent,
        retrieval: RetrievalResult
    ) -> List[PremiumModifier]:
        """Extract premium/modifier information."""
        # Build context from vector results (premiums often in policy text)
        context_parts = [r.get('text', '')[:400] for r in retrieval.vector_results[:5]]
        context = "\n\n".join(context_parts)

        if not context:
            return []

        prompt = f"""Extract premium/modifier information for: "{intent.original_query}"

Information:
{context}

Return ONLY valid JSON:
{{
    "premiums": [
        {{
            "code": "<premium code>",
            "description": "<what premium is for>",
            "amount": <amount or null>,
            "eligibility": "<when it applies>"
        }}
    ]
}}"""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return [PremiumModifier(**p) for p in result.get("premiums", [])]

        except Exception as e:
            logger.error(f"Error extracting premiums: {e}")
            return []

    async def _generate_explanation(
        self,
        intent: BillingQueryIntent,
        retrieval: RetrievalResult
    ) -> str:
        """Generate clear explanation for any billing query."""
        # Build context with requirements emphasized
        context_parts = []

        for sql_result in retrieval.sql_results[:5]:
            code = sql_result.get('code')
            desc = sql_result.get('description')
            fee = sql_result.get('fee', 'N/A')
            reqs = sql_result.get('requirements')

            context_parts.append(f"{code}: {desc} - ${fee}")
            if reqs:
                context_parts.append(f"  REQUIREMENTS: {reqs}")

        for vec_result in retrieval.vector_results[:3]:
            context_parts.append(vec_result.get('text', '')[:300])

        context = "\n".join(context_parts)

        if not context:
            return "No billing information found for this query."

        prompt = f"""Provide a clear, concise explanation for: "{intent.original_query}"

OHIP Information:
{context}

CRITICAL RULES FOR BILLING GUIDANCE:

1. PREMIUM/MODIFIER CODES (fee=null/None + "Add X%"):
   - These ARE billable - they add a percentage to the base service code
   - Answer should be "Yes, this is a X% premium you add to the base code"
   - Example: E082 with "Add 30%" means "Yes, add 30% to your MRP admission assessment"

2. RESTRICTION CODES ("Not eligible when"):
   - These are NOT billable when the condition applies
   - Answer should be "No, you cannot bill when [condition]"
   - Example: "Not eligible when using studies from other institution" = "No, cannot bill"

3. NEVER contradict REQUIREMENTS - they are the authoritative source

Write 2-3 sentences that:
- Directly answers with "Yes" or "No" based on the question
- For premiums: Explain it ADDS to base code (not standalone)
- For restrictions: Clearly state when billing is not allowed"""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "Unable to generate explanation."
