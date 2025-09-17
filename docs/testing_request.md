# Health Assistant Testing Request

Hi team,

I'd appreciate your help testing our new AI Health Assistant. Please visit: https://health-assistant-lndatvv6g-stewart-mckendrys-projects.vercel.app/

## App Features Overview

### **Dual Mode Operation**
- **Patient Mode** (Default): Educational health information with patient-friendly language
- **Provider Mode** (Password: `iunderstandthisisaresearchproject`): Technical/clinical information with access to 169 domains (vs 119 for patients)

### **Trusted Medical Sources**
- Powered by Claude with web search across 169 trusted medical domains
- Examples: Mayo Clinic, CDC, NIH, NEJM, JAMA, The Lancet, UpToDate
- All responses include numbered citations with verifiable links
- Prioritizes recent sources (<5 years) and Canadian/Ontario guidelines

### **Multi-Layer Safety System**
- **Emergency Detection**: Identifies medical emergencies and mental health crises
- **No Diagnosis/Treatment**: Strictly educational - won't provide personal diagnoses or treatment plans
- **Three-Layer Guardrails**: Input checking, output validation, and hybrid LLM/regex verification
- **14 Violation Categories**: Monitors for inappropriate medical advice

### **Enhanced User Experience**
- **Real-Time Streaming**: Responses start appearing in <1 second
- **Multi-Turn Conversations**: Full context preservation across 24-hour sessions
- **Message Regeneration**: Re-generate responses while keeping conversation history
- **Multilingual Support**: 7 languages with localized emergency resources
- **Session Controls**: New session, clear conversation, settings viewer

### **Performance Features**
- **Citation Deduplication**: Automatically filters redundant sources
- **Markdown Formatting**: Rich text for better readability
- **Mobile Responsive**: Works seamlessly on all devices

## Feedback Requested

For each feature tested:
- ⭐ Rate 1-5 stars
- 💬 Add specific comments about what worked/didn't work
- 🐛 Note any bugs or unexpected behaviors

## Langfuse Evaluation

I'll be running automated quality evaluations using Langfuse:
- Generated bank of 200+ medical test cases
- Will run batches through the system
- You'll receive results to review and "grade" the AI's responses
- Helps us measure accuracy, safety, and usefulness at scale

Thanks for your help!