#!/usr/bin/env python3
"""
Evaluation CLI for Dr. OPA and Dr. OFF agents.

Usage:
    # Dr. OFF evaluations
    python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl
    python eval/run.py --agent dr_off --set eval/gold/dr_off/adp_devices.jsonl
    python eval/run.py --agent dr_off --set eval/gold/dr_off/odb_drugs.jsonl

    # Dr. OPA evaluations
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl
    python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl

    # Custom output path
    python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl --output results/custom.json
"""

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eval.metrics.retrieval import RetrievalMetrics
from eval.metrics.answer_quality import AnswerQualityJudge

# Import MCP client (same as agents use)
from agents.mcp.server import MCPServerStdio, MCPServerStdioParams

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_retrieved_items(items: List[Dict], agent: str) -> List[Dict]:
    """
    Normalize retrieved items from different agents into standard format with 'text' field.

    Dr. OFF schedule items have structured fields (code, description, fee, etc.)
    Dr. OPA sections already have a 'text' field.

    Args:
        items: Raw retrieved items from MCP tool
        agent: "dr_off" or "dr_opa"

    Returns:
        Normalized items with 'text' field added (modifies in place)
    """
    if agent == "dr_opa":
        # Dr. OPA sections already have 'text' field
        return items

    # Dr. OFF: construct text from ScheduleItem fields
    # Note: With Option A schema, text field should always be present,
    # but we maintain backward compatibility here
    for item in items:
        if "text" not in item or not item.get("text"):
            # Try to get fields from metadata first (Option A schema)
            metadata = item.get("metadata", {})

            # If metadata exists, use it; otherwise fall back to top-level fields
            parts = []
            code = metadata.get("code") or item.get("code")
            description = metadata.get("description") or item.get("description")
            fee = metadata.get("fee") or item.get("fee")
            requirements = metadata.get("requirements") or item.get("requirements")
            limits = metadata.get("limits") or item.get("limits")

            if code:
                parts.append(f"OHIP Fee Code {code}")
            if description:
                parts.append(f"Service: {description}")
            if fee is not None:
                parts.append(f"Fee Amount: ${fee}")
            if requirements:
                parts.append(f"Billing Requirements: {requirements}")
            if limits:
                parts.append(f"Service Limits: {limits}")

            item["text"] = "\n".join(parts) if parts else str(item)

    return items


def keyword_prefilter(chunk_text: str, keywords: List[str], min_matches: int = 1) -> bool:
    """
    Fast keyword-based pre-filter before expensive LLM evaluation.

    Args:
        chunk_text: The text content to check
        keywords: Keywords to look for
        min_matches: Minimum number of keywords that must match

    Returns:
        True if chunk passes pre-filter (has enough keyword matches)
    """
    chunk_lower = chunk_text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in chunk_lower)
    return matches >= min_matches


def llm_batch_evaluate_relevance(chunks: List[Dict], keywords: List[str], reason: str, query: str = "", expected_elements: List[str] = None) -> List[Dict]:
    """
    Batch LLM evaluation of multiple chunks in one API call for efficiency.

    Args:
        chunks: List of chunks with 'text' field
        keywords: Expected keywords to look for
        reason: What information we're looking for
        query: The user's original question
        expected_elements: List of information elements that should be present

    Returns:
        List of evaluation results (same order as chunks)
    """
    from openai import OpenAI
    import os
    import json

    if not chunks:
        return []

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Build expected information section
    expected_info = ""
    if expected_elements:
        expected_info = "\nInformation needed:\n" + "\n".join(f"- {elem}" for elem in expected_elements[:5]) + "\n"  # Limit to 5 elements

    # Build query context
    query_context = f'User asked: "{query}"\n\n' if query else ""

    # Format all chunks for batch evaluation
    chunks_text = ""
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")[:800]  # Reduced from 1500 to fit more chunks
        chunks_text += f"\n--- CHUNK {i} ---\n{text}\n"

    prompt = f"""{query_context}Looking for: {reason}
{expected_info}Keywords: {', '.join(keywords[:10])}

Evaluate ALL chunks below and respond with a JSON array where each element corresponds to a chunk:
{chunks_text}

Respond with ONLY a JSON array like:
[
  {{"relevant": true, "confidence": 0.9, "reasoning": "Contains X and Y"}},
  {{"relevant": false, "confidence": 0.3, "reasoning": "Missing key info"}},
  ...
]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise evaluator. Respond with ONLY a JSON array, one evaluation per chunk in order."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000  # Enough for ~10-15 chunks
        )

        result_text = response.choices[0].message.content.strip()
        results = json.loads(result_text)

        # Ensure we have results for all chunks
        while len(results) < len(chunks):
            results.append({"relevant": False, "confidence": 0.0, "reasoning": "No evaluation returned"})

        return results[:len(chunks)]  # Trim to exact chunk count

    except Exception as e:
        logger.warning(f"Batch LLM evaluation failed: {e}")
        return [{"relevant": False, "confidence": 0.0, "reasoning": f"Evaluation failed: {str(e)}"} for _ in chunks]


def llm_evaluate_relevance(chunk_text: str, keywords: List[str], reason: str, query: str = "", expected_elements: List[str] = None) -> Dict:
    """
    Use LLM to evaluate chunk relevance with confidence score and gap analysis.

    Args:
        chunk_text: The text content to evaluate
        keywords: Expected keywords to look for
        reason: What information we're looking for (e.g., "C124 MRP billing requirements")
        query: The user's original question (provides context for relevance)
        expected_elements: List of information elements that should be present

    Returns:
        Dict with: relevant (bool), confidence (float), reasoning (str),
                   keyword_coverage (dict), information_coverage (dict), gaps (list)
    """
    from openai import OpenAI
    import os
    import json

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Build expected information section
    expected_info = ""
    if expected_elements:
        expected_info = "\nInformation needed to answer the question:\n" + "\n".join(f"- {elem}" for elem in expected_elements) + "\n"

    # Build query context
    query_context = f'User asked: "{query}"\n\nYou are evaluating whether this chunk helps answer that question.\n\n' if query else ""

    prompt = f"""{query_context}What we're looking for: {reason}
{expected_info}
Expected keywords to look for: {', '.join(keywords)}

Chunk text:
{chunk_text[:1500]}

Evaluate this chunk and respond with a JSON object containing:
{{
    "relevant": true/false,
    "confidence": 0.0-1.0 (how confident are you in this assessment),
    "reasoning": "brief explanation of why it is or isn't relevant",
    "keyword_coverage": {{"keyword1": true/false, "keyword2": true/false, ...}},
    "information_coverage": {{"element1": "covered/partial/missing", ...}} (only if expected elements provided),
    "gaps": ["list", "of", "missing", "information"] (empty array if fully relevant)
}}

Respond with ONLY the JSON object, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise evaluator of document relevance. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=500  # Increased to accommodate information_coverage field
        )

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        return result

    except Exception as e:
        logger.warning(f"LLM relevance evaluation failed: {e}")
        # Return default structure on error
        return {
            "relevant": False,
            "confidence": 0.0,
            "reasoning": f"Evaluation failed: {str(e)}",
            "keyword_coverage": {},
            "gaps": ["LLM evaluation error"]
        }


def is_chunk_relevant(chunk: Dict, match_criteria: List[Dict], query: str = "", expected_elements: List[str] = None, confidence_threshold: float = 0.7) -> bool:
    """
    Check if a retrieved chunk matches any relevance criteria using LLM-based semantic matching.

    Uses OpenAI GPT-4o-mini to evaluate semantic relevance with confidence scoring,
    allowing for flexible interpretation while capturing detailed matching information.

    Args:
        chunk: Retrieved chunk with 'text' and 'metadata' fields
        match_criteria: List of matching criteria from gold dataset
        query: The user's original question (provides context for relevance)
        expected_elements: List of information elements that should be present
        confidence_threshold: Minimum confidence (0.0-1.0) to consider chunk relevant

    Returns:
        True if chunk matches any criterion with sufficient confidence

    Example:
        >>> chunk = {"text": "Fee Code C124 - Most Responsible Physician requires 48 hour admission"}
        >>> criteria = [{
        ...     "type": "content_keywords",
        ...     "keywords": ["C124", "MRP", "48 hour"],
        ...     "min_matches": 3,
        ...     "reason": "C124 MRP billing requirements"
        ... }]
        >>> is_chunk_relevant(chunk, criteria, query="What are C124 billing requirements?")
        True
    """
    chunk_text = chunk.get("text", "")
    if not chunk_text:
        return False

    # Store detailed match results in chunk for later inspection
    if "match_details" not in chunk:
        chunk["match_details"] = []

    for criterion in match_criteria:
        if criterion["type"] == "content_keywords":
            keywords = criterion["keywords"]
            reason = criterion.get("reason", "relevant information")

            # Use LLM to evaluate semantic relevance with query and expected elements for context
            match_result = llm_evaluate_relevance(chunk_text, keywords, reason, query, expected_elements)

            # Store detailed results
            chunk["match_details"].append({
                "criterion": reason,
                "result": match_result
            })

            # Check if relevant with sufficient confidence
            if match_result["relevant"] and match_result["confidence"] >= confidence_threshold:
                logger.debug(
                    f"✓ LLM matched chunk (confidence: {match_result['confidence']:.2f}): {reason}\n"
                    f"  Reasoning: {match_result['reasoning']}\n"
                    f"  Keywords: {match_result['keyword_coverage']}"
                )
                return True
            else:
                logger.debug(
                    f"✗ LLM rejected chunk (confidence: {match_result['confidence']:.2f}): {reason}\n"
                    f"  Reasoning: {match_result['reasoning']}\n"
                    f"  Gaps: {match_result['gaps']}"
                )

        elif criterion["type"] == "document_metadata":
            metadata = chunk.get("metadata", {})

            # Check document title
            if "doc_title_contains" in criterion:
                doc_title = metadata.get("document_title", "").lower()
                if criterion["doc_title_contains"].lower() in doc_title:
                    logger.debug(f"Chunk matched document title: {criterion.get('reason', 'N/A')}")
                    return True

            # Check section heading
            if "section_contains" in criterion:
                section = metadata.get("section_heading", "").lower()
                if criterion["section_contains"].lower() in section:
                    logger.debug(f"Chunk matched section: {criterion.get('reason', 'N/A')}")
                    return True

    return False


class MCPToolClient:
    """Client for calling MCP tools via stdio."""

    def __init__(self, agent: str):
        """
        Initialize MCP client for given agent.

        Args:
            agent: "dr_off" or "dr_opa"
        """
        self.agent = agent
        self.server: Optional[MCPServerStdio] = None

        # Set up MCP server command
        if agent == "dr_off":
            command = ["python", "-m", "src.ai_agents.dr_off_agent.mcp.server"]
            server_name = "dr-off-eval"
        elif agent == "dr_opa":
            command = ["python", "-m", "src.ai_agents.dr_opa_agent.dr_opa_mcp.server"]
            server_name = "dr-opa-eval"
        else:
            raise ValueError(f"Unknown agent: {agent}")

        self.server = MCPServerStdio(
            params=MCPServerStdioParams(
                command=command[0],
                args=command[1:],
                env=dict(os.environ),
                cwd=str(project_root),
                encoding="utf-8"
            ),
            name=server_name,
            client_session_timeout_seconds=90.0  # Extended timeout for web searches
        )

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response as dict
        """
        if not self.server:
            raise RuntimeError("MCP server not initialized")

        logger.debug(f"Calling {tool_name} with args: {arguments}")

        try:
            # Call the tool through MCP server
            result = await self.server.call_tool(tool_name, arguments)

            # Debug: log the result structure
            logger.debug(f"Result type: {type(result)}")
            logger.debug(f"Result has content: {hasattr(result, 'content')}")
            if hasattr(result, 'content'):
                logger.debug(f"Content type: {type(result.content)}")
                logger.debug(f"Content length: {len(result.content) if isinstance(result.content, list) else 'N/A'}")
                if isinstance(result.content, list) and len(result.content) > 0:
                    logger.debug(f"First content item: {result.content[0]}")

            # Parse the result (MCP returns different formats)
            if hasattr(result, 'content'):
                # MCP result object
                if isinstance(result.content, list) and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        text = content.text
                        logger.debug(f"Text content: {text[:200] if text else 'EMPTY'}")
                        if text and text.strip():
                            try:
                                response = json.loads(text)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON from {tool_name}: {e}")
                                logger.error(f"Raw text length: {len(text)}, content: {text[:500]}")
                                response = {"answer": "", "sources": [], "retrieved_chunks": []}
                        else:
                            logger.warning(f"Empty text response from {tool_name}")
                            response = {"answer": "", "sources": [], "retrieved_chunks": []}
                    else:
                        response = {"text": str(content)}
                else:
                    response = {"text": str(result.content)}
            elif isinstance(result, dict):
                response = result
            elif isinstance(result, str):
                response = json.loads(result)
            else:
                response = {"text": str(result)}

            return response

        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise


async def call_dr_off_tool(client: MCPToolClient, tool_name: str, query: str, k: int = 50, filters: Dict = None) -> Dict:
    """
    Call Dr. OFF MCP tool using StandardToolRequest.

    Args:
        client: MCPToolClient instance
        tool_name: MCP tool name (e.g., "schedule_get")
        query: Query string
        k: Number of results to return (default: 50)
        filters: Optional tool-specific filters

    Returns:
        Tool response with items, summary, citations
    """
    # Build StandardToolRequest
    request = {
        "query": query,
        "k": k
    }
    if filters:
        request["filters"] = filters

    response = await client.call_tool(tool_name, request)

    # Dr. OFF tools return: {items: [...], confidence: ..., citations: [...]}
    # Return standardized format consistent with Option A schema
    return {
        "items": response.get("items", []),
        "summary": response.get("summary", ""),
        "citations": response.get("citations", []),
        "confidence": response.get("confidence", 0.0)
    }


async def call_dr_opa_tool(client: MCPToolClient, tool_name: str, query: str, k: int = 50, filters: Dict = None) -> Dict:
    """
    Call Dr. OPA MCP tool using StandardToolRequest.

    Args:
        client: MCPToolClient instance
        tool_name: MCP tool name (e.g., "opa_search_sections")
        query: Query string
        k: Number of results to retrieve (default: 50)
        filters: Optional tool-specific filters

    Returns:
        Tool response with items, summary, citations
    """
    # Build StandardToolRequest
    request = {
        "query": query,
        "k": k
    }
    if filters:
        request["filters"] = filters

    response = await client.call_tool(tool_name, request)

    # Dr. OPA tools return: {items: [...], summary: "...", citations: [...]}
    # Return standardized format consistent with Option A schema
    return {
        "items": response.get("items", []),
        "summary": response.get("summary", ""),
        "citations": response.get("citations", []),
        "confidence": response.get("confidence", 0.0)
    }


async def evaluate_query(
    item: Dict,
    agent: str,
    mcp_client: MCPToolClient,
    retrieval_metrics: RetrievalMetrics,
    answer_judge: AnswerQualityJudge
) -> Dict:
    """
    Evaluate a single query.

    Args:
        item: Gold dataset item
        agent: "dr_off" or "dr_opa"
        retrieval_metrics: RetrievalMetrics instance
        answer_judge: AnswerQualityJudge instance

    Returns:
        Dict with evaluation results
    """
    query_id = item["id"]
    query = item["query"]
    intent = item["intent"]

    logger.info(f"\n🔍 Evaluating query {query_id}: {query[:60]}...")
    logger.debug(f"Item keys: {list(item.keys())}")
    logger.debug(f"Has expert_answer: {'expert_answer' in item}, value preview: {str(item.get('expert_answer', 'MISSING'))[:50]}")

    # Execute query through agent
    if agent == "dr_off":
        # Call appropriate Dr. OFF tool based on intent
        # All tools now use StandardToolRequest with query, k, filters
        if intent == "ohip_billing":
            response = await call_dr_off_tool(mcp_client, "schedule_get", query, k=50)
        elif intent == "adp_devices":
            response = await call_dr_off_tool(mcp_client, "adp_get", query, k=50)
        elif intent == "odb_drugs":
            response = await call_dr_off_tool(mcp_client, "odb_get", query, k=50)
        else:
            logger.error(f"Unknown intent for dr_off: {intent}")
            return {"error": f"Unknown intent: {intent}"}

        # All Dr. OFF tools now return "items" with Option A schema:
        # - schedule_get: List[ScheduleItem]
        # - adp_get: List[RetrievedItem]
        # - odb_get: List[RetrievedItem]
        retrieved_items = response.get("items", [])

        # DEBUG: Log what we got back
        logger.debug(f"Response keys: {response.keys()}")
        logger.debug(f"Retrieved items count: {len(retrieved_items)}")
        if retrieved_items:
            logger.debug(f"Sample item keys: {retrieved_items[0].keys() if retrieved_items else 'N/A'}")

        # Normalize Dr. OFF items to ensure 'text' field exists
        retrieved_items = normalize_retrieved_items(retrieved_items, agent)

    elif agent == "dr_opa":
        # Call appropriate Dr. OPA tool based on intent
        # All tools now use StandardToolRequest with query, k, filters
        if intent == "cpso_policy":
            response = await call_dr_opa_tool(mcp_client, "opa_policy_check", query, k=50)
        elif intent == "ontario_health_program":
            response = await call_dr_opa_tool(mcp_client, "opa_program_lookup", query, k=50)
        elif intent == "pho_ipac":
            response = await call_dr_opa_tool(mcp_client, "opa_ipac_guidance", query, k=50)
        elif intent == "cep_tool":
            response = await call_dr_opa_tool(mcp_client, "opa_clinical_tools", query, k=50)
        elif intent == "quality_standard":
            response = await call_dr_opa_tool(mcp_client, "opa_quality_standards", query, k=50)
        elif intent == "choosing_wisely":
            response = await call_dr_opa_tool(mcp_client, "opa_choosing_wisely", query, k=50)
        else:
            # Fallback to general search
            response = await call_dr_opa_tool(mcp_client, "opa_search_sections", query, k=50)

        # All Dr. OPA tools now return "items" with Option A schema:
        # - opa_search_sections, opa_get_section, opa_policy_check, opa_program_lookup, opa_ipac_guidance: List[Section]
        # - opa_quality_standards: List[QualityStatement]
        # - opa_choosing_wisely: List[ChoosingWiselyRecommendation]
        retrieved_items = response.get("items", [])

        # DEBUG: Log what we got back
        logger.info(f"Dr. OPA Response keys: {response.keys()}")
        logger.info(f"Retrieved items count: {len(retrieved_items)}")
        if retrieved_items:
            logger.info(f"Sample item keys: {retrieved_items[0].keys() if retrieved_items else 'N/A'}")

        # Normalize Dr. OPA items to ensure consistency
        retrieved_items = normalize_retrieved_items(retrieved_items, agent)

    else:
        logger.error(f"Unknown agent: {agent}")
        return {"error": f"Unknown agent: {agent}"}

    # Extract retrieval IDs for tracking
    retrieved_ids = [r.get("id", r.get("section_id", f"item_{i}"))
                     for i, r in enumerate(retrieved_items)]

    # Use flexible matching to determine relevant chunks
    expected_sources = item.get("expected_sources", [])
    match_details_all = []  # Collect detailed match info for debugging

    # Extract query and expected answer elements for LLM context
    query = item.get("query", "")
    expected_elements = item.get("expected_answer_elements", None)

    if expected_sources and "match_criteria" in expected_sources[0]:
        # New schema: flexible matching with LLM evaluation (OPTIMIZED)
        match_criteria = expected_sources[0]["match_criteria"]
        relevant_ids = set()

        # Extract keywords and reason from first criterion (most datasets have one criterion)
        criterion = match_criteria[0] if match_criteria else {}
        keywords = criterion.get("keywords", [])
        reason = criterion.get("reason", "relevant information")
        min_matches = criterion.get("min_matches", 1)

        # OPTIMIZATION 1: Fast keyword pre-filter to reduce LLM calls
        candidates = []
        filtered_out = 0
        for i, chunk in enumerate(retrieved_items):
            chunk_text = chunk.get("text", "")
            if keyword_prefilter(chunk_text, keywords, min_matches=min_matches):
                candidates.append((i, chunk))
            else:
                filtered_out += 1

        logger.info(f"Keyword pre-filter: {len(candidates)}/{len(retrieved_items)} chunks passed (filtered {filtered_out})")

        # OPTIMIZATION 2: Batch LLM evaluation (10 chunks at a time)
        batch_size = 10
        for batch_start in range(0, len(candidates), batch_size):
            batch = candidates[batch_start:batch_start + batch_size]
            batch_chunks = [chunk for _, chunk in batch]

            # Batch evaluate all chunks in this batch with one LLM call
            evaluations = llm_batch_evaluate_relevance(batch_chunks, keywords, reason, query, expected_elements)

            # Process results
            for (orig_idx, chunk), eval_result in zip(batch, evaluations):
                if eval_result.get("relevant") and eval_result.get("confidence", 0.0) >= 0.7:
                    chunk_id = chunk.get("id", chunk.get("section_id", f"item_{orig_idx}"))
                    relevant_ids.add(chunk_id)

                # Store evaluation details
                if "match_details" not in chunk:
                    chunk["match_details"] = []
                chunk["match_details"].append({
                    "criterion": reason,
                    "result": eval_result
                })

                match_details_all.append({
                    "chunk_id": chunk.get("id", chunk.get("section_id", f"item_{orig_idx}")),
                    "chunk_preview": chunk.get("text", "")[:100],
                    "evaluations": chunk["match_details"]
                })

        logger.info(f"LLM-based matching found {len(relevant_ids)} relevant chunks out of {len(retrieved_items)} ({len(candidates)} evaluated)")

    elif expected_sources and "relevant_chunks" in expected_sources[0]:
        # Old schema: exact chunk IDs (for backwards compatibility)
        relevant_ids = set(expected_sources[0]["relevant_chunks"])
        logger.warning(f"Using old schema with exact chunk IDs - consider updating to flexible matching")

    else:
        relevant_ids = set()
        logger.warning(f"No matching criteria found for query {item['id']}")

    # Compute retrieval metrics (skip if no retrieval for web-based tools)
    if intent == "ontario_health_program":
        # opa_program_lookup uses web search, not vector retrieval
        retrieval_results = {
            "recall@50": None,
            "recall@10": None,
            "mrr": None,
            "ndcg@10": None,
            "hit@10": None,
            "precision@10": None,
            "note": "N/A - tool uses Claude + Web Search, not vector retrieval"
        }
    else:
        retrieval_results = retrieval_metrics.compute_all_metrics(
            retrieved_ids=retrieved_ids,
            relevant_ids=relevant_ids
        )

    # Evaluate answer quality
    # Use summary if available (orchestrator tools), otherwise use retrieved items as the "answer"
    answer_text = response.get("summary", "")

    # If no summary, construct answer from retrieved items (retrieval-only tools)
    if not answer_text and retrieved_items:
        # Format items as a simple answer for evaluation
        item_texts = []
        for retrieved_item in retrieved_items[:5]:  # Use top 5 items (renamed to avoid shadowing)
            if "text" in retrieved_item:
                item_texts.append(retrieved_item["text"])
        answer_text = "\n\n".join(item_texts) if item_texts else ""

    # Combine retrieved context for faithfulness check
    context_texts = [r.get("text", r.get("content", "")) for r in retrieved_items[:10]]
    context = "\n\n".join(context_texts) if context_texts else "[No context retrieved]"

    # Get expected answer elements and expert answer
    expected_elements = item.get("expected_answer_elements", [])
    expert_answer = item.get("expert_answer", "")

    # Evaluate answer quality
    if expert_answer and expert_answer != "TBD - requires SME annotation":
        logger.info(f"Evaluating answer quality (expert_answer exists, {len(answer_text)} chars in answer)")
        try:
            faithfulness = answer_judge.evaluate_faithfulness(answer_text, context)
            helpfulness = answer_judge.evaluate_helpfulness(query, answer_text, expert_answer)
            coverage = answer_judge.evaluate_coverage(expected_elements, answer_text)

            answer_quality = {
                "faithfulness": faithfulness["score"],
                "helpfulness": helpfulness["score"],
                "coverage": coverage["score"]
            }
            answer_quality_details = {
                "faithfulness": faithfulness,
                "helpfulness": helpfulness,
                "coverage": coverage
            }
            logger.info(f"Answer quality: faithfulness={faithfulness['score']:.2f}, helpfulness={helpfulness['score']:.2f}, coverage={coverage['score']:.2f}")
        except Exception as e:
            logger.error(f"Answer quality evaluation failed: {e}")
            answer_quality = {
                "faithfulness": None,
                "helpfulness": None,
                "coverage": None,
                "note": f"Evaluation error: {str(e)}"
            }
            answer_quality_details = None
    else:
        # Skip answer quality if no expert answer yet
        logger.info(f"Skipping answer quality (expert_answer={'exists' if expert_answer else 'missing'}, is_TBD={expert_answer == 'TBD - requires SME annotation' if expert_answer else 'N/A'})")
        answer_quality = {
            "faithfulness": None,
            "helpfulness": None,
            "coverage": None,
            "note": "Skipped - SME annotation pending"
        }
        answer_quality_details = None

    # Compile results
    result = {
        "query_id": query_id,
        "query": query,
        "intent": intent,
        "retrieval": retrieval_results,
        "answer_quality": answer_quality,
        "trace": {
            "retrieved_count": len(retrieved_ids),
            "retrieved_ids_top10": retrieved_ids[:10],
            "retrieved_items_top10": [
                {
                    "id": item.get("id", item.get("section_id", f"item_{i}")),
                    "text": item.get("text", "")[:200] + ("..." if len(item.get("text", "")) > 200 else ""),  # Truncate for readability
                    "relevance_score": item.get("relevance_score", item.get("similarity", 0.0)),
                    "source": item.get("source", item.get("source_org", "unknown"))
                }
                for i, item in enumerate(retrieved_items[:10])
            ],
            "answer": answer_text,
            "citations": response.get("citations", [])
        }
    }

    if answer_quality_details:
        result["answer_quality_details"] = answer_quality_details

    # Add detailed match analysis for debugging
    if match_details_all:
        result["match_analysis"] = {
            "total_chunks_evaluated": len(match_details_all),
            "chunks_matched": len(relevant_ids),
            "detailed_evaluations": match_details_all
        }

    # Print summary
    if retrieval_results.get("recall@50") is not None:
        logger.info(f"  ✓ Recall@50: {retrieval_results['recall@50']:.2f} | "
                   f"MRR: {retrieval_results['mrr']:.2f} | "
                   f"Faithfulness: {answer_quality['faithfulness'] or 0:.2f}")
    else:
        logger.info(f"  ✓ Tool: {intent} (web-based) | "
                   f"Faithfulness: {answer_quality['faithfulness'] or 0:.2f}")

    return result


async def run_evaluation(agent: str, gold_file: Path, output_file: Path, limit: int = None):
    """Run evaluation on gold dataset."""

    # Load gold dataset
    with open(gold_file) as f:
        gold_items = [json.loads(line) for line in f if line.strip()]

    # Apply limit if specified
    if limit is not None and limit > 0:
        gold_items = gold_items[:limit]
        logger.info(f"\n📊 Evaluating {agent} on {limit} queries (limited) from {gold_file.name}\n")
    else:
        logger.info(f"\n📊 Evaluating {agent} on {len(gold_items)} queries from {gold_file.name}\n")

    # Initialize MCP client
    logger.info(f"Initializing {agent} MCP server...")
    mcp_client = MCPToolClient(agent)

    # Initialize metrics
    retrieval_metrics = RetrievalMetrics()
    answer_judge = AnswerQualityJudge()

    results = []

    # Use async context manager to properly connect/disconnect server
    async with mcp_client.server:
        logger.info(f"Connected to {agent} MCP server")
        for item in gold_items:
            result = await evaluate_query(item, agent, mcp_client, retrieval_metrics, answer_judge)
            results.append(result)
        logger.info("Shutting down MCP server...")

    # Aggregate metrics (excluding None values and web-based tools)
    retrieval_scores = {
        "recall@50": [r["retrieval"]["recall@50"] for r in results if r["retrieval"].get("recall@50") is not None],
        "recall@10": [r["retrieval"]["recall@10"] for r in results if r["retrieval"].get("recall@10") is not None],
        "mrr": [r["retrieval"]["mrr"] for r in results if r["retrieval"].get("mrr") is not None],
        "ndcg@10": [r["retrieval"]["ndcg@10"] for r in results if r["retrieval"].get("ndcg@10") is not None],
        "hit@10": [r["retrieval"]["hit@10"] for r in results if r["retrieval"].get("hit@10") is not None],
        "precision@10": [r["retrieval"]["precision@10"] for r in results if r["retrieval"].get("precision@10") is not None],
    }

    answer_scores = {
        "faithfulness": [r["answer_quality"]["faithfulness"] for r in results if r["answer_quality"].get("faithfulness") is not None],
        "helpfulness": [r["answer_quality"]["helpfulness"] for r in results if r["answer_quality"].get("helpfulness") is not None],
        "coverage": [r["answer_quality"]["coverage"] for r in results if r["answer_quality"].get("coverage") is not None],
    }

    aggregate = {
        "agent": agent,
        "gold_set": str(gold_file),
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "queries_evaluated": len(results),
            "queries_with_retrieval": len(retrieval_scores["recall@50"]),
            "queries_with_answer_eval": len(answer_scores["faithfulness"]),
            "avg_recall@50": sum(retrieval_scores["recall@50"]) / len(retrieval_scores["recall@50"]) if retrieval_scores["recall@50"] else None,
            "avg_mrr": sum(retrieval_scores["mrr"]) / len(retrieval_scores["mrr"]) if retrieval_scores["mrr"] else None,
            "avg_ndcg@10": sum(retrieval_scores["ndcg@10"]) / len(retrieval_scores["ndcg@10"]) if retrieval_scores["ndcg@10"] else None,
            "avg_hit@10": sum(retrieval_scores["hit@10"]) / len(retrieval_scores["hit@10"]) if retrieval_scores["hit@10"] else None,
            "avg_faithfulness": sum(answer_scores["faithfulness"]) / len(answer_scores["faithfulness"]) if answer_scores["faithfulness"] else None,
            "avg_helpfulness": sum(answer_scores["helpfulness"]) / len(answer_scores["helpfulness"]) if answer_scores["helpfulness"] else None,
            "avg_coverage": sum(answer_scores["coverage"]) / len(answer_scores["coverage"]) if answer_scores["coverage"] else None,
        },
        "results": results
    }

    # Save report
    with open(output_file, "w") as f:
        json.dump(aggregate, f, indent=2)

    logger.info(f"\n✅ Evaluation complete! Report saved to {output_file}\n")
    logger.info(f"📈 Summary:")
    if aggregate["summary"]["avg_recall@50"] is not None:
        logger.info(f"  Recall@50: {aggregate['summary']['avg_recall@50']:.2%}")
        logger.info(f"  MRR: {aggregate['summary']['avg_mrr']:.3f}")
        logger.info(f"  nDCG@10: {aggregate['summary']['avg_ndcg@10']:.3f}")
    if aggregate["summary"]["avg_faithfulness"] is not None:
        logger.info(f"  Faithfulness: {aggregate['summary']['avg_faithfulness']:.2%}")
        logger.info(f"  Helpfulness: {aggregate['summary']['avg_helpfulness']:.2%}")
        logger.info(f"  Coverage: {aggregate['summary']['avg_coverage']:.2%}")
    else:
        logger.info(f"  ⚠️  Answer quality metrics skipped - SME annotations needed")


def main():
    parser = argparse.ArgumentParser(description="Evaluate agent retrieval and answer quality")
    parser.add_argument("--agent", required=True, choices=["dr_off", "dr_opa"],
                       help="Agent to evaluate")
    parser.add_argument("--set", required=True, type=Path, dest="gold_file",
                       help="Path to gold JSONL file")
    parser.add_argument("--output", type=Path, default=None,
                       help="Output JSON report path (default: eval/results/{agent}_{timestamp}.json)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of queries to evaluate (for testing)")

    args = parser.parse_args()

    # Validate gold file exists
    if not args.gold_file.exists():
        logger.error(f"Gold file not found: {args.gold_file}")
        sys.exit(1)

    # Default output path
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = args.gold_file.stem
        args.output = Path(f"eval/results/{args.agent}_{dataset_name}_{timestamp}.json")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Run async evaluation
    asyncio.run(run_evaluation(args.agent, args.gold_file, args.output, args.limit))


if __name__ == "__main__":
    main()
