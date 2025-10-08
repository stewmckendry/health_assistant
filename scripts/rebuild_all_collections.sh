#!/bin/bash
# Re-run all ingestion and restructuring scripts to ensure latest data

set -e  # Exit on error

echo "🔄 Rebuilding All Collections with Latest Scripts"
echo "=================================================="

source ~/spacy_env/bin/activate

# Dr. OPA collections
echo ""
echo "📚 Dr. OPA Collections"
echo "----------------------"

echo ""
echo "1/7: CEP Clinical Tools (ingester_v2)..."
python scripts/reingest_cep_v2.py

echo ""
echo "2/7: CPSO Policies (ingester_v2)..."
if [ -f "src/ai_agents/dr_opa_agent/ingestion/cpso/ingester_v2.py" ]; then
    python -c "
from src.ai_agents.dr_opa_agent.ingestion.cpso.ingester_v2 import CPSOIngesterV2
import chromadb
from chromadb.config import Settings

# Delete and recreate
client = chromadb.PersistentClient(
    path='data/dr_opa_agent/chroma',
    settings=Settings(anonymized_telemetry=False, allow_reset=False, is_persistent=True)
)
try:
    client.delete_collection('opa_cpso_corpus')
    print('✓ Deleted existing opa_cpso_corpus')
except:
    print('No existing collection to delete')

del client

ingester = CPSOIngesterV2()
result = ingester.ingest_all_policies()
print(f'✅ CPSO: {result.get(\"total_chunks\", 0)} chunks from {result.get(\"total_policies\", 0)} policies')
"
fi

echo ""
echo "3/7: Quality Standards (restructure)..."
python scripts/restructure_quality_standards.py

echo ""
echo "4/7: Choosing Wisely (restructure)..."
python scripts/restructure_choosing_wisely.py

# Dr. OFF collections
echo ""
echo "📚 Dr. OFF Collections"
echo "----------------------"

echo ""
echo "5/7: OHIP Billing (restructure)..."
python scripts/restructure_ohip.py

echo ""
echo "6/7: ADP Devices (restructure)..."
python scripts/restructure_adp.py

echo ""
echo "7/7: ODB Formulary (restructure)..."
python scripts/restructure_odb.py

echo ""
echo "=================================================="
echo "✅ All Collections Rebuilt Successfully!"
echo ""
echo "Summary:"
python scripts/show_chroma_status.py
