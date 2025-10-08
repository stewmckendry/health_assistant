#!/usr/bin/env python3
"""
Run comprehensive evaluation of Dr. OFF, Dr. OPA, and Chief agents using Langfuse datasets.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import argparse

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()


async def evaluate_dr_off_agent(query: str, trace_id: str) -> Dict[str, Any]:
    """
    Evaluate Dr. OFF agent on a single query.

    Args:
        query: User query
        trace_id: Langfuse trace ID

    Returns:
        Agent response with metadata
    """
    from src.ai_agents.dr_off_agent.openai_agent import create_dr_off_agent

    agent = await create_dr_off_agent()

    result = await agent.query(
        user_input=query,
        session_id=trace_id,
        user_id="eval_user"
    )

    return result


async def evaluate_dr_opa_agent(query: str, trace_id: str) -> Dict[str, Any]:
    """
    Evaluate Dr. OPA agent on a single query.

    Args:
        query: User query
        trace_id: Langfuse trace ID

    Returns:
        Agent response with metadata
    """
    from src.ai_agents.dr_opa_agent.openai_agent import create_dr_opa_agent

    agent = await create_dr_opa_agent()

    result = await agent.query(
        user_input=query,
        session_id=trace_id,
        user_id="eval_user"
    )

    return result


async def evaluate_chief_agent(query: str, trace_id: str) -> Dict[str, Any]:
    """
    Evaluate Chief orchestrator agent on a single query.

    Args:
        query: User query
        trace_id: Langfuse trace ID

    Returns:
        Agent response with metadata
    """
    from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import DiagnosticOrchestrator

    orchestrator = DiagnosticOrchestrator(enable_langfuse=True)
    await orchestrator.initialize()

    result = await orchestrator.orchestrate(
        clinical_query=query,
        session_id=trace_id,
        user_id="eval_user"
    )

    return result


async def run_dataset_evaluation(dataset_name: str,
                                agent_type: str,
                                run_name: Optional[str] = None,
                                limit: Optional[int] = None):
    """
    Run evaluation on a Langfuse dataset.

    Args:
        dataset_name: Name of the Langfuse dataset
        agent_type: Type of agent to evaluate (dr_off, dr_opa, chief)
        run_name: Optional name for this evaluation run
        limit: Optional limit on number of items to evaluate
    """
    langfuse = Langfuse()

    # Get dataset
    try:
        dataset = langfuse.get_dataset(name=dataset_name)
    except Exception as e:
        print(f"❌ Error loading dataset '{dataset_name}': {e}")
        return

    # Get dataset items
    items = dataset.items
    if limit:
        items = items[:limit]

    print(f"\n📊 Evaluating {len(items)} items from dataset '{dataset_name}'")
    print(f"   Agent: {agent_type}")

    # Select evaluation function
    if agent_type == "mixed":
        # For mixed datasets, we'll determine agent per item from metadata
        eval_func = None
        print(f"   Mode: Mixed agent evaluation (routing per item)")
    else:
        eval_func = {
            "dr_off": evaluate_dr_off_agent,
            "dr_opa": evaluate_dr_opa_agent,
            "chief": evaluate_chief_agent
        }[agent_type]

    # Create run name
    if run_name is None:
        run_name = f"{agent_type}_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"   Run: {run_name}")
    print(f"   Dataset run will be created for tracking")

    # Run evaluations
    success_count = 0
    error_count = 0

    for i, item in enumerate(items, 1):
        query = item.input.get("query", "")
        expected_output = item.expected_output or {}

        # Determine agent for this item (for mixed datasets)
        item_agent = agent_type
        if agent_type == "mixed":
            # Get agent from item metadata
            item_agent = item.metadata.get("agent", "dr_off")

            # Select appropriate eval function
            eval_func = {
                "dr_off": evaluate_dr_off_agent,
                "dr_opa": evaluate_dr_opa_agent,
                "chief": evaluate_chief_agent
            }[item_agent]

        print(f"\n   [{i}/{len(items)}] Evaluating ({item_agent}): {query[:60]}...")

        # Create a trace ID for linking
        trace_id = f"eval_{run_name}_{i}"

        try:
            # Use dataset item's run() context manager for automatic trace linking
            with item.run(
                run_name=run_name,
                run_description=f"Smoke test evaluation - {item_agent}",
                run_metadata={
                    "agent": item_agent,
                    "tools_expected": expected_output.get("tools_expected", []),
                    "difficulty": expected_output.get("difficulty", "unknown"),
                    "trace_id": trace_id
                }
            ) as run_span:
                # Run evaluation - agents handle their own Langfuse tracing
                result = await eval_func(query, trace_id)

                # Update span with results
                run_span.update(
                    output=result,
                    metadata={
                        "tools_used": result.get("tools_used", []),
                        "confidence": result.get("confidence", 0.0),
                        "citations_count": len(result.get("citations", []))
                    }
                )

                success_count += 1
                tools_used_str = ', '.join(result.get('tools_used', [])) if result.get('tools_used') else 'none'
                confidence = result.get('confidence', 0.0)
                print(f"      ✅ Success (tools: {tools_used_str}, confidence: {confidence:.2f})")
                print(f"         Linked to dataset run: {run_name}")

        except Exception as e:
            error_count += 1
            print(f"      ❌ Error: {e}")

        # Small delay between requests
        if i < len(items):
            await asyncio.sleep(2)

    # Flush Langfuse
    langfuse.flush()

    print(f"\n{'='*60}")
    print(f"📈 Evaluation Complete")
    print(f"   Successful: {success_count}/{len(items)}")
    print(f"   Errors: {error_count}/{len(items)}")
    print(f"   Success rate: {success_count/len(items)*100:.1f}%")
    print(f"{'='*60}")


async def main():
    """Main function to run agent evaluations."""
    parser = argparse.ArgumentParser(description="Run agent evaluation on Langfuse datasets")
    parser.add_argument("--agent", choices=["dr_off", "dr_opa", "chief", "all"],
                       default="all", help="Which agent to evaluate")
    parser.add_argument("--dataset", type=str, default=None,
                       help="Custom dataset name to evaluate (overrides --agent)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of items to evaluate per dataset")
    parser.add_argument("--run-name", type=str, default=None,
                       help="Custom name for this evaluation run")
    args = parser.parse_args()

    print("=" * 60)
    print("AGENT EVALUATION RUNNER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Handle custom dataset
    if args.dataset:
        print(f"Dataset: {args.dataset}")
        print(f"Mode: Custom dataset evaluation")

        # Determine agent type from dataset name
        if "dr_off" in args.dataset.lower():
            agent_type = "dr_off"
        elif "dr_opa" in args.dataset.lower():
            agent_type = "dr_opa"
        elif "chief" in args.dataset.lower() or "orchestrator" in args.dataset.lower():
            agent_type = "chief"
        elif "smoke" in args.dataset.lower():
            # Smoke test - run all agents
            print(f"Smoke test detected - will run all agents on mixed dataset")
            agent_type = "all"
        else:
            print(f"⚠️  Could not determine agent type from dataset name. Defaulting to 'all'")
            agent_type = "all"

        if args.limit:
            print(f"Limit: {args.limit} items")
        print()

        if agent_type == "all":
            # For smoke test, we need to evaluate each item with the correct agent
            print("\n🤖 Evaluating Mixed Dataset (All Agents)...")
            print("-" * 60)
            # We'll need to determine agent per item - let's run as dr_off for now
            # and handle routing in the evaluation function
            await run_dataset_evaluation(
                dataset_name=args.dataset,
                agent_type="mixed",
                run_name=args.run_name,
                limit=args.limit
            )
        else:
            await run_dataset_evaluation(
                dataset_name=args.dataset,
                agent_type=agent_type,
                run_name=args.run_name,
                limit=args.limit
            )
    else:
        # Original logic for --agent flag
        print(f"Agent(s): {args.agent}")
        if args.limit:
            print(f"Limit: {args.limit} items per dataset")
        print()

        # Run evaluations based on selection
        if args.agent in ["dr_off", "all"]:
            print("\n🤖 Evaluating DR. OFF Agent...")
            print("-" * 60)
            await run_dataset_evaluation(
                dataset_name="dr_off_agent_eval",
                agent_type="dr_off",
                run_name=args.run_name,
                limit=args.limit
            )

        if args.agent in ["dr_opa", "all"]:
            print("\n🤖 Evaluating DR. OPA Agent...")
            print("-" * 60)
            await run_dataset_evaluation(
                dataset_name="dr_opa_agent_eval",
                agent_type="dr_opa",
                run_name=args.run_name,
                limit=args.limit
            )

        if args.agent in ["chief", "all"]:
            print("\n🤖 Evaluating CHIEF Orchestrator...")
            print("-" * 60)
            await run_dataset_evaluation(
                dataset_name="chief_orchestrator_eval",
                agent_type="chief",
                run_name=args.run_name,
                limit=args.limit
            )

    print("\n" + "=" * 60)
    print("✅ ALL EVALUATIONS COMPLETE")
    print("=" * 60)
    print("\nView results in Langfuse:")
    print("  https://cloud.langfuse.com")


if __name__ == "__main__":
    asyncio.run(main())
