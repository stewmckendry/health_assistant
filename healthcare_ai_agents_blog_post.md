# From Patient Education to Clinical Support: Building a Healthcare AI Agent Team

*Co-authored with Will Falk and Dr. Keith Thompson*

*A follow-up to "White Coat, Black Box: Helping Patients Navigate AI Health Information" - where we shift from patient education to clinician support*

---

Last week, we shared the story of building [My Health Assistant](https://coachingthemachine.substack.com/p/white-coat-black-box-helping-patients) - an AI system designed to help patients understand their health information in plain language using only trusted medical sources. The response was overwhelming, but it also surfaced a fascinating pattern in the feedback.

While patients loved having their medical reports explained in understandable terms, healthcare professionals began asking a different question: "This is great for patient education, but what about the administrative complexity we face every day?"

That question led us down a completely different path - and to the **Ontario Healthcare AI Agents Registry**.

## Two Different Problems, Two Different Solutions

The Health Assistant we built last week serves a clear need: patients receive medical information they can't understand, and they need it translated into plain language using sources they can trust. It's fundamentally an educational tool - taking complex medical concepts and making them accessible.

But healthcare professionals face a different challenge entirely. They don't need medical concepts explained in simple terms - they need to navigate the labyrinthine administrative systems that surround patient care. They need to know if a medication is covered, which billing code applies, what the regulatory requirements are for a specific procedure, and how all these pieces fit together.

These are precision problems, not education problems. And they require a fundamentally different approach.

## The Ontario Healthcare Reality

Working in Ontario healthcare means juggling multiple complex systems:

**For Billing and Coverage**:
- 4,166 OHIP fee codes with specific billing requirements and restrictions
- 8,401 drugs in the ODB formulary, each with detailed coverage rules
- 735 ADP funding scenarios across 11 assistive device categories
- 1,101 documented exclusions and limitations

**For Clinical Practice**:
- 366 CPSO policies covering physician regulations and expectations
- Dozens of Ontario Health clinical programs (cancer, kidney, cardiac, mental health)
- 132 PHO infection control guidelines
- 57 CEP clinical decision support tools

**The Real Challenge**: This information is scattered across dozens of websites, buried in PDFs, and constantly changing. A family physician might need to check three different systems just to answer a single coverage question.

## Meet the Specialist Agents

Rather than building another generalist AI, we created four specialized agents that mirror how real healthcare teams work:

### Dr. OFF (Ontario Funding Finder): The Billing Specialist

Dr. OFF embeds the complete Ontario healthcare funding ecosystem:
- Every ODB formulary entry with coverage rules and restrictions
- All OHIP billing codes with requirements and limitations
- ADP funding matrices for assistive devices
- 10,815 semantic vectors enabling intelligent cross-referencing

When you ask "Can I bill E078 for a virtual assessment with a patient over 75?", Dr. OFF doesn't search the web - it knows the answer from embedded OHIP schedules, including all the edge cases and exceptions.

### Dr. OPA (Ontario Practice Advice): The Regulatory Expert

Dr. OPA specializes in practice standards and clinical pathways:
- Complete CPSO policy database with contextual understanding
- Real-time connections to all Ontario Health clinical programs
- PHO infection prevention and control guidance
- CEP clinical decision support tools and algorithms

Ask "What are the consent requirements for prescribing medical cannabis?" and Dr. OPA provides precise regulatory guidance, not generic advice.

### Agent 97: The Patient Education Bridge

Agent 97 inherits the mission of our original Health Assistant but with enhanced focus:
- 97 carefully vetted medical sources (Canadian healthcare organizations, major medical centers, peer-reviewed journals, global health authorities)
- Automatic emergency detection and crisis intervention
- Educational responses with built-in safety guardrails

This agent handles the patient-facing side while the others support clinical workflows.

### The Chief: The Clinical Orchestrator

The Chief doesn't have its own knowledge base - it's the coordinator. When faced with complex, multi-domain questions like "What are the billing codes for diabetes management, is CGM covered, and what are the CPSO documentation requirements?", The Chief:

1. Recognizes which specialists need to be consulted
2. Coordinates parallel consultations with Dr. OFF and Dr. OPA
3. Synthesizes responses into unified, actionable guidance
4. Provides confidence scoring and comprehensive citations

## Technical Architecture: Beyond Simple RAG

While the original Health Assistant used straightforward Retrieval-Augmented Generation, the Agent Registry requires a more sophisticated approach:

### Hybrid Knowledge Systems

Each agent combines three complementary approaches:
- **Embedded Knowledge**: Pre-processed, vectorized content from Ontario-specific resources providing instant, accurate retrieval
- **Structured Data**: SQL databases for precise lookups of codes, percentages, and formulaic relationships
- **Selective Web Search**: Domain-filtered searches limited to verified Ontario healthcare domains for recent updates

This hybrid approach is crucial. Dr. OFF can instantly retrieve the exact OHIP fee for a procedure from embedded data while simultaneously checking for recent policy updates through targeted web search.

### Agent-to-Agent Collaboration Using OpenAI's Framework

The real innovation is in how these agents work together. Using OpenAI's new Agents framework, they can autonomously consult each other, creating sophisticated workflows that mirror real clinical decision-making:

- Dr. OFF identifies a coverage requirement that has clinical implications
- The Chief automatically consults Dr. OPA for related practice guidelines
- Agent 97 contributes patient education materials for the complete picture

This isn't just concatenating search results - it's genuine inter-agent collaboration.

## What We Learned: The Data Challenge

Building this registry revealed a critical insight: the biggest technical challenge wasn't the AI architecture - it was data extraction and integration.

Healthcare organizations publish essential information in formats designed for human consumption: PDFs with complex layouts, websites with information scattered across multiple pages, documents that reference other documents in circular patterns. Extracting structured, reliable data from these sources was harder than building the AI agents themselves.

This challenge illuminated a broader trend: AI agents are fundamentally changing how healthcare information gets accessed. Organizations that don't prepare for this shift risk having their knowledge become effectively invisible to the next generation of healthcare tools.

### The Structured Data Imperative

We found ourselves arguing for a fundamental shift in how healthcare organizations present information:

- **Schema.org Healthcare Vocabularies**: Using MedicalEntity, MedicalProcedure, Drug markup extensively
- **API-First Documentation**: Building RESTful APIs for formulary lookups, coverage checks, policy searches
- **Machine-Readable Policies**: Converting guidelines into structured, searchable formats rather than just PDFs
- **Semantic Clarity**: Using precise medical terminology consistently and structuring policies with clear hierarchies

The organizations that make these changes now will have a significant advantage as AI-mediated healthcare information access becomes the norm.

## Measuring What Matters in the AI Agent Era

We realized we need new metrics that reflect this shift:
- API call patterns for clinical queries
- Structured data completeness scores for all policies
- Time-to-answer for common healthcare questions via AI
- Error rates in AI agent interactions
- Coverage determination accuracy through automated channels
- Cross-platform consistency in healthcare information

## Beyond Information Retrieval: The Future Vision

The current registry focuses on answering questions accurately and quickly. But we can see the next evolution: agents that don't just provide information but take action.

**Workflow Automation**:
- Automated prior authorization submissions
- Billing code optimization and validation
- Clinical documentation assistance
- Quality reporting and metrics generation

**Proactive Intelligence**:
- Guideline update notifications
- Coverage change alerts
- Compliance monitoring
- Billing opportunity identification

**Deep Integration**:
- EMR/EHR system integration
- Direct submission to government portals
- Real-time collaboration tools
- Mobile and voice interfaces

## The Bigger Picture: Preparing for the AI Agent Era

This project represents more than just a technical experiment - it's a preview of how healthcare information access is evolving. We're moving from a world where healthcare professionals manually search multiple websites to one where AI agents work behind the scenes, aggregating and synthesizing information from authoritative sources.

The implications are significant:
- **For Healthcare Professionals**: Dramatic reduction in administrative time, allowing more focus on patient care
- **For Healthcare Organizations**: Need to rethink information architecture for AI consumption
- **For Patients**: Better-informed providers with instant access to current, accurate information

Healthcare organizations that recognize this fundamental shift - that their websites are no longer just visual interfaces for human visitors but critical data sources for AI agents making real-time clinical and administrative decisions - will thrive in this new era.

## The Demo and What We're Learning

The Ontario Healthcare AI Agents Registry is currently available as an educational demonstration. We're not commercializing it - we're using it to explore how AI agent teams might support healthcare workflows.

Early feedback has been fascinating. Clinicians appreciate the precision and speed, but they're also identifying use cases we hadn't considered. Emergency physicians want integration with triage protocols. Family doctors want medication interaction checking. Specialists want pathway navigation for complex cases.

Each new use case reinforces our core insight: healthcare is too complex for monolithic AI solutions. The future lies in specialized agents working together, each excellent in their domain, collaborating to tackle multifaceted healthcare challenges.

## What's Next

This project has opened up several research directions:

1. **Expanding the Specialist Team**: Laboratory Results Interpreter, Radiology Report Analyzer, Medication Interaction Checker, Clinical Pathway Navigator
2. **Organization-Specific Agents**: Hospital protocol specialists, clinic workflow assistants, research institution knowledge bases
3. **Personal Medical Assistants**: Individual physician preference agents, patient-specific care coordinators, family health team collaborators

But the most important next step might be the simplest: proving that this approach actually improves healthcare outcomes. We have the technology to build sophisticated AI agent teams. Now we need to demonstrate they make healthcare better, not just more efficient.

The investment in restructuring healthcare content for AI consumption will pay dividends in reduced administrative burden, improved accuracy in coverage determinations, and better clinical decision support. Most importantly, it enables healthcare professionals to spend less time searching for information and more time caring for patients.

---

*The Ontario Healthcare AI Agents Registry is available as an educational demonstration. If you're working on similar challenges in healthcare AI, or if you're a healthcare organization thinking about preparing for the AI agent era, we'd love to connect. The best innovations in healthcare AI will come from collaboration between technologists and the people who actually deliver care.*

*This exploration of AI agents in healthcare continues our broader investigation into building AI systems that serve human needs responsibly. What aspects of healthcare AI should we tackle next?*