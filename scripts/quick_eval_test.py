#!/usr/bin/env python
"""Quick evaluation test - runs 2 items and exits without waiting."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.evaluation.evaluator import DatasetEvaluator


def quick_test():
    """Run a quick 2-item test without waiting for scores."""
    
    print("\n" + "="*60)
    print("🚀 QUICK EVALUATION TEST")
    print("="*60)
    print("\nThis will:")
    print("1. Run 2 test items through the assistant")
    print("2. Create dataset run in Langfuse")
    print("3. Exit immediately (check dashboard for scores)")
    print("-"*60)
    
    # Initialize evaluator
    evaluator = DatasetEvaluator()
    
    # Run evaluation on just 2 items
    print("\n📊 Starting evaluation run...")
    results = evaluator.run_dataset_evaluation(
        dataset_name="health-assistant-eval-v1",
        run_name="quick_safety_test",
        limit=2,  # Just 2 items for quick test
        description="Quick test of Safety Compliance evaluator"
    )
    
    if results.get("successful", 0) > 0:
        print("\n✅ Dataset run completed!")
        print(f"   Run Name: {results['run_name']}")
        print(f"   Successful: {results['successful']}/{results['total_items']}")
        print(f"\n📊 Check Langfuse dashboard for evaluation scores:")
        print(f"   {results['dashboard_url']}")
        print(f"   Go to: Datasets → health-assistant-eval-v1 → Runs → {results['run_name']}")
        print("\n⏳ Safety Compliance evaluator should run automatically in 1-2 minutes")
        
        # Print how to check scores later
        print("\n📝 To check scores later, run this Python code:")
        print("```python")
        print("from src.evaluation.evaluator import DatasetEvaluator")
        print("evaluator = DatasetEvaluator()")
        print(f"scores = evaluator.get_run_scores('{results['run_name']}')")
        print("```")
    else:
        print("\n❌ No items processed successfully")
        print("   Check error messages above")


if __name__ == "__main__":
    quick_test()