# Deployment Instructions - Step by Step

## ✅ Completed
- Database backup created: `scratch_pad/deploy_agents/backups/20250928_230159`
- Apps tested locally (Frontend on port 3001, Backend on port 8001)

## 🚀 Ready for Testing

### Test Health Assistant Locally
**Open in browser: http://localhost:3001**

Test these features:
1. Chat interface works (Patient mode)
2. Provider mode toggle
3. Settings panel
4. Session persistence

### Test AI Agents Locally  
**Open in browser: http://localhost:3001/agents**

Should see:
1. Agent registry page
2. Dr. OPA, Dr. OFF, Agent 97, Chief cards
3. Individual agent chat interfaces

---

## 📋 Next Steps - Railway Setup

### Step 1: Merge to Main Branch
```bash
# After testing is complete
git add .
git commit -m "chore: prepare for deployment"
git checkout main
git pull origin main
git merge feat/dr-off-agent-worktree --no-ff -m "feat: add Ontario Healthcare AI Agents"
git push origin main
```

### Step 2: Sign up for Railway
1. Go to https://railway.app
2. Sign up with GitHub (recommended)
3. Choose Hobby plan ($5/month)

### Step 3: Install Railway CLI
```bash
# Install via npm (you already have npm)
npm install -g @railway/cli

# Or via brew if you prefer
brew install railway
```

### Step 4: Create Railway Project
```bash
# Login to Railway
railway login

# Initialize new project
railway init
# Choose: "Empty Project"
# Name it: "ontario-health-backend"
```

### Step 5: Add Database (Choose One)

#### Option A: Free PostgreSQL (Neon.tech) - RECOMMENDED
1. Go to https://neon.tech
2. Sign up (free)
3. Create database "ontario_health"
4. Copy connection string
5. In Railway:
```bash
railway variables set DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/ontario_health"
```

#### Option B: Railway PostgreSQL ($5-7/month extra)
```bash
railway add postgresql
# DATABASE_URL will be auto-set
```

#### Option C: SQLite on Volume (simplest)
```bash
# Create persistent volume
railway volume add
# Name: data-volume
# Mount: /app/data
```

### Step 6: Set Environment Variables in Railway
```bash
# Set all required variables
railway variables set ANTHROPIC_API_KEY="your-key-here"
railway variables set OPENAI_API_KEY="your-key-here"  
railway variables set LANGFUSE_PUBLIC_KEY="your-key-here"
railway variables set LANGFUSE_SECRET_KEY="your-key-here"
railway variables set LANGFUSE_HOST="https://us.cloud.langfuse.com"
railway variables set CHROMA_PERSIST_DIR="/app/data/chroma"
railway variables set PYTHONPATH="/app"
```

### Step 7: Create Railway Configuration Files
```bash
# Create railway.toml
cat > railway.toml << 'EOF'
[build]
builder = "nixpacks"

[deploy]
startCommand = "source /opt/venv/bin/activate && uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[mounts]]
source = "data-volume"
destination = "/app/data"
EOF

# Create nixpacks.toml  
cat > nixpacks.toml << 'EOF'
[phases.setup]
nixPkgs = ["python311", "gcc"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT"
EOF
```

### Step 8: Deploy to Railway
```bash
# Deploy the backend
railway up

# Watch the logs
railway logs

# Get your app URL
railway open
# Your URL will be something like: https://ontario-health-backend-production.up.railway.app
```

---

## 🎨 Vercel Setup (Frontend)

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Deploy AI Agents App
```bash
cd web

# Deploy as agents app
vercel --name ontario-health-agents
# Choose:
# - Set up and deploy? Y
# - Which scope? (your username)
# - Link to existing project? N
# - What's your project's name? ontario-health-agents
# - In which directory? ./
# - Want to modify settings? N

# Set environment variables
vercel env add NEXT_PUBLIC_API_URL
# Enter: https://ontario-health-backend-production.up.railway.app

vercel env add NEXT_PUBLIC_APP_MODE
# Enter: agents

# Deploy to production
vercel --prod
```

### Step 3: Deploy Health Assistant App
```bash
# Still in web directory
vercel --name ontario-health-assistant

# Set different environment variables
vercel env add NEXT_PUBLIC_API_URL
# Enter: https://ontario-health-backend-production.up.railway.app

vercel env add NEXT_PUBLIC_APP_MODE  
# Enter: health

# Deploy to production
vercel --prod
```

### Step 4: Set Custom Domains (Optional)
In Vercel Dashboard:
1. Go to ontario-health-agents project
2. Settings → Domains
3. Add: agents.yourdomain.com

4. Go to ontario-health-assistant project
5. Settings → Domains  
6. Add: health.yourdomain.com

---

## 🔍 Verification Checklist

### Backend (Railway)
- [ ] https://your-app.railway.app/health returns {"status": "healthy"}
- [ ] https://your-app.railway.app/docs shows FastAPI docs

### Frontend (Vercel)
- [ ] Agents app: https://ontario-health-agents.vercel.app
- [ ] Health app: https://ontario-health-assistant.vercel.app
- [ ] Both can connect to backend API

### Test Each Agent
- [ ] Dr. OPA responds
- [ ] Dr. OFF responds  
- [ ] Agent 97 responds
- [ ] Chief orchestrator works
- [ ] Health Assistant (patient/provider) works

---

## 🔧 Troubleshooting

### Railway Issues

**"Build failed"**
```bash
# Check logs
railway logs

# Common fix: add Python version
railway variables set PYTHON_VERSION="3.11"
```

**"Module not found"**
```bash
# Set PYTHONPATH
railway variables set PYTHONPATH="/app"
```

**"Database connection failed"**
- If using Neon: Check connection string
- If using SQLite: Ensure volume is mounted

### Vercel Issues

**"API calls failing"**
- Check NEXT_PUBLIC_API_URL is set correctly
- Ensure no trailing slash in URL
- Check CORS settings in backend

**"Wrong app showing"**
- Check NEXT_PUBLIC_APP_MODE environment variable
- Clear browser cache
- Redeploy with correct settings

---

## 📱 Quick Test URLs

Once deployed:

**AI Agents App:**
- Home: https://ontario-health-agents.vercel.app
- Dr. OPA: https://ontario-health-agents.vercel.app/agents/dr-opa
- Dr. OFF: https://ontario-health-agents.vercel.app/agents/dr-off

**Health Assistant App:**
- Home: https://ontario-health-assistant.vercel.app
- Chat: https://ontario-health-assistant.vercel.app/chat

**Backend API:**
- Health: https://your-app.railway.app/health
- Docs: https://your-app.railway.app/docs

---

## 💰 Cost Summary

### Current Setup (Recommended)
- Railway Hobby: $5/month
- Neon PostgreSQL: FREE (3GB)
- Vercel (2 apps): FREE
- **Total: $5/month**

### With Railway PostgreSQL
- Railway Hobby: $5/month  
- Railway PostgreSQL: ~$5-7/month
- Vercel: FREE
- **Total: $10-12/month**

---

## 🚨 Important Notes

1. **DO NOT COMMIT** .env files or API keys
2. **TEST LOCALLY** before deploying
3. **BACKUP DATA** before migrations
4. **MONITOR USAGE** on Railway dashboard
5. **CHECK LOGS** if anything fails

---

## Ready to Deploy?

You're all set! The apps are running locally for testing:
- Frontend: http://localhost:3001
- Backend: http://localhost:8001

Once you've tested and are happy, follow the Railway and Vercel steps above.