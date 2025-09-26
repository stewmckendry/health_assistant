#!/usr/bin/env python3
"""
Python Backend API for Clinical AI Agents Web App

FastAPI server that provides endpoints for the web app to interact with
the OpenAI Agent implementations (Dr. OPA, Agent 97, Dr. OFF).

This bridges the Next.js web app with the Python agent implementations.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import agents
try:
    from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent
    # Agent 97 now uses PatientAssistant directly via the agent_97_endpoint
except ImportError as e:
    print(f"Warning: Could not import agents: {e}")
    print("Running in mock mode")

app = FastAPI(title="Clinical AI Agents API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class QueryRequest(BaseModel):
    sessionId: str
    query: str
    stream: bool = False

# Global agent instances
agents: Dict[str, Any] = {}
sessions: Dict[str, Dict] = {}  # Simple in-memory session storage

@app.on_event("startup")
async def startup():
    """Initialize agents on startup"""
    try:
        print("Initializing Dr. OPA agent...")
        agents['dr-opa'] = await create_dr_opa_agent()
        print("✓ Dr. OPA agent ready")
    except Exception as e:
        print(f"Failed to initialize Dr. OPA: {e}")
        agents['dr-opa'] = None

    # Agent 97 is handled directly by PatientAssistant through dedicated endpoint
    # See src/web/api/agent_97_endpoint.py
    agents['agent-97'] = None  # Placeholder for agent list

    print(f"Backend API ready with {len([a for a in agents.values() if a is not None])} active agents")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agents": {
            name: "ready" if agent is not None else "unavailable"
            for name, agent in agents.items()
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/agents/{agent_id}/query")
async def query_agent(agent_id: str, request: QueryRequest):
    """Send a query to an agent and get response"""
    if agent_id not in agents or agents[agent_id] is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not available")

    try:
        agent = agents[agent_id]
        
        # Call the agent's query method
        result = await agent.query(request.query)
        
        # Handle both old string format and new dict format
        if isinstance(result, dict):
            return {
                "response": result.get('response', ''),
                "tool_calls": result.get('tool_calls', []),
                "tools_used": result.get('tools_used', []),
                "error": result.get('error')
            }
        else:
            return {
                "response": str(result),
                "tool_calls": [],
                "tools_used": [],
                "error": None
            }
    
    except Exception as e:
        print(f"Error querying agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/stream")
async def stream_agent_response(agent_id: str, request: QueryRequest):
    """Stream response from an agent using Server-Sent Events"""
    if agent_id not in agents or agents[agent_id] is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not available")

    async def generate_stream():
        try:
            agent = agents[agent_id]
            
            # Send start event
            yield f"data: {json.dumps({'type': 'response_start', 'data': {}, 'timestamp': datetime.now().isoformat()})}\n\n"

            # For now, simulate streaming by calling the regular query method
            # In the future, this would use the OpenAI SDK's streaming capabilities
            result = await agent.query(request.query)
            
            if isinstance(result, dict):
                response_text = result.get('response', '')
                tool_calls = result.get('tool_calls', [])
                error = result.get('error')
                
                # Send tool calls
                for tool_call in tool_calls:
                    yield f"data: {json.dumps({'type': 'tool_call', 'data': {'name': tool_call.get('name'), 'arguments': tool_call.get('arguments'), 'status': 'completed'}, 'timestamp': datetime.now().isoformat()})}\n\n"

                # Stream text response word by word
                words = response_text.split(' ')
                accumulated_text = ''
                
                for i, word in enumerate(words):
                    accumulated_text += word + (' ' if i < len(words) - 1 else '')
                    yield f"data: {json.dumps({'type': 'text_delta', 'data': {'content': accumulated_text, 'delta': word + (' ' if i < len(words) - 1 else '')}, 'timestamp': datetime.now().isoformat()})}\n\n"
                    await asyncio.sleep(0.05)  # Small delay for realistic streaming

                # Extract and send citations
                citations = extract_citations_from_response(response_text)
                for citation in citations:
                    yield f"data: {json.dumps({'type': 'citation', 'data': citation, 'timestamp': datetime.now().isoformat()})}\n\n"

                if error:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': error}, 'timestamp': datetime.now().isoformat()})}\n\n"
            else:
                # Handle string response
                response_text = str(result)
                words = response_text.split(' ')
                accumulated_text = ''
                
                for i, word in enumerate(words):
                    accumulated_text += word + (' ' if i < len(words) - 1 else '')
                    yield f"data: {json.dumps({'type': 'text_delta', 'data': {'content': accumulated_text, 'delta': word + (' ' if i < len(words) - 1 else '')}, 'timestamp': datetime.now().isoformat()})}\n\n"
                    await asyncio.sleep(0.05)

            # Send completion event
            yield f"data: {json.dumps({'type': 'response_done', 'data': {'message_id': f'msg_{uuid.uuid4().hex[:8]}'}, 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            print(f"Error streaming from agent {agent_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}, 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

def extract_citations_from_response(response: str) -> list:
    """Extract citations from agent response text"""
    citations = []
    
    # Simple regex-based citation extraction
    # This would be more sophisticated in production
    import re
    
    # Look for URLs in the response
    url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
    urls = re.findall(url_pattern, response)
    
    for i, url in enumerate(urls):
        domain = url.split('/')[2] if '://' in url else url
        citations.append({
            'id': f'citation_{i}_{uuid.uuid4().hex[:8]}',
            'title': f'Source from {domain}',
            'source': domain,
            'url': url,
            'domain': domain.replace('www.', ''),
            'is_trusted': is_trusted_domain(domain)
        })
    
    return citations

def is_trusted_domain(domain: str) -> bool:
    """Check if domain is in trusted sources list"""
    trusted = [
        'ontario.ca', 'cpso.on.ca', 'publichealthontario.ca', 
        'mayoclinic.org', 'cdc.gov', 'who.int', 'nih.gov',
        'nejm.org', 'bmj.com', 'thelancet.com'
    ]
    return any(trusted_domain in domain for trusted_domain in trusted)

@app.get("/agents")
async def list_agents():
    """List available agents"""
    return {
        "agents": [
            {
                "id": agent_id,
                "status": "ready" if agent is not None else "unavailable",
                "last_check": datetime.now().isoformat()
            }
            for agent_id, agent in agents.items()
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "python-backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )