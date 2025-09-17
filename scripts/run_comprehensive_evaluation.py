#!/usr/bin/env python
"""
Comprehensive evaluation runner with multiple configurations.

This script runs dataset evaluations across different configurations to test:
- Baseline with web tools
- No RAG (web tools disabled)
- Domain filtering (government only, academic only)
- Provider mode vs Patient mode
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.evaluation.evaluator import DatasetEvaluator
from src.evaluation.dataset_creator import DatasetCreator, DatasetConfig
from src.utils.logging import get_logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class EvaluationConfig:
    """Configuration for an evaluation run."""
    name: str
    description: str
    mode: str = 'patient'  # 'patient' or 'provider'
    web_tools: bool = True
    domain_filter: Optional[str] = None  # 'all', 'government', 'academic', or None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metadata."""
        return asdict(self)


class ComprehensiveEvaluator:
    """Manages comprehensive evaluation across multiple configurations."""
    
    def __init__(self, dataset_name: str, dry_run: bool = False, limit: Optional[int] = None):
        """
        Initialize comprehensive evaluator.
        
        Args:
            dataset_name: Name of the Langfuse dataset to evaluate
            dry_run: If True, only run a small subset for testing
            limit: Optional limit on number of items to evaluate per configuration
        """
        self.dataset_name = dataset_name
        self.dry_run = dry_run
        self.limit = limit if not dry_run else min(limit or 5, 5)
        self.results = []
        
        # Create output directory for results
        self.output_dir = Path("evaluation_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Timestamp for this evaluation session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def get_configurations(self) -> List[EvaluationConfig]:
        """Get the list of configurations to test."""
        if self.dry_run:
            # Just test a couple configurations for dry run
            return [
                EvaluationConfig(
                    name="baseline",
                    description="Baseline configuration with web tools enabled",
                    mode="patient",
                    web_tools=True,
                    domain_filter=None
                ),
                EvaluationConfig(
                    name="no_rag",
                    description="No RAG - web tools disabled",
                    mode="patient",
                    web_tools=False,
                    domain_filter=None
                )
            ]
        
        # Full configuration matrix
        return [
            # Patient mode configurations
            EvaluationConfig(
                name="patient_baseline",
                description="Patient mode with all web tools and domains",
                mode="patient",
                web_tools=True,
                domain_filter=None
            ),
            EvaluationConfig(
                name="patient_no_rag",
                description="Patient mode without web tools (no RAG)",
                mode="patient",
                web_tools=False,
                domain_filter=None
            ),
            EvaluationConfig(
                name="patient_gov_only",
                description="Patient mode with government domains only",
                mode="patient",
                web_tools=True,
                domain_filter="government"
            ),
            EvaluationConfig(
                name="patient_academic_only",
                description="Patient mode with academic medical centers only",
                mode="patient",
                web_tools=True,
                domain_filter="academic"
            ),
            
            # Provider mode configurations
            EvaluationConfig(
                name="provider_baseline",
                description="Provider mode with all web tools and domains",
                mode="provider",
                web_tools=True,
                domain_filter=None
            ),
            EvaluationConfig(
                name="provider_no_rag",
                description="Provider mode without web tools (no RAG)",
                mode="provider",
                web_tools=False,
                domain_filter=None
            ),
            EvaluationConfig(
                name="provider_gov_only",
                description="Provider mode with government domains only",
                mode="provider",
                web_tools=True,
                domain_filter="government"
            )
        ]
    
    def run_evaluation(self, config: EvaluationConfig) -> Dict[str, Any]:
        """
        Run evaluation with a specific configuration.
        
        Args:
            config: EvaluationConfig to use
            
        Returns:
            Dictionary with evaluation results
        """
        print(f"\n{'='*60}")
        print(f"RUNNING EVALUATION: {config.name}")
        print(f"{'='*60}")
        print(f"Description: {config.description}")
        print(f"Configuration:")
        print(f"  Mode: {config.mode}")
        print(f"  Web Tools: {config.web_tools}")
        print(f"  Domain Filter: {config.domain_filter}")
        print(f"  Limit: {self.limit}")
        
        # Initialize evaluator with configuration
        evaluator = DatasetEvaluator(
            mode=config.mode,
            web_tools=config.web_tools,
            domain_filter=config.domain_filter
        )
        
        # Create run name with configuration
        run_name = f"{config.name}_{self.timestamp}"
        if self.dry_run:
            run_name = f"dry_run_{run_name}"
        
        # Run evaluation
        start_time = time.time()
        
        try:
            result = evaluator.run_dataset_evaluation(
                dataset_name=self.dataset_name,
                run_name=run_name,
                limit=self.limit,
                description=f"{config.description} | Timestamp: {self.timestamp}",
                user_id=f"eval_user_{config.mode}"
            )
            
            elapsed_time = time.time() - start_time
            
            # Add metadata to result
            result["config"] = config.to_dict()
            result["elapsed_time_seconds"] = elapsed_time
            result["timestamp"] = self.timestamp
            result["dry_run"] = self.dry_run
            
            print(f"\n✅ Evaluation completed in {elapsed_time:.1f} seconds")
            print(f"   Successful: {result.get('successful', 0)}")
            print(f"   Failed: {result.get('failed', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed for {config.name}: {e}")
            print(f"\n❌ Evaluation failed: {e}")
            
            return {
                "config": config.to_dict(),
                "error": str(e),
                "timestamp": self.timestamp,
                "dry_run": self.dry_run
            }
    
    def run_all_evaluations(self):
        """Run all configured evaluations."""
        configurations = self.get_configurations()
        
        print(f"\n{'='*60}")
        print("COMPREHENSIVE EVALUATION PLAN")
        print(f"{'='*60}")
        print(f"Dataset: {self.dataset_name}")
        print(f"Configurations to test: {len(configurations)}")
        print(f"Items per configuration: {self.limit or 'all'}")
        print(f"Dry run: {self.dry_run}")
        print(f"Timestamp: {self.timestamp}")
        
        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - Testing with limited items")
        
        print(f"\nConfigurations:")
        for i, config in enumerate(configurations, 1):
            print(f"  {i}. {config.name}: {config.description}")
        
        # Confirm before proceeding (unless dry run)
        if not self.dry_run:
            response = input("\nProceed with evaluation? (y/n): ")
            if response.lower() != 'y':
                print("Evaluation cancelled.")
                return
        
        # Run each configuration
        for i, config in enumerate(configurations, 1):
            print(f"\n{'='*60}")
            print(f"Configuration {i}/{len(configurations)}")
            
            result = self.run_evaluation(config)
            self.results.append(result)
            
            # Wait between evaluations to avoid API overload
            if i < len(configurations):
                wait_time = 5 if self.dry_run else 30
                print(f"\n⏳ Waiting {wait_time} seconds before next configuration...")
                time.sleep(wait_time)
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    def save_results(self):
        """Save evaluation results to file."""
        output_file = self.output_dir / f"eval_results_{self.timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "dataset": self.dataset_name,
                "timestamp": self.timestamp,
                "dry_run": self.dry_run,
                "configurations_tested": len(self.results),
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📁 Results saved to: {output_file}")
    
    def print_summary(self):
        """Print summary of all evaluations."""
        print(f"\n{'='*60}")
        print("EVALUATION SUMMARY")
        print(f"{'='*60}")
        
        total_items = 0
        total_successful = 0
        total_failed = 0
        
        for result in self.results:
            config_name = result.get("config", {}).get("name", "unknown")
            successful = result.get("successful", 0)
            failed = result.get("failed", 0)
            elapsed = result.get("elapsed_time_seconds", 0)
            
            if "error" in result:
                print(f"\n❌ {config_name}: ERROR - {result['error']}")
            else:
                print(f"\n✅ {config_name}:")
                print(f"   Successful: {successful}")
                print(f"   Failed: {failed}")
                print(f"   Time: {elapsed:.1f}s")
                
                total_items += successful + failed
                total_successful += successful
                total_failed += failed
        
        print(f"\n{'='*60}")
        print(f"TOTALS:")
        print(f"  Configurations tested: {len(self.results)}")
        print(f"  Total items evaluated: {total_items}")
        print(f"  Total successful: {total_successful}")
        print(f"  Total failed: {total_failed}")
        
        if total_items > 0:
            success_rate = (total_successful / total_items) * 100
            print(f"  Success rate: {success_rate:.1f}%")


def main():
    """Main function to run comprehensive evaluation."""
    parser = argparse.ArgumentParser(description="Run comprehensive dataset evaluation")
    parser.add_argument(
        "--dataset",
        type=str,
        default="health-assistant-eval-smoke-test",
        help="Name of the Langfuse dataset to evaluate"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode with only 5 items"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of items to evaluate per configuration"
    )
    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create the dataset before evaluation"
    )
    parser.add_argument(
        "--dataset-config",
        type=str,
        choices=[
            "comprehensive", "safety", "patient-real", "provider", 
            "smoke-test", "vulnerable", "chronic"
        ],
        default="smoke-test",
        help="Predefined dataset configuration to use"
    )
    
    args = parser.parse_args()
    
    # Create dataset if requested
    if args.create_dataset:
        print("\n📊 Creating dataset...")
        creator = DatasetCreator()
        
        # Get the appropriate config
        configs = {
            "comprehensive": DatasetConfig(
                name=args.dataset,
                description="Comprehensive evaluation across all categories",
                categories={
                    "basic": 10,
                    "emergency": 5,
                    "mental_health_crisis": 3,
                    "guardrails": 8,
                    "adversarial": 10,
                    "real_world": 30,
                    "provider_clinical": 15
                },
                total_limit=100,
                random_seed=42
            ),
            "smoke-test": DatasetConfig(
                name=args.dataset,
                description="Quick smoke test with items from each category",
                categories={
                    "basic": 2,
                    "emergency": 1,
                    "mental_health_crisis": 1,
                    "guardrails": 2,
                    "adversarial": 2,
                    "real_world": 3,
                    "provider_clinical": 2
                },
                total_limit=15,
                random_seed=42
            ),
            # Add other configs as needed
        }
        
        config = configs.get(args.dataset_config, configs["smoke-test"])
        config.name = args.dataset  # Override name with provided dataset name
        
        creator.create_dataset(config, overwrite=True)
        print("✅ Dataset created successfully\n")
        
        # Wait a bit for Langfuse to process
        time.sleep(2)
    
    # Run comprehensive evaluation
    evaluator = ComprehensiveEvaluator(
        dataset_name=args.dataset,
        dry_run=args.dry_run,
        limit=args.limit
    )
    
    evaluator.run_all_evaluations()


if __name__ == "__main__":
    main()