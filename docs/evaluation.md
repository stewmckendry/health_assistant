# Health Assistant Evaluation Framework

## Overview

The Health Assistant evaluation framework provides comprehensive testing across diverse medical scenarios, demographics, and system configurations. It uses Langfuse for LLM-as-judge evaluations and supports configurable dataset creation from a pool of 200+ test cases.

## Architecture

### Components

1. **Test Cases Repository** (`src/config/evaluation_test_cases.yaml`)
   - 200+ diverse test cases covering all medical specialties
   - Organized by categories and subcategories
   - Realistic patient narratives with detailed scenarios
   - Provider-specific clinical cases

2. **Dataset Creator** (`src/evaluation/dataset_creator.py`)
   - Configurable sampling from test case pool
   - Predefined dataset configurations
   - Reproducible with random seeds
   - Category and subcategory filtering

3. **Dataset Evaluator** (`src/evaluation/evaluator.py`)
   - Multi-mode support (patient/provider)
   - Web tools configuration (on/off)
   - Domain filtering (government/academic/all)
   - Langfuse integration for automated scoring

4. **Batch Runner** (`scripts/run_comprehensive_evaluation.py`)
   - Multiple configuration testing
   - Automated result collection
   - Performance comparison across settings

## Test Case Categories

### Primary Categories

- **basic**: Common health queries (symptoms, prevention, lifestyle)
- **emergency**: Life-threatening situations requiring immediate action
- **mental_health_crisis**: Suicide, self-harm, crisis intervention
- **guardrails**: Diagnosis attempts, medication dosing, boundary testing
- **adversarial**: Prompt injection, misinformation, edge cases
- **real_world**: Detailed patient scenarios with demographics/context
- **provider_clinical**: Technical queries for healthcare providers

### Diverse Coverage

The test cases include:
- **Demographics**: All ages (newborn to elderly), LGBTQ+, immigrants, prisoners
- **Conditions**: Chronic diseases, rare conditions, genetic disorders
- **Specialties**: 20+ medical specialties represented
- **Social Factors**: Uninsured, homeless, rural access, language barriers
- **Cultural**: Religious considerations, traditional medicine integration

## Dataset Configurations

### Predefined Datasets

```python
# Comprehensive baseline (100 items)
"health-assistant-eval-comprehensive": {
    "basic": 10, "emergency": 5, "mental_health_crisis": 3,
    "guardrails": 8, "adversarial": 10, "real_world": 30,
    "provider_clinical": 15
}

# Safety-focused (50 items)
"health-assistant-eval-safety": {
    "emergency": 10, "mental_health_crisis": 10,
    "guardrails": 15, "adversarial": 15
}

# Quick smoke test (15 items)
"health-assistant-eval-smoke-test": {
    "basic": 2, "emergency": 1, "mental_health_crisis": 1,
    "guardrails": 2, "adversarial": 2, "real_world": 3,
    "provider_clinical": 2
}

# Provider-specific (50 items)
"health-assistant-eval-provider": {
    "provider_clinical": 40, "real_world": 10
}

# Vulnerable populations (40 items)
"health-assistant-eval-vulnerable": {
    "real_world": 40,
    "include_subcategories": ["homeless_health", "veteran_ptsd", ...]
}
```

### Custom Dataset Creation

```python
from src.evaluation.dataset_creator import DatasetCreator, DatasetConfig

# Create custom dataset with specific sampling
config = DatasetConfig(
    name="my-custom-eval",
    description="Custom evaluation dataset",
    categories={
        "basic": 5,
        "emergency": 3,
        "real_world": 10
    },
    total_limit=20,
    random_seed=42,
    include_subcategories=["diabetes_complications", "hypertension"]
)

creator = DatasetCreator()
creator.create_dataset(config)
```

## Evaluation Configurations

### Configuration Matrix

Each evaluation can be run with different configurations:

| Configuration | Mode | Web Tools | Domain Filter | Use Case |
|--------------|------|-----------|---------------|----------|
| patient_baseline | Patient | ✓ | All | Standard patient queries with full RAG |
| patient_no_rag | Patient | ✗ | - | Test without web retrieval |
| patient_gov_only | Patient | ✓ | Government | Restrict to CDC, NIH, FDA, etc. |
| patient_academic_only | Patient | ✓ | Academic | Mayo Clinic, Johns Hopkins, etc. |
| provider_baseline | Provider | ✓ | All | Clinical queries with full access |
| provider_no_rag | Provider | ✗ | - | Provider mode without web tools |

## Running Evaluations

### Quick Start

```bash
# 1. Set up environment
source ~/spacy_env/bin/activate
source ~/thunder_playbook/.env

# 2. Create a smoke test dataset
python scripts/run_comprehensive_evaluation.py \
  --dataset health-assistant-eval-smoke \
  --create-dataset \
  --dataset-config smoke-test \
  --dry-run

# 3. Run full evaluation
python scripts/run_comprehensive_evaluation.py \
  --dataset health-assistant-eval-comprehensive \
  --limit 50
```

### Command Line Options

```bash
python scripts/run_comprehensive_evaluation.py [OPTIONS]

Options:
  --dataset NAME         Langfuse dataset name
  --dry-run             Test with 5 items only
  --limit N             Limit items per configuration
  --create-dataset      Create dataset before evaluation
  --dataset-config TYPE  Predefined config (comprehensive|safety|smoke-test|...)
```

### Creating Datasets Only

```python
# Run the dataset creator directly
python -m src.evaluation.dataset_creator

# This will:
# 1. Show summary of available test cases
# 2. Create a demo custom dataset
# 3. List all predefined configurations
```

## Trace Structure

### Hierarchy

Each API request creates a nested trace structure:

```
Dataset run: <run_name> (SPAN)
└── patient_query (SPAN)
    ├── input_guardrail_check (SPAN)
    ├── llm_call (GENERATION)
    │   ├── tool:web_search (SPAN)
    │   └── tool:web_fetch (SPAN) [multiple]
    └── output_guardrail_check (SPAN)
```

### Span Details

#### 1. **llm_call** (GENERATION)
- **Type**: Generation (for LLM API calls)
- **Input**: Messages array sent to Claude
- **Output**: Complete response text with citations
- **Metadata**:
  - `session_id`: Unique session identifier
  - `citations_count`: Number of citations in response
  - `tool_calls_count`: Number of tools invoked
  - `model`: Model name (e.g., claude-3-5-sonnet)
  - `usage`: Token counts

#### 2. **tool:web_search** (SPAN)
- **Type**: Span (nested under llm_call)
- **Input**: Search query
- **Output**: Search results
- **Metadata**:
  - `tool_name`: "web_search"
  - `query`: Search query
  - `result_count`: Number of results
  - `duration_ms`: Execution time

#### 3. **tool:web_fetch** (SPAN)
- **Type**: Span (nested under llm_call)
- **Input**: URL to fetch
- **Output**: Fetched content
- **Metadata**:
  - `tool_name`: "web_fetch"
  - `url`: Fetched URL
  - `title`: Page title
  - `content_length`: Characters fetched
  - `citation_index`: Index in citations list

## Langfuse Integration

### LLM Evaluators

The system uses 6 LLM-as-judge evaluators configured in Langfuse:

1. **Safety Compliance** (30% weight) - Emergency detection, crisis handling
2. **Medical Accuracy** (25% weight) - Factual correctness, evidence-based
3. **Citation Quality** (20% weight) - Source reliability, proper attribution
4. **Response Helpfulness** (15% weight) - Addresses query, actionable advice
5. **Emergency Handling** (5% weight) - Appropriate urgency, 911 referrals
6. **Disclaimer Presence** (5% weight) - Educational disclaimers, no diagnosis

### Viewing Results

1. **Langfuse Dashboard**: View traces, scores, and comparisons
2. **JSON Output**: `evaluation_results/eval_results_[timestamp].json`
3. **Console Summary**: Immediate feedback during runs

### Session and User Tracking

```python
# CLI usage with session/user tracking
python scripts/test_assistant.py \
    --query "What are symptoms of flu?" \
    --session-id "conv-2024-001" \
    --user-id "user-123"

# Programmatic usage
response = assistant.query(
    query="What are symptoms of flu?",
    session_id="conv-2024-001",
    user_id="user-123"
)

# Evaluation with user tracking
evaluator.run_dataset_evaluation(
    dataset_name="health-assistant-eval-v1",
    user_id="eval-user-456"
)
```

### Retrieving Evaluation Data

```python
from src.evaluation.evaluator import DatasetEvaluator

evaluator = DatasetEvaluator()

# Get trace details
trace_data = evaluator.get_trace_details("trace-id-here")

# Get evaluation scores
scores = evaluator.get_run_scores("my_evaluation_run")
if scores:
    for metric, value in scores.items():
        print(f"{metric}: {value:.2f}")

# Get session traces
session_traces = evaluator.get_session_traces(
    session_id="conv-2024-001",
    limit=100
)

# Get user activity
user_traces = evaluator.get_user_traces(
    user_id="user-123",
    limit=100
)
```

## Workflow

### Standard Evaluation Process

1. **Dataset Preparation**
   - Choose or create dataset configuration
   - Sample from 200+ test cases pool
   - Upload to Langfuse

2. **Configuration Selection**
   - Select evaluation configurations
   - (mode, web_tools, domain_filter)

3. **Batch Execution**
   - Run evaluations across configurations
   - Automatic scoring via LLM evaluators
   - Result collection and storage

4. **Analysis**
   - Compare configurations
   - Identify failure patterns
   - Generate improvement recommendations

## Best Practices

### Dataset Design

- **Balance categories** based on evaluation goals
- **Use random seeds** for reproducibility
- **Include edge cases** from adversarial category
- **Test vulnerable populations** for equity
- **Vary complexity** from basic to complex scenarios

### Evaluation Strategy

- **Start with smoke tests** (15 items) for quick validation
- **Run comprehensive** (100+ items) for final validation
- **Compare configurations** to understand system behavior
- **Focus evaluations** on specific concerns (safety, accuracy)
- **Iterate based on results** - create targeted datasets

### Performance Optimization

- **Use limits** to control evaluation size
- **Run in parallel** when possible (different datasets)
- **Cache results** in Langfuse for analysis
- **Monitor API usage** to avoid rate limits

## Success Criteria (Phase 2)

- **Safety Compliance**: >99% pass rate
- **Medical Accuracy**: >90% average score
- **Citation Quality**: >80% from trusted sources
- **Overall Quality**: >85% weighted average
- **Emergency Detection**: 100% correct identification
- **Response Time**: <5 seconds p95

## Results Analysis

### Output Format

```json
{
  "dataset": "health-assistant-eval-comprehensive",
  "timestamp": "20240117_143022",
  "configurations_tested": 7,
  "results": [
    {
      "config": {
        "name": "patient_baseline",
        "mode": "patient",
        "web_tools": true,
        "domain_filter": null
      },
      "successful": 95,
      "failed": 5,
      "elapsed_time_seconds": 234.5
    }
  ]
}
```

### Key Metrics

- **Success Rate**: Percentage of queries handled without errors
- **Safety Score**: Average of emergency/crisis detection scores
- **Accuracy Score**: Medical accuracy evaluator results
- **Citation Quality**: Proper sourcing and attribution
- **Response Time**: Average time per query

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Add delays between items
   - Reduce batch sizes
   - Use dry-run mode for testing

2. **Dataset Not Found**
   - Ensure dataset exists in Langfuse
   - Check dataset name spelling
   - Create dataset with `--create-dataset`

3. **Configuration Errors**
   - Verify provider assistant exists for provider mode
   - Check domain lists in evaluator
   - Ensure web tools properly disabled

4. **Memory Issues**
   - Limit dataset size
   - Process in smaller batches
   - Clear cache between runs

### Missing Tool Spans
If tool spans aren't appearing:
1. Check that tools are enabled in API call
2. Verify anthropic-beta headers are set
3. Ensure Langfuse client is initialized
4. Check logs for span creation errors

### No Evaluation Scores
If scores aren't appearing:
1. Wait 1-2 minutes for async evaluation
2. Check evaluator configuration in Langfuse
3. Verify dataset run was created successfully
4. Check for evaluator errors in Langfuse dashboard

## Advanced Usage

### Custom Evaluations

```python
from src.evaluation.evaluator import DatasetEvaluator

# Custom configuration
evaluator = DatasetEvaluator(
    mode='provider',
    web_tools=False,
    domain_filter='government'
)

# Run with specific parameters
results = evaluator.run_dataset_evaluation(
    dataset_name='my-custom-dataset',
    run_name='experiment-001',
    limit=25,
    user_id='researcher-1'
)
```

### Programmatic Dataset Creation

```python
from src.evaluation.dataset_creator import DatasetCreator, DatasetConfig

creator = DatasetCreator()

# Get available categories
categories = creator.get_available_categories()
print(f"Available: {categories}")

# Sample specific subcategories
config = DatasetConfig(
    name="targeted-eval",
    description="Targeted evaluation",
    categories={"real_world": 20},
    include_subcategories=["chronic_disease", "elderly_care"],
    exclude_subcategories=["pediatric"],
    random_seed=100
)

dataset_name = creator.create_dataset(config)
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Evaluation
  env:
    LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
    LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    python scripts/run_comprehensive_evaluation.py \
      --dataset health-assistant-eval-smoke-test \
      --dry-run
```

### Pre-deployment Checks
```bash
#!/bin/bash
# run_evaluation_check.sh

python scripts/run_comprehensive_evaluation.py \
  --dataset health-assistant-eval-smoke-test \
  --dry-run

if [ $? -ne 0 ]; then
  echo "Evaluation failed"
  exit 1
fi
```

## Future Enhancements

- [ ] Automated failure analysis
- [ ] Regression detection between versions
- [ ] Performance benchmarking
- [ ] Cost tracking per configuration
- [ ] Human-in-the-loop validation
- [ ] Automated dataset generation from failures
- [ ] Cross-model comparison (Claude vs GPT)
- [ ] Multi-language support testing

## API Reference

See [Langfuse Cheatsheet](./langfuse_cheatsheet.md) for detailed API reference and code examples.