# Agent Comparison Guide: When to Use Each Agent

This guide helps you understand when to use each AI agent in the health assistant system.

---

## Agent Summary: When to Use Each

### **Agent 97** (Patient Education Assistant)
**Use when:** A **patient** needs general health education and information

**Purpose:** Provides educational health information to patients in accessible, non-technical language

**Key features:**
- General health topics explained in plain language
- Evidence-based information from trusted medical sources
- Canadian/Ontario sources prioritized (Ontario Health, Health Canada, PHAC)
- Safety guardrails to prevent diagnosis/prescribing
- Emergency detection and redirection
- Web search for current health information

**Example queries:**
- "What are the symptoms of diabetes?"
- "How do vaccines work?"
- "What should I know about high blood pressure?"

**NOT for:** Medical diagnosis, treatment plans, medication dosing, or individualized medical advice

---

### **Dr. OFF** (Ontario Finance & Formulary)
**Use when:** A **clinician** needs guidance on Ontario healthcare billing, drug coverage, or device funding

**Purpose:** Specialized AI for navigating Ontario's healthcare financing and coverage landscape

**Key features:**
- **OHIP billing codes** and fee schedules
- **Ontario Drug Benefit (ODB)** formulary coverage and Limited Use criteria
- **Assistive Devices Program (ADP)** funding and eligibility
- Generic alternatives and cost-effective prescribing
- Prior authorization requirements

**Example queries:**
- "What's the billing code for a comprehensive assessment?" (OHIP)
- "Is rosuvastatin covered by ODB? What's the cheapest alternative?" (Drugs)
- "Can my patient get funding for a CPAP machine?" (ADP)
- "What are the Limited Use criteria for statins?"

**NOT for:** Clinical practice guidance, medical protocols, or treatment decisions

---

### **Dr. OPA** (Ontario Practice Advice)
**Use when:** A **clinician** needs Ontario-specific clinical practice guidance and regulatory information

**Purpose:** Specialized AI for Ontario healthcare practice guidance from trusted authorities

**Key features:**
- **CPSO** regulatory policies and professional expectations
- **Ontario Health** clinical programs, screening guidelines, quality standards
- **CEP** clinical decision support tools and algorithms
- **PHO** infection prevention and control guidance
- **Choosing Wisely Canada** recommendations to avoid unnecessary care
- Program eligibility and referral pathways

**Example queries:**
- "What are the CPSO expectations for prescribing opioids?" (Regulation)
- "Is a 55-year-old eligible for breast cancer screening?" (Programs)
- "What are the quality standards for heart failure care?" (Quality Standards)
- "What does Choosing Wisely say about imaging for low back pain?" (Evidence-based care)
- "What are the hand hygiene protocols for my clinic?" (IPAC)

**NOT for:** Billing/financial questions or general patient education

---

### **The Chief** (Clinical Intelligence Orchestrator)
**Use when:** A **clinician** has a **complex clinical question** that requires insights from multiple domains (practice guidance + coverage + medical evidence)

**Purpose:** Intelligent orchestrator inspired by Microsoft's MAI-DxO that coordinates between Dr. OPA, Dr. OFF, and Agent 97 to provide comprehensive multi-domain clinical guidance

**Key features:**
- **Automatically routes queries** to appropriate specialist agents
- **Synthesizes insights** from multiple agents into cohesive narrative
- **Preserves all citations** from individual agents
- **Highlights conflicts** between different sources
- **Emphasizes critical safety** and regulatory information
- Uses **GPT-4o** for sophisticated orchestration

**Example queries (complex scenarios requiring multiple perspectives):**
- "72-year-old with newly diagnosed type 2 diabetes, BMI 32, limited income. What are CPSO documentation requirements, ODB coverage for metformin and newer drugs, and evidence-based management?"
- "55-year-old with acute chest pain. Need Ontario cardiac pathway, OHIP billing codes for ECG/troponins, and current ACS guidelines."
- "Young adult with suicidal ideation. What are mandatory reporting requirements, OHIP billing codes for psych assessment, and crisis intervention protocols?"

**The Chief consults:**
- **Dr. OPA** → for regulatory/policy questions
- **Dr. OFF** → for cost/coverage questions
- **Agent 97** → for general medical knowledge
- Then **synthesizes all responses** into comprehensive guidance

**NOT for:** Simple single-domain questions (use the individual agents directly instead)

---

## Quick Decision Guide

| User Type | Need | Use This Agent |
|-----------|------|----------------|
| **Patient** | Health education and information | **Agent 97** |
| **Clinician** | OHIP billing / ODB coverage / ADP funding | **Dr. OFF** |
| **Clinician** | Clinical practice guidance / CPSO policies / screening programs | **Dr. OPA** |
| **Clinician** | Complex scenario requiring practice guidance + coverage + medical evidence | **The Chief** |

---

## Detailed Comparison Table

| Feature | Agent 97 | Dr. OFF | Dr. OPA | The Chief |
|---------|----------|---------|---------|-----------|
| **Target User** | Patients | Clinicians | Clinicians | Clinicians |
| **Primary Focus** | Patient education | Healthcare financing | Clinical practice guidance | Multi-domain orchestration |
| **Data Sources** | 97 trusted medical sources | OHIP, ODB, ADP databases | CPSO, Ontario Health, CEP, PHO, Choosing Wisely | All specialist agents |
| **Model** | Claude 3.5 Sonnet | GPT-4o-mini | GPT-4o-mini | GPT-4o |
| **Safety Guardrails** | Yes (input/output) | No (financial data) | No (professional use) | Yes (inherited from Agent 97) |
| **Geographic Focus** | Canadian/Ontario priority | Ontario only | Ontario only | Ontario only |
| **Response Style** | Accessible, non-technical | Comprehensive financial detail | Professional clinical guidance | Synthesized multi-perspective |
| **Streaming Support** | Yes | Yes | Yes | Yes |
| **Langfuse Tracing** | Yes | Yes | Yes | Yes |
| **MCP Tools** | web_search, web_fetch | schedule_get, odb_get, adp_get | opa_policy_check, opa_program_lookup, opa_ipac_guidance, opa_clinical_tools, opa_quality_standards, opa_choosing_wisely | Orchestrates all MCP tools via sub-agents |

---

## Workflow Recommendations

### For Simple Questions
**Use individual agents directly:**
- Billing code lookup → **Dr. OFF**
- CPSO policy check → **Dr. OPA**
- Patient education → **Agent 97**

### For Complex Clinical Scenarios
**Use The Chief when you need:**
- Insights from multiple domains (clinical + regulatory + financial)
- Comprehensive guidance synthesized from all sources
- Coordination between practice guidelines, coverage policies, and evidence

**Example:** Instead of calling Dr. OPA for CPSO requirements, then Dr. OFF for billing codes, then Agent 97 for treatment evidence, ask **The Chief** one comprehensive question and get all perspectives synthesized.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        The Chief                            │
│                (Clinical Intelligence Orchestrator)          │
│                                                             │
│  Analyzes query → Routes to specialists → Synthesizes       │
└──────────────┬──────────────┬──────────────┬───────────────┘
               │              │              │
       ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼────────┐
       │   Dr. OPA    │ │ Dr. OFF  │ │   Agent 97    │
       │  (Practice)  │ │(Finance) │ │  (Education)  │
       └──────┬───────┘ └────┬─────┘ └───────┬───────┘
              │              │                │
         MCP Tools      MCP Tools        MCP Tools
         (CPSO, CEP,    (OHIP, ODB,     (web_search,
          PHO, OH)       ADP)            web_fetch)
```

---

## Additional Resources

- [Agent 97 Documentation](./agent_97_documentation.md)
- [Dr. OFF Documentation](./dr_off_agent/dr_off_agent.md)
- [Dr. OPA Documentation](./dr_opa_agent/dr_opa_agent.md)
- [The Chief Implementation](../../src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py)

---

**Last Updated:** 2025-01-09
