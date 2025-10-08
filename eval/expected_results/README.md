# Agent Evaluation Expected Results

## Overview
This directory contains expected results for agent evaluation test cases, generated through systematic web searches of authoritative Ontario healthcare sources.

**Generated**: October 8, 2025
**Total Test Cases**: 25 (10 Dr. OFF + 10 Dr. OPA + 5 Chief)

## Methodology

### Data Collection
- Used `mcp__exa__web_search_exa` tool to search authoritative Ontario sources
- Focused on official government and regulatory websites:
  - ontario.ca / health.gov.on.ca (OHIP, ODB, ADP)
  - cpso.on.ca (CPSO policies)
  - publichealthontario.ca (IPAC guidelines)
  - formulary.health.gov.on.ca (ODB formulary)
  - cep.health (Clinical Education & Practice)
  - ontariohealth.ca (Quality Standards)

### Expected Result Structure
Each test case includes:
- **key_facts**: Array of factual statements from authoritative sources
- **sources**: Array of source documents with URLs, titles, and relevant snippets
- **tools_expected**: MCP tools the agent should use
- **answer_quality_criteria**: Specific criteria for evaluating agent responses

## Files

### dr_off_expected_results.json
**Agent**: Dr. OFF (Ontario Finance & Formulary)
**Test Cases**: 10
**Coverage**:
- OHIP billing codes and fees (4 cases)
- ODB drug coverage and formulary (3 cases)
- ADP device coverage (2 cases)
- Edge cases (1 case)

**Key Sources**:
- Schedule of Benefits for Physician Services
- ODB Formulary Search
- ADP Policy and Administration Manuals
- OHIP INFOBulletins

### dr_opa_expected_results.json
**Agent**: Dr. OPA (Ontario Practice Advice)
**Test Cases**: 10
**Coverage**:
- CPSO policies (5 cases: virtual care, consent, prescribing, records, privacy)
- IPAC guidelines (4 cases: hand hygiene, PPE/TB, cleaning, contact precautions)
- Clinical tools and quality standards (1 case each)

**Key Sources**:
- CPSO Policy Documents and Advice to the Profession
- PHO/PIDAC Best Practice Documents
- Routine Practices and Additional Precautions
- CEP and Ontario Health Quality Standards

### chief_expected_results.json
**Agent**: Chief (Diagnostic Orchestrator)
**Test Cases**: 5
**Coverage**:
- Integrated queries requiring both Dr. OFF and Dr. OPA (3 cases)
- Ambiguous queries requiring scope determination (1 case)
- Sequential reasoning queries (1 case)

**Note**: Chief expected results focus on coordination quality and integration rather than specific factual content, as Chief orchestrates between other agents.

## Quality Assurance

### Source Reliability
- All sources are official Ontario government or regulatory body websites
- Documents include policy manuals, clinical guidelines, and formulary databases
- Sources dated 2018-2025, with preference for most recent versions
- Direct quotes and excerpts captured where applicable

### Factual Accuracy
- Key facts extracted directly from source documents
- Cross-referenced across multiple sources where possible
- Focused on stable, policy-based information rather than frequently changing details
- Included version/effective dates where relevant (e.g., "Effective December 1, 2022")

### Coverage Prioritization
Started with simpler, high-value test cases:
1. **Dr. OFF**: Basic billing lookups, common drug coverage queries, standard device funding
2. **Dr. OPA**: Frequently referenced CPSO policies, core IPAC practices
3. **Chief**: Saved for last as these are most complex

## Usage in Evaluation

These expected results can be used to:

1. **Ground Truth Comparison**: Compare agent responses to authoritative facts
2. **Tool Usage Validation**: Verify agents call correct MCP tools
3. **Source Attribution**: Check if agents cite authoritative sources
4. **Answer Completeness**: Assess if key facts are covered
5. **Quality Scoring**: Use answer_quality_criteria as rubric for evaluation

## Next Steps

1. **Run Agent Evaluation**: Use these expected results with `run_agent_evaluation.py`
2. **Generate Metrics**: Calculate accuracy, completeness, tool usage scores
3. **Expand Coverage**: Add expected results for remaining test cases
4. **Iterate**: Update expected results as policies/guidelines change

## Limitations

- **Temporal**: Healthcare policies and fees change regularly; expected results need periodic updates
- **Scope**: Focused on 10 cases per agent (25 total) out of larger test suites
- **Depth**: Some complex queries may have multiple valid answers; expected results capture primary facts
- **Integration**: Chief test cases are challenging to score as they depend on coordination quality

## Sources Summary

### Government of Ontario
- ontario.ca - OHIP Schedule of Benefits, ADP manuals, policy documents
- health.gov.on.ca - Ministry of Health resources and guidelines
- formulary.health.gov.on.ca - ODB Formulary search tool

### Regulatory Bodies
- cpso.on.ca - College of Physicians and Surgeons of Ontario policies
- publichealthontario.ca - Public Health Ontario IPAC guidelines

### Clinical Resources
- cep.health - Clinical Education and Practice tools
- ontariohealth.ca - Quality Standards

## Contact

For questions about these expected results or evaluation methodology, refer to the project documentation or the test case definitions in `/scripts/create_agent_eval_dataset.py`.
