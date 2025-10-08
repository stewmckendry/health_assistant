#!/usr/bin/env python3
"""
Generate expected results for agent evaluation test cases using web search.
Uses Exa AI to fetch authoritative Ontario healthcare sources.
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()


# Ontario healthcare sources for web search
ONTARIO_HEALTHCARE_DOMAINS = [
    "ontario.ca",
    "health.gov.on.ca",
    "cpso.on.ca",
    "publichealthontario.ca",
    "ontariohealth.ca",
    "cep.health",
    "hqontario.ca",
    "cno.org",
    "ocp.on.ca"
]


async def generate_expected_result_for_case(exa: Exa, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate expected result for a single test case using web search.

    Args:
        exa: Exa client
        test_case: Test case dictionary

    Returns:
        Enhanced test case with expected_result
    """
    query = test_case["query"]
    case_id = test_case.get("id", "unknown")

    print(f"\n🔍 Generating expected result for: {case_id}")
    print(f"   Query: {query[:80]}...")

    try:
        # Search for relevant information
        # Use domain filtering for Ontario healthcare sources
        search_results = exa.search_and_contents(
            query=query,
            type="neural",
            num_results=5,
            include_domains=ONTARIO_HEALTHCARE_DOMAINS,
            text={"max_characters": 2000}
        )

        # Extract key information
        sources = []
        key_facts = []

        for result in search_results.results:
            sources.append({
                "url": result.url,
                "title": result.title,
                "snippet": result.text[:300] if hasattr(result, 'text') else ""
            })

            # Extract key facts from content
            if hasattr(result, 'text') and result.text:
                # Simple extraction - in production, use LLM to extract structured facts
                key_facts.append(result.text[:500])

        expected_result = {
            "query": query,
            "sources": sources,
            "key_facts": key_facts,
            "tools_expected": test_case.get("tools_expected", []),
            "generated_at": datetime.now().isoformat(),
            "search_engine": "exa"
        }

        print(f"   ✅ Found {len(sources)} sources")

        return {
            **test_case,
            "expected_result": expected_result
        }

    except Exception as e:
        print(f"   ❌ Error generating result: {e}")
        return {
            **test_case,
            "expected_result": {
                "query": query,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
        }


async def generate_expected_results_batch(test_cases: List[Dict[str, Any]],
                                         output_file: Path,
                                         batch_size: int = 5):
    """
    Generate expected results for a batch of test cases.

    Args:
        test_cases: List of test cases
        output_file: Path to save results
        batch_size: Number of concurrent requests
    """
    exa = Exa()

    # Process in batches to avoid rate limits
    enhanced_cases = []

    for i in range(0, len(test_cases), batch_size):
        batch = test_cases[i:i+batch_size]
        print(f"\n📦 Processing batch {i//batch_size + 1} ({len(batch)} cases)...")

        # Process batch concurrently
        tasks = [generate_expected_result_for_case(exa, case) for case in batch]
        batch_results = await asyncio.gather(*tasks)
        enhanced_cases.extend(batch_results)

        # Save intermediate results
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(enhanced_cases, f, indent=2)

        print(f"   💾 Saved {len(enhanced_cases)} results to {output_file}")

        # Wait between batches to respect rate limits
        if i + batch_size < len(test_cases):
            print(f"   ⏳ Waiting 5 seconds before next batch...")
            await asyncio.sleep(5)

    return enhanced_cases


async def main():
    """Main function to generate expected results for all datasets."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate expected results for agent evaluation")
    parser.add_argument("--agent", choices=["dr_off", "dr_opa", "chief", "all"],
                       default="all", help="Which agent dataset to process")
    parser.add_argument("--batch-size", type=int, default=5,
                       help="Number of concurrent requests (default: 5)")
    args = parser.parse_args()

    print("=" * 60)
    print("GENERATING EXPECTED RESULTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Batch size: {args.batch_size}")
    print()

    # Import test cases from create_agent_eval_dataset
    from create_agent_eval_dataset import DR_OFF_TEST_CASES, DR_OPA_TEST_CASES, CHIEF_TEST_CASES

    results_dir = Path("eval/expected_results")

    # Process datasets based on selection
    if args.agent in ["dr_off", "all"]:
        print("\n📋 Processing DR. OFF test cases...")
        print("-" * 60)
        await generate_expected_results_batch(
            test_cases=DR_OFF_TEST_CASES,
            output_file=results_dir / "dr_off_expected_results.json",
            batch_size=args.batch_size
        )

    if args.agent in ["dr_opa", "all"]:
        print("\n📋 Processing DR. OPA test cases...")
        print("-" * 60)
        await generate_expected_results_batch(
            test_cases=DR_OPA_TEST_CASES,
            output_file=results_dir / "dr_opa_expected_results.json",
            batch_size=args.batch_size
        )

    if args.agent in ["chief", "all"]:
        print("\n📋 Processing CHIEF test cases...")
        print("-" * 60)
        await generate_expected_results_batch(
            test_cases=CHIEF_TEST_CASES,
            output_file=results_dir / "chief_expected_results.json",
            batch_size=args.batch_size
        )

    print("\n" + "=" * 60)
    print("✅ EXPECTED RESULTS GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nResults saved to: {results_dir}/")
    print("\nNext step:")
    print("  python scripts/run_agent_evaluation.py")


if __name__ == "__main__":
    asyncio.run(main())
