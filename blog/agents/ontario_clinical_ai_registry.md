# Coaching the Machine, Part 2: Building Ontario's Clinical AI Agent Registry

**By Stewart McKendry, Will Falk, and Dr. Keith Thompson**

---

## From Patient Assistant to Clinical Team

In [Part 1](https://coachingthemachine.substack.com/p/white-coat-black-box-helping-patients) of this series, we introduced **My Health Assistant**—an AI tool designed to help patients ask smarter questions by drawing only from 97 vetted medical sources. The goal was clear: provide reliable health information while respecting the boundaries between education and diagnosis.

But as we built that patient-facing assistant, a larger question emerged: **What happens when we flip the perspective and build AI assistants for the clinicians themselves?**

Not a single all-knowing AI doctor, but a *team* of specialized agents—each with deep expertise in a specific domain, working together like residents supervised by a chief resident. Each agent grounded in trusted data. Each one auditable, improvable, and ultimately accountable to the physician making the final call.

This is Part 2: **Building Ontario's Clinical AI Agent Registry**.

---

## Inspiration: Microsoft's Diagnostic Orchestrator and Google's Health AI Agent

The idea of coordinating multiple AI agents isn't science fiction—it's happening now.

Microsoft recently published research on **MAI-DxO (Medical AI Diagnostic Orchestrator)**, an AI system that coordinates multiple specialized agents to solve complex diagnostic cases. On challenging *New England Journal of Medicine* case studies, MAI-DxO correctly diagnosed 85.5% of cases—**more than four times higher than experienced physicians working alone**. The system works by having an orchestrator model coordinate specialist agents, iteratively ordering tests and refining diagnostic reasoning.

Google has taken a similar approach with their **Health AI Agent** concept, where an orchestrator coordinates three specialized agents: a **Data Science Agent** (analyzes variables and labs), a **Domain Expert Agent** (grounds in verified medical knowledge), and a **Health Coach Agent** (guides goals and lifestyle change). The orchestrator maintains memory, updates context, and synthesizes recommendations collaboratively.

Both approaches share a critical insight: **the future of clinical AI isn't a single omniscient model—it's a coordinated team of specialists, each excellent in their domain, orchestrated to provide comprehensive, auditable guidance.**

We asked ourselves: **What would this look like in Ontario?**

Not just for rare diagnostic puzzles, but for the daily questions clinicians face: *Is this drug covered? What does the CPSO say about virtual care documentation? What's the latest evidence on SGLT2 inhibitors? Can I bill this code?*

So we built a demonstration: four AI agents—three specialists and one orchestrator—working together as an **Ontario Clinical AI Agent Registry**.

---

## Meet the Registry: Four Ontario Clinical AI Agents

Think of this as a team of digital residents, each specialized in a different domain, coordinated by a Chief Resident who knows when to consult whom.

---

### 🧩 Chief Resident (Clinical Intelligence Orchestrator)

**Mission:** Coordinate Dr. OPA, Dr. OFF, and Agent 97 to provide comprehensive, Ontario-contextualized clinical guidance for complex diagnostic and treatment planning questions.

**What Chief Resident Does:**
The orchestrator doesn't have its own knowledge base—it **routes queries to specialist agents** and synthesizes their responses:
1. **Analyzes query intent:** Does this need evidence? Coverage info? Regulatory guidance?
2. **Calls agents in parallel:** Consults 2-3 specialists simultaneously
3. **Internal reasoning:** Summarizes findings, identifies conflicts, resolves contradictions
4. **Synthesizes response:** Combines evidence (Agent 97), regulations (Dr. OPA), and coverage (Dr. OFF) into cohesive guidance with all citations preserved

**Example Question:**
> *"72-year-old patient with newly diagnosed type 2 diabetes, BMI 32, limited income. What are CPSO documentation requirements, ODB coverage options for metformin and newer diabetes drugs, and evidence-based management approaches?"*

**Chief Resident's Process:**
1. **Reasoning:** Needs evidence (Agent 97), quality standards (Dr. OPA), and formulary (Dr. OFF)
2. **Calls (parallel):**
   - Agent 97 → Latest diabetes management guidelines (ADA, Diabetes Canada)
   - Dr. OPA → Ontario Health Diabetes Quality Standard + CPSO documentation expectations
   - Dr. OFF → ODB coverage for metformin, SGLT2i, GLP-1 agonists (with Limited Use criteria and costs)
3. **Synthesis:** Combines global evidence with Ontario-specific coverage and regulatory context
4. **Output:** Comprehensive treatment plan with clinical approach, coverage details, and documentation requirements—with 8-20 mixed citations

**[📹 Demo Video 1: Chief Resident in Action]**
Watch the orchestrator coordinate all three specialists to answer a complex anemia workup question—from agent registry to live trace to synthesized response.

*Query: "55-year-old with fatigue and low hemoglobin. What's the diagnostic workup for anemia, OHIP codes for iron studies and B12, and when to refer to hematology based on current evidence?"*

---

### 🧾 Dr. OFF (Ontario Finance & Formulary)

**Mission:** Help clinicians navigate Ontario's healthcare financing maze—OHIP billing, ODB drug coverage, and Assistive Devices Program (ADP) funding—critical for treatment planning and patient access.

**What Dr. OFF Knows:**
- **8,401 ODB-listed drugs** (DINs, Limited Use criteria, generic alternatives)
- **4,166 OHIP billing codes** (fees, requirements, frequency limits)
- **11 ADP device categories** (funding percentages, eligibility)
- All embedded in 3,951 searchable chunks from official sources

**Example Questions:**
- *"Is Ozempic covered by ODB for weight loss, or only for diabetes? What are the Limited Use criteria?"*
- *"What's the OHIP code for a comprehensive geriatric assessment and what documentation is required?"*
- *"Patient needs assistive devices for mobility. What's covered by ADP and what will they pay out of pocket?"*

**Clinical Use Case:** When prescribing medications or ordering diagnostics, Dr. OFF helps you understand coverage constraints upfront—preventing delays and helping patients access needed treatments.

**[📹 Demo Video 2: Dr. OFF Coverage Comparison]**
See Dr. OFF search the ODB formulary in real-time to compare statin coverage, Limited Use criteria, and costs.

*Query: "Compare ODB coverage for rosuvastatin vs atorvastatin for a patient with diabetes and high LDL—show me brand vs generic options with costs."*

---

### ⚖️ Dr. OPA (Ontario Practice Advisor)

**Mission:** Provide real-time guidance on Ontario practice standards, regulatory requirements, infection control, and clinical pathways—ensuring diagnostic and treatment plans align with provincial standards and avoid unnecessary care.

**What Dr. OPA Knows:**
- **CPSO policies** (366 chunks) - Professional obligations, consent, virtual care, prescribing
- **Public Health Ontario IPAC guidelines** (132 chunks) - Infection control, PPE, outbreak management
- **Centre for Effective Practice (CEP) tools** (639 chunks) - Clinical decision support algorithms, diagnostic tools, treatment protocols
- **Ontario Health Quality Standards** (340 chunks) - Disease-specific quality standards (diabetes, hypertension, COPD, mental health)
- **Choosing Wisely recommendations** (544 chunks) - Avoiding unnecessary tests, imaging, and treatments
- Total: 2,021 searchable chunks from trusted Ontario authorities

**Example Questions:**
- *"What are the Ontario Health quality standards for managing hypertension? What's the treatment algorithm?"*
- *"Patient with recurrent UTIs—does Choosing Wisely recommend routine imaging?"*
- *"What PHO IPAC guidance applies to managing TB exposure in my clinic?"*

**Clinical Use Case:** When developing treatment plans, Dr. OPA ensures you're following provincial quality standards, using evidence-based clinical tools, and avoiding unnecessary interventions flagged by Choosing Wisely.

**[📹 Demo Video 3: Dr. OPA Quality Standards & Clinical Tools]**
Watch Dr. OPA retrieve Ontario Health quality standards, CEP diagnostic tools, and Choosing Wisely guidance for COPD management.

*Query: "Patient with suspected COPD. What are the Ontario diagnostic criteria, quality standards for management, and CEP tools available?"*

---

### 📚 Agent 97 (Evidence-Based Clinical Search)

**Mission:** Provide rapid access to current medical evidence from 97 trusted sources to inform differential diagnosis, treatment selection, and clinical decision-making.

**What Agent 97 Knows:**
- **Medical journals:** NEJM, Lancet, JAMA, BMJ, Nature Medicine, Cell
- **Clinical guidelines:** NICE, AHA/ACC, ADA, IDSA, ASCO, Canadian Cardiovascular Society
- **Academic medical centers:** Mayo, Cleveland Clinic, Johns Hopkins, Mass General
- **Health authorities:** WHO, CDC, NIH, Health Canada, FDA
- **Canadian healthcare:** Ontario Health, CPSO, CMA, CFPC
- **Evidence databases:** PubMed, Cochrane, UpToDate, DynaMed

**Example Questions:**
- *"Patient with new-onset hypertension and proteinuria. What's the diagnostic workup and when do I refer to nephrology?"*
- *"Latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction—who benefits most?"*
- *"Comparing biologic options for moderate-to-severe rheumatoid arthritis—what does the evidence say about efficacy and safety?"*

**Key Advantage:** Always current information (no need to re-embed). Real-time search across all 97 trusted domains to support evidence-based diagnostic and therapeutic decisions.

**Clinical Use Case:** When facing diagnostic uncertainty or treatment decisions, Agent 97 retrieves current evidence from authoritative sources—helping you apply the latest guidelines to your patient's specific presentation.

**[📹 Demo Video 4: Agent 97 Evidence Search]**
See Agent 97 search across 97 medical sources in real-time—from query to cited evidence to OpenAI trace.

*Query: "What are current best practices for diagnosing and managing mild cognitive impairment? When should I refer to neurology?"*

---

## Why This Matters: Rethinking Clinical Decision Support

Clinical Decision Support (CDS) tools have been around for decades—pop-up alerts in EMRs, formulary lookups, outdated PDF guidelines buried in bookmarks. They're fragmented, interruptive, and often ignored because they don't understand context.

**This is different.** Instead of interrupting your workflow, these agents work like consultants. Ask a question naturally, get a synthesized answer with citations in 20-45 seconds. The agents don't make decisions—they retrieve, reconcile, and present. You retain full clinical authority.

The promise: **enabling clinicians to practice at the top of their license by offloading the cognitive load of navigating fragmented information systems.** Like having a team of residents who've already done the literature review, checked the formulary, and read the CPSO policies before rounds.

---

## Building from the Ground Up: Data → Tools → Agents

This wasn't a quick ChatGPT wrapper. Each agent was built methodically from the data up—and unlike standard AI chat, these agents make **multiple LLM calls and tool invocations**, reasoning through problems to reach higher-quality answers. This increases response time (20-45 seconds for orchestrated queries) but dramatically improves accuracy and completeness.

### **🧩 Chief Resident (Orchestrator Layer)**
Clinician Query → Analyze Intent → Call Specialists in Parallel
[Agent 97] [Dr. OPA] [Dr. OFF]
Internal Reasoning → Resolve Conflicts → Synthesize Response

⬇️

### **🤖 Specialist Agents (Agent Layer)**
Reasoning workflow: **PLAN** → **RETRIEVE** → **SELF-CHECK** → **SYNTHESIZE**

Each agent is **non-deterministic**—it reasons through the query, decides which tools to call, evaluates completeness, and iterates if needed. Minimum 2 tool calls per query to ensure comprehensive answers. Conversation memory enables follow-up questions.

⬇️

### **🔧 Custom Tools (MCP Layer)**
**Smart retrieval tools that connect agents to data.** These aren't simple database lookups—they perform semantic search, auto-classify query intent, adjust retrieval scope, and assemble context intelligently:

- **Dr. OPA:** 8 tools (policy_check, ipac_guidance, quality_standards, clinical_tools, choosing_wisely, etc.)
- **Dr. OFF:** 3 tools (schedule_get, odb_get, adp_get)
- **Agent 97:** 1 tool (clinician_search via Claude API with real-time web search)

⬇️

### **📚 Knowledge Bases (Data Layer)**
**Two types of databases serving different needs:**

**Vector/Embedding Databases (ChromaDB):** For unstructured text—policies, guidelines, formulary descriptions. Enables semantic search ("find me guidance on virtual care consent" → retrieves relevant CPSO policy sections).
- **Dr. OPA:** 2,021 chunks (CPSO, PHO, CEP, Quality Standards, Choosing Wisely)
- **Dr. OFF:** 3,951 chunks (OHIP Schedule, ODB Formulary, ADP)

**Structured Data (SQL):** For precise lookups—DIN numbers, billing codes, fee amounts. Enables exact matching and filtering.
- Drug Identification Numbers (DINs), OHIP codes, Limited Use criteria

**Real-Time Search (Agent 97):** No embedding—searches 97 trusted medical domains in real-time for always-current evidence.

---

**Tech Stack:** OpenAI Agents SDK (orchestration, reasoning), Claude 3.5 Sonnet (Agent 97 search), ChromaDB (semantic embeddings), SQLite (structured data), FastAPI (web endpoints), Langfuse/Logfire (observability).

---

## Where We Go From Here: A Certified Agent Registry for Ontario

This demonstration is just the beginning. Imagine scaling this concept:

### A Provincial AI Agent Registry

**Inspired by OntarioMD's AI Scribe Program**, which certifies clinical AI products for use in Ontario primary care through vendor evaluation and a "Vendor of Record" list, we envision a similar registry for clinical AI agents:

**What It Could Look Like:**
1. **Agent Evaluation:** Each agent undergoes standardized testing
   - **Clinical accuracy:** Benchmarked against physician gold standards
   - **Citation quality:** Sources verified, bias assessed
   - **Privacy compliance:** Data handling, audit trails
   - **Fairness testing:** Evaluated for equity across patient populations

2. **Certification Levels:**
   - **Certified:** Tested, approved for clinical use
   - **Experimental:** In evaluation, use with caution
   - **Versioned:** `Dr. OPA v2.1` (clear lineage, changelog)

3. **Organizational Customization:**
   - **Hospital-specific agents:** "SickKids Formulary Agent" (pediatric drug database)
   - **Specialty-specific agents:** "Ortho Practice Agent" (joint replacement pathways, prosthetic coverage)
   - **Regional agents:** "Thunder Bay Referral Agent" (Northern Ontario specialist access)

4. **Continuous Improvement:**
   - **Feedback loops:** Clinicians flag errors, upvote helpful responses
   - **Update cycles:** Quarterly re-embedding as guidelines change
   - **Audit trails:** Every agent response traceable to source documents

5. **Interoperability:**
   - **EMR integration:** Query agents directly from patient chart
   - **Standardized APIs:** Agents callable from any clinical workflow
   - **Orchestrator flexibility:** Swap specialists based on context (e.g., palliative care vs acute care teams)

### Why This Matters

**The registry model ensures:**
- **Trust:** Only certified agents with validated data sources
- **Transparency:** Clear provenance from query → agent → tool → source document
- **Accountability:** Trace IDs link every response to feedback and improvement
- **Modularity:** Agents can be added, updated, or retired without breaking the system
- **Governance:** Clinical oversight, not tech companies, determines what's safe to deploy

**The alternative—unregulated, black-box AI in clinical workflows—is already happening.** A registry provides the guardrails.

---

## The Data Quality Challenge: RAG-Readiness

Building these agents taught us something critical: **AI agents are only as good as their data sources.**

Our agents work well because sources like CPSO policies (clean HTML), ODB Formulary (searchable database), and Ontario Health Quality Standards (structured PDFs) were relatively machine-readable. But we encountered challenges:
- **Image-based PDFs** where tables couldn't be extracted
- **Legacy websites** with nested tables and inconsistent formatting
- **Fragmented information** scattered across multiple pages without clear structure

This matters because **Retrieval-Augmented Generation (RAG)**—the backbone of these agents—only works when data is machine-readable, semantically rich, and properly structured.

Think of it as **WCAG (Web Content Accessibility Guidelines) for the AI era**: making information accessible not just to humans, but to the AI agents that increasingly mediate access to knowledge.

**For Ontario to scale trusted AI agents across health, housing, education, and services, public websites need:**
- Clean semantic HTML (proper headings, metadata)
- Structured data feeds (APIs, not just PDFs)
- Stable URLs for citations
- Update timestamps and version control

Without this infrastructure, even the best AI agents will miss critical information, cite outdated content, or generate incomplete answers. The registry we've built demonstrates what's possible—but it also reveals the data infrastructure gap that needs addressing.

---

## What This Means In Practice

Imagine a family physician mid-morning, seeing a 68-year-old patient with newly diagnosed atrial fibrillation. Instead of toggling between UpToDate, the ODB formulary website, CPSO virtual care guidelines, and trying to remember if there's an Ontario stroke prevention pathway, she asks Chief Resident:

> *"New AFib, CHADS score 3. What's the evidence on DOACs vs warfarin, ODB coverage for apixaban with Limited Use criteria, and do I need specific consent documentation for anticoagulation?"*

In 30 seconds: current evidence from cardiology guidelines, ODB coverage details with generic alternatives, CPSO consent expectations, and Ontario Health quality standards—all cited, all synthesized. She prescribes confidently, knowing the patient can afford it, documentation meets regulatory standards, and the decision aligns with best evidence.

That means fewer calls to the formulary hotline, fewer prescriptions rejected at the pharmacy, fewer documentation gaps flagged in audits. Patients get the right treatment faster. Clinicians spend less time navigating bureaucracy and more time on clinical judgment and conversations that matter.

**This is clinical decision support reimagined:** not interrupting your workflow with pop-ups, but working alongside you like a well-prepared resident team.

---

**If you're a clinician in Ontario and want to try these agents or provide feedback**, reach out to the authors. Your experience will help shape safer, more useful AI agents that respect the judgment clinicians bring—while removing the friction that buries it.

---

*For more on Coaching the Machine, subscribe at [coachingthemachine.substack.com](https://coachingthemachine.substack.com).*
