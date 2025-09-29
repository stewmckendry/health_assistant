# Ontario Healthcare AI Agents Registry - Version 2

**Note: This is a demonstration project for education and experimentation, showcasing how AI agents could be used to assist with healthcare information retrieval in Ontario.**

## Executive Overview

The Ontario Healthcare AI Agents Registry represents Part 2 of our healthcare AI exploration. Where Part 1 (My Health Assistant) focused on helping patients understand their medical information in plain language using trusted sources, this registry takes the concept several steps further - creating specialized AI agents that support healthcare professionals in navigating Ontario's complex administrative and clinical landscape.

Inspired by Microsoft AI's Medical Diagnosis Orchestrator (MAI-DxO) concept of a "digital conductor" coordinating multiple AI specialists, this project explores what purpose-built AI agents could look like in Ontario's healthcare context - and how they might support clinicians in reducing administrative burden while enhancing clinical decision-making.

By combining advanced language models with authoritative Ontario-specific healthcare data, the registry demonstrates how AI agents could provide instant, accurate, and actionable information for clinical and administrative needs.

## The Vision: A Chief Medical Officer with AI Specialists

Imagine a Chief Medical Officer (CMO) at a hospital who can instantly consult with a team of specialists for any clinical or administrative question. This is the model we've implemented digitally - The Chief orchestrator working with three specialized agents, each an expert in their domain.

Just as a real CMO would consult different specialists for different problems, our Chief agent analyzes incoming queries and delegates to the appropriate specialist agents. When faced with complex questions that span multiple domains, The Chief coordinates parallel consultations and synthesizes the responses - even negotiating when specialists provide conflicting information or different perspectives on the same issue.

## The Agents

### 1. Dr. OFF (Ontario Finance & Formulary)
**Scope**: Healthcare financing, billing, and coverage determinations

**Knowledge Base**:
- **8,401 unique drugs** from the Ontario Drug Benefit formulary (verified by SQL query)
- **4,166 unique OHIP fee codes** with billing requirements (verified by SQL query)  
- **ADP funding scenarios** across 11 assistive device categories
- **Comprehensive coverage rules** embedded as structured data (not just searchable text, but queryable database records)

**Capabilities in Plain Language**: 
- Instantly answers "Can I bill this code for this patient?" 
- Checks drug coverage and finds cheaper alternatives
- Determines device funding eligibility including income-based programs
- Validates billing combinations and requirements

**Real-world Questions**: "Can I bill C124 for a 75-year-old patient discharged after 3 days?" or "Is Ozempic covered for weight loss versus diabetes?"

### 2. Dr. OPA (Ontario Practice Advice)
**Scope**: Clinical practice standards, regulatory compliance, and evidence-based care pathways

**Knowledge Base**:
- **CPSO policy database** covering physician regulations and expectations
- **All Ontario Health clinical programs** via real-time web search (cancer, kidney, cardiac, mental health, etc.)
- **PHO infection control guidance** for IPAC requirements
- **CEP clinical tools and algorithms** for evidence-based practice
- Direct access to **25+ Ontario Health domains** for current program information

**Capabilities in Plain Language**:
- Provides regulatory guidance on what physicians can and cannot do
- Explains clinical pathways and screening programs
- Clarifies infection control requirements
- Links to appropriate clinical decision support tools

**Real-world Questions**: "What are CPSO requirements for virtual care consent?" or "What kidney care programs are available for a 65-year-old patient?"

### 3. Agent 97 (Medical Education Assistant)
**Scope**: Patient education and general medical information from trusted sources

**Knowledge Base**:
- **97 carefully vetted medical sources** including:
  - Canadian healthcare organizations (Ontario Health, Health Canada, major hospitals)
  - US medical centers (Mayo Clinic, Johns Hopkins, Cleveland Clinic)
  - Medical journals (NEJM, Lancet, JAMA, BMJ)
  - Global authorities (WHO, CDC, NIH)

**Capabilities in Plain Language**:
- Provides educational health information for patients
- Automatically detects medical emergencies and redirects appropriately
- Explains medical conditions and treatments in accessible language
- Always includes citations from trusted sources

**Real-world Application**: Provides safe, educational health information while automatically detecting emergencies and redirecting to appropriate resources

### 4. The Chief (Clinical Intelligence Orchestrator)
**Scope**: Intelligent routing and synthesis across all specialist agents

Like a Chief Medical Officer consulting with department heads, The Chief:
- **Analyzes** complex multi-domain queries to identify which specialists to consult
- **Coordinates** parallel consultations with multiple agents when needed
- **Synthesizes** responses into unified, actionable guidance
- **Negotiates** when specialists provide conflicting information or different perspectives
- **Aggregates** citations and provides confidence scoring based on evidence quality

**Architecture**: Powered by GPT-4o with real-time streaming, comprehensive observability tracing, and sophisticated citation management

**Real-world Application**: Handles complex questions like "What are the billing codes for diabetes management and is continuous glucose monitoring covered?" by consulting multiple agents and providing a comprehensive, synthesized response

## What Makes It Different

### Beyond Traditional Chatbots
Unlike general health assistants that rely solely on web searches, the Ontario Healthcare AI Agents Registry combines:

1. **Deep Ontario-Specific Knowledge**: Instead of generic medical information, these agents have embedded knowledge (think of it as pre-loaded expertise) containing thousands of Ontario healthcare documents, policies, and guidelines that aren't readily available through general web searches

2. **Precise Information Architecture**: The system uses two complementary approaches:
   - **Structured databases** for exact lookups (like finding a specific drug's DIN number or fee code)
   - **Semantic understanding** for context-aware searching (understanding that "heart medication" relates to "cardiac drugs")

3. **Trusted Source Restriction**: Web searches are limited to verified Ontario healthcare domains, ensuring information comes only from authoritative sources - no random health blogs or US-specific guidance

4. **Agent Collaboration**: Using OpenAI's Agents framework, these specialists don't just work in isolation - they actively consult each other when expertise from multiple domains is needed, creating sophisticated workflows that mirror real clinical teams

5. **Real-time Currency**: Combines stable, embedded knowledge with selective web searches to capture recent policy changes and updates not yet in the knowledge base

## Technical Innovation

### The Power of Hybrid Knowledge Systems
The registry uniquely combines three approaches:

- **Embedded Knowledge**: Think of this as the agent's "long-term memory" - pre-processed Ontario healthcare content that's instantly accessible without needing to search the internet
- **Structured Databases**: Like a filing cabinet with perfectly organized records - for precise lookups of codes, drug information, and percentages
- **Selective Web Search**: Like having a research assistant who only checks official Ontario government websites for the latest updates

This hybrid approach ensures Dr. OFF can instantly tell you the exact OHIP fee while also checking if there were any policy changes last week.

### How Agents Work Together
Using OpenAI's Agents framework, our specialists collaborate like a real healthcare team:
- The Chief acts as the team leader, understanding the full scope of a question
- Specialists are consulted based on their expertise
- Agents can "hand off" parts of a query to colleagues with relevant knowledge
- Conflicting information is reconciled through The Chief's synthesis
- All responses include traceable citations back to authoritative sources

## Future Vision: Scaling Intelligence Through a True Registry

The registry is designed to grow with Ontario's healthcare needs through:

**The Registry Model - Unlimited Expansion**:
- **Add Agents by Specialty**: Cardiology AI, Oncology AI, Pediatric AI - each bringing deep domain expertise
- **Add Agents by Healthcare Organization**: Hospital-specific agents that know local protocols, clinic agents with practice-specific guidelines
- **Add Agents by Function**: Prior Authorization Agent, Clinical Trials Matcher, Drug Interaction Checker
- **Certification and Evaluation**: New agents could be evaluated against clinical standards and certified for specific use cases before joining the registry

This is the power of a true registry approach - it's not a fixed team but an expandable ecosystem. Healthcare organizations could contribute their own specialized agents, which would be evaluated, certified, and made available to the broader healthcare community.

**From Information to Action**:
- Evolution from answering questions to initiating workflows
- Integration with healthcare systems for direct action (prior authorizations, claim submissions)
- Proactive intelligence that alerts clinicians to relevant updates

The modular architecture means new capabilities can be added without disrupting existing agents - like adding new specialists to a medical team or new departments to a hospital.

## Preparing Healthcare Organizations for the AI Agent Era

*Acknowledging insights from "Future-Proofing Your Website for the Age of AI Agents" by Olivier Dobberkau*

### The Critical Challenge We Discovered
Building this registry revealed that extracting structured, usable content from PDFs and websites was the biggest technical challenge. Healthcare organizations must fundamentally rethink information presentation for the AI era.

### Key Actions for Future-Proofing

1. **Structure Your Data**: Convert policies, formularies, and guidelines into machine-readable formats (JSON-LD, APIs) not just PDFs
2. **Semantic Clarity**: Use consistent medical terminology and clear hierarchies in all documentation
3. **Enable Programmatic Access**: Build APIs for common queries (coverage checks, eligibility verification)
4. **Maintain Currency Signals**: Include clear "last updated" dates and version control on all content
5. **Think Beyond Visual**: Your website is no longer just for human eyes - it's a critical data source for AI agents

Organizations that adapt now will ensure their knowledge remains accessible and actionable as AI-mediated healthcare information access becomes the standard.

## The "So What?"

This experimental registry demonstrates a fundamental shift in how healthcare information could be accessed and utilized:

**For Clinicians**: Instead of spending hours navigating multiple systems and documents, get instant, accurate answers with authoritative citations - freeing up time for patient care.

**For Healthcare Systems**: The potential to reduce administrative burden, improve billing accuracy, and ensure consistent application of guidelines across the organization.

**For the Future of Healthcare**: A glimpse at how specialized AI agents working in concert could transform healthcare delivery - not replacing clinical judgment, but augmenting it with instant access to comprehensive, current, Ontario-specific knowledge.

The Ontario Healthcare AI Agents Registry isn't just about faster information retrieval - it's about reimagining how healthcare professionals interact with the vast, complex knowledge base that governs modern medicine. By demonstrating how AI agents can work as a coordinated team, we're exploring a future where technology handles the complexity, allowing healthcare professionals to focus on what matters most: caring for patients.

---
*This demonstration project is for educational and experimental purposes. For questions or to explore the demo, please contact the project team.*