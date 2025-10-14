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

---

## Why This Matters: Rethinking Clinical Decision Support

Clinical Decision Support (CDS) tools have been around for decades—pop-up alerts in EMRs, formulary lookups, outdated PDF guidelines buried in bookmarks. They're fragmented, interruptive, and often ignored because they don't understand context.

What if CDS wasn't an interruption but a conversation? What if you could ask:

> *"I have a 72-year-old patient with newly diagnosed type 2 diabetes, BMI 32, and limited income. What are the CPSO documentation requirements, ODB coverage options for metformin and newer diabetes drugs, and evidence-based management approaches?"*

And instead of juggling five browser tabs, three PDFs, and a phone call to the formulary hotline, you get a synthesized answer—with citations—in 30 seconds?

**This is the promise: enabling clinicians to practice at the top of their license by offloading the cognitive load of navigating fragmented information systems.**

The user experience feels like having a conversation with the knowledge bases themselves—asking questions naturally and getting clear, cited answers. Like consulting a colleague who's memorized every policy, guideline, and formulary, but can actually explain it clearly.

The agents don't make decisions. They retrieve, reconcile, and present. The clinician retains full authority. The agents are transparent, traceable, and improvable as guidelines evolve.

---

## Meet the Registry: Four Ontario Clinical AI Agents

We built four agents—three specialists and one orchestrator—to demonstrate what a registry of certified, Ontario-contextualized AI agents might look like.

---

### 🧾 Dr. OFF (Ontario Finance & Formulary)

**Mission:** Help clinicians navigate Ontario's healthcare financing maze—OHIP billing, ODB drug coverage, and Assistive Devices Program (ADP) funding.

**What Dr. OFF Knows:**
- **8,401 ODB-listed drugs** (DINs, Limited Use criteria, generic alternatives)
- **4,166 OHIP billing codes** (fees, requirements, frequency limits)
- **11 ADP device categories** (funding percentages, eligibility)
- All embedded in 3,951 searchable chunks from official sources

**Example Questions:**
- *"Is Ozempic covered by ODB for weight loss, or only for diabetes?"*
- *"What's the OHIP code for a comprehensive geriatric assessment?"*
- *"Can my patient get ADP funding for a power wheelchair? What's the cost breakdown?"*

**[📹 Demo Video Placeholder 1]**
*Suggested demo: "Compare ODB coverage for rosuvastatin vs atorvastatin for a patient with diabetes and high LDL—show me brand vs generic options with costs."*

---

### ⚖️ Dr. OPA (Ontario Practice Advisor)

**Mission:** Provide real-time guidance on Ontario practice standards, regulatory requirements, infection control, and clinical pathways.

**What Dr. OPA Knows:**
- **CPSO policies** (366 chunks) - Professional obligations, consent, virtual care, prescribing
- **Public Health Ontario IPAC guidelines** (132 chunks) - Infection control, PPE, outbreak management
- **Centre for Effective Practice (CEP) tools** (57 chunks) - Clinical decision support algorithms
- **Ontario Health Quality Standards** (340 chunks) - Diabetes, hypertension, mental health, screening
- **Choosing Wisely recommendations** (544 chunks) - Avoiding unnecessary tests and overuse
- Total: 1,439 searchable chunks from trusted Ontario authorities

**Example Questions:**
- *"What are the CPSO expectations for documenting virtual care consent?"*
- *"What are the PHO IPAC requirements for N95 fit testing?"*
- *"Does Choosing Wisely have recommendations about ordering vitamin D levels?"*

**[📹 Demo Video Placeholder 2]**
*Suggested demo: "I'm starting virtual care visits. What are the CPSO documentation requirements, and what consent do I need?"*

---

### 📚 Agent 97 (Evidence-Based Clinical Search)

**Mission:** Provide rapid access to current medical evidence from 97 trusted sources for clinical decision-making.

**What Agent 97 Knows:**
- **Medical journals:** NEJM, Lancet, JAMA, BMJ, Nature Medicine, Cell
- **Clinical guidelines:** NICE, AHA/ACC, ADA, IDSA, ASCO, Canadian Cardiovascular Society
- **Academic medical centers:** Mayo, Cleveland Clinic, Johns Hopkins, Mass General
- **Health authorities:** WHO, CDC, NIH, Health Canada, FDA
- **Canadian healthcare:** Ontario Health, CPSO, CMA, CFPC
- **Evidence databases:** PubMed, Cochrane, UpToDate, DynaMed

**Example Questions:**
- *"What are the current guidelines for hypertension management in adults?"*
- *"What's the latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?"*
- *"What are the diagnostic criteria for rheumatoid arthritis?"*

**Key Advantage:** Always current information (no need to re-embed). Real-time search across all 97 trusted domains.

**[📹 Demo Video Placeholder 3]**
*Suggested demo: "What's the latest evidence on using GLP-1 agonists for heart failure? Compare efficacy and safety."*

---

### 🧩 Chief Resident (Clinical Intelligence Orchestrator)

**Mission:** Coordinate Dr. OPA, Dr. OFF, and Agent 97 to provide comprehensive, Ontario-contextualized clinical guidance for complex questions.

**What Chief Resident Does:**
The orchestrator doesn't have its own knowledge base—it **routes queries to specialist agents** and synthesizes their responses:
1. **Analyzes query intent:** Does this need evidence? Coverage info? Regulatory guidance?
2. **Calls agents in parallel:** Consults 2-3 specialists simultaneously (using OpenAI Agents SDK `as_tool()` pattern)
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
4. **Output:** Comprehensive answer organized by importance (clinical approach → coverage → documentation) with 8-20 mixed citations

---

## Building from the Ground Up: Data → Tools → Agents

This wasn't a quick ChatGPT wrapper. Each agent was built methodically from the data up:

### **🧩 Chief Resident (Orchestrator Layer)**
Clinician Query → Analyze Intent → Call Specialists in Parallel
[Agent 97] [Dr. OPA] [Dr. OFF]
Internal Reasoning → Resolve Conflicts → Synthesize Response

⬇️

### **🤖 Specialist Agents (Agent Layer)**
Reasoning workflow: **PLAN** → **RETRIEVE** → **SELF-CHECK** → **SYNTHESIZE**
Each agent ensures complete, cited responses with conversation memory

⬇️

### **🔧 Custom Tools (MCP Layer)**
Domain-specific retrieval functions per agent:
- **Dr. OPA:** 8 tools (policy_check, ipac_guidance, quality_standards, etc.)
- **Dr. OFF:** 3 tools (schedule_get, odb_get, adp_get)
- **Agent 97:** 1 tool (clinician_search via Claude API)

⬇️

### **📚 Knowledge Bases (Data Layer)**
Ontario healthcare sources → Scraped & Chunked → Searchable databases
- **Dr. OPA:** 1,439 chunks (CPSO, PHO, CEP, Quality Standards, Choosing Wisely)
- **Dr. OFF:** 3,951 chunks (OHIP Schedule, ODB Formulary, ADP)
- **Agent 97:** 97 trusted medical domains (real-time web search)

---

**Tech Stack:** OpenAI Agents SDK (orchestration), Claude 3.5 Sonnet (Agent 97 search), ChromaDB (embeddings), FastAPI (web endpoints), Langfuse/Logfire (observability).

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

## Sidebar: RAG-Readiness in the Age of AI Agents

As we built these agents, we learned something critical: **the quality of AI clinical agents depends entirely on the quality of the underlying data sources.**

Our agents perform well because they draw from well-structured sources: CPSO policies (clean HTML), ODB Formulary (searchable database), OHIP Schedule (structured PDFs). But many Ontario healthcare resources are buried in:
- **PDFs without metadata** (tables extracted as images, no searchable text)
- **Legacy HTML** (nested tables, broken links, outdated content)
- **Fragmented websites** (information scattered across 20+ pages)

This problem isn't unique to Ontario. Most government and public health websites were built for humans browsing with their eyes—not AI agents retrieving with precision.

### RAG-Readiness: A New Digital Accessibility Standard

**Retrieval-Augmented Generation (RAG)** is the backbone of these agents: retrieve relevant context, augment it into a prompt, generate a grounded response. But RAG only works if data is **machine-readable, structured, and semantically rich.**

Think of this as **WCAG (Web Content Accessibility Guidelines) for the AI era**—ensuring information is accessible not just to humans, but to the AI agents that increasingly mediate access to knowledge.

**What RAG-Readiness Means:**
- **Clean HTML structure:** Proper headings, semantic tags, no nested tables
- **Metadata richness:** Document titles, publication dates, author/org attribution
- **API availability:** Structured data feeds (JSON, XML) instead of scanned PDFs
- **Citation-friendly:** Stable URLs, version control, clear licensing
- **Content freshness:** Update timestamps, change logs

**Why This Matters for Ontario:**
If Ontario wants trusted AI agents for health, housing, education, and services, then Ontario's official websites need to be optimized for both human and machine readability. Otherwise, AI agents will:
- Miss critical information buried in image-based PDFs
- Cite outdated content without knowing it's obsolete
- Generate incomplete answers because key details aren't properly structured

The best government data sources we worked with (CPSO policies, ODB formulary) succeeded because they had clean structure and rich metadata. The challenge: most public resources weren't designed with AI retrieval in mind.

---

## We're Testing — Join Us

This is a demonstration, not a product. We're testing these agents with Ontario clinicians to understand:
- **Utility:** Are these agents actually helpful in daily practice?
- **Trust:** Do clinicians trust the citations and reasoning?
- **Gaps:** What data sources are missing? What questions can't be answered?
- **Workflow:** How should agents integrate with EMRs and clinical workflows?

**If you're a clinician in Ontario and want to participate in testing, reach out:**
- **Stewart McKendry:** [stewart@example.com](#)
- **Will Falk:** [will@example.com](#)
- **Dr. Keith Thompson:** [keith@example.com](#)

We're especially interested in:
- **Specialty-specific needs:** What agents would be most useful in your field?
- **Error cases:** Where do agents fail or provide misleading info?
- **Integration ideas:** How could this fit into your workflow?

---

## The Big Picture: AI That Augments, Not Replaces

The next time someone says *"AI will replace doctors,"* show them **Chief Resident**.

This orchestrator doesn't diagnose. It doesn't prescribe. It doesn't decide. It **retrieves, reconciles, and routes**—so clinicians can focus on judgment, empathy, and care.

The real promise of clinical AI isn't replacing human expertise. It's **removing the friction** that keeps clinicians from practicing at the top of their license: hunting for billing codes, checking formularies, re-reading policies, digging through guidelines.

AI agents like Dr. OPA, Dr. OFF, and Agent 97 are **infrastructure**—like reliable internet, secure EMRs, or well-maintained roads. They make the system work better. They don't replace the destination.

**This registry is a rehearsal for that future.**

---

*For more on Coaching the Machine, subscribe at [coachingthemachine.substack.com](https://coachingthemachine.substack.com).*
