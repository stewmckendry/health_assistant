# Deployment Guide

This guide covers deployment instructions for both local development and Railway production environments.

## Architecture Overview

The system consists of:
1. **Main FastAPI Server** - Health Assistant & Agent endpoints
2. **MCP Servers** - Tool servers for Dr. OFF and Dr. OPA agents
3. **Next.js Frontend** - Web interface (deployed separately on Vercel)

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Virtual environment with dependencies installed
- Environment variables loaded from `.env`

### Starting Services Locally

Use the provided startup script that handles all services:

```bash
# From project root
./start_local.sh
```

This script:
1. Activates the Python virtual environment
2. Starts MCP servers in stdio mode (as child processes)
3. Launches the main FastAPI server on port 8000
4. Agents use stdio communication with MCP servers

### Manual Local Start (Alternative)

If you prefer to start services manually:

```bash
# Terminal 1: Main API server
source ~/spacy_env/bin/activate
python -m src.web.api.main

# The MCP servers are spawned automatically as child processes in stdio mode
```

### Local Environment Variables

Create a `.env` file in the project root:

```env
# API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
EXA_API_KEY=your_key_here

# Langfuse (optional)
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# Local development (no HTTP MCP)
USE_HTTP_MCP=false
```

## Railway Production Deployment

### Architecture on Railway

On Railway, MCP servers run as separate HTTP services because stdio communication doesn't work in containerized environments:

```
Main Process (PORT 8000)
├── FastAPI Server
├── MCP Dr. OFF Server (HTTP on port 8001)
└── MCP Dr. OPA Server (HTTP on port 8002)
```

### Railway Configuration

#### 1. Start Command

Update the start command in Railway settings:

```bash
bash src/web/api/start_railway.sh
```

#### 2. Environment Variables

Add these environment variables in Railway dashboard:

```env
# Required API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  
EXA_API_KEY=your_key_here

# Langfuse Tracing (optional but recommended)
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# MCP Server Configuration (auto-set by script, but can override)
MCP_DR_OFF_PORT=8001
MCP_DR_OPA_PORT=8002
MCP_DR_OFF_URL=http://localhost:8001
MCP_DR_OPA_URL=http://localhost:8002

# Railway will automatically set:
# PORT=<assigned_port>
# RAILWAY_ENVIRONMENT=production
```

#### 3. Build Configuration

Railway should auto-detect Python, but you can specify:

- **Builder**: Nixpacks or Dockerfile
- **Root Directory**: `/` (project root)
- **Build Command**: `pip install -r requirements.txt`

### How Railway Deployment Works

1. **start_railway.sh** executes on container start
2. Script sets `RAILWAY_ENVIRONMENT=true` triggering HTTP mode
3. MCP servers start as HTTP services on internal ports (8001, 8002)
4. Agents detect Railway environment and use `MCPServerStreamableHttp`
5. Main FastAPI server starts on `$PORT` (provided by Railway)
6. Agents connect to MCP servers via HTTP instead of stdio

### Deployment Process

1. **Push to GitHub**:
```bash
git push origin main
```

2. **Railway Auto-Deploy**:
- Railway detects push to main branch
- Builds and deploys automatically
- Check Railway dashboard for deployment status

3. **Verify Deployment**:
```bash
# Test health endpoint
curl https://healthassistant-production-3613.up.railway.app/health

# Test agent endpoints
curl -X POST https://healthassistant-production-3613.up.railway.app/agents/dr-off/stream \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test", "query": "What is code A001?", "userId": "test"}'
```

## Vercel Frontend Deployment

The Next.js frontend is deployed separately on Vercel:

### Environment Variables for Vercel

Add in Vercel dashboard:

```env
NEXT_PUBLIC_API_URL=https://healthassistant-production-3613.up.railway.app
```

### Deploy to Vercel

```bash
cd web
vercel --prod
```

## Troubleshooting

### Issue: Agents not responding on Railway

**Check MCP servers are running:**
- Look for startup logs showing MCP servers on ports 8001, 8002
- Verify `RAILWAY_ENVIRONMENT` is set
- Check Railway logs for any MCP server errors

### Issue: "Connection closed" errors

**Ensure MCP servers started before main API:**
- The startup script includes a 5-second delay
- If still failing, increase the delay in `start_railway.sh`

### Issue: Local development using HTTP mode accidentally

**Check environment:**
```bash
unset USE_HTTP_MCP
unset RAILWAY_ENVIRONMENT
```

### Issue: Frontend can't connect to backend

**Verify CORS and API URL:**
- Check `NEXT_PUBLIC_API_URL` in Vercel
- Ensure Railway URL is in CORS allowed origins in `main.py`

## Monitoring

### Railway Logs
- View in Railway dashboard under Deployments → View Logs
- Filter by service to see specific components

### Langfuse Tracing
- If configured, view traces at https://cloud.langfuse.com
- Check for successful agent executions and tool calls

### Health Checks
- Main API: `GET /health`
- Individual agents have internal health logging

## Rollback Procedure

### Railway
1. Go to Railway dashboard
2. Select the service
3. Go to Deployments tab
4. Click on a previous successful deployment
5. Click "Redeploy"

### Vercel
1. Go to Vercel dashboard
2. Select the project
3. Go to Deployments
4. Find previous deployment
5. Click "Promote to Production"