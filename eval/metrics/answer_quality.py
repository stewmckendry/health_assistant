"""
Answer quality metrics using LLM-as-judge evaluation.

Implements three core metrics for evaluating answer quality:

- **Faithfulness**: "Is the answer grounded in the source material?"
  Measures whether the answer contains only claims that can be verified in the retrieved context.
  High faithfulness means no hallucinations or unsupported statements.
  Example: Answer says "48 hours required" but context says "72 hours" → Low faithfulness

- **Helpfulness**: "Would this answer actually help the clinician?"
  Compares the generated answer to an expert gold-standard answer.
  Evaluates directional correctness, completeness, clarity, and practical value.
  Example: Answer is correct but missing key details → Medium helpfulness

- **Coverage**: "Did we include all the important facts?"
  Checks what percentage of required factual elements are present in the answer.
  High coverage means all expected information is included.
  Example: 3 required facts, answer includes 2 → Coverage = 0.67
"""

from typing import Dict, List
import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AnswerQualityJudge:
    """LLM-based evaluation of answer quality using GPT-4o as judge."""

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the answer quality judge.

        Args:
            model: OpenAI model to use for evaluation (default: gpt-4o)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized AnswerQualityJudge with model: {model}")

    def evaluate_faithfulness(self, answer: str, retrieved_context: str) -> Dict:
        """
        Faithfulness: Does answer only contain claims supported by context?

        Evaluates whether the generated answer contains only information that can be
        verified in the retrieved context. Identifies any hallucinated or unsupported claims.

        Args:
            answer: The generated answer to evaluate
            retrieved_context: The context used to generate the answer

        Returns:
            Dict with:
                - score: 0.0-1.0 (1.0 = fully faithful, 0.0 = hallucinated)
                - reasoning: Explanation of the score
                - unsupported_claims: List of claims not supported by context (empty if fully faithful)

        Example:
            >>> judge = AnswerQualityJudge()
            >>> result = judge.evaluate_faithfulness(
            ...     answer="C124 can be billed as MRP if patient admitted >48 hours.",
            ...     retrieved_context="Schedule of Benefits Section C: C124 MRP requires 48h admission."
            ... )
            >>> print(result)
            {'score': 1.0, 'reasoning': 'All claims directly supported', 'unsupported_claims': []}
        """
        prompt = f"""You are evaluating the faithfulness of an AI-generated answer to retrieved context.

RETRIEVED CONTEXT:
{retrieved_context}

GENERATED ANSWER:
{answer}

TASK: Determine if the answer contains ONLY claims that are directly supported by the context.
Look for:
- Factual claims that are stated in the context
- Reasonable inferences clearly derivable from the context
- Citations or references mentioned in the context

Flag as unsupported:
- Specific facts, numbers, or requirements not in the context
- Interpretations that go beyond what the context states
- Details that seem plausible but aren't explicitly mentioned

Output JSON:
{{
  "score": 0.0-1.0,  // 1.0 = fully faithful (all claims supported), 0.5 = partially faithful, 0.0 = hallucinated
  "reasoning": "brief explanation of the score",
  "unsupported_claims": ["claim 1", "claim 2"]  // Empty list if score is 1.0
}}

IMPORTANT: Be strict. Only give 1.0 if ALL claims are directly supported."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1000
            )

            # Extract JSON from response
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"Faithfulness evaluation: {result['score']}")
            return result

        except Exception as e:
            logger.error(f"Faithfulness evaluation failed: {e}")
            return {
                "score": 0.0,
                "reasoning": f"Evaluation error: {str(e)}",
                "unsupported_claims": ["Error during evaluation"]
            }

    def evaluate_helpfulness(self, question: str, answer: str, expert_answer: str) -> Dict:
        """
        Helpfulness: Is the answer useful for the clinician's question?

        Compares the generated answer to a gold-standard expert answer to assess
        whether it would be helpful to a busy clinician.

        Args:
            question: The original clinical question
            answer: The generated answer to evaluate
            expert_answer: Gold-standard expert answer for comparison

        Returns:
            Dict with:
                - score: 0.0-1.0 (1.0 = fully helpful, 0.0 = not useful)
                - reasoning: Explanation of the score
                - missing_elements: List of important facts not included

        Example:
            >>> judge = AnswerQualityJudge()
            >>> result = judge.evaluate_helpfulness(
            ...     question="Can I bill C124 as MRP after 3 days?",
            ...     answer="Yes, C124 can be billed.",
            ...     expert_answer="Yes, C124 can be billed as MRP if patient admitted >48h. 3 days = 72h meets requirement."
            ... )
            >>> print(result['score'])
            0.7  # Missing some detail but directionally correct
        """
        prompt = f"""You are evaluating the helpfulness of an AI answer to a clinical question.

QUESTION:
{question}

EXPERT ANSWER (gold standard):
{expert_answer}

AI ANSWER:
{answer}

TASK: Rate helpfulness for a busy clinician. Does it answer the question clearly and completely?

Consider:
- Directional correctness (is the yes/no/maybe right?)
- Completeness (are key facts included?)
- Clarity (is it easy to understand and act on?)
- Practical value (can the clinician use this immediately?)

Output JSON:
{{
  "score": 0.0-1.0,  // 1.0 = fully helpful (as good as expert), 0.5 = somewhat helpful, 0.0 = not useful
  "reasoning": "brief explanation comparing to expert answer",
  "missing_elements": ["element 1", "element 2"]  // Key facts from expert answer that are missing
}}

IMPORTANT: Compare to the expert answer, but don't penalize different phrasing if the content is equivalent."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)
            logger.debug(f"Helpfulness evaluation: {result['score']}")
            return result

        except Exception as e:
            logger.error(f"Helpfulness evaluation failed: {e}")
            return {
                "score": 0.0,
                "reasoning": f"Evaluation error: {str(e)}",
                "missing_elements": ["Error during evaluation"]
            }

    def evaluate_coverage(self, expected_elements: List[str], answer: str) -> Dict:
        """
        Coverage: What percentage of required facts are included?

        Checks if the answer includes all required factual elements specified
        in the gold dataset. This is a more structured evaluation than helpfulness.

        Args:
            expected_elements: List of required facts that should appear in the answer
            answer: The generated answer to evaluate

        Returns:
            Dict with:
                - score: 0.0-1.0 (fraction of required facts covered)
                - covered: List of expected elements that are present
                - missing: List of expected elements that are absent

        Example:
            >>> judge = AnswerQualityJudge()
            >>> result = judge.evaluate_coverage(
            ...     expected_elements=["C124 is MRP code", "48 hour requirement", "3 days meets requirement"],
            ...     answer="C124 is the MRP code and 3 days meets the requirement."
            ... )
            >>> print(result)
            {'score': 0.667, 'covered': ['C124 is MRP code', '3 days meets requirement'], 'missing': ['48 hour requirement']}
        """
        if not expected_elements:
            return {"score": 1.0, "covered": [], "missing": []}

        prompt = f"""You are checking if an answer includes all required facts.

REQUIRED FACTS:
{chr(10).join(f"{i+1}. {elem}" for i, elem in enumerate(expected_elements))}

ANSWER:
{answer}

TASK: For each required fact, determine if it's clearly stated in the answer.
The answer doesn't need to use the exact same words, but the factual content must be present.

Output JSON:
{{
  "covered": ["fact 1", "fact 3"],  // Facts that are present in the answer
  "missing": ["fact 2"]  // Facts that are absent or not clearly stated
}}

IMPORTANT: A fact is covered if the same information is conveyed, even with different wording."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)

            # Calculate coverage score
            score = len(result["covered"]) / len(expected_elements) if expected_elements else 1.0
            result["score"] = score

            logger.debug(f"Coverage evaluation: {score:.2f} ({len(result['covered'])}/{len(expected_elements)} facts)")
            return result

        except Exception as e:
            logger.error(f"Coverage evaluation failed: {e}")
            return {
                "score": 0.0,
                "covered": [],
                "missing": expected_elements,
                "error": str(e)
            }

    def evaluate_all(
        self,
        question: str,
        answer: str,
        retrieved_context: str,
        expected_elements: List[str],
        expert_answer: str
    ) -> Dict[str, Dict]:
        """
        Evaluate all three answer quality metrics at once.

        Args:
            question: Original clinical question
            answer: Generated answer to evaluate
            retrieved_context: Context used to generate the answer
            expected_elements: List of required facts
            expert_answer: Gold-standard expert answer

        Returns:
            Dict with all three evaluation results:
                {
                    'faithfulness': {...},
                    'helpfulness': {...},
                    'coverage': {...}
                }

        Example:
            >>> judge = AnswerQualityJudge()
            >>> results = judge.evaluate_all(
            ...     question="Can I bill C124 after 3 days?",
            ...     answer="Yes, C124 can be billed.",
            ...     retrieved_context="C124 requires 48h admission.",
            ...     expected_elements=["48h requirement", "3 days meets it"],
            ...     expert_answer="Yes, C124 can be billed. 48h required, 3 days meets it."
            ... )
        """
        logger.info("Running complete answer quality evaluation")

        return {
            'faithfulness': self.evaluate_faithfulness(answer, retrieved_context),
            'helpfulness': self.evaluate_helpfulness(question, answer, expert_answer),
            'coverage': self.evaluate_coverage(expected_elements, answer)
        }
