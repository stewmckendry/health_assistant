# White Coat Black Box: Helping Patients Ask Smarter Questions

By Stewart McKendry, Dr. Keith Thompson, and Will Falk

---

Away from the sports field and back to healthcare again with my former colleague Will Falk—this time joined by primary care doctor Keith Thompson—we've been tinkering with something new. We're calling it My Health Assistant (working name: White Coat Black Box). It's an experiment to see if an AI helper can give patients plain-language explanations they can trust, without wandering into territory that belongs to a doctor.

A few weeks back, Will and I were listening to Dr. Danielle Martin and Dr. Brian Goldman on their podcast, batting around the whole "Dr. AI" question. Both are seasoned Canadian physicians who've seen plenty of tech promises come and go, and their worries were blunt. Danielle talked about patients who arrive with printouts that derail visits or create unnecessary anxiety. Brian noted that too many chatbots sound confident but get facts wrong—or worse, stray into handing out diagnoses or prescriptions. They flagged real dangers: bad information, fragmented care, and the risk of patients skipping or delaying real medical attention because a bot falsely reassured them.

That got us thinking: people are always going to look up health information—telling them not to isn't realistic. So rather than shrug off those objections, we decided to meet them head-on. My Health Assistant is our attempt to build something that stays firmly inside the lines: answers only from excellent, verifiable sources (with a soft spot for Canadian guidance when it exists), a hard stop on diagnosing or prescribing, and clear reminders when it's time to talk to a professional instead of a bot.

## See It In Action

Before diving into how it works, let me show you what it actually does. We've created several short demos that capture different use cases:

**Basic Health Questions**  
Watch how the assistant handles common queries like "What are the symptoms of flu?" with proper citations and educational disclaimers:  
[Health Assistant - Patient Mode - Flu Symptoms](https://drive.google.com/file/d/1JZWXpSYdEErrUZhsZIEBCIRJeQLaKAuI/view?usp=drive_link)

**Complex Medical Scenarios**  
See it navigate nuanced questions about diabetes with multiple symptoms while maintaining clear boundaries:  
[Health Assistant - Patient Mode - Diabetes and Headaches](https://drive.google.com/file/d/1DwwQ5jQj_FdPlxkHVRRncbOlcwQ3CuJL/view?usp=drive_link)

**Provider Mode**  
Healthcare professionals get access to technical terminology and clinical guidance, shown here with a pediatric growth question:  
[Health Assistant - Provider Mode - Pediatric Growth Assessment](https://drive.google.com/file/d/1-LH28bV9YXx73aoFTIs-oz43mH9HHOB9/view?usp=drive_link)

## Why This Isn't Just ChatGPT in a Lab Coat

You might wonder: "Can't I just ask ChatGPT or Claude these same questions?" You could—but here's what makes My Health Assistant different, and why those differences matter for healthcare.

Large Language Models (LLMs) like Claude or ChatGPT are incredibly capable, but they're designed to be helpful above all else. Ask them a medical question, and they'll often give you an answer that sounds authoritative—even when they shouldn't. Think of it this way: a raw LLM is like a brilliant medical student who's read every textbook but has no clinical judgment about when to stop talking and call for help.

We took Claude (from Anthropic) and gave it three critical upgrades:

**Trusted Information Only**  
Instead of letting the AI search the entire internet, we implemented what's called RAG—Retrieval-Augmented Generation. In simple terms, we gave the AI a curated library card. It can only pull information from our vetted list of 97 trusted sources. No random blogs, no forums, no questionable "miracle cure" websites.

**Input Guardrails**  
Before your question even reaches the AI, we check it against patterns that need immediate human help. Chest pain? Difficulty breathing? Thoughts of self-harm? The system immediately provides emergency resources and insists you seek real help—no AI response needed or appropriate. This isn't just keyword matching—we use a sophisticated combination that understands context.

**Output Guardrails**  
Even with the best instructions, LLMs can occasionally slip up. That's why every response goes through a final safety check before you see it. If the AI accidentally suggests a diagnosis or recommends a specific treatment, our guardrails catch it and either modify the response or block it entirely.

## How It Actually Works

Here's how it works under the hood. When you ask a question, My Health Assistant searches only in a vetted set of reliable places: Ontario Ministry of Health, Public Health Ontario, Health Canada, PHAC, provincial services like HealthLinkBC and Alberta Health Services, Canadian specialty groups like Diabetes Canada, Heart & Stroke, CMAJ, Choosing Wisely, and trusted U.S. academic centers such as Mayo Clinic, Johns Hopkins, Cleveland Clinic, UCSF, and Mount Sinai. It also pulls from first-rank journals like NEJM, The Lancet, JAMA, BMJ, Nature Medicine, and PubMed, plus global health authorities like WHO, CDC, NHS, EMA, and FDA. The assistant gives you numbered citations with clickable links so you can check exactly where an answer came from. The chatbot can only "see" the 97 sources we have provided (techies: this is a Claude 3.5 feature). We have allowed you to also add or remove sources—transparency is baked in. And clear, sourced references (a bibliography for the answer) are provided at the end.

Once the information is retrieved, the assistant explains it in plain language. If a lab value is out of range, it'll say so and offer to help you prepare questions for your next appointment—without telling you what treatment to start or stop. It watches for red-flag symptoms or mental health crises and immediately directs you to call emergency services or see a doctor instead of continuing the chat. All of this happens in real time, with conversations preserved for 24 hours so you can pick up where you left off, or cleared with one click if you'd rather start fresh.

## Proving It Works (Without Taking Our Word For It)

Building healthcare AI isn't like building regular software. With traditional code, you write it, test it, and know exactly what it will do every time. With AI, there's inherent uncertainty—the same question might generate slightly different responses. That's why evaluation isn't just important; it's essential.

We use Langfuse—an open platform that lets developers systematically test and evaluate AI applications—to create a comprehensive testing framework. Think of it as a quality control system specifically designed for AI, where you can track every interaction, score responses, and identify patterns. We created over 200 test cases covering every scenario we could imagine: basic health questions, emergency situations, mental health crises, attempts to get diagnoses, complex real-world scenarios with elderly patients or uninsured individuals, and even adversarial attempts to trick the AI.

We ran a batch of 50 test cases through different configurations of our system. Each response gets evaluated by five different AI judges looking at specific aspects:

- **Medical Accuracy** (97% score from AI evaluators)
- **Emergency Handling** (95%+ correctly identified and redirected crisis situations) 
- **Response Helpfulness** (96% appropriately addressed user queries)
- **Citation Quality** (74% properly sourced from trusted domains)
- **Safety Compliance** (100% avoided diagnosing, prescribing, personal advice)

The AI evaluators gave us scores above 95%—perhaps being a bit generous, which tells us we could refine the evaluation prompts. But the real test came when Dr. Thompson manually reviewed a subset as a practicing physician. His overall quality score? **88%**. This human expert validation matters more than the AI scores, giving us both confidence in what works and clear areas for improvement.

Every real user interaction is also traced and can be evaluated, allowing us to identify patterns where the assistant struggles, discover new edge cases, and continuously refine our guardrails.

See the evaluation platform in action:  
[Health Assistant - Langfuse Observing and Evaluating](https://drive.google.com/file/d/1ClBEbjeXRegbi-atgFS-sLWR7Z1lYrfP/view?usp=drive_link)

## What This Means In Practice

Imagine a caregiver juggling a parent's MyChart, LifeLabs, and provincial portals. Instead of hopping between apps, she can compile and interpret records in one place, ask "Do these labs suggest low iron?", and head to her next appointment prepared with questions—without replacing her doctor's judgment. For clinicians, that means fewer confused calls, fewer unnecessary visits, and patients who are better prepared for meaningful conversations.

If you'd like to try My Health Assistant or give feedback, send a message to any of us—Stewart McKendry, Dr. Keith Thompson, or Will Falk—and we'll share access. Your experience will help shape safer, smarter AI support for patients while respecting the guardrails clinicians have rightly demanded.

(Afterword: There's a clinician-focused view with more technical language and broader domain access, but that's behind a password and outside what most people need.)

---

## Dr. Thompson

As a family physician and researcher, Dr. Thompson spent the past years trying to reconcile technology with the compassionate, patient-centred clinical method. His mentor, Dr. Ian McWhinney, often reminded him that family medicine is as much an art as a science, requiring presence, trust, and careful listening. Tools like My Health Assistant won't replace that encounter—but they can help prepare patients and caregivers to use precious time with their clinician more wisely. If designed with humility and the right guardrails, AI can support—not erode—the craft of family medicine.