import { NextRequest, NextResponse } from 'next/server';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { ApiError } from '@/types/agents';

/**
 * GET /api/agents/[agentId]/stream
 * Server-sent events endpoint for streaming agent responses
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ agentId: string }> }
) {
  try {
    const { agentId } = await params;
    const { searchParams } = new URL(req.url);
    const sessionId = searchParams.get('sessionId');
    const query = searchParams.get('query');

    // Validate parameters
    if (!agentId) {
      return NextResponse.json({ error: 'Agent ID is required' }, { status: 400 });
    }

    if (!sessionId || !query) {
      return NextResponse.json({ 
        error: 'Session ID and query are required' 
      }, { status: 400 });
    }

    // Verify agent exists and is available
    const agent = getAgentById(agentId);
    if (!agent) {
      return NextResponse.json({ 
        error: `Agent '${agentId}' not found` 
      }, { status: 404 });
    }

    if (!isAgentAvailable(agentId)) {
      return NextResponse.json({ 
        error: `Agent '${agentId}' is not currently available` 
      }, { status: 503 });
    }

    console.log(`Starting stream for agent ${agentId}, session ${sessionId}`);

    // For Agent 97, use the working /chat/stream endpoint since it's just PatientAssistant
    const endpoint = agentId === 'agent-97' 
      ? 'http://localhost:8000/chat/stream'
      : `http://localhost:8000/agents/${agentId}/stream`;
    
    const requestBody = agentId === 'agent-97'
      ? { query, sessionId, mode: 'patient' }
      : { sessionId, query, stream: true };

    // Call the Python backend directly and pass through the response
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`Backend request failed: ${response.statusText}`);
    }

    // Simply pass through the streaming response body from the backend
    return new NextResponse(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });

  } catch (error) {
    console.error(`Error starting stream for agent:`, error);
    
    const errorResponse: ApiError = {
      error: 'Internal Server Error', 
      message: 'Failed to start streaming response',
      code: 'STREAM_START_ERROR'
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

/**
 * POST /api/agents/[agentId]/stream
 * Server-sent events endpoint for streaming agent responses (POST version)
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ agentId: string }> }
) {
  try {
    const { agentId } = await params;
    const body = await req.json();
    const { sessionId, query, userId } = body;

    // Validate parameters
    if (!agentId) {
      return NextResponse.json({ error: 'Agent ID is required' }, { status: 400 });
    }

    if (!sessionId || !query) {
      return NextResponse.json({ 
        error: 'Session ID and query are required' 
      }, { status: 400 });
    }

    // Verify agent exists and is available
    const agent = getAgentById(agentId);
    if (!agent) {
      return NextResponse.json({ 
        error: `Agent '${agentId}' not found` 
      }, { status: 404 });
    }

    if (!isAgentAvailable(agentId)) {
      return NextResponse.json({ 
        error: `Agent '${agentId}' is not currently available` 
      }, { status: 503 });
    }

    console.log(`Starting stream for agent ${agentId}, session ${sessionId}, user ${userId}`);

    // For Agent 97, use the working /chat/stream endpoint since it's just PatientAssistant
    const endpoint = agentId === 'agent-97' 
      ? 'http://localhost:8000/chat/stream'
      : `http://localhost:8000/agents/${agentId}/stream`;
    
    // Stream to backend Python API with userId
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        sessionId,
        query,
        userId,  // Pass userId for Langfuse tracing
        stream: true
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || 'Failed to stream from backend' },
        { status: response.status }
      );
    }

    // Forward the SSE stream from backend to frontend
    if (response.body) {
      return new NextResponse(response.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    } else {
      throw new Error('No response body from backend');
    }
  } catch (error) {
    console.error('Stream error:', error);
    const apiError: ApiError = {
      error: 'stream_failed',
      message: error instanceof Error ? error.message : 'Failed to stream response'
    };
    return NextResponse.json(apiError, { status: 500 });
  }
}

/**
 * OPTIONS /api/agents/[agentId]/stream
 * CORS preflight handler
 */
export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}