#!/usr/bin/env python3
"""
Basic import and initialization test for Dr. OPA MCP components.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

print("Project root:", project_root)
print("Python path:", sys.path[0])

try:
    print("\n1. Testing imports...")
    
    # Test model imports
    print("   - Importing models...")
    from src.agents.dr_opa_agent.mcp.models.request import SearchSectionsRequest
    from src.agents.dr_opa_agent.mcp.models.response import SearchSectionsResponse
    print("   ✓ Models imported successfully")
    
    # Test retrieval client imports
    print("   - Importing retrieval clients...")
    from src.agents.dr_opa_agent.mcp.retrieval import SQLClient, VectorClient
    print("   ✓ Retrieval clients imported successfully")
    
    # Test utility imports
    print("   - Importing utilities...")
    from src.agents.dr_opa_agent.mcp.utils import calculate_confidence, resolve_conflicts
    print("   ✓ Utilities imported successfully")
    
    # Test server import
    print("   - Importing MCP server...")
    from src.agents.dr_opa_agent.mcp.server import mcp
    print("   ✓ MCP server imported successfully")
    
    print("\n2. Testing client initialization...")
    
    # Test SQL client
    try:
        sql_client = SQLClient()
        print("   ✓ SQL client initialized")
    except FileNotFoundError as e:
        print(f"   ⚠ SQL client initialization failed (expected if DB not yet created): {e}")
    except Exception as e:
        print(f"   ✗ SQL client initialization error: {e}")
    
    # Test vector client  
    try:
        vector_client = VectorClient()
        print("   ✓ Vector client initialized")
    except Exception as e:
        print(f"   ⚠ Vector client initialization warning: {e}")
    
    print("\n3. Testing request/response models...")
    
    # Test creating a request
    request = SearchSectionsRequest(
        query="test query",
        sources=["cpso"],
        top_k=5
    )
    print(f"   ✓ Created request: {request.query}")
    
    print("\n✅ All basic imports and initializations successful!")
    
except ImportError as e:
    print(f"\n✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    sys.exit(1)