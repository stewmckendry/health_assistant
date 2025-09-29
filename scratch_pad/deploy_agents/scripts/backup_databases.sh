#!/bin/bash

# Database Backup Script for Ontario Healthcare AI Agents
# Creates timestamped backups of all SQLite databases and ChromaDB

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="scratch_pad/deploy_agents/backups/${TIMESTAMP}"
PROJECT_ROOT="$(pwd)"

echo -e "${GREEN}Starting database backup...${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Backup directory: ${BACKUP_DIR}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Function to backup SQLite database
backup_sqlite() {
    local db_path=$1
    local db_name=$(basename "${db_path}")
    
    if [ -f "${db_path}" ]; then
        echo -e "${YELLOW}Backing up ${db_name}...${NC}"
        
        # Create backup using SQLite's backup command
        sqlite3 "${db_path}" ".backup '${BACKUP_DIR}/${db_name}'"
        
        # Also create a SQL dump for safety
        sqlite3 "${db_path}" .dump > "${BACKUP_DIR}/${db_name%.db}.sql"
        
        # Get file size
        size=$(du -h "${db_path}" | cut -f1)
        echo -e "${GREEN}✓ ${db_name} backed up (${size})${NC}"
    else
        echo -e "${RED}✗ ${db_path} not found${NC}"
    fi
}

# Function to backup ChromaDB
backup_chroma() {
    local chroma_path=$1
    local chroma_name=$(basename "${chroma_path}")
    
    if [ -d "${chroma_path}" ]; then
        echo -e "${YELLOW}Backing up ChromaDB: ${chroma_name}...${NC}"
        
        # Create tar archive of ChromaDB
        tar -czf "${BACKUP_DIR}/chroma_${chroma_name}.tar.gz" -C "$(dirname ${chroma_path})" "${chroma_name}"
        
        # Get directory size
        size=$(du -sh "${chroma_path}" | cut -f1)
        echo -e "${GREEN}✓ ChromaDB ${chroma_name} backed up (${size})${NC}"
    else
        echo -e "${RED}✗ ${chroma_path} not found${NC}"
    fi
}

# Backup all SQLite databases
echo -e "\n${GREEN}=== Backing up SQLite Databases ===${NC}"

backup_sqlite "data/ohip.db"
backup_sqlite "data/dr_opa_conversations.db"
backup_sqlite "data/dr_off_conversations.db"
backup_sqlite "data/orchestrator_conversations.db"

# Backup ChromaDB directories
echo -e "\n${GREEN}=== Backing up ChromaDB Vector Stores ===${NC}"

backup_chroma "data/dr_opa_agent/chroma"
backup_chroma "data/dr_off_agent/processed/dr_off/chroma"

# Alternative ChromaDB locations (if they exist)
[ -d "data/processed/dr_opa/chroma" ] && backup_chroma "data/processed/dr_opa/chroma"
[ -d "data/processed/dr_off/chroma" ] && backup_chroma "data/processed/dr_off/chroma"

# Create manifest file
echo -e "\n${GREEN}=== Creating Backup Manifest ===${NC}"

cat > "${BACKUP_DIR}/manifest.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "project_root": "${PROJECT_ROOT}",
  "backup_dir": "${BACKUP_DIR}",
  "databases": {
    "sqlite": [
      "ohip.db",
      "dr_opa_conversations.db",
      "dr_off_conversations.db",
      "orchestrator_conversations.db"
    ],
    "chroma": [
      "dr_opa_agent/chroma",
      "dr_off_agent/processed/dr_off/chroma"
    ]
  },
  "git_info": {
    "branch": "$(git branch --show-current)",
    "commit": "$(git rev-parse HEAD)",
    "status": "$(git status --short)"
  }
}
EOF

# Create compressed archive of entire backup
echo -e "\n${GREEN}=== Creating Compressed Archive ===${NC}"

cd scratch_pad/deploy_agents/backups
tar -czf "backup_${TIMESTAMP}.tar.gz" "${TIMESTAMP}"
cd "${PROJECT_ROOT}"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)

# Summary
echo -e "\n${GREEN}=== Backup Complete ===${NC}"
echo "Backup location: ${BACKUP_DIR}"
echo "Archive: scratch_pad/deploy_agents/backups/backup_${TIMESTAMP}.tar.gz"
echo "Total size: ${TOTAL_SIZE}"
echo ""
echo "To restore, use:"
echo "  ./scratch_pad/deploy_agents/scripts/restore_databases.sh ${TIMESTAMP}"

# Verify backups
echo -e "\n${GREEN}=== Verifying Backups ===${NC}"

for db in "${BACKUP_DIR}"/*.db; do
    if [ -f "$db" ]; then
        db_name=$(basename "$db")
        tables=$(sqlite3 "$db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        echo -e "${GREEN}✓ ${db_name}: ${tables} tables${NC}"
    fi
done

echo -e "\n${GREEN}Backup completed successfully!${NC}"