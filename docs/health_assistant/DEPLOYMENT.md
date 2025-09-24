# Health Assistant Cloud Deployment Guide

## 🚀 Production Deployment

The Health Assistant is deployed to production using:
- **Frontend**: Vercel (Next.js application)
- **Backend**: Railway (FastAPI server)
- **Monitoring**: Langfuse (Cloud)

## 📍 Production URLs

### Live Application
- **Frontend**: https://health-assistant-stewart-mckendrys-projects.vercel.app
- **Backend API**: https://healthassistant-production-3613.up.railway.app
- **API Documentation**: https://healthassistant-production-3613.up.railway.app/docs

## 🏗️ Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐
│                 │     │                  │
│     Vercel      │────▶│     Railway      │
│   (Frontend)    │     │    (Backend)     │
│                 │     │                  │
└─────────────────┘     └──────────────────┘
         │                       │
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │             │
              │  Langfuse   │
              │ (Monitoring)│
              │             │
              └─────────────┘
```

## 🔧 Deployment Configuration

### Backend (Railway)

**Platform**: Railway  
**Service**: healthassistant  
**Environment**: Production  
**Region**: US East  

#### Environment Variables
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

#### Start Command
```bash
uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT
```

#### Key Features
- Auto-deploy on push to `main` branch
- Health check endpoint: `/health`
- Session management (in-memory)
- CORS configured for Vercel domains

### Frontend (Vercel)

**Platform**: Vercel  
**Project**: health-assistant  
**Framework**: Next.js 15.5.3  
**Node Version**: 18.x  

#### Environment Variables
```env
NEXT_PUBLIC_BACKEND_URL=https://healthassistant-production-3613.up.railway.app
```

#### Build Settings
- **Framework Preset**: Next.js
- **Root Directory**: `web`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`

#### Deployment Protection
- **Status**: Disabled for public access
- **Note**: Can be enabled for staging environments

## 🚢 Deployment Process

### Automatic Deployments

Both platforms are configured for automatic deployments:

1. **Push to `main`** → Railway deploys backend
2. **Push to `main`** → Vercel deploys frontend
3. **PR created** → Vercel creates preview deployment

### Manual Deployment

#### Backend (Railway CLI)
```bash
# Link to project
railway link -p nurturing-communication

# Deploy manually
railway up

# Check logs
railway logs
```

#### Frontend (Vercel CLI)
```bash
# Deploy to production
vercel --prod

# Deploy preview
vercel

# Check deployment status
vercel ls
```

## 🔍 Monitoring & Debugging

### Health Checks

#### Backend Health
```bash
curl https://healthassistant-production-3613.up.railway.app/health
```
Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-16T14:00:00.000000"
}
```

#### Frontend Health
```bash
curl -I https://health-assistant-stewart-mckendrys-projects.vercel.app
```
Expected: `HTTP/2 200`

### Logs

#### Railway Logs
- Dashboard: https://railway.app/dashboard
- CLI: `railway logs`

#### Vercel Logs
- Dashboard: https://vercel.com/dashboard
- CLI: `vercel logs`

#### Langfuse Tracking
- Dashboard: https://us.cloud.langfuse.com
- View traces, scores, and user feedback

### Common Issues & Solutions

#### CORS Errors
**Problem**: Frontend can't connect to backend  
**Solution**: Update `allow_origins` in `src/web/api/main.py`:
```python
allow_origins=[
    "https://health-assistant.vercel.app",
    "https://health-assistant-*.vercel.app",
    "https://*.vercel.app"
]
```

#### Environment Variable Issues
**Problem**: API keys not working  
**Solution**: 
1. Check Railway/Vercel environment variables
2. Ensure no trailing spaces in values
3. Redeploy after changes

#### Build Failures
**Problem**: TypeScript or ESLint errors  
**Solution**:
1. Run `npm run build` locally first
2. Fix any type errors
3. Update ESLint config if needed

#### Session Persistence
**Problem**: Sessions lost after backend restart  
**Solution**: Currently using in-memory storage (by design). For persistence, implement Redis in future phase.

## 🔐 Security Considerations

### API Keys
- ✅ Stored as environment variables
- ✅ Never committed to repository
- ✅ Different keys for dev/prod

### CORS
- ✅ Restricted to specific domains
- ✅ Credentials allowed only for trusted origins

### Authentication
- ⚠️ Currently no user authentication (demo phase)
- 📝 Planned for Phase 7

## 📈 Performance Optimization

### Current Setup
- **Backend**: Single Railway dyno
- **Frontend**: Vercel Edge Network
- **Latency**: ~200-300ms API responses

### Optimization Tips
1. Enable Vercel Edge Functions for API routes
2. Implement caching for common queries
3. Use Railway's autoscaling (paid tier)
4. Add CDN for static assets

## 🔄 Rollback Procedures

### Railway Rollback
```bash
# List deployments
railway deployments

# Rollback to specific deployment
railway rollback <deployment-id>
```

### Vercel Rollback
```bash
# List deployments
vercel ls

# Promote previous deployment to production
vercel promote <deployment-url>
```

## 📊 Metrics & KPIs

Monitor these key metrics:

1. **Uptime**: Target 99.9%
2. **Response Time**: < 500ms p95
3. **Error Rate**: < 1%
4. **Daily Active Users**: Track via Langfuse

## 🆘 Emergency Contacts

- **Railway Status**: https://status.railway.app
- **Vercel Status**: https://www.vercel-status.com
- **Langfuse Status**: https://status.langfuse.com

## 🔮 Future Improvements

### Phase 5-7 Enhancements
- [ ] Add Redis for session persistence
- [ ] Implement user authentication
- [ ] Add rate limiting
- [ ] Set up staging environment
- [ ] Configure auto-scaling
- [ ] Add comprehensive error tracking (Sentry)
- [ ] Implement A/B testing framework
- [ ] Add GraphQL API layer

## 📝 Deployment Checklist

Before deploying to production:

- [ ] Run tests locally: `pytest`
- [ ] Build frontend: `npm run build`
- [ ] Check environment variables
- [ ] Update CORS settings if domains changed
- [ ] Test API endpoints
- [ ] Verify Langfuse tracking
- [ ] Update this documentation if needed

## 🎯 Quick Commands Reference

```bash
# Local Development
npm run dev                    # Start frontend dev server
uvicorn src.web.api.main:app  # Start backend server

# Deployment
vercel --prod                  # Deploy frontend to production
railway up                     # Deploy backend to production

# Monitoring
railway logs                   # View backend logs
vercel logs                    # View frontend logs

# Testing
curl https://healthassistant-production-3613.up.railway.app/health
curl https://health-assistant.vercel.app
```

---

*Last Updated: September 16, 2025*  
*Version: 1.0.0*  
*Phase 4 Complete ✅*