#!/usr/bin/env python3
"""
Create synthetic evaluation datasets for Dr. OFF, Dr. OPA, and Chief (Diagnostic Orchestrator) agents.
Includes realistic test cases that exercise all MCP tools and edge cases.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
sys.path.append(str(Path(__file__).parent.parent))

from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# DR. OFF (Ontario Finance & Formulary) Test Cases
# ============================================================================

DR_OFF_TEST_CASES = [
    # OHIP Billing - schedule_get tool
    {
        "id": "dr_off_billing_001",
        "query": "What is the OHIP billing code and fee for a comprehensive assessment?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "simple",
        "tags": ["ohip", "billing", "assessment", "fee_lookup"]
    },
    {
        "id": "dr_off_billing_002",
        "query": "Can I bill C124 as MRP for a patient admitted Monday 3pm and discharged Thursday 1pm?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "complex",
        "tags": ["ohip", "discharge", "mrp", "length_of_stay", "timing"]
    },
    {
        "id": "dr_off_billing_003",
        "query": "What premiums can I add to a house call for an 80-year-old patient at 9pm on Saturday?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "medium",
        "tags": ["ohip", "premiums", "house_call", "elderly", "after_hours"]
    },
    {
        "id": "dr_off_billing_004",
        "query": "What is the billing code for a dermatology consultation in the ER?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "medium",
        "tags": ["ohip", "consultation", "er", "specialist"]
    },
    {
        "id": "dr_off_billing_005",
        "query": "How do I bill for a virtual care visit with a new patient?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "simple",
        "tags": ["ohip", "virtual_care", "new_patient"]
    },

    # ODB Drug Coverage - odb_get tool
    {
        "id": "dr_off_drug_001",
        "query": "Is rosuvastatin 20mg covered by ODB? What are the generic alternatives?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "simple",
        "tags": ["odb", "statin", "generic", "alternatives"]
    },
    {
        "id": "dr_off_drug_002",
        "query": "What are the Limited Use criteria for adalimumab (Humira)?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "medium",
        "tags": ["odb", "biologic", "limited_use", "criteria"]
    },
    {
        "id": "dr_off_drug_003",
        "query": "Is insulin glargine U300 (Toujeo) covered? If not, what covered alternatives exist?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "medium",
        "tags": ["odb", "insulin", "diabetes", "alternatives", "coverage"]
    },
    {
        "id": "dr_off_drug_004",
        "query": "Does ODB cover escitalopram? What about the brand name Cipralex?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "simple",
        "tags": ["odb", "antidepressant", "brand_vs_generic"]
    },
    {
        "id": "dr_off_drug_005",
        "query": "My patient can't afford their diabetes medication. What are the cheapest ODB-covered options for type 2 diabetes?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "medium",
        "tags": ["odb", "diabetes", "cost", "financial_barrier"]
    },

    # ADP Device Coverage - adp_get tool
    {
        "id": "dr_off_adp_001",
        "query": "Does ADP cover power wheelchairs? What is the patient's cost share?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "simple",
        "tags": ["adp", "wheelchair", "funding", "eligibility"]
    },
    {
        "id": "dr_off_adp_002",
        "query": "What hearing aids are covered by ADP for a 75-year-old with moderate hearing loss?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "medium",
        "tags": ["adp", "hearing_aid", "elderly", "eligibility"]
    },
    {
        "id": "dr_off_adp_003",
        "query": "Is there ADP coverage for insulin pumps? What are the eligibility requirements?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "medium",
        "tags": ["adp", "insulin_pump", "diabetes", "eligibility"]
    },
    {
        "id": "dr_off_adp_004",
        "query": "Does ADP cover CPAP machines for sleep apnea?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "simple",
        "tags": ["adp", "cpap", "sleep_apnea"]
    },
    {
        "id": "dr_off_adp_005",
        "query": "What documentation do I need to submit for ADP approval for a patient walker?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "medium",
        "tags": ["adp", "walker", "documentation", "application"]
    },

    # Multi-tool queries (complex scenarios)
    {
        "id": "dr_off_multi_001",
        "query": "My diabetic patient needs insulin and an insulin pump. What's covered by ODB and ADP? How do I bill the consultation?",
        "agent": "dr_off",
        "tools_expected": ["odb_get", "adp_get", "schedule_get"],
        "difficulty": "complex",
        "tags": ["multi_tool", "diabetes", "comprehensive"]
    },
    {
        "id": "dr_off_multi_002",
        "query": "Patient on ODSP needs hearing aids and hypertension medication. What coverage exists and what are the costs?",
        "agent": "dr_off",
        "tools_expected": ["adp_get", "odb_get"],
        "difficulty": "complex",
        "tags": ["multi_tool", "odsp", "financial_barrier"]
    },

    # Edge cases
    {
        "id": "dr_off_edge_001",
        "query": "What happens if a drug is not on the ODB formulary?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "medium",
        "tags": ["edge_case", "non_formulary", "alternatives"]
    },
    {
        "id": "dr_off_edge_002",
        "query": "Can I bill a second comprehensive assessment within 12 months for the same patient?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "medium",
        "tags": ["edge_case", "frequency_limits", "billing_rules"]
    },

    # Additional Edge Cases - Tool Failures & Error Handling
    {
        "id": "dr_off_edge_003",
        "query": "What is the billing code for XYZZZ123?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "simple",
        "tags": ["edge_case", "invalid_code", "no_results", "error_handling"]
    },
    {
        "id": "dr_off_edge_004",
        "query": "Is the drug 'supermagicpill' covered by ODB?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "simple",
        "tags": ["edge_case", "invalid_drug", "no_results", "error_handling"]
    },
    {
        "id": "dr_off_edge_005",
        "query": "Does ADP cover flying cars for mobility?",
        "agent": "dr_off",
        "tools_expected": ["adp_get"],
        "difficulty": "simple",
        "tags": ["edge_case", "nonsensical_query", "no_results", "graceful_failure"]
    },
    {
        "id": "dr_off_edge_006",
        "query": "I found two different OHIP codes for the same service - E078 and E079. Which one should I use?",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "medium",
        "tags": ["edge_case", "conflicting_codes", "disambiguation", "comparison"]
    },
    {
        "id": "dr_off_edge_007",
        "query": "My patient needs a medication that has both an ODB-covered generic and a non-covered brand. The patient insists on the brand name. What are my options?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "complex",
        "tags": ["edge_case", "patient_preference", "brand_vs_generic", "coverage_conflict"]
    },
    {
        "id": "dr_off_edge_008",
        "query": "Can I bill for",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "simple",
        "tags": ["edge_case", "incomplete_query", "clarification_needed", "malformed_input"]
    },
    {
        "id": "dr_off_edge_009",
        "query": "billing code fee cost price payment charge amount reimbursement",
        "agent": "dr_off",
        "tools_expected": ["schedule_get"],
        "difficulty": "medium",
        "tags": ["edge_case", "keyword_stuffing", "ambiguous", "clarification_needed"]
    },
    {
        "id": "dr_off_edge_010",
        "query": "What is the ODB coverage for a patient who is both on ODSP and has private insurance from their employer?",
        "agent": "dr_off",
        "tools_expected": ["odb_get"],
        "difficulty": "complex",
        "tags": ["edge_case", "dual_coverage", "coordination_of_benefits", "complex_eligibility"]
    },
]


# ============================================================================
# DR. OPA (Ontario Practice Advice) Test Cases
# ============================================================================

DR_OPA_TEST_CASES = [
    # CPSO Policy - opa_policy_check tool
    {
        "id": "dr_opa_cpso_001",
        "query": "What are CPSO requirements for informed consent in virtual care?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "simple",
        "tags": ["cpso", "virtual_care", "consent", "documentation"]
    },
    {
        "id": "dr_opa_cpso_002",
        "query": "Can I prescribe opioids via telemedicine? What are the CPSO expectations?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "complex",
        "tags": ["cpso", "opioids", "prescribing", "virtual_care", "controlled_substances"]
    },
    {
        "id": "dr_opa_cpso_003",
        "query": "What medical records must I keep for virtual care visits?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "medium",
        "tags": ["cpso", "medical_records", "documentation", "virtual_care"]
    },
    {
        "id": "dr_opa_cpso_004",
        "query": "What are CPSO expectations for continuity of care when I go on vacation?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "medium",
        "tags": ["cpso", "continuity", "coverage", "availability"]
    },
    {
        "id": "dr_opa_cpso_005",
        "query": "Can I send lab results to patients via unencrypted email?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "medium",
        "tags": ["cpso", "privacy", "email", "phi", "encryption"]
    },

    # IPAC Guidelines - opa_ipac_guidance tool
    {
        "id": "dr_opa_ipac_001",
        "query": "What are the current hand hygiene requirements in clinical settings?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "simple",
        "tags": ["pho", "ipac", "hand_hygiene", "infection_control"]
    },
    {
        "id": "dr_opa_ipac_002",
        "query": "What PPE is required when seeing a patient with suspected tuberculosis?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "medium",
        "tags": ["pho", "ipac", "ppe", "tuberculosis", "airborne"]
    },
    {
        "id": "dr_opa_ipac_003",
        "query": "How should I clean and disinfect my clinic after seeing a COVID-positive patient?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "medium",
        "tags": ["pho", "ipac", "covid", "disinfection", "cleaning"]
    },
    {
        "id": "dr_opa_ipac_004",
        "query": "When should I use contact precautions in long-term care?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "medium",
        "tags": ["pho", "ipac", "contact_precautions", "ltc"]
    },

    # Clinical Tools - opa_clinical_tools tool (CEP)
    {
        "id": "dr_opa_cep_001",
        "query": "What CEP tools are available for hypertension management?",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "simple",
        "tags": ["cep", "hypertension", "tools", "chronic_disease"]
    },
    {
        "id": "dr_opa_cep_002",
        "query": "How do I use the CEP diabetes screening tool?",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "medium",
        "tags": ["cep", "diabetes", "screening", "prevention"]
    },
    {
        "id": "dr_opa_cep_003",
        "query": "What are the CEP recommendations for cardiovascular risk assessment?",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "medium",
        "tags": ["cep", "cardiovascular", "risk_assessment"]
    },
    {
        "id": "dr_opa_cep_004",
        "query": "Does CEP have a tool for COPD management and action plans?",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "simple",
        "tags": ["cep", "copd", "respiratory", "action_plan"]
    },

    # Quality Standards - opa_quality_standards tool
    {
        "id": "dr_opa_qs_001",
        "query": "What are the Ontario Health quality standards for diabetes care?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards"],
        "difficulty": "simple",
        "tags": ["quality_standards", "diabetes", "chronic_disease"]
    },
    {
        "id": "dr_opa_qs_002",
        "query": "What quality indicators should I measure for heart failure patients?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards"],
        "difficulty": "medium",
        "tags": ["quality_standards", "heart_failure", "indicators"]
    },
    {
        "id": "dr_opa_qs_003",
        "query": "What are the quality standards for palliative care in Ontario?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards"],
        "difficulty": "medium",
        "tags": ["quality_standards", "palliative", "end_of_life"]
    },

    # Choosing Wisely - opa_choosing_wisely tool
    {
        "id": "dr_opa_cw_001",
        "query": "What tests should I avoid ordering for acute low back pain?",
        "agent": "dr_opa",
        "tools_expected": ["opa_choosing_wisely"],
        "difficulty": "simple",
        "tags": ["choosing_wisely", "overuse", "back_pain", "imaging"]
    },
    {
        "id": "dr_opa_cw_002",
        "query": "What are the Choosing Wisely recommendations for preoperative testing?",
        "agent": "dr_opa",
        "tools_expected": ["opa_choosing_wisely"],
        "difficulty": "medium",
        "tags": ["choosing_wisely", "preoperative", "testing", "overuse"]
    },
    {
        "id": "dr_opa_cw_003",
        "query": "When should I NOT order antibiotics for upper respiratory infections?",
        "agent": "dr_opa",
        "tools_expected": ["opa_choosing_wisely"],
        "difficulty": "simple",
        "tags": ["choosing_wisely", "antibiotics", "stewardship", "uri"]
    },

    # Ontario Health Programs - opa_program_lookup tool
    {
        "id": "dr_opa_program_001",
        "query": "How do I refer a patient to the Ontario Diabetes Program?",
        "agent": "dr_opa",
        "tools_expected": ["opa_program_lookup"],
        "difficulty": "simple",
        "tags": ["ontario_health", "diabetes", "referral", "program"]
    },
    {
        "id": "dr_opa_program_002",
        "query": "What screening programs are available through Cancer Care Ontario?",
        "agent": "dr_opa",
        "tools_expected": ["opa_program_lookup"],
        "difficulty": "medium",
        "tags": ["ontario_health", "screening", "cancer", "prevention"]
    },
    {
        "id": "dr_opa_program_003",
        "query": "How does the Ontario Stroke Network coordinate care for stroke patients?",
        "agent": "dr_opa",
        "tools_expected": ["opa_program_lookup"],
        "difficulty": "medium",
        "tags": ["ontario_health", "stroke", "care_coordination"]
    },

    # Multi-tool queries
    {
        "id": "dr_opa_multi_001",
        "query": "I want to prescribe opioids via virtual care. What are the CPSO requirements and CEP tools available?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check", "opa_clinical_tools"],
        "difficulty": "complex",
        "tags": ["multi_tool", "opioids", "virtual_care", "tools"]
    },
    {
        "id": "dr_opa_multi_002",
        "query": "What are the quality standards and Choosing Wisely recommendations for heart failure management?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards", "opa_choosing_wisely"],
        "difficulty": "complex",
        "tags": ["multi_tool", "heart_failure", "quality", "overuse"]
    },

    # Edge cases
    {
        "id": "dr_opa_edge_001",
        "query": "What if no specific CPSO policy exists for my situation?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "medium",
        "tags": ["edge_case", "guidance", "professional_judgment"]
    },
    {
        "id": "dr_opa_edge_002",
        "query": "How do I handle conflicting guidance from different sources?",
        "agent": "dr_opa",
        "tools_expected": ["opa_search_sections"],
        "difficulty": "complex",
        "tags": ["edge_case", "conflicts", "priority"]
    },

    # Additional Edge Cases - Tool Failures & Error Handling
    {
        "id": "dr_opa_edge_003",
        "query": "What is the CPSO policy on treating alien patients from Mars?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "simple",
        "tags": ["edge_case", "nonsensical_query", "no_results", "graceful_failure"]
    },
    {
        "id": "dr_opa_edge_004",
        "query": "Does CEP have a tool for diagnosing",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "simple",
        "tags": ["edge_case", "incomplete_query", "clarification_needed", "malformed_input"]
    },
    {
        "id": "dr_opa_edge_005",
        "query": "CPSO virtual care policy says one thing but my college newsletter says something different. Which takes precedence?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "complex",
        "tags": ["edge_case", "conflicting_sources", "policy_hierarchy", "authority"]
    },
    {
        "id": "dr_opa_edge_006",
        "query": "What are the IPAC requirements for a disease that doesn't exist yet?",
        "agent": "dr_opa",
        "tools_expected": ["opa_ipac_guidance"],
        "difficulty": "medium",
        "tags": ["edge_case", "hypothetical", "general_guidance", "principles"]
    },
    {
        "id": "dr_opa_edge_007",
        "query": "I need CEP tools for diabetes hypertension COPD heart failure asthma stroke cancer",
        "agent": "dr_opa",
        "tools_expected": ["opa_clinical_tools"],
        "difficulty": "medium",
        "tags": ["edge_case", "multi_condition", "broad_query", "prioritization"]
    },
    {
        "id": "dr_opa_edge_008",
        "query": "The Quality Standard says to do X but Choosing Wisely says NOT to do X. What should I do?",
        "agent": "dr_opa",
        "tools_expected": ["opa_quality_standards", "opa_choosing_wisely"],
        "difficulty": "complex",
        "tags": ["edge_case", "contradictory_guidance", "clinical_judgment", "evidence_hierarchy"]
    },
    {
        "id": "dr_opa_edge_009",
        "query": "Where can I find the most recent CPSO policy on [topic that was updated last week]?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check", "opa_freshness_probe"],
        "difficulty": "medium",
        "tags": ["edge_case", "freshness", "recent_updates", "version_control"]
    },
    {
        "id": "dr_opa_edge_010",
        "query": "policy guideline recommendation standard expectation advice requirement",
        "agent": "dr_opa",
        "tools_expected": ["opa_search_sections"],
        "difficulty": "medium",
        "tags": ["edge_case", "keyword_stuffing", "ambiguous", "clarification_needed"]
    },
    {
        "id": "dr_opa_edge_011",
        "query": "I searched the CPSO website and found one answer, but my colleague says the policy says something different. Can you check what's actually correct?",
        "agent": "dr_opa",
        "tools_expected": ["opa_policy_check"],
        "difficulty": "medium",
        "tags": ["edge_case", "verification", "fact_checking", "source_of_truth"]
    },
]


# ============================================================================
# CHIEF (Diagnostic Orchestrator) Test Cases
# ============================================================================

CHIEF_TEST_CASES = [
    # Cases requiring both practice advice AND coverage information
    {
        "id": "chief_integrated_001",
        "query": "I have a 68-year-old diabetic patient who needs better glycemic control. What medication options are ODB-covered, what are the CPSO expectations for diabetes management, and how do I bill the visit?",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["integrated", "diabetes", "medication", "cpso", "billing"]
    },
    {
        "id": "chief_integrated_002",
        "query": "Patient with COPD exacerbation needs home oxygen. What's the ADP coverage, what are the CEP management guidelines, and what quality standards apply?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["integrated", "copd", "oxygen", "adp", "quality"]
    },
    {
        "id": "chief_integrated_003",
        "query": "I want to start a virtual care clinic. What are the CPSO requirements, billing codes, and IPAC considerations?",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["integrated", "virtual_care", "cpso", "billing", "ipac"]
    },
    {
        "id": "chief_integrated_004",
        "query": "Elderly patient with hearing loss and hypertension needs care optimization. What devices are covered, what drugs are on formulary, what CEP tools exist, and how should I document this?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["integrated", "elderly", "multi_morbidity", "devices", "medication"]
    },
    {
        "id": "chief_integrated_005",
        "query": "Setting up house calls for palliative patients. What are the billing premiums, CPSO documentation requirements, and quality standards for palliative care?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["integrated", "palliative", "house_calls", "billing", "quality"]
    },

    # Edge case: ambiguous intent (orchestrator must decide)
    {
        "id": "chief_ambiguous_001",
        "query": "Tell me about diabetes management in Ontario",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["ambiguous", "diabetes", "comprehensive"]
    },
    {
        "id": "chief_ambiguous_002",
        "query": "What do I need to know about prescribing for my patients?",
        "agent": "chief",
        "tools_expected": ["dr_opa"],
        "difficulty": "medium",
        "tags": ["ambiguous", "prescribing", "general"]
    },

    # Sequential reasoning (must gather info from one agent before querying another)
    {
        "id": "chief_sequential_001",
        "query": "My patient can't afford their medication. First tell me what's covered, then help me find the cheapest effective alternative, and explain how to apply for financial assistance programs.",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["sequential", "financial_barrier", "alternatives", "programs"]
    },

    # Additional Edge Cases - Orchestration Failures & Error Handling
    {
        "id": "chief_edge_001",
        "query": "I need help with my patient but I'm not sure what kind of help exactly.",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["edge_case", "extremely_vague", "clarification_needed", "intent_unclear"]
    },
    {
        "id": "chief_edge_002",
        "query": "Tell me everything about billing, coverage, policies, and guidelines for diabetes.",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["edge_case", "overly_broad", "scope_management", "prioritization"]
    },
    {
        "id": "chief_edge_003",
        "query": "What if Dr. OFF says a drug is covered but Dr. OPA says not to prescribe it due to Choosing Wisely recommendations?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["edge_case", "inter_agent_conflict", "reconciliation", "clinical_judgment"]
    },
    {
        "id": "chief_edge_004",
        "query": "My patient needs [lists 10 different medications and 5 devices]. Tell me everything about coverage, policies, and billing for all of them.",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["edge_case", "volume_overload", "batching", "prioritization"]
    },
    {
        "id": "chief_edge_005",
        "query": "I'm starting a new practice. What do I need to know?",
        "agent": "chief",
        "tools_expected": ["dr_opa", "dr_off"],
        "difficulty": "complex",
        "tags": ["edge_case", "extremely_broad", "comprehensive", "scope_too_large"]
    },
    {
        "id": "chief_edge_006",
        "query": "Can you help with both billing AND policies for [incomplete sentence]",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "medium",
        "tags": ["edge_case", "incomplete_query", "multi_agent", "clarification_needed"]
    },
    {
        "id": "chief_edge_007",
        "query": "I think I need Dr. OFF but maybe also Dr. OPA? I'm not sure which one or maybe both?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "medium",
        "tags": ["edge_case", "user_uncertainty", "routing_guidance", "meta_query"]
    },
    {
        "id": "chief_edge_008",
        "query": "What are the differences between what Dr. OFF and Dr. OPA can help me with?",
        "agent": "chief",
        "tools_expected": [],
        "difficulty": "medium",
        "tags": ["edge_case", "meta_query", "capability_explanation", "system_description"]
    },
    {
        "id": "chief_edge_009",
        "query": "Patient with rare genetic disorder needs experimental treatment not covered by ODB and no CPSO policy exists. What now?",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["edge_case", "no_guidance_available", "both_agents_fail", "general_principles"]
    },
    {
        "id": "chief_edge_010",
        "query": "Give me billing codes, drug coverage, device funding, CPSO policies, IPAC guidelines, CEP tools, quality standards, and Choosing Wisely recommendations for heart failure management.",
        "agent": "chief",
        "tools_expected": ["dr_off", "dr_opa"],
        "difficulty": "complex",
        "tags": ["edge_case", "kitchen_sink", "comprehensive", "all_tools", "prioritization"]
    },
]


# ============================================================================
# Dataset Creation Functions
# ============================================================================

def create_dataset(langfuse: Langfuse, dataset_name: str, test_cases: List[Dict],
                   description: str, overwrite: bool = False):
    """Create a Langfuse dataset from test cases."""

    try:
        # Check if dataset exists
        existing = langfuse.get_dataset(name=dataset_name)
        if existing and not overwrite:
            print(f"⚠️  Dataset '{dataset_name}' already exists. Use --overwrite to replace.")
            return dataset_name
        elif existing and overwrite:
            print(f"🔄 Overwriting existing dataset '{dataset_name}'")
    except Exception:
        pass

    # Create dataset
    dataset = langfuse.create_dataset(
        name=dataset_name,
        description=description,
        metadata={
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "test_cases_count": len(test_cases)
        }
    )
    print(f"✅ Created dataset: {dataset_name}")

    # Add test cases
    success_count = 0
    for case in test_cases:
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
                    "tags": case.get("tags", [])
                }
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Error adding item {case.get('id')}: {e}")

    print(f"✅ Added {success_count}/{len(test_cases)} items to dataset")

    # Print summary
    print(f"\n📊 Dataset Summary:")
    print(f"   Name: {dataset_name}")
    print(f"   Total items: {len(test_cases)}")

    # Count by difficulty
    difficulty_counts = {}
    for case in test_cases:
        diff = case.get("difficulty", "unknown")
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

    print(f"   By difficulty:")
    for diff, count in sorted(difficulty_counts.items()):
        print(f"     - {diff}: {count}")

    return dataset_name


def main():
    """Main function to create all agent evaluation datasets."""
    import argparse

    parser = argparse.ArgumentParser(description="Create agent evaluation datasets")
    parser.add_argument("--agent", choices=["dr_off", "dr_opa", "chief", "all"],
                       default="all", help="Which agent dataset to create")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing datasets")
    args = parser.parse_args()

    # Initialize Langfuse
    langfuse = Langfuse()

    print("=" * 60)
    print("CREATING AGENT EVALUATION DATASETS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'Overwrite' if args.overwrite else 'Create new only'}")
    print()

    # Create datasets based on selection
    if args.agent in ["dr_off", "all"]:
        print("\n📋 Creating DR. OFF Dataset...")
        print("-" * 60)
        create_dataset(
            langfuse=langfuse,
            dataset_name="dr_off_agent_eval",
            test_cases=DR_OFF_TEST_CASES,
            description="Evaluation dataset for Dr. OFF (Ontario Finance & Formulary) agent - OHIP billing, ODB drug coverage, and ADP device funding",
            overwrite=args.overwrite
        )

    if args.agent in ["dr_opa", "all"]:
        print("\n📋 Creating DR. OPA Dataset...")
        print("-" * 60)
        create_dataset(
            langfuse=langfuse,
            dataset_name="dr_opa_agent_eval",
            test_cases=DR_OPA_TEST_CASES,
            description="Evaluation dataset for Dr. OPA (Ontario Practice Advice) agent - CPSO policies, IPAC guidelines, CEP tools, quality standards, and Ontario Health programs",
            overwrite=args.overwrite
        )

    if args.agent in ["chief", "all"]:
        print("\n📋 Creating CHIEF Dataset...")
        print("-" * 60)
        create_dataset(
            langfuse=langfuse,
            dataset_name="chief_orchestrator_eval",
            test_cases=CHIEF_TEST_CASES,
            description="Evaluation dataset for Chief (Diagnostic Orchestrator) - integrated queries requiring coordination between Dr. OFF and Dr. OPA",
            overwrite=args.overwrite
        )

    print("\n" + "=" * 60)
    print("✅ DATASET CREATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review datasets in Langfuse: https://cloud.langfuse.com")
    print("2. Generate expected results: python scripts/generate_expected_results.py")
    print("3. Run evaluation: python scripts/run_agent_evaluation.py")


if __name__ == "__main__":
    main()
