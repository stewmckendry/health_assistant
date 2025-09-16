# Health Assistant Web Application

## Overview
Modern Next.js 14 web interface for the AI Health Assistant, providing:
- Real-time chat with PatientAssistant
- Citation display with trusted sources
- User feedback collection
- Session management
- Dark mode support
- Mobile responsive design

## Tech Stack
- **Frontend**: Next.js 14 with App Router
- **UI**: Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python)
- **Observability**: Langfuse
- **State**: Local storage + session API

## Project Structure
```
web/
├── app/                    # Next.js App Router
│   ├── api/               # API Routes
│   │   ├── chat/         # Chat endpoint
│   │   ├── feedback/     # Feedback submission
│   │   └── sessions/     # Session management
│   ├── layout.tsx        # Root layout with theme
│   └── page.tsx          # Main chat page
├── components/
│   ├── chat/             # Chat components
│   │   ├── ChatInterface.tsx
│   │   ├── Message.tsx
│   │   └── FeedbackButtons.tsx
│   ├── ui/               # shadcn/ui components
│   ├── theme-provider.tsx
│   └── theme-toggle.tsx
├── hooks/
│   └── useSession.ts     # Session management hook
├── lib/
│   ├── python-backend.ts # Backend API client
│   └── langfuse-client.ts # Langfuse tracking
└── types/
    └── chat.ts           # TypeScript types
```

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Environment variables configured

### Installation
```bash
# Install dependencies
npm install

# Copy environment variables
cp ../.env .env.local
```

### Development
```bash
# Start both servers (from project root)
../scripts/start_servers.sh

# Or separately:
# Backend (from project root)
python -m uvicorn src.web.api.main:app --reload --port 8000

# Frontend (from web directory)
npm run dev
```

### Environment Variables
Required in `.env.local`:
```env
ANTHROPIC_API_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY=
PYTHON_BACKEND_URL=http://localhost:8000
```

## Features

### Chat Interface
- Multi-turn conversations
- Real-time streaming responses
- Citation display from trusted sources
- Guardrail status indicators
- Loading states and error handling

### Feedback System
- Thumbs up/down rating
- 5-star rating
- Comment submission
- Linked to Langfuse traces

### Session Management
- Persistent sessions across refreshes
- New session creation
- User ID tracking (anonymous)
- 24-hour session expiry

### Dark Mode
- System preference detection
- Manual toggle
- Persistent preference

### Mobile Responsive
- Touch-friendly interface
- Adaptive layout
- Optimized for small screens

## API Endpoints

### Next.js API Routes
- `POST /api/chat` - Process chat messages
- `POST /api/feedback` - Submit user feedback
- `GET/POST /api/sessions` - Manage sessions

### Python Backend
- `POST /chat` - PatientAssistant query
- `POST /feedback` - Store feedback
- `GET /sessions/{id}` - Get session data

## Testing
```bash
# Run tests
npm test

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Deployment
```bash
# Build for production
npm run build

# Start production server
npm start
```

## Notes
- No PHI storage (demo only)
- Medical disclaimers always visible
- WCAG 2.1 AA accessibility target
- Performance: <3s load, <1s response
