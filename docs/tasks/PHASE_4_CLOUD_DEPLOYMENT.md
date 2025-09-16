# Phase 4: Cloud Deployment

## 🚀 Ready to Deploy!

Your development environment is set up:
- **GitHub Issue**: #9 - Phase 4: Cloud Deployment to Vercel and Railway
- **Branch**: `phase-4-cloud-deployment`
- **Worktree**: `../health_assistant_phase4_cloud`

## 📍 Current State

### What's Ready
- ✅ Full-featured web application (Next.js + FastAPI)
- ✅ Patient and Provider modes with mode switching
- ✅ Langfuse cloud integration already configured
- ✅ `python-backend.ts` created with configurable backend URL
- ✅ All tests passing locally

### What Needs Deployment
- **Frontend**: Next.js app currently runs on localhost:3000
- **Backend**: FastAPI app currently runs on localhost:8000
- **Sessions**: In-memory storage (no changes needed)

## 🎯 Phase 4 Objectives

Deploy the Health Assistant to cloud platforms:
1. **Frontend to Vercel** - Free tier, auto-deploy from GitHub
2. **Backend to Railway** - Simple Python app deployment
3. **Minimal changes** - Keep it simple, no extra infrastructure

## 📝 Deployment Steps

### 1. Backend Deployment (Railway) - Do First!
```bash
cd ../health_assistant_phase4_cloud
```

**Steps:**
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. New Project → Deploy from GitHub repo
4. Select `stewmckendry/health_assistant`
5. Configure:
   - **Root Directory**: `/` (leave as default)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
7. Deploy and get public URL (e.g., `https://health-assistant.railway.app`)

### 2. Frontend Deployment (Vercel)

**Prepare the code:**
```bash
# Create .env.local for Vercel
echo "NEXT_PUBLIC_BACKEND_URL=https://health-assistant.railway.app" > web/.env.local
```

**Deploy to Vercel:**
1. Go to [vercel.com](https://vercel.com)
2. Sign in with GitHub
3. Import Project → Import Git Repository
4. Select `stewmckendry/health_assistant`
5. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `web`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
6. Add Environment Variable:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://health-assistant.railway.app
   ```
7. Deploy!

### 3. Update CORS Settings

Edit `src/web/api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://health-assistant.vercel.app",  # Add your Vercel URL
        "https://*.vercel.app"  # Allow Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Test Everything

1. **Health Check**: 
   - Frontend: `https://health-assistant.vercel.app`
   - Backend: `https://health-assistant.railway.app/health`
   - API Docs: `https://health-assistant.railway.app/docs`

2. **Test Chat**:
   - Try patient mode query
   - Switch to provider mode
   - Verify citations work
   - Check Langfuse tracking

3. **Test Session Persistence**:
   - Start conversation
   - Refresh page
   - Continue conversation

## 🛠️ Files to Create/Modify

### Required Files
- [x] `web/lib/python-backend.ts` - Already created ✅
- [ ] `web/.env.example` - Template for environment variables
- [ ] `.env.example` - Root level for backend
- [ ] Update `src/web/api/main.py` - CORS settings

### Example .env Files

**web/.env.example**:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**.env.example** (root):
```env
ANTHROPIC_API_KEY=your-api-key-here
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 💡 Deployment Notes

### Railway Specifics
- Railway provides `$PORT` environment variable automatically
- Python buildpack auto-detected from requirements.txt
- No Dockerfile needed for simple Python apps
- Free tier includes 500 hours/month

### Vercel Specifics
- Auto-deploys on push to main branch
- Preview deployments for PRs
- Environment variables can be scoped (Production/Preview/Development)
- Free tier includes unlimited deployments

### Session Storage
- Keeping in-memory storage for simplicity
- Sessions reset when backend restarts
- Acceptable for demo/testing purposes
- Can upgrade to Redis later if needed

## 🔧 Troubleshooting

### Backend Issues
- **Import errors**: Ensure `PYTHONPATH` includes src directory
- **Port binding**: Use `$PORT` environment variable
- **CORS errors**: Check allowed origins in FastAPI

### Frontend Issues
- **API connection**: Verify `NEXT_PUBLIC_BACKEND_URL` is set
- **Build errors**: Check Node version (18+ required)
- **Type errors**: Run `npm run build` locally first

### Integration Issues
- **CORS**: Update allowed origins in backend
- **Timeouts**: Railway has 5-minute timeout by default
- **Rate limits**: Check Anthropic API rate limits

## ✅ Success Criteria

- [ ] Backend deployed and accessible via public URL
- [ ] Frontend deployed and accessible via public URL
- [ ] Chat functionality works in both modes
- [ ] Citations display correctly
- [ ] Langfuse tracking operational
- [ ] Session persistence works (within memory limits)
- [ ] External testers can access the app

## 🚦 Ready to Deploy!

Your next steps:
1. Open worktree: `cd ../health_assistant_phase4_cloud`
2. Deploy backend to Railway first (get the URL)
3. Deploy frontend to Vercel with backend URL
4. Update CORS settings
5. Test everything!

Good luck with the deployment! 🎉