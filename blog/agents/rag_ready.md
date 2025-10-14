# RAG-Ready Government — Ranking Public Websites for the Age of Conversational AI

**From:** William Falk & Stewart McKendry  
**To:** Sunil Johal & Jordann Thurgood  
**Date:** October 2025

**Purpose:**  
Proposal for CSA Public Policy Series paper and demonstration chatbot to evaluate and rank public-sector website readiness for AI retrieval.

---

## 1. The Core Problem

Citizens now ask questions of the web, not browse it.  
AI systems (ChatGPT, Perplexity, Copilot, Gemini, etc.) are only as reliable as the information they can retrieve and verify.

Most government websites are designed for human readers, not AI retrievers. Critical information—eligibility rules, health guidance, licensing requirements—is often locked in formats AIs struggle to parse: PDFs, scattered FAQs, outdated HTML, missing metadata.

This gap between human and machine accessibility is a new public-policy blind spot.  
When AIs cannot ground answers in official content, governments lose informational authority and misinformation fills the void.

---

## 2. Why “RAG-Readiness” Matters

**Retrieval-Augmented Generation (RAG)** is now the standard for factual, explainable AI.

A RAG-ready website enables:

- Automatic indexing and chunking
- AI citation with source attribution
- Trusted, auditable origin of truth

RAG-readiness is a new dimension of digital trust infrastructure, essential for:

- **Citizens:** authoritative, conversational answers from credible sources
- **Governments:** maintaining informational sovereignty in AI-mediated environments
- **Developers:** structured, license-safe, machine-readable inputs
- **Policy bodies:** standards for transparency, traceability, accessibility

*RAG-readiness is the next generation of public digital accessibility—the WCAG of the AI era.*

---

## 3. The RAG-Readiness Index (RRI) and Ranking System

**RRI** scores and ranks public-sector domains (federal, provincial, municipal, agency-level) across five dimensions:

| Dimension         | Indicators                                  | Example Metrics                       |
|-------------------|---------------------------------------------|---------------------------------------|
| Retrievability (25%) | Crawlability, sitemap completeness, accessible PDFs | % text-parsable, robots.txt coverage  |
| Structure (20%)   | Semantic tags, JSON-LD, schema.org use      | Structured data density               |
| Content Quality (20%) | Plain-language clarity, redundancy, completeness | Flesch readability, FAQ density       |
| Provenance (20%)  | Source traceability, date stamps, version control | Metadata freshness, canonical links   |
| Machine Confidence (15%) | RAG retrieval precision, citation accuracy | LLM retrieval evaluation, hallucination rate |

**Outputs:**

- 0–100 RRI Score per site
- Letter Grade (A–F)
- Public Ranking Table by jurisdiction and sector
- “Gold Star” digital-trust certification for high-scoring sites

**Initial evaluation:** 30–40 government domains  
Examples:  
- Federal: canada.ca, cra.gc.ca, ircc.canada.ca  
- Provincial: ontario.ca, alberta.ca, saskatchewan.ca  
- Agencies: serviceontario.ca, publichealthontario.ca, statcan.gc.ca  
- International: nhs.uk, irs.gov, gov.uk, australia.gov.au

---

## 4. The Demonstration Chatbot (“GovRAG”)

A limited-release GovRAG Chatbot will:

- Retrieve information live from evaluated sites
- Display inline citations with RRI metadata
- Show confidence score and “Gold Star” indicator for RAG-ready content
- Allow self-evaluation using the same metrics

**Key Capabilities:**

- Built with LangChain or LlamaIndex, GPT-4-turbo as synthesizer
- Evaluation via Langfuse / OpenAI Evals
- Streamlit front-end, bilingual support
- Generates RRI dashboard and comparative rankings

**Outcome:**  
Governments and agencies can interactively test their own information’s AI retrievability—effectively self-certifying RAG-readiness.

---

## 5. The “Gold Star” Trust Layer

Deliverable: machine-readable trust signal at domain level

- JSON-LD metadata (govtrust.ca/schema#goldstar)
- Cryptographic provenance (C2PA / Content Authenticity Initiative)
- Discoverable via search APIs and LLM retrievers
- Weighted positively in RAG retrieval systems (like HTTPS for search ranking)

Creates an auditable, open, trust-by-design framework for governments in a generative-AI world.

---

## 6. Policy and Research Implications

- **Digital Sovereignty:** Control over data access, citation, recombination by AI
- **Procurement & Standards:** Future contracts include RAG-readiness criteria
- **Accountability:** Transparent rankings drive digital accessibility improvements
- **Public Confidence:** Gold Star certification distinguishes official sources
- **Research Infrastructure:** Enables comparative studies on AI retrievability, accuracy, bias

---

## 7. Deliverables and Timeline

| Phase                      | Deliverable                                 | Target                |
|----------------------------|---------------------------------------------|-----------------------|
| 1. Framework Development   | RRI methodology, open metrics               | November 2025         |
| 2. Site Evaluations (30–40)| Federal, provincial, municipal, international| Dec 2025 – Jan 2026   |
| 3. GovRAG Chatbot Prototype| Interactive self-assessment & retrieval demo| Jan 2026              |
| 4. CSA Paper Publication   | Full report with rankings                   | Q1 2026               |
| 5. Public Release/Workshop | Launch rankings + self-evaluation toolkit   | Q2 2026               |

---

## 8. Why CSA and Why Now

The Canadian Standards Association is uniquely positioned to convene this work—bridging technical architecture and public policy, with credibility to issue voluntary standards that evolve into procurement norms.

**Why now?**

- AI assistants are becoming the dominant citizen interface
- Governments are grappling with digital trust and data sovereignty
- No public benchmark yet defines AI-readable government

CSA can set that benchmark—visibly, credibly, and first.

---

## 9. Next Steps

- Approve concept for CSA Public Policy stream
- Greenlight initial 30-site evaluation and chatbot prototype
- Draft and circulate paper outline by November 2025
- Launch pilot rankings early 2026
