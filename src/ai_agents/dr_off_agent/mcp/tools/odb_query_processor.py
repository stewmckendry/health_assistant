"""
ODB Query Processor - Flexible natural language query understanding and processing.

This module implements an LLM + retrieval hybrid approach to handle the full range
of clinical queries about the ODB formulary, including:
- Coverage questions
- Limited Use criteria
- Therapeutic alternatives
- Cost comparisons
- Drug class searches
- Yes/no authorization questions

Architecture:
    Query → Understand (LLM) → Retrieve (SQL+Vector) → Enrich (LLM) → Format
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from .odb_query_models import (
    QueryIntent,
    QueryModifiers,
    RetrievalResult,
    EnrichedResult,
    LUCriteriaExtraction,
    YesNoAnswer,
    TherapeuticAlternative
)
from ..retrieval import SQLClient, VectorClient

load_dotenv()
logger = logging.getLogger(__name__)


class ODBQueryProcessor:
    """
    Flexible natural language query processor for ODB formulary.
    Uses LLM for understanding and enrichment, retrieval for facts.
    """

    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None,
        model: str = "gpt-4o-mini"  # Fast, cheap model for query understanding
    ):
        """
        Initialize query processor.

        Args:
            sql_client: SQL client for structured drug data
            vector_client: Vector client for policy documents
            model: OpenAI model for query understanding and enrichment
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

        logger.info(f"ODB Query Processor initialized with model: {model}")

    # ========================================================================
    # STEP 1: Query Understanding
    # ========================================================================

    async def understand_query(self, raw_query: str) -> QueryIntent:
        """
        Use LLM to understand user's intent from natural language query.

        This is the key to flexibility - the LLM can handle any variation
        of how clinicians might phrase their questions.

        Args:
            raw_query: Natural language query from user

        Returns:
            QueryIntent with structured understanding of the query
        """
        logger.info(f"Understanding query: '{raw_query}'")

        prompt = f"""You are analyzing a query about the Ontario Drug Benefit (ODB) formulary.

Query: "{raw_query}"

Analyze this query and extract structured information. Return ONLY valid JSON with this structure:

{{
    "query_type": "<coverage|alternatives|lu_criteria|cost|class_search|yes_no|general>",
    "drug_names": ["list of specific drug names mentioned (brand or generic)"],
    "drug_classes": ["therapeutic drug classes mentioned"],
    "clinical_terms": ["clinical terminology like 'GLP-1 agonist', 'ACE inhibitor', 'statin'"],
    "modifiers": {{
        "formulation": "<specific formulation like 'extended release' or null>",
        "cost_focused": <true if asking about cost/price>,
        "authorization_focused": <true if asking about authorization/LU>
    }},
    "expects_yes_no": <true if expecting yes/no answer>,
    "context": "<any condition or indication mentioned, or null>"
}}

Query type definitions:
- "coverage": Asking if a drug is covered (e.g., "Is X covered?", "coverage for X")
- "alternatives": Asking for alternative drugs (e.g., "alternatives to X", "generic for X")
- "lu_criteria": Asking about Limited Use criteria (e.g., "LU requirements for X", "does X need authorization")
- "cost": Focused on pricing (e.g., "cheapest X", "price of X")
- "class_search": Asking about a drug class (e.g., "diabetes medications", "statins")
- "yes_no": Expects yes/no answer (e.g., "does X need special authorization")
- "general": Doesn't fit other categories

Examples:
- "Is Ozempic covered?" → {{"query_type": "yes_no", "drug_names": ["Ozempic"], "expects_yes_no": true}}
- "blood pressure medications" → {{"query_type": "class_search", "drug_classes": ["antihypertensives"]}}
- "GLP-1 agonist" → {{"query_type": "class_search", "clinical_terms": ["GLP-1 agonist"]}}
- "alternatives to Lipitor" → {{"query_type": "alternatives", "drug_names": ["Lipitor"]}}
- "metformin LU criteria" → {{"query_type": "lu_criteria", "drug_names": ["metformin"]}}

Return ONLY the JSON object, no other text."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent parsing
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM parsed intent: {result}")

            # Convert to QueryIntent model
            intent = QueryIntent(
                query_type=result.get("query_type", "general"),
                drug_names=result.get("drug_names", []),
                drug_classes=result.get("drug_classes", []),
                clinical_terms=result.get("clinical_terms", []),
                modifiers=QueryModifiers(**result.get("modifiers", {})),
                expects_yes_no=result.get("expects_yes_no", False),
                context=result.get("context"),
                original_query=raw_query
            )

            # Enrich with clinical term expansion if needed
            if intent.clinical_terms:
                logger.info(f"Expanding clinical terms: {intent.clinical_terms}")
                expanded_drugs = await self._expand_clinical_terms(intent.clinical_terms)
                intent.drug_names.extend(expanded_drugs)
                logger.info(f"Expanded to drugs: {expanded_drugs}")

            return intent

        except Exception as e:
            logger.error(f"Error understanding query: {e}")
            # Fallback to basic intent
            return QueryIntent(
                query_type="general",
                drug_names=[],
                drug_classes=[],
                clinical_terms=[],
                modifiers=QueryModifiers(),
                expects_yes_no=False,
                context=None,
                original_query=raw_query
            )

    # ========================================================================
    # STEP 2: Clinical Term Expansion
    # ========================================================================

    async def _expand_clinical_terms(self, clinical_terms: List[str]) -> List[str]:
        """
        Map clinical terminology to actual drug names using vector search + LLM validation.

        This discovers drugs from ODB data itself rather than hardcoding mappings.
        For example: "GLP-1 agonist" → ["semaglutide", "liraglutide", "dulaglutide"]

        Args:
            clinical_terms: List of clinical terms (e.g., ["GLP-1 agonist"])

        Returns:
            List of drug names matching those clinical terms
        """
        expanded_drugs = []

        for term in clinical_terms:
            try:
                # Search ODB for drugs matching this clinical term
                query = f"therapeutic class {term} mechanism of action drugs"

                results = await self.vector_client.search_odb(
                    query=query,
                    n_results=15  # Cast wide net
                )

                # Extract candidate drugs from metadata
                candidates = []
                for result in results:
                    metadata = result.get('metadata', {})
                    generic = metadata.get('generic_name')
                    brand = metadata.get('brand_name')
                    text = result.get('text', '')

                    if generic:
                        candidates.append({
                            'drug': generic,
                            'context': text[:500]  # Keep context for validation
                        })
                    if brand and brand != generic:
                        candidates.append({
                            'drug': brand,
                            'context': text[:500]
                        })

                # Deduplicate
                unique_candidates = {c['drug']: c['context'] for c in candidates}

                # Validate with LLM (batch validation for efficiency)
                if unique_candidates:
                    validated = await self._validate_drug_matches(
                        term,
                        list(unique_candidates.items())[:10]  # Top 10 candidates
                    )
                    expanded_drugs.extend(validated)

            except Exception as e:
                logger.error(f"Error expanding clinical term '{term}': {e}")

        return list(set(expanded_drugs))  # Deduplicate

    async def _validate_drug_matches(
        self,
        clinical_term: str,
        candidates: List[tuple]  # [(drug_name, context), ...]
    ) -> List[str]:
        """
        Validate which drugs actually match the clinical term using LLM.

        This prevents false positives (e.g., insulin being returned for "GLP-1").

        Args:
            clinical_term: Clinical term to validate against
            candidates: List of (drug_name, context) tuples

        Returns:
            List of validated drug names
        """
        if not candidates:
            return []

        # Build validation prompt with all candidates
        candidate_list = "\n".join([
            f"- {drug}: {context[:200]}"
            for drug, context in candidates
        ])

        prompt = f"""Which of these drugs are "{clinical_term}" medications?

Candidates:
{candidate_list}

Return ONLY valid JSON:
{{
    "matches": ["list of drug names that match"],
    "reasoning": "brief explanation"
}}

Be strict - only include drugs that are actually {clinical_term} medications."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            matches = result.get("matches", [])
            logger.debug(f"Validated {len(matches)}/{len(candidates)} matches for '{clinical_term}'")

            return matches

        except Exception as e:
            logger.error(f"Error validating drug matches: {e}")
            # Fallback: return all candidates (permissive)
            return [drug for drug, _ in candidates]

    # ========================================================================
    # STEP 3: Retrieval (SQL + Vector)
    # ========================================================================

    async def retrieve(self, intent: QueryIntent) -> RetrievalResult:
        """
        Execute retrieval based on understood intent.

        Routes to appropriate retrieval strategy:
        - Class searches: vector-only (SQL won't help)
        - Specific drugs: dual-path (SQL + vector)
        - LU criteria: vector-focused

        Args:
            intent: Understood query intent

        Returns:
            RetrievalResult with SQL and vector results
        """
        logger.info(f"Retrieving data for query_type: {intent.query_type}")

        # Route based on query type
        if intent.query_type == "class_search":
            # Vector-only for broad class searches
            logger.debug("Using vector-only retrieval for class search")
            vector_results = await self._vector_retrieval(intent)
            return RetrievalResult(
                sql_results=[],
                vector_results=vector_results,
                sql_success=True,  # We intentionally skipped SQL
                vector_success=len(vector_results) > 0
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

    async def _sql_retrieval(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """
        SQL query for structured drug data.

        Builds flexible query based on intent, supporting:
        - Drug name search (brand OR generic)
        - Formulation filtering
        - Cost sorting

        Args:
            intent: Query intent

        Returns:
            List of drug records from SQL
        """
        if not intent.drug_names:
            return []

        try:
            results = await self.sql_client.query_odb_drugs(
                ingredient=' OR '.join(intent.drug_names) if intent.drug_names else None,
                limit=50
            )

            logger.debug(f"SQL retrieved {len(results)} drugs")
            return results

        except Exception as e:
            logger.error(f"SQL retrieval error: {e}")
            raise

    async def _vector_retrieval(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """
        Vector search for policy context, LU criteria, alternatives.

        Builds comprehensive semantic query from intent components.

        Args:
            intent: Query intent

        Returns:
            List of relevant document chunks from vector search
        """
        # Build semantic query
        query_parts = []

        # Add drugs
        query_parts.extend(intent.drug_names)

        # Add drug classes
        query_parts.extend(intent.drug_classes)

        # Add clinical context
        if intent.context:
            query_parts.append(intent.context)

        # Add focus-specific terms
        if intent.modifiers.authorization_focused:
            query_parts.append("limited use criteria special authorization requirements")

        if intent.modifiers.cost_focused:
            query_parts.append("lowest cost alternative generic price")

        if intent.query_type == "alternatives":
            query_parts.append("therapeutic alternatives interchangeable drugs")

        semantic_query = " ".join(query_parts) if query_parts else intent.original_query

        try:
            results = await self.vector_client.search_odb(
                query=semantic_query,
                n_results=20
            )

            logger.debug(f"Vector retrieved {len(results)} chunks")
            return results

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            raise

    # ========================================================================
    # STEP 4: LLM-Powered Enrichment
    # ========================================================================

    async def enrich_with_llm(
        self,
        intent: QueryIntent,
        retrieval: RetrievalResult
    ) -> EnrichedResult:
        """
        Use LLM to extract structured information from retrieved text.

        This is where we handle complex extractions that would be brittle
        with regex or rule-based approaches.

        Args:
            intent: Query intent
            retrieval: Retrieved data from SQL and vector

        Returns:
            EnrichedResult with structured extractions
        """
        logger.info(f"Enriching results for query_type: {intent.query_type}")

        enriched = EnrichedResult(
            intent=intent,
            retrieval=retrieval
        )

        # Route to appropriate enrichment based on query type
        try:
            if intent.query_type == "lu_criteria":
                enriched.lu_criteria = await self._extract_lu_criteria(intent, retrieval)
                enriched.enrichment_method = "llm_extraction"

            elif intent.query_type == "yes_no" or intent.expects_yes_no:
                enriched.yes_no_answer = await self._extract_yes_no_answer(intent, retrieval)
                enriched.enrichment_method = "llm_extraction"

            elif intent.query_type == "alternatives":
                enriched.therapeutic_alternatives = await self._extract_alternatives(intent, retrieval)
                enriched.enrichment_method = "hybrid"

            else:
                # For other types, just note we're using retrieval results
                enriched.enrichment_method = "sql_only" if retrieval.sql_results and not retrieval.vector_results else \
                                           "vector_only" if retrieval.vector_results and not retrieval.sql_results else \
                                           "hybrid"

        except Exception as e:
            logger.error(f"Error during LLM enrichment: {e}")
            enriched.processing_notes.append(f"Enrichment error: {str(e)}")

        return enriched

    async def _extract_lu_criteria(
        self,
        intent: QueryIntent,
        retrieval: RetrievalResult
    ) -> Optional[LUCriteriaExtraction]:
        """Extract Limited Use criteria from policy text using LLM."""
        # Gather context from vector results
        context_chunks = [
            chunk.get('text', '')
            for chunk in retrieval.vector_results[:10]
        ]
        context = "\n\n".join(context_chunks)

        if not context:
            return None

        drug_name = intent.drug_names[0] if intent.drug_names else "the drug"

        prompt = f"""Extract Limited Use (LU) criteria for {drug_name} from this ODB policy text:

{context}

Return ONLY valid JSON:
{{
    "lu_required": <true/false>,
    "criteria": "<specific requirements in plain language or null>",
    "exceptions": ["list any exceptions or empty list"],
    "documentation_required": ["what docs physician must submit or empty list"],
    "reference": "<section of formulary or null>"
}}

If no LU criteria found, return lu_required: false with other fields null/empty."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return LUCriteriaExtraction(**result)

        except Exception as e:
            logger.error(f"Error extracting LU criteria: {e}")
            return None

    async def _extract_yes_no_answer(
        self,
        intent: QueryIntent,
        retrieval: RetrievalResult
    ) -> Optional[YesNoAnswer]:
        """Answer yes/no questions about coverage using SQL + LLM."""
        # Check SQL first
        sql_covered = len(retrieval.sql_results) > 0

        # Gather context
        context_chunks = [
            chunk.get('text', '')
            for chunk in retrieval.vector_results[:5]
        ]
        context = "\n\n".join(context_chunks)

        prompt = f"""Question: {intent.original_query}

SQL Database: {"Drug found in formulary" if sql_covered else "Drug not found in formulary"}

Policy Context:
{context if context else "No additional policy context available"}

Provide a clear yes/no answer. Return ONLY valid JSON:
{{
    "answer": "<yes|no|conditional>",
    "explanation": "<brief explanation>",
    "conditions": ["any conditions or restrictions, or empty list"],
    "confidence": <0.0-1.0>
}}

Be conservative - use "conditional" if there are restrictions or requirements."""

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

    async def _extract_alternatives(
        self,
        intent: QueryIntent,
        retrieval: RetrievalResult
    ) -> List[TherapeuticAlternative]:
        """Find therapeutic alternatives using SQL + LLM."""
        alternatives = []

        # Gather context for LLM
        context_chunks = [
            chunk.get('text', '')
            for chunk in retrieval.vector_results[:10]
        ]
        context = "\n\n".join(context_chunks)

        if not context:
            return alternatives

        drug_name = intent.drug_names[0] if intent.drug_names else "the drug"

        prompt = f"""The patient is asking about alternatives to: {drug_name}

From this ODB formulary context, identify therapeutic alternatives:
{context}

Return ONLY valid JSON:
{{
    "therapeutic_alternatives": [
        {{
            "drug_name": "<generic name>",
            "brand_names": ["list of brand names or empty"],
            "reason": "<why this is an alternative>",
            "covered": <true/false>
        }}
    ]
}}

Only include drugs that are therapeutically similar (same drug class or indication).
Maximum 5 alternatives."""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Convert to TherapeuticAlternative objects
            for alt in result.get("therapeutic_alternatives", []):
                alternatives.append(TherapeuticAlternative(**alt))

            logger.debug(f"Extracted {len(alternatives)} therapeutic alternatives")

        except Exception as e:
            logger.error(f"Error extracting alternatives: {e}")

        return alternatives
