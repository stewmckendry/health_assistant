# Ontario Healthcare AI Agents Registry

**Note: This is a demonstration project for education and experimentation, showcasing how AI agents could be used to assist with healthcare information retrieval in Ontario.**

## Executive Overview

The Ontario Healthcare AI Agents Registry is a suite of specialized AI assistants designed to help healthcare professionals and patients navigate Ontario's complex healthcare ecosystem. By combining advanced language models with authoritative Ontario-specific healthcare data, the registry provides instant, accurate, and actionable information for clinical, administrative, and educational needs.

## Purpose & Vision

### The Challenge
Healthcare professionals in Ontario face challenges navigating:
- Complex billing codes and coverage rules across OHIP, ODB, and ADP programs
- Ever-changing regulatory requirements from CPSO and Ontario Health
- Clinical guidelines scattered across dozens of organizations
- Administrative complexity that takes time away from patient care

### The Solution
The registry demonstrates how manual document searching could be accelerated through AI assistance, potentially enabling clinicians to focus more on patient care. Each agent specializes in a specific domain, while working together to provide comprehensive answers to complex healthcare questions.

## The Agents

### 1. Dr. OFF (Ontario Funding Finder)
**Scope**: Healthcare financing, billing, and coverage determinations

**Knowledge Base**:
- **8,401 drugs** from the Ontario Drug Benefit formulary with coverage rules
- **4,166 OHIP fee codes** with billing requirements and restrictions  
- **735 ADP funding scenarios** across 11 assistive device categories
- **1,101 documented exclusions** and limitations for devices
- **10,815 semantic vectors** for intelligent drug searching

**MCP Tools**: 5 specialized tools including coverage.answer orchestrator, schedule.get for OHIP billing, adp.get for device funding, odb.get for drug formulary, and source.passages for direct retrieval

**Real-world Impact**: Answers questions like "Can I bill C124 for a 75-year-old patient discharged after 3 days?" or "Is Ozempic covered for weight loss versus diabetes?"

### 2. Dr. OPA (Ontario Practice Advice)
**Scope**: Clinical practice standards, regulatory compliance, and evidence-based care pathways

**Knowledge Base**:
- **366 CPSO policy vectors** covering physician regulations and expectations
- **All Ontario Health clinical programs** via real-time web search (cancer, kidney, cardiac, mental health, etc.)
- **132 PHO infection control vectors** for IPAC guidance
- **57 CEP clinical tools** and algorithms
- Direct access to **25+ Ontario Health domains** for current program information

**MCP Tools**: 7 tools including policy_check for CPSO guidance, program_lookup for Ontario Health programs, ipac_guidance for infection control, and freshness_probe for guideline updates

**Real-world Impact**: Provides instant answers to "What are CPSO requirements for virtual care consent?" or "What kidney care programs are available for a 65-year-old patient?"

### 3. Agent 97 (Medical Education Assistant)
**Scope**: Patient education and general medical information from trusted sources

**Knowledge Base**:
- **97 carefully vetted medical sources** including:
  - Canadian healthcare organizations (Ontario Health, Health Canada, major hospitals)
  - US medical centers (Mayo Clinic, Johns Hopkins, Cleveland Clinic)
  - Medical journals (NEJM, Lancet, JAMA, BMJ)
  - Global authorities (WHO, CDC, NIH)

**MCP Tools**: 5 tools including agent_97_query for medical questions, emergency detection, crisis intervention, and streaming responses

**Real-world Impact**: Provides safe, educational health information while automatically detecting emergencies and redirecting to appropriate resources

### 4. The Chief (Clinical Intelligence Orchestrator)
**Scope**: Intelligent routing and synthesis across all specialist agents

**Capabilities**:
- Analyzes complex multi-domain queries
- Coordinates parallel consultations with specialist agents
- Synthesizes responses into unified, actionable guidance
- Aggregates and deduplicates citations
- Provides confidence scoring based on evidence quality

**Architecture**: GPT-4o powered orchestration with real-time streaming, Langfuse observability tracing, and comprehensive citation management

**Real-world Impact**: Handles complex questions like "What are the billing codes for diabetes management and is continuous glucose monitoring covered?" by consulting multiple agents and providing a comprehensive, synthesized response

## What Makes It Different

### Beyond Traditional Chatbots
Unlike general health assistants that rely solely on web searches, the Ontario Healthcare AI Agents Registry combines:

1. **Deep Ontario-Specific Knowledge**: Embedded knowledge bases containing thousands of Ontario healthcare documents, policies, and guidelines that aren't readily available through general web searches

2. **Precise Retrieval Architecture**: Dual-path retrieval using both SQL databases for structured data (drug DINs, fee codes, percentages) and semantic vector search for contextual understanding

3. **Trusted Source Restriction**: Web searches are limited to verified Ontario healthcare domains (20 for Dr. OFF, 19 for Dr. OPA, 97 for Agent 97), ensuring information comes only from authoritative sources

4. **Agent-to-Agent Collaboration**: Using OpenAI's Agents framework, agents can autonomously consult each other, creating sophisticated workflows that mirror real clinical decision-making

5. **Real-time Currency**: Combines embedded knowledge with selective web search to capture recent policy changes and updates not yet in the knowledge base

## Technical Innovation

### The Power of Embeddings + Web Search
The registry uniquely combines:
- **Embedded Knowledge**: Pre-processed, vectorized content from Ontario-specific resources providing instant, accurate retrieval
- **Selective Web Search**: Domain-filtered searches to trusted sources for recent updates and edge cases
- **Hybrid Approach**: Always runs both structured (SQL) and semantic (vector) searches in parallel, surfacing any conflicts

### Agents Framework Advantages
Using OpenAI's Agents framework enables:
- **Autonomous Operation**: Agents can work independently on complex, multi-step tasks
- **Inter-agent Communication**: Agents consult each other when expertise from multiple domains is needed
- **Workflow Automation**: Beyond Q&A, agents can perform research, process documents, and generate reports
- **Scalable Architecture**: Easy to add new specialist agents as needs evolve

## Future Vision

### Expanding the Registry
The platform is designed to grow with Ontario's healthcare needs:

**New Specialist Agents**:
- Laboratory Results Interpreter
- Radiology Report Analyzer
- Medication Interaction Checker
- Clinical Pathway Navigator

**Organization-Specific Agents**:
- Hospital-specific protocol agents
- Specialty clinic workflow assistants
- Research institution knowledge bases

**Personal Medical Assistants**:
- Individual physician preference agents
- Patient-specific care coordinators
- Family health team collaborators

### Beyond Information Retrieval
The next evolution moves from answering questions to actively supporting healthcare delivery:

**Workflow Automation**:
- Automated prior authorization submissions
- Billing code optimization and validation
- Clinical documentation assistance
- Quality reporting and metrics generation

**Proactive Intelligence**:
- Guideline update notifications
- Billing opportunity identification
- Coverage change alerts
- Compliance monitoring

**Integration Capabilities**:
- EMR/EHR system integration
- Direct submission to government portals
- Real-time collaboration tools
- Mobile and voice interfaces

## Implementation & Access

The registry is currently available as:
- Web-based interface for easy access
- API endpoints for system integration
- MCP server architecture for tool interoperability
- Streaming responses for real-time interaction

All agents include comprehensive:
- Session logging for audit trails
- Citation tracking for accountability
- Confidence scoring for decision support
- Observability tracing for performance monitoring

## Impact & Benefits

### For Healthcare Providers
- **Time Savings**: Reduce hours of manual searching to seconds
- **Accuracy**: Authoritative, cited information from official sources
- **Compliance**: Stay current with regulatory requirements
- **Focus**: More time for patient care, less on administration

### For Healthcare Organizations
- **Efficiency**: Streamlined billing and coverage determinations
- **Standardization**: Consistent application of guidelines
- **Training**: Rapid onboarding and continuous education
- **Quality**: Improved documentation and compliance

### For Patients
- **Education**: Trusted health information from verified sources
- **Safety**: Automatic emergency detection and redirection
- **Access**: 24/7 availability for health questions
- **Empowerment**: Better understanding of health conditions

## Preparing Your Healthcare Organization for AI Agents

### The Challenge We Faced
Building the Ontario Healthcare AI Agents Registry revealed a critical insight: extracting structured, usable content from PDFs and websites across Ontario health domains was the single biggest technical challenge. Healthcare organizations must fundamentally rethink how they present information—shifting from websites designed primarily for visual human consumption to platforms that serve both humans and AI agents equally well.

### Why This Matters Now
AI agents are transforming how healthcare information is accessed:
- **Mediated Access**: Healthcare professionals increasingly use AI to gather information rather than browsing multiple sites
- **Background Processing**: AI agents work behind the scenes, aggregating and synthesizing content from multiple sources
- **Efficiency Priority**: Time-pressed clinicians need instant, accurate answers, not browsing experiences
- **Comparison & Synthesis**: AI agents excel at comparing guidelines, policies, and options across organizations

### Strategic Recommendations for Healthcare Organizations

#### 1. Implement Comprehensive Structured Data
Transform your content into machine-readable formats:
- Use Schema.org healthcare vocabularies extensively (MedicalEntity, MedicalProcedure, Drug, etc.)
- Implement JSON-LD for all clinical guidelines, policies, and procedures
- Structure drug formularies, fee schedules, and coverage rules as data, not just PDFs
- Mark up eligibility criteria, forms, and application processes clearly

#### 2. Develop Robust Healthcare APIs
Create direct communication channels for AI agents:
- Build RESTful APIs for formulary lookups, coverage checks, and policy searches
- Include comprehensive metadata about guidelines and their effective dates
- Design endpoints specifically for common clinical queries
- Ensure high reliability—healthcare decisions depend on your data

#### 3. Prioritize Semantic Clarity in Healthcare Content
AI systems need unambiguous healthcare information:
- Use precise medical terminology consistently throughout your site
- Structure policies with clear hierarchies (eligibility → requirements → exceptions)
- Avoid healthcare jargon that varies between organizations
- Implement clear version control for guidelines and policies
- Date all clinical content and mark superseded documents clearly

#### 4. Optimize Documents for Machine Extraction
Move beyond PDFs as the primary format:
- Provide policies in multiple formats (HTML, JSON, XML, not just PDF)
- Present fee schedules and drug lists as structured data tables
- Use consistent formatting for billing codes, DINs, and procedural codes
- Implement proper metadata for all documents (author, date, version, scope)
- Create machine-readable summaries of lengthy policy documents

#### 5. Enable Programmatic Healthcare Transactions
Streamline administrative processes for AI-mediated interactions:
- Design prior authorization processes that can be completed programmatically
- Structure eligibility checking with clear input/output parameters
- Create machine-readable formulary and coverage determination rules
- Implement standardized response formats for coverage queries
- Document complete workflows for common healthcare transactions

#### 6. Build Healthcare Authority Signals
AI agents prioritize trustworthy medical sources:
- Maintain clear "last updated" dates on all clinical content
- Include comprehensive credentialing and accreditation information
- Provide transparent change logs for guidelines and policies
- Implement digital signatures for official documents
- Create clear chains of authority for policy documents

#### 7. Healthcare-Specific Considerations

**For Provincial Health Organizations**:
- Structure all programs with detailed eligibility and enrollment APIs
- Create comprehensive service catalogs with location data
- Implement real-time wait time and availability feeds
- Provide programmatic access to forms and applications

**For Regulatory Bodies**:
- Convert all policies to structured, searchable formats
- Create decision trees for common compliance questions
- Implement change tracking with detailed revision histories
- Provide machine-readable professional standards and requirements

**For Hospitals and Health Networks**:
- Structure clinical pathways as navigable data
- Create APIs for referral processes and admission criteria
- Implement standardized quality metrics reporting
- Provide machine-readable physician directories and specialties

### Measuring Success in the AI Agent Era
Track new metrics that reflect AI consumption:
- API call patterns for clinical queries
- Structured data completeness scores for all policies
- Time-to-answer for common healthcare questions via AI
- Error rates in AI agent interactions
- Coverage determination accuracy through automated channels
- Cross-platform consistency in healthcare information

### The Path Forward
The healthcare organizations that thrive in the AI agent era will be those that recognize this fundamental shift: your website is no longer just a visual interface for human visitors—it's a critical data source for AI agents making real-time clinical and administrative decisions. By implementing these changes now, you ensure your organization's knowledge remains accessible and actionable, regardless of how it's accessed.

The investment in restructuring content for AI consumption will pay dividends in reduced administrative burden, improved accuracy in coverage determinations, and better clinical decision support. Most importantly, it enables healthcare professionals to spend less time searching for information and more time caring for patients.

## Conclusion

The Ontario Healthcare AI Agents Registry explores new approaches to healthcare information management. By combining embedded Ontario-specific knowledge with AI-powered synthesis, it demonstrates potential tools for supporting clinical decision-making and reducing administrative burden.

This experimental platform showcases how AI agents could evolve from information resources to active partners in healthcare delivery—potentially automating workflows, identifying opportunities, and integrating with existing healthcare systems. The project envisions a future where AI agents work alongside healthcare professionals, handling complexity so humans can focus on healing.

---
*This demonstration project is for educational and experimental purposes. For questions or to explore the demo, please contact the project team.*