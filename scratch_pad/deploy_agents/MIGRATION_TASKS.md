# Ontario Healthcare AI Agents - Migration Task List

## Phase 1: Pre-Migration Preparation (On Current Branch)
*Stay on `feat/dr-off-agent-worktree` branch*

### 1.1 Database Preparation
- [ ] Inventory all databases and their sizes
  ```bash
  ls -lh data/*.db
  du -sh data/*/chroma
  ```
- [ ] Test SQLite databases are working
  ```bash
  sqlite3 data/ohip.db "SELECT COUNT(*) FROM schedule_benefits;"
  sqlite3 data/dr_opa_conversations.db "SELECT COUNT(*) FROM conversations;"
  sqlite3 data/dr_off_conversations.db "SELECT COUNT(*) FROM conversations;"
  sqlite3 data/orchestrator_conversations.db "SELECT COUNT(*) FROM conversations;"
  ```
- [ ] Document database schemas
  ```bash
  sqlite3 data/ohip.db ".schema" > scratch_pad/deploy_agents/schemas/ohip_schema.sql
  ```

### 1.2 Create Migration Scripts
- [ ] Create database backup script
  ```bash
  touch scratch_pad/deploy_agents/scripts/backup_databases.sh
  ```
- [ ] Create ChromaDB export script
  ```bash
  touch scratch_pad/deploy_agents/scripts/export_chroma.py
  ```
- [ ] Create PostgreSQL migration script
  ```bash
  touch scratch_pad/deploy_agents/scripts/migrate_to_postgres.py
  ```
- [ ] Create Railway init script
  ```bash
  touch scratch_pad/deploy_agents/scripts/init_railway_volume.sh
  ```

### 1.3 Environment Configuration
- [ ] Document all required environment variables
  ```bash
  touch scratch_pad/deploy_agents/env_variables.md
  ```
- [ ] Create `.env.production` template
- [ ] Create `.env.railway` template
- [ ] List all API keys needed:
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - LANGFUSE_PUBLIC_KEY
  - LANGFUSE_SECRET_KEY
  - EXA_API_KEY (if used)

### 1.4 Code Updates for Cloud Compatibility
- [ ] Update database connection logic in `src/config/database.py`
- [ ] Add environment detection (local vs Railway)
- [ ] Update ChromaDB paths to use environment variables
- [ ] Update conversation DB paths
- [ ] Add connection pooling for PostgreSQL

### 1.5 Test Locally with Docker
- [ ] Create `Dockerfile` for Railway
- [ ] Create `docker-compose.yml` for local testing
- [ ] Test backend runs in Docker
- [ ] Test database connections work

## Phase 2: Merge to Main Branch
*Critical decision point*

### 2.1 Pre-Merge Checklist
- [ ] All tests passing on feature branch
- [ ] Create backup of current main branch
  ```bash
  git checkout main
  git checkout -b main-backup-$(date +%Y%m%d)
  git checkout feat/dr-off-agent-worktree
  ```
- [ ] Document what's different between branches
- [ ] Ensure no conflicts with existing Health Assistant code

### 2.2 Merge Strategy
- [ ] **MERGE TO MAIN** (Choose one approach):
  
  **Option A: Clean Merge (Recommended)**
  ```bash
  git checkout main
  git pull origin main
  git merge feat/dr-off-agent-worktree --no-ff
  git push origin main
  ```
  
  **Option B: Squash Merge (Cleaner history)**
  ```bash
  git checkout main
  git merge --squash feat/dr-off-agent-worktree
  git commit -m "feat: add Ontario Healthcare AI Agents (Dr. OPA, Dr. OFF, Agent 97, Chief)"
  git push origin main
  ```

### 2.3 Post-Merge Verification
- [ ] Verify main branch has all agent files
- [ ] Check existing Health Assistant still works
- [ ] Run all tests on main branch
- [ ] Tag the release
  ```bash
  git tag -a v2.0.0-agents -m "Added Ontario Healthcare AI Agents"
  git push origin v2.0.0-agents
  ```

## Phase 3: Set Up Cloud Services
*Now working on main branch*

### 3.1 Railway Setup
- [ ] Create Railway account (if needed)
- [ ] Install Railway CLI
  ```bash
  npm install -g @railway/cli
  railway login
  ```
- [ ] Create new Railway project
  ```bash
  railway init --name ontario-health-backend
  ```
- [ ] Add persistent volume for data
  ```bash
  railway volume create health-data --mount /app/data
  ```

### 3.2 Database Setup
- [ ] **Choose SQL solution**:
  - [ ] Option 1: Neon.tech (Recommended - 3GB free)
    - Create account at neon.tech
    - Create database `ontario_health`
    - Get connection string
  - [ ] Option 2: Railway PostgreSQL ($5/month)
    ```bash
    railway add postgresql
    ```
  - [ ] Option 3: Keep SQLite on Railway volume

- [ ] Test database connection
- [ ] Set DATABASE_URL in Railway

### 3.3 Vercel Projects Setup
- [ ] Create Vercel account (if needed)
- [ ] Install Vercel CLI
  ```bash
  npm install -g vercel
  vercel login
  ```
- [ ] Create two Vercel projects:
  ```bash
  cd web
  vercel --name ontario-health-agents
  vercel --name ontario-health-assistant
  ```

## Phase 4: Database Migration
*Execute migration scripts*

### 4.1 Backup Local Data
- [ ] Run backup script
  ```bash
  ./scratch_pad/deploy_agents/scripts/backup_databases.sh
  ```
- [ ] Verify backups created
- [ ] Upload backups to cloud storage (optional)

### 4.2 Migrate SQL Data
- [ ] If using PostgreSQL:
  ```bash
  python scratch_pad/deploy_agents/scripts/migrate_to_postgres.py
  ```
- [ ] If keeping SQLite:
  ```bash
  scp data/*.db railway:/app/data/
  ```
- [ ] Verify data migrated correctly

### 4.3 Migrate Vector Data
- [ ] Export ChromaDB collections
  ```bash
  python scratch_pad/deploy_agents/scripts/export_chroma.py
  ```
- [ ] Upload to Railway volume
- [ ] Verify vector search works

## Phase 5: Deploy Backend to Railway

### 5.1 Railway Configuration
- [ ] Create `railway.toml` in project root
- [ ] Configure build and start commands
- [ ] Set all environment variables in Railway dashboard:
  ```bash
  railway variables set ANTHROPIC_API_KEY=xxx
  railway variables set OPENAI_API_KEY=xxx
  railway variables set DATABASE_URL=xxx
  railway variables set CHROMA_PERSIST_DIR=/app/data/chroma
  ```

### 5.2 Deploy Backend
- [ ] Push to Railway
  ```bash
  railway up
  ```
- [ ] Check deployment logs
  ```bash
  railway logs
  ```
- [ ] Test health endpoint
  ```bash
  curl https://your-app.railway.app/health
  ```
- [ ] Test each agent endpoint

## Phase 6: Deploy Frontends to Vercel

### 6.1 Configure AI Agents Frontend
- [ ] Set environment variables for agents app:
  ```bash
  cd web
  vercel env add NEXT_PUBLIC_APP_MODE=agents
  vercel env add NEXT_PUBLIC_API_URL=https://your-app.railway.app
  vercel env add NEXT_PUBLIC_APP_TITLE="Ontario Healthcare AI Agents"
  ```
- [ ] Deploy agents frontend
  ```bash
  vercel --prod --project ontario-health-agents
  ```
- [ ] Set custom domain: `agents.yourdomain.com`

### 6.2 Configure Health Assistant Frontend
- [ ] Set environment variables for health app:
  ```bash
  vercel env add NEXT_PUBLIC_APP_MODE=health
  vercel env add NEXT_PUBLIC_API_URL=https://your-app.railway.app
  vercel env add NEXT_PUBLIC_APP_TITLE="Health Assistant"
  ```
- [ ] Deploy health frontend
  ```bash
  vercel --prod --project ontario-health-assistant
  ```
- [ ] Set custom domain: `health.yourdomain.com`

## Phase 7: Testing & Validation

### 7.1 Functional Testing
- [ ] Test Dr. OPA agent
- [ ] Test Dr. OFF agent  
- [ ] Test Agent 97
- [ ] Test Chief orchestrator
- [ ] Test Health Assistant (existing functionality)
- [ ] Test conversation persistence
- [ ] Test vector search functionality

### 7.2 Performance Testing
- [ ] Test response times
- [ ] Test concurrent users
- [ ] Monitor Railway metrics
- [ ] Check Vercel Analytics

### 7.3 UI/UX Testing
- [ ] Verify agents UI loads correctly
- [ ] Verify health assistant UI unchanged
- [ ] Test mobile responsiveness
- [ ] Test chat interactions
- [ ] Test streaming responses

## Phase 8: DNS & Domain Setup

### 8.1 Domain Configuration
- [ ] Point `agents.yourdomain.com` to Vercel
- [ ] Point `health.yourdomain.com` to Vercel
- [ ] Point `api.yourdomain.com` to Railway (optional)
- [ ] Wait for DNS propagation
- [ ] Verify SSL certificates active

## Phase 9: Monitoring & Logging

### 9.1 Setup Monitoring
- [ ] Enable Vercel Analytics
- [ ] Enable Railway metrics
- [ ] Setup Langfuse tracing
- [ ] Configure error tracking (Sentry free tier)

### 9.2 Setup Alerts
- [ ] Railway health check alerts
- [ ] Database connection alerts
- [ ] API error rate alerts

## Phase 10: Documentation & Handoff

### 10.1 Update Documentation
- [ ] Update README with deployment info
- [ ] Document environment variables
- [ ] Create runbook for common issues
- [ ] Document rollback procedure

### 10.2 Create Admin Guide
- [ ] How to view logs
- [ ] How to restart services
- [ ] How to update environment variables
- [ ] How to deploy updates

## Rollback Plan

### If Issues Occur:
1. [ ] Frontend rollback:
   ```bash
   vercel rollback
   ```

2. [ ] Backend rollback:
   ```bash
   railway rollback
   ```

3. [ ] Database restore:
   ```bash
   python scratch_pad/deploy_agents/scripts/restore_backup.py
   ```

4. [ ] Switch back to feature branch:
   ```bash
   git checkout feat/dr-off-agent-worktree
   ```

## Success Criteria

- [ ] Both frontends accessible via custom domains
- [ ] All 4 agents responding correctly
- [ ] Health Assistant functionality preserved
- [ ] Conversations persisting across sessions
- [ ] Vector search returning relevant results
- [ ] Response time < 3 seconds
- [ ] No errors in logs for 24 hours
- [ ] Costs within budget ($5-10/month)

## Notes

- **Critical**: Test everything on feature branch before merging
- **Merge Timing**: Choose low-traffic time for merge to main
- **Backup**: Keep local backups until cloud is stable for 1 week
- **Secrets**: Never commit API keys, use environment variables
- **Monitoring**: Check Railway usage to stay within limits