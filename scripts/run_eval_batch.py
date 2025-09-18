#!/usr/bin/env python
"""
Non-interactive batch evaluation runner.
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from run_comprehensive_evaluation import ComprehensiveEvaluator
from dotenv import load_dotenv

load_dotenv()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run batch evaluation (non-interactive)")
    parser.add_argument("--dataset", default="health-assistant-eval-v1")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    evaluator = ComprehensiveEvaluator(
        dataset_name=args.dataset,
        dry_run=args.dry_run,
        limit=args.limit
    )
    
    # Run without confirmation prompt
    configurations = evaluator.get_configurations()
    
    print(f"\nRunning {len(configurations)} configurations...")
    print(f"Dataset: {args.dataset}")
    print(f"Items per config: {args.limit}")
    
    for i, config in enumerate(configurations, 1):
        print(f"\n[{i}/{len(configurations)}] {config.name}")
        result = evaluator.run_evaluation(config)
        evaluator.results.append(result)
        
        if i < len(configurations):
            import time
            wait_time = 30  # 30 second pause between configs to avoid rate limits
            print(f"⏳ Waiting {wait_time}s before next configuration...")
            time.sleep(wait_time)
    
    evaluator.save_results()
    evaluator.print_summary()

if __name__ == "__main__":
    main()