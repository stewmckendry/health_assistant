import { NextRequest, NextResponse } from 'next/server';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { ConversationSession, ApiError } from '@/types/agents';
import { v4 as uuidv4 } from 'uuid';

/**
 * POST /api/agents/[agentId]/conversations
 * Initialize a new conversation session with the agent
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ agentId: string }> }
) {
  try {
    const { agentId } = await params;

    if (!agentId) {
      const errorResponse: ApiError = {
        error: 'Bad Request',
        message: 'Agent ID is required',
        code: 'AGENT_ID_REQUIRED'
      };
      return NextResponse.json(errorResponse, { status: 400 });
    }

    // Verify agent exists and is available
    const agent = getAgentById(agentId);
    if (!agent) {
      const errorResponse: ApiError = {
        error: 'Not Found',
        message: `Agent '${agentId}' not found`,
        code: 'AGENT_NOT_FOUND'
      };
      return NextResponse.json(errorResponse, { status: 404 });
    }

    if (!isAgentAvailable(agentId)) {
      const errorResponse: ApiError = {
        error: 'Service Unavailable',
        message: `Agent '${agentId}' is not currently available`,
        code: 'AGENT_UNAVAILABLE'
      };
      return NextResponse.json(errorResponse, { status: 503 });
    }

    // Parse optional request body
    let userId: string | undefined;
    try {
      const body = await req.json();
      userId = body.userId;
    } catch {
      // Body is optional for conversation initialization
    }

    // Generate new session
    const sessionId = uuidv4();
    const now = new Date().toISOString();

    const session: ConversationSession = {
      sessionId,
      agentId,
      userId,
      startedAt: now,
      lastMessageAt: now,
      messageCount: 0,
      status: 'active'
    };

    // In production, this would be stored in a database
    // For now, we just return the session info
    console.log(`Created new conversation session: ${sessionId} for agent: ${agentId}`);

    return NextResponse.json({
      sessionId: session.sessionId,
      agentId: session.agentId,
      status: session.status,
      createdAt: session.startedAt
    }, { status: 201 });

  } catch (error) {
    const resolvedParams = await params;
    console.error(`Error creating conversation for agent ${resolvedParams.agentId}:`, error);
    
    const errorResponse: ApiError = {
      error: 'Internal Server Error',
      message: 'Failed to create conversation session',
      code: 'SESSION_CREATE_ERROR'
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

/**
 * GET /api/agents/[agentId]/conversations
 * List conversations for an agent (if implemented in the future)
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ agentId: string }> }
) {
  // This could be implemented to list user's conversations with this agent
  const { agentId } = await params;
  return NextResponse.json({ 
    message: 'Conversation listing not yet implemented',
    agentId: agentId 
  }, { status: 501 });
}

/**
 * OPTIONS /api/agents/[agentId]/conversations
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