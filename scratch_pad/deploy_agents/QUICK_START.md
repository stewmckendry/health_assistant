# Quick Start Migration Guide

## When to Merge to Main

**Answer: After Phase 1.5 (local Docker testing)**

The merge happens AFTER you've:
1. Created all migration scripts
2. Tested locally with Docker
3. Verified everything works

But BEFORE you:
1. Set up cloud services
2. Deploy to Railway/Vercel
3. Migrate databases to cloud

## Critical Path (Fastest Route)

### Today (On feature branch)
```bash
# 1. Create backup
chmod +x scratch_pad/deploy_agents/scripts/backup_databases.sh
./scratch_pad/deploy_agents/scripts/backup_databases.sh

# 2. Test current branch works
python src/web/api/main.py  # Should start on port 8000
```

### Merge Day
```bash
# 3. Merge to main (after backup!)
git checkout main
git pull origin main
git merge feat/dr-off-agent-worktree --no-ff -m "feat: add Ontario Healthcare AI Agents"
git push origin main
```

### Deploy Day (On main branch)
```bash
# 4. Quick Railway setup
railway login
railway init
railway up

# 5. Quick Vercel setup  
cd web
vercel --prod

# Done! Both live in ~30 minutes
```

## Merge Decision Tree

```
Should I merge now?
│
├─ Have you tested the agents? 
│  └─ NO → Test first, then merge
│  └─ YES → Continue ↓
│
├─ Do you have backups?
│  └─ NO → Run backup script, then merge
│  └─ YES → Continue ↓
│
├─ Is main branch clean?
│  └─ NO → Clean up main first
│  └─ YES → MERGE NOW ✓
```

## Key Files to Check Before Merge

1. **Agents working?**
   - `src/agents/dr_opa_agent/` exists
   - `src/agents/dr_off_agent/` exists
   - `src/agents/diagnostic_orchestrator/` exists

2. **Databases present?**
   - `data/ohip.db` exists
   - `data/dr_opa_conversations.db` exists
   - ChromaDB folders exist

3. **API endpoints registered?**
   - Check `src/web/api/main.py` has all agents

## After Merge Checklist

- [ ] Main branch has all agent files
- [ ] Can still run `python src/web/api/main.py`
- [ ] Frontend still builds: `cd web && npm run build`
- [ ] Tag the release: `git tag v2.0.0-agents`