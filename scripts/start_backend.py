#!/usr/bin/env python
"""
Start the backend API server with environment variables loaded.
"""

import os
import sys
from pathlib import Path

# Load environment variables before any other imports
from dotenv import load_dotenv

# Find and load .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
print(f"Loading environment from: {env_file}")
load_dotenv(env_file, override=True)

# Verify key is loaded
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    print(f"✓ ANTHROPIC_API_KEY loaded: {api_key[:20]}...")
else:
    print("✗ ANTHROPIC_API_KEY not found in .env")

# Add project root to Python path
sys.path.insert(0, str(project_root))

# Now start the server
import uvicorn

if __name__ == "__main__":
    # Change to project root directory
    os.chdir(project_root)
    
    uvicorn.run(
        "src.web.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False to avoid subprocess issues
        log_level="info"
    )