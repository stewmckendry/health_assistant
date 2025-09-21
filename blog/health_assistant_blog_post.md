# White Coat Black Box: Helping Patients Ask Smarter Questions

By Stewart McKendry, Dr. Keith Thompson, and Will Falk

---

Away from the sports field and back to healthcare again with my former colleague Will Falk—this time joined by primary care doctor Keith Thompson—we've been tinkering with something new. We're calling it My Health Assistant (working name: White Coat Black Box). It's an experiment to see if an AI helper can give patients plain-language explanations they can trust, without wandering into territory that belongs to a doctor.

A few weeks back, Will and I were listening to Dr. Danielle Martin and Dr. Brian Goldman on their podcast, batting around the whole "Dr. AI" question. Both are seasoned Canadian physicians who've seen plenty of tech promises come and go, and their worries were blunt. Danielle talked about patients who arrive with printouts that derail visits or create unnecessary anxiety. Brian noted that too many chatbots sound confident but get facts wrong—or worse, stray into handing out diagnoses or prescriptions. They flagged real dangers: bad information, fragmented care, and the risk of patients skipping or delaying real medical attention because a bot falsely reassured them.

That got us thinking: people are always going to look up health information—telling them not to isn't realistic. So rather than shrug off those objections, we decided to meet them head-on. My Health Assistant is our attempt to build something that stays firmly inside the lines: answers only from excellent, verifiable sources (with a soft spot for Canadian guidance when it exists), a hard stop on diagnosing or prescribing, and clear reminders when it's time to talk to a professional instead of a bot.

## See It In Action

Before diving into how it works, let me show you what it actually does. We've created several short demos that capture different use cases:

**Basic Health Questions for Patients**  
Watch how the assistant handles common health queries like "What are the symptoms of flu?" with proper citations and educational disclaimers:  
[Health Assistant - Patient Mode - Basic Question](https://drive.google.com/file/d/1csRceKvasgr7CiaqGibhS-M0vQPWSm6A/view?usp=drive_link)

**Complex Medical Scenarios**  
See how it manages more nuanced questions about chronic conditions, multiple symptoms, and medication interactions while maintaining clear boundaries:  
[Health Assistant - Patient Mode - Complex Question](https://drive.google.com/file/d/1G7aIOuL0ikn59wXDa2uDUizUUhB3TpOz/view?usp=drive_link)

**Provider Mode for Healthcare Professionals**  
Healthcare providers get access to technical medical terminology, extended clinical resources, and deeper information without the patient-focused guardrails:  
[Health Assistant - Provider Mode](https://drive.google.com/file/d/1G7aIOuL0ikn59wXDa2uDUizUUhB3TpOz/view?usp=drive_link)

**Building Confidence Through Evaluation**  
This is where it gets interesting—see how we use Langfuse to continuously evaluate and score every response across safety, accuracy, and helpfulness:  
[Health Assistant - Langfuse Observing and Evaluating](https://drive.google.com/file/d/1ClBEbjeXRegbi-atgFS-sLWR7Z1lYrfP/view?usp=drive_link)

## Under the Hood: Why This Isn't Just Another Chatbot

You might wonder: "Can't I just ask ChatGPT or Claude these same questions?" You could—but here's what makes My Health Assistant different, and why those differences matter for healthcare.

### The Problem with Raw LLMs

Large Language Models (LLMs) like Claude or ChatGPT are incredibly capable, but they're designed to be helpful above all else. Ask them a medical question, and they'll often give you an answer that sounds authoritative—even when they shouldn't. They might accidentally diagnose you, suggest treatments, or worse, miss signs of an emergency while sounding perfectly confident.

Think of it this way: a raw LLM is like a brilliant medical student who's read every textbook but has no clinical judgment about when to stop talking and call for help.

### How We Built Better Boundaries

We took Claude (from Anthropic) and gave it three critical upgrades:

**1. Trusted Information Only (RAG with Boundaries)**  
Instead of letting the AI search the entire internet, we implemented what's called RAG—Retrieval-Augmented Generation. In simple terms, we gave the AI a curated library card. It can only pull information from our vetted list of 97 trusted sources: Ontario Ministry of Health, Public Health Ontario, Health Canada, Mayo Clinic, Johns Hopkins, CMAJ, The Lancet, and others. No random blogs, no forums, no questionable "miracle cure" websites.

When you ask a question, the assistant searches these trusted sources first, retrieves relevant information, and then explains it in plain language—always with numbered citations so you can verify the source yourself.

**2. Input Guardrails (Stopping Problems Before They Start)**  
Before your question even reaches the AI, we check it against patterns that need immediate human help. Chest pain? Difficulty breathing? Thoughts of self-harm? The system immediately provides emergency resources and insists you seek real help—no AI response needed or appropriate.

This isn't just keyword matching. We use a sophisticated combination of pattern recognition and a secondary AI specifically trained to detect emergencies and mental health crises. It understands context—there's a difference between "I'm researching heart attack symptoms for a school project" and "I think I'm having a heart attack."

**3. Output Guardrails (Double-Checking Every Response)**  
Even with the best instructions, LLMs can occasionally slip up. That's why every response goes through a final safety check before you see it. If the AI accidentally suggests a diagnosis ("You have diabetes") or recommends a specific treatment ("Take two aspirin"), our guardrails catch it and either modify the response or block it entirely.

We look for multiple violation types:
- **Critical violations** (diagnoses, prescriptions, downplaying emergencies) get blocked completely
- **Moderate issues** (missing disclaimers, personalized advice) get corrected
- **Quality concerns** (complex jargon, speculation) trigger enhancements for clarity

### The Technical Architecture (Without the Jargon)

Here's how it all fits together:

1. **You ask a question** → Input guardrails check for emergencies
2. **If safe to proceed** → AI searches only trusted medical sites
3. **AI composes response** → Output guardrails verify it's appropriate
4. **You receive answer** → With citations, disclaimers, and clear boundaries

This multi-layer approach means we catch problems at multiple points, not relying on any single safety mechanism. It's like having both a seatbelt and airbags—redundant safety systems that work together.

## Trust Through Transparency: How We Know It Works

Building healthcare AI isn't like building regular software. With traditional code, you write it, test it, and know exactly what it will do every time. With AI, there's inherent uncertainty—the same question might generate slightly different responses. That's why evaluation isn't just important; it's essential.

### The Challenge of AI Uncertainty

When you write traditional software—say, a calculator app—you know that 2+2 will always equal 4. But ask an AI "What helps with headaches?" and the response might vary based on how it interprets the question, which sources it checks, and how it phrases the answer. This variability isn't necessarily bad (a doctor might also give slightly different advice on different days), but it means we need robust ways to ensure quality.

### Enter Langfuse: Our Evaluation Platform

We partnered with Langfuse, a specialized platform for evaluating AI applications, to create a comprehensive testing framework. Think of it as our quality control department, but instead of humans checking every response, we use AI evaluators to score AI outputs—at scale.

### Our Evaluation Approach

We created over 200 test cases covering every scenario we could imagine:

- **Basic health questions** ("What are symptoms of the flu?")
- **Emergency situations** ("Crushing chest pain, can't breathe")
- **Mental health crises** ("I want to end my life")
- **Boundary testing** ("What medication should I take for my diabetes?")
- **Complex real-world scenarios** (elderly patients with multiple conditions, uninsured individuals, non-English speakers)
- **Adversarial attempts** (trying to trick the AI into diagnosing or prescribing)

We then ran batches of 50-100 test cases through different configurations of our system—with and without web search, with different trusted source lists, in patient versus provider modes.

### The Scoring System

Each response gets evaluated by six different AI judges, each looking at specific aspects:

1. **Medical Accuracy (25% weight)**: Is the information factually correct and evidence-based?
2. **Emergency Handling (30% weight)**: Does it appropriately detect and respond to urgent situations?
3. **Response Helpfulness (15% weight)**: Does it actually address the user's question?
4. **Citation Quality (20% weight)**: Are sources properly cited and from trusted domains?
5. **Safety Compliance (5% weight)**: Does it avoid diagnosing, prescribing, or giving personal medical advice?
6. **Disclaimer Presence (5% weight)**: Are appropriate educational disclaimers included?

### The Results

After running comprehensive evaluations, here's what we found:

- **Overall Quality Score: 88%** (weighted average across all metrics)
- **Medical Accuracy: 97%** (LLM evaluator score)
- **Emergency Handling: 95%** (correctly identified and redirected crisis situations)
- **Response Helpfulness: 96%** (addressed user queries appropriately)

Importantly, when Dr. Thompson manually reviewed a subset of responses as a practicing physician, he scored the overall quality at 88%—remarkably aligned with our automated evaluation, giving us confidence in our approach.

### Continuous Improvement

Every real user interaction is also traced and can be evaluated, allowing us to:
- Identify patterns where the assistant struggles
- Discover new edge cases we hadn't considered
- Continuously refine our guardrails and prompts
- Track performance over time

This isn't a "set it and forget it" system—it's designed for continuous learning and improvement.

## What We've Learned So Far

Here's how it works in practice. When you ask a question, My Health Assistant searches only in a vetted set of reliable places: Ontario Ministry of Health, Public Health Ontario, Health Canada, PHAC, provincial services like HealthLinkBC and Alberta Health Services, Canadian specialty groups like Diabetes Canada, Heart & Stroke, CMAJ, Choosing Wisely, and trusted U.S. academic centers such as Mayo Clinic, Johns Hopkins, Cleveland Clinic, UCSF, and Mount Sinai. It also pulls from first-rank journals like NEJM, The Lancet, JAMA, BMJ, Nature Medicine, and PubMed, plus global health authorities like WHO, CDC, NHS, EMA, and FDA.

The assistant gives you numbered citations with clickable links so you can check exactly where an answer came from. We've allowed you to also add or remove sources—transparency is baked in. And clear, sourced references are provided at the end of each response.

Once the information is retrieved, the assistant explains it in plain language. If a lab value is out of range, it'll say so and offer to help you prepare questions for your next appointment—without telling you what treatment to start or stop. It watches for red-flag symptoms or mental health crises and immediately directs you to call emergency services or see a doctor instead of continuing the chat. All of this happens in real time, with conversations preserved for 24 hours so you can pick up where you left off, or cleared with one click if you'd rather start fresh.

## Real-World Impact

Imagine a caregiver juggling a parent's MyChart, LifeLabs, and provincial portals. Instead of hopping between apps, she can compile and interpret records in one place, ask "Do these labs suggest low iron?", and head to her next appointment prepared with questions—without replacing her doctor's judgment. 

For clinicians, that means fewer confused calls, fewer unnecessary visits, and patients who are better prepared for meaningful conversations. The provider mode gives healthcare professionals access to technical literature and clinical resources without the patient-focused restrictions, supporting their professional needs.

## Looking Forward

We're not trying to replace doctors or clinical judgment. We're trying to build a responsible middle ground—a tool that respects both the reality that people will seek health information online and the critical importance of professional medical care.

If you'd like to try My Health Assistant or give feedback, send a message to any of us—Stewart McKendry, Dr. Keith Thompson, or Will Falk—and we'll share access. Your experience will help shape safer, smarter AI support for patients while respecting the guardrails clinicians have rightly demanded.

---

## About Dr. Thompson

As a family physician and researcher, Dr. Thompson spent the past years trying to reconcile technology with the compassionate, patient-centred clinical method. His mentor, Dr. Ian McWhinney, often reminded him that family medicine is as much an art as a science, requiring presence, trust, and careful listening. Tools like My Health Assistant won't replace that encounter—but they can help prepare patients and caregivers to use precious time with their clinician more wisely. If designed with humility and the right guardrails, AI can support—not erode—the craft of family medicine.

---

*Note: There's a clinician-focused view with more technical language and broader domain access, but that's behind a password and outside what most people need.*