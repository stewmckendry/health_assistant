#!/usr/bin/env python3
"""
Create a curated smoke test dataset with 1 representative test case per tool per agent.
This provides a quick sanity check that all agents and tools are working correctly.
"""

import sys
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent.parent))

from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# CURATED SMOKE TEST CASES (1 per tool per agent)
# ============================================================================

SMOKE_TEST_CASES = [
    # ========================================================================
    # DR. OFF - 1 case per tool (3 total)
    # ========================================================================

    # schedule_get - Representative OHIP billing query
    {
        "id": "dr_off_billing_001",
        "query": "What is the OHIP billing code and fee for a comprehensive assessment?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "simple",
        "tags": ["ohip", "billing", "assessment", "fee_lookup"],
        "rationale": "Tests basic schedule_get functionality - most common query type"
    },

    # odb_get - Representative drug coverage query
    {
        "id": "dr_off_drug_001",
        "query": "Is rosuvastatin 20mg covered by ODB? What are the generic alternatives?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "simple",
        "tags": ["odb", "statin", "generic", "alternatives"],
        "rationale": "Tests odb_get with common statin query + alternatives check"
    },

    # adp_get - Representative device coverage query
    {
        "id": "dr_off_adp_001",
        "query": "Does ADP cover power wheelchairs? What is the patient's cost share?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "simple",
        "tags": ["adp", "wheelchair", "funding", "eligibility"],
        "rationale": "Tests adp_get with common mobility device query"
    },

    # ========================================================================
    # DR. OPA - 1 case per tool (7 total)
    # ========================================================================

    # opa_policy_check - Representative CPSO policy query
    {
        "id": "dr_opa_cpso_001",
        "query": "What are CPSO requirements for informed consent in virtual care?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "simple",
        "tags": ["cpso", "virtual_care", "consent", "documentation"],
        "rationale": "Tests opa_policy_check with highly relevant virtual care policy"
    },

    # opa_ipac_guidance - Representative IPAC query
    {
        "id": "dr_opa_ipac_001",
        "query": "What are the current hand hygiene requirements in clinical settings?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "simple",
        "tags": ["pho", "ipac", "hand_hygiene", "infection_control"],
        "rationale": "Tests opa_ipac_guidance with fundamental IPAC requirement"
    },

    # opa_clinical_tools - Representative CEP tools query
    {
        "id": "dr_opa_cep_001",
        "query": "What CEP tools are available for hypertension management?",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "simple",
        "tags": ["cep", "hypertension", "tools", "chronic_disease"],
        "rationale": "Tests opa_clinical_tools with common chronic disease"
    },

    # opa_quality_standards - Representative quality standards query
    {
        "id": "dr_opa_qs_001",
        "query": "What are the Ontario Health quality standards for diabetes care?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards"],
        "difficulty": "simple",
        "tags": ["quality_standards", "diabetes", "chronic_disease"],
        "rationale": "Tests opa_quality_standards with well-established diabetes QS"
    },

    # opa_choosing_wisely - Representative Choosing Wisely query
    {
        "id": "dr_opa_cw_001",
        "query": "What tests should I avoid ordering for acute low back pain?",
        "agent": "dr_opa",
        "tools_expected": ["opa_choosing_wisely"],
        "difficulty": "simple",
        "tags": ["choosing_wisely", "overuse", "back_pain", "imaging"],
        "rationale": "Tests opa_choosing_wisely with classic overuse example"
    },

    # opa_program_lookup - Representative Ontario Health program query
    {
        "id": "dr_opa_program_001",
        "query": "How do I refer a patient to the Ontario Diabetes Program?",
        "agent": "dr_opa",
        "tools_expected": ["opa_program_lookup"],
        "difficulty": "simple",
        "tags": ["ontario_health", "diabetes", "referral", "program"],
        "rationale": "Tests opa_program_lookup with common referral scenario"
    },

    # opa_search_sections - Representative general search query
    {
        "id": "dr_opa_edge_002",
        "query": "How do I handle conflicting guidance from different sources?",
        "agent": "dr_opa",
        "tools_expected": ["opa_search_sections"],
        "difficulty": "complex",
        "tags": ["edge_case", "conflicts", "priority"],
        "rationale": "Tests opa_search_sections with multi-source conflict scenario"
    },

    # ========================================================================
    # CHIEF - 2 representative orchestration cases
    # ========================================================================

    # Integrated query requiring both agents - medium complexity
    {
        "id": "chief_integrated_001",
        "query": "I have a 68-year-old diabetic patient who needs better glycemic control. What medication options are ODB-covered, what are the CPSO expectations for diabetes management, and how do I bill the visit?",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["integrated", "diabetes", "medication", "cpso", "billing"],
        "rationale": "Tests Chief's ability to coordinate both agents for comprehensive answer"
    },

    # Ambiguous query requiring intelligent routing
    {
        "id": "chief_ambiguous_001",
        "query": "Tell me about diabetes management in Ontario",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["ambiguous", "diabetes", "comprehensive"],
        "rationale": "Tests Chief's routing logic for broad, ambiguous queries"
    },
]


def create_smoke_test_dataset():
    """Create the smoke test dataset in Langfuse."""

    langfuse = Langfuse()

    dataset_name = "agent_smoke_test"
    description = "Curated smoke test with 1 representative case per tool per agent (12 cases total). Quick sanity check for all agents and tools."

    print("=" * 60)
    print("CREATING AGENT SMOKE TEST DATASET")
    print("=" * 60)
    print(f"Dataset name: {dataset_name}")
    print(f"Total cases: {len(SMOKE_TEST_CASES)}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Check if dataset exists
    try:
        existing = langfuse.get_dataset(name=dataset_name)
        print(f"⚠️  Dataset '{dataset_name}' already exists. Overwriting...")
    except Exception:
        pass

    # Create dataset
    dataset = langfuse.create_dataset(
        name=dataset_name,
        description=description,
        metadata={
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "test_cases_count": len(SMOKE_TEST_CASES),
            "purpose": "smoke_test",
            "coverage": {
                "dr_off_tools": ["schedule_get", "odb_get", "adp_get"],
                "dr_opa_tools": ["opa_policy_check", "opa_ipac_guidance", "opa_clinical_tools",
                               "opa_quality_standards", "opa_choosing_wisely", "opa_program_lookup",
                               "opa_search_sections"],
                "chief_scenarios": ["integrated", "ambiguous"]
            }
        }
    )
    print(f"✅ Created dataset: {dataset_name}")

    # Add test cases
    success_count = 0

    print(f"\n📋 Adding test cases:")
    print("-" * 60)

    for case in SMOKE_TEST_CASES:
        try:
            langfuse.create_dataset_item(
                dataset_name=dataset_name,
                input={"query": case["query"]},
                expected_output={
                    "tools_expected": case.get("tools_expected", []),
                    "difficulty": case.get("difficulty", "unknown"),
                    "agent": case.get("agent", "unknown")
                },
                metadata={
                    "id": case.get("id"),
                    "agent": case.get("agent"),
                    "difficulty": case.get("difficulty"),
                    "tags": case.get("tags", []),
                    "rationale": case.get("rationale", "")
                }
            )
            success_count += 1
            print(f"  ✓ {case['id']}: {case['agent']} - {case['tools_expected']}")
        except Exception as e:
            print(f"  ✗ Error adding {case.get('id')}: {e}")

    print("-" * 60)
    print(f"✅ Added {success_count}/{len(SMOKE_TEST_CASES)} items to dataset")

    # Print breakdown
    print(f"\n📊 Smoke Test Breakdown:")

    # Count by agent
    agent_counts = {}
    for case in SMOKE_TEST_CASES:
        agent = case.get("agent", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1

    print(f"\n   By Agent:")
    for agent, count in sorted(agent_counts.items()):
        print(f"     - {agent}: {count} cases")

    # List tools covered
    print(f"\n   Tools Covered:")
    print(f"     Dr. OFF: schedule_get, odb_get, adp_get")
    print(f"     Dr. OPA: opa_policy_check, opa_ipac_guidance, opa_clinical_tools,")
    print(f"              opa_quality_standards, opa_choosing_wisely, opa_program_lookup,")
    print(f"              opa_search_sections")
    print(f"     Chief: integrated queries, ambiguous routing")

    print("\n" + "=" * 60)
    print("✅ SMOKE TEST DATASET CREATED")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Verify dataset in Langfuse: https://cloud.langfuse.com")
    print("2. Run evaluation:")
    print("   python scripts/run_agent_evaluation.py --dataset agent_smoke_test")
    print()

    return dataset_name


def main():
    """Main function."""
    dataset_name = create_smoke_test_dataset()
    return dataset_name


if __name__ == "__main__":
    main()
