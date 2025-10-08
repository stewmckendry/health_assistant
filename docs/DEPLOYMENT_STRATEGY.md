# Vercel + Railway Deployment Strategy

## Architecture Overview

```
┌──────────────────┐         ┌──────────────────┐
│  Vercel Frontend │         │  Vercel Frontend │
│  (AI Agents)     │         │ (Health Assistant)│
│ agents.domain.com│         │  main.domain.com │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         ▼                            ▼
┌──────────────────────────────────────────────┐
│           Railway Backend (Shared)            │
│         api.your-railway-app.up               │
├──────────────────────────────────────────────┤
│  • /agents/* endpoints (Dr OPA, OFF, 97)     │
│  • /chat endpoint (Health Assistant)         │
│  • ChromaDB (persistent volume)              │
│  • SQLite → PostgreSQL (Railway)             │
└──────────────────────────────────────────────┘
```

## Database Strategy

### SQL Databases - Options

#### Option 1: Railway PostgreSQL ($5/month)
```bash
# Add PostgreSQL to Railway
railway add postgresql

# Connection available as $DATABASE_URL
```

#### Option 2: Neon.tech PostgreSQL (Free - 3GB)
```bash
# Create free account at neon.tech
# Get connection string
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname
```

#### Option 3: Supabase (Free - 500MB)
```bash
# Best for smaller datasets
# Includes auth, realtime, storage
```

#### Option 4: Keep SQLite on Railway Persistent Volume
```bash
# Mount volume in Railway
# /app/data → persistent volume
# SQLite files persist between deploys
```

### ChromaDB on Railway
```dockerfile
# Dockerfile for Railway
FROM python:3.11

# Create persistent directory
RUN mkdir -p /app/data/chroma

# Mount volume here
VOLUME ["/app/data"]

# ChromaDB will use persistent path
ENV CHROMA_PERSIST_DIR=/app/data/chroma
```

## Migration Scripts

### 1. SQLite to PostgreSQL Migration
```python
# scripts/migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os

def migrate_ohip_to_postgres():
    # Source SQLite
    sqlite_conn = sqlite3.connect('data/ohip.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    # Target PostgreSQL (Railway or Neon)
    pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    pg_cur = pg_conn.cursor()
    
    # Create tables
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS schedule_benefits (
            id SERIAL PRIMARY KEY,
            fee_code VARCHAR(10),
            description TEXT,
            fee_amount DECIMAL(10,2),
            effective_date DATE
        )
    ''')
    
    # Copy data
    sqlite_cur = sqlite_conn.execute('SELECT * FROM schedule_benefits')
    for row in sqlite_cur:
        pg_cur.execute(
            'INSERT INTO schedule_benefits VALUES (%s, %s, %s, %s)',
            tuple(row)
        )
    
    pg_conn.commit()
    print("✓ OHIP data migrated")

def migrate_conversations():
    """Migrate conversation databases"""
    dbs = [
        'dr_opa_conversations.db',
        'dr_off_conversations.db', 
        'orchestrator_conversations.db'
    ]
    
    for db_file in dbs:
        # Similar migration logic
        pass
```

### 2. ChromaDB Migration
```python
# scripts/migrate_chroma.py
import chromadb
import pickle
import os

def backup_chroma_locally():
    """Backup ChromaDB to portable format"""
    
    # Local ChromaDB
    local_client = chromadb.PersistentClient(
        path="data/dr_opa_agent/chroma"
    )
    
    collections = {}
    for collection_name in ['opa_docs', 'cep_tools']:
        collection = local_client.get_collection(collection_name)
        
        # Get all data
        data = collection.get(
            include=["documents", "metadatas", "embeddings"]
        )
        
        collections[collection_name] = data
    
    # Save as pickle for upload
    with open('chroma_backup.pkl', 'wb') as f:
        pickle.dump(collections, f)
    
    return collections

def restore_chroma_on_railway():
    """Restore ChromaDB on Railway"""
    
    # Railway ChromaDB (persistent volume)
    railway_client = chromadb.PersistentClient(
        path="/app/data/chroma"  # Persistent volume path
    )
    
    # Load backup
    with open('chroma_backup.pkl', 'rb') as f:
        collections = pickle.load(f)
    
    # Recreate collections
    for name, data in collections.items():
        collection = railway_client.create_collection(name)
        collection.add(
            ids=data['ids'],
            documents=data['documents'],
            metadatas=data['metadatas'],
            embeddings=data['embeddings']
        )
```

## App Separation Strategy

### 1. Subdomain Approach (Recommended)
```javascript
// vercel.json for AI Agents app
{
  "alias": ["agents.yourdomain.com"],
  "env": {
    "NEXT_PUBLIC_APP_MODE": "agents",
    "NEXT_PUBLIC_API_URL": "https://api.railway.app"
  }
}

// vercel.json for Health Assistant app  
{
  "alias": ["health.yourdomain.com"],
  "env": {
    "NEXT_PUBLIC_APP_MODE": "health",
    "NEXT_PUBLIC_API_URL": "https://api.railway.app"
  }
}
```

### 2. Route-Based Separation
```typescript
// web/app/layout.tsx
export default function RootLayout() {
  const pathname = usePathname();
  const isAgentsApp = pathname.startsWith('/agents');
  
  return (
    <html>
      <body>
        {isAgentsApp ? <AgentsHeader /> : <HealthHeader />}
        {children}
      </body>
    </html>
  );
}
```

### 3. Environment-Based UI
```typescript
// web/config/app-config.ts
const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE || 'health';

export const appConfig = {
  health: {
    title: "Health Assistant",
    description: "AI-powered medical education",
    features: ['patient', 'provider'],
    theme: 'medical-blue'
  },
  agents: {
    title: "Ontario Healthcare AI Agents",
    description: "Dr. OPA, Dr. OFF, Agent 97 & The Chief",
    features: ['dr-opa', 'dr-off', 'agent-97', 'chief'],
    theme: 'ontario-green'
  }
}[APP_MODE];
```

## Railway Deployment Configuration

### railway.toml
```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"

[[services]]
name = "ontario-health-api"
  
  [[services.volumes]]
  mount = "/app/data"
  name = "health-data"

[variables]
ENABLE_AGENTS = "true"
ENABLE_HEALTH_ASSISTANT = "true"
```

### Dockerfile (Alternative)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY data/ temp_data/

# Setup persistent volume mount point
RUN mkdir -p /app/data

# Copy initial data if volume is empty
COPY scripts/init_volume.sh .
RUN chmod +x init_volume.sh

# Start script checks if volume is empty and copies data
ENTRYPOINT ["./init_volume.sh"]
CMD ["uvicorn", "src.web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### init_volume.sh
```bash
#!/bin/bash

# Check if volume is empty (first deployment)
if [ ! -f /app/data/.initialized ]; then
    echo "Initializing persistent volume..."
    
    # Copy SQLite databases
    cp temp_data/*.db /app/data/
    
    # Copy ChromaDB
    cp -r temp_data/*/chroma /app/data/
    
    # Mark as initialized
    touch /app/data/.initialized
    
    echo "Volume initialized!"
fi

# Start the application
exec "$@"
```

## Step-by-Step Deployment

### Phase 1: Prepare Databases
```bash
# 1. Backup local databases
python scripts/migrate_sqlite_to_postgres.py --backup
python scripts/migrate_chroma.py --backup

# 2. Test migrations locally
docker-compose up -d postgres
python scripts/migrate_sqlite_to_postgres.py --test
```

### Phase 2: Deploy Backend to Railway
```bash
# 1. Create Railway project
railway login
railway init

# 2. Add persistent volume
railway volume create health-data

# 3. Set environment variables
railway variables set ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
railway variables set OPENAI_API_KEY=$OPENAI_API_KEY
railway variables set DATABASE_URL=$DATABASE_URL

# 4. Deploy
railway up
```

### Phase 3: Deploy Frontends to Vercel

#### AI Agents App
```bash
cd web
vercel --prod --env NEXT_PUBLIC_APP_MODE=agents
# Set custom domain: agents.yourdomain.com
```

#### Health Assistant App
```bash
cd web  
vercel --prod --env NEXT_PUBLIC_APP_MODE=health
# Set custom domain: health.yourdomain.com
```

## Database Connection Updates

### Update Backend Code
```python
# src/config/database.py
import os
from sqlalchemy import create_engine

def get_db_url():
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Production - Use PostgreSQL
        return os.getenv('DATABASE_URL', 'postgresql://...')
    else:
        # Development - Use SQLite
        return 'sqlite:///data/local.db'

def get_chroma_path():
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Production - Persistent volume
        return '/app/data/chroma'
    else:
        # Development - Local path
        return 'data/dr_opa_agent/chroma'
```

## Cost Breakdown

### Railway (Backend + Databases)
- **Hobby Plan**: $5/month (includes $5 credit)
- **PostgreSQL**: ~$5-7/month (or use free Neon.tech)
- **Persistent Volume**: ~$0.50/GB/month
- **Total**: ~$5-10/month

### Vercel (2 Frontends)
- **Free Tier**: Sufficient for both apps
- **Custom Domains**: Free
- **Total**: $0/month

### Alternative Free SQL Options
1. **Neon.tech**: 3GB free PostgreSQL
2. **PlanetScale**: 5GB free MySQL  
3. **Turso**: 9GB free SQLite-compatible
4. **Supabase**: 500MB free PostgreSQL

## Quick Migration Path

```bash
# 1. One-command backup
./scripts/backup_all_data.sh

# 2. Deploy to Railway
railway up

# 3. Restore data
railway run python scripts/restore_data.py

# 4. Deploy frontends
vercel --prod

# Done! Both apps live
```

This gives you:
- Clear separation between apps
- Shared backend (cost-effective)
- Persistent data storage
- Easy local-to-cloud migration
- ~$5-10/month total cost