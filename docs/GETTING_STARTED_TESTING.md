# Getting Started with AI Clinical Assistants - Testing Guide

Welcome! This guide will help you get started testing our AI clinical decision support agents for your Quality Improvement project.

## What Are These Agents?

Four specialized AI assistants designed to support Ontario clinicians:

### **Agent 97** - Medical Knowledge Assistant
- Accesses 97 trusted medical sources (PubMed, UpToDate, clinical guidelines)
- Provides evidence-based clinical information with citations
- **Use for:** General medical knowledge, differential diagnoses, treatment guidelines, clinical pathways

### **Dr. OFF** - Ontario Finance & Formulary
- OHIP billing codes and fee schedules
- ODB drug coverage and Limited Use criteria
- ADP device funding eligibility
- **Use for:** "What's the billing code?", "Is this drug covered?", "Can my patient get funding?"

### **Dr. OPA** - Ontario Practice Advice
- CPSO regulatory policies and expectations
- Ontario Health clinical programs and quality standards
- CEP clinical decision tools
- PHO infection control guidance
- Choosing Wisely recommendations
- **Use for:** "What are the CPSO requirements?", "Is my patient eligible for screening?", "What does Choosing Wisely say?"

### **The Chief** - Clinical Intelligence Orchestrator
- **Diagnostic decision support** - coordinates all three agents above
- Synthesizes multi-domain insights (clinical + regulatory + financial)
- **Use for:** Complex clinical scenarios requiring comprehensive guidance
- **Best for diagnostics:** Combines evidence-based medicine, Ontario pathways, and coverage in one response

## Three Ways to Test

### 1. **Web UI** (Easiest - Start Here!)
🔗 **https://health-assistant-git-main-stewart-mckendrys-projects.vercel.app/agents/**

- Test all four agents through browser interface
- Real-time streaming responses
- See citations and tool calls
- No setup required

### 2. **Terminal/Command Line** (Most Flexible)
Clone repository and run test scripts with custom queries

### 3. **Langfuse Evaluation** (Advanced - Next Session)
- Create datasets of clinical scenarios
- Run batch evaluations
- Track performance metrics
- Compare agent outputs

---

## Setting Up Terminal Testing

### Step 1: Clone the Repository
```bash
cd ~
git clone https://github.com/stewmckendry/health_assistant.git
cd health_assistant
```

### Step 2: Activate Python Environment
```bash
source ~/spacy_env/bin/activate
```

### Step 3: Test with Your Own Queries

**Test The Chief (Diagnostic Decision Support):**
```bash
python scripts/test_agents.py \
  --agent chief \
  --queries "72F with new onset dyspnea, bilateral leg edema, JVP elevated. Need diagnostic workup, OHIP codes, and evidence-based management."
```

**Test Dr. OPA (Practice Guidance):**
```bash
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "What are the CPSO requirements for virtual care documentation?"
```

**Test Dr. OFF (Billing & Coverage):**
```bash
python scripts/test_agents.py \
  --agent dr_off \
  --queries "Patient needs rosuvastatin. What are ODB coverage options and cost differences?"
```

**Test Agent 97 (Medical Knowledge):**
```bash
python scripts/test_agents.py \
  --agent agent_97 \
  --queries "What are the diagnostic criteria for acute coronary syndrome?"
```

### Test Multiple Queries at Once
```bash
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "Query 1 here" "Query 2 here" "Query 3 here"
```

---

## Understanding Test Results

### What You'll See
- **Query:** Your clinical question
- **Response:** Full agent answer with citations
- **Confidence:** Quality score (0-1)
- **Response Time:** How long it took
- **Citations:** Evidence sources used
- **Tool Calls:** Which tools the agent used

### Good Signs ✓
- **Confidence > 0.7** - High quality response
- **Citations > 0** - Evidence-based answer
- **Response time < 10s** - Acceptable performance

### Results Saved To:
```
eval/results/agent_tests/{agent}_{timestamp}.json
```

You can review the full JSON output with all details.

---

## Clinical Scenarios to Test

### Diagnostic Support (Use The Chief)
```bash
python scripts/test_agents.py \
  --agent chief \
  --queries \
    "65M chest pain radiating to left arm, diaphoretic. Need cardiac pathway + OHIP codes + ACS guidelines" \
    "55F with headache, fever, photophobia. Need diagnostic approach + billing codes + meningitis protocol"
```

### Practice Guidance (Use Dr. OPA)
```bash
python scripts/test_agents.py \
  --agent dr_opa \
  --queries \
    "What are CPSO expectations for prescribing opioids in chronic pain?" \
    "Is a 52-year-old woman eligible for breast cancer screening?" \
    "What do quality standards say about diabetes management?"
```

### Coverage & Billing (Use Dr. OFF)
```bash
python scripts/test_agents.py \
  --agent dr_off \
  --queries \
    "What's the billing code for comprehensive geriatric assessment?" \
    "Is metformin covered by ODB? What about newer diabetes drugs?" \
    "Can my low-income patient get funding for a CPAP machine?"
```

### Medical Knowledge (Use Agent 97)
```bash
python scripts/test_agents.py \
  --agent agent_97 \
  --queries \
    "What are the latest hypertension management guidelines?" \
    "Differential diagnosis for acute abdominal pain in elderly" \
    "Treatment approach for community-acquired pneumonia"
```

---

## Quick Reference

| What You Want to Test | Use This Agent | Example Query |
|-----------------------|----------------|---------------|
| **Diagnostic workup** | The Chief | "65M chest pain, need cardiac pathway + OHIP codes + ACS guidelines" |
| **Billing codes** | Dr. OFF | "What's the code for mental health assessment?" |
| **Drug coverage** | Dr. OFF | "Is empagliflozin covered for heart failure?" |
| **Device funding** | Dr. OFF | "Can patient get CPAP funding?" |
| **CPSO requirements** | Dr. OPA | "What are prescribing requirements for stimulants?" |
| **Screening programs** | Dr. OPA | "Is 52F eligible for mammography?" |
| **Quality standards** | Dr. OPA | "What are Ontario standards for diabetes care?" |
| **Unnecessary tests** | Dr. OPA | "Choosing Wisely on head CTs for minor head injury?" |
| **Clinical guidelines** | Agent 97 | "Latest hypertension management guidelines?" |

---

## Langfuse Access

You've been added to Langfuse for observability:
- **Browse traces** - See detailed execution logs of agent queries
- **Review performance** - Response times, tool usage, citations
- **Explore datasets** - Pre-configured test scenarios
- **Next session:** I'll show you how to create evaluation datasets and run batch tests

🔗 **Langfuse Dashboard:** Check your email for invite link

---

## For Your QI Project

**Recommended Testing Approach:**

1. **Week 1:** Test via Web UI
   - Get familiar with each agent
   - Try 10-15 clinical scenarios relevant to your practice
   - Note which agents are most useful

2. **Week 2:** Terminal testing with custom queries
   - Create list of common clinical questions from your rotation
   - Test all agents systematically
   - Document accuracy and usefulness

3. **Week 3:** Langfuse evaluation (we'll do together)
   - Build dataset of validated clinical scenarios
   - Run batch evaluations
   - Measure performance metrics

**Metrics to Track:**
- Response accuracy (clinical correctness)
- Citation quality (trusted sources)
- Completeness (all aspects addressed)
- Usefulness (would you use in practice?)
- Response time (clinical workflow)

---

## Need Help?

- **More testing options:** `tests/QUICK_REFERENCE.md`
- **Full documentation:** `tests/README_AGENT_TESTING.md`
- **Agent comparison:** `docs/agents/agent_comparison_guide.md`
- **Questions?** Reach out anytime!

---

**Next Steps:**
1. ✅ Start with Web UI testing
2. ✅ Clone repo and test with your own queries
3. ✅ Document findings for QI project
4. 📅 Schedule session for Langfuse evaluation setup

Good luck with testing! Looking forward to your clinical insights on how these agents can support diagnostic decision-making and clinical workflow.
