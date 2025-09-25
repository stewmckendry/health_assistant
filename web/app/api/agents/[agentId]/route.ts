import { NextRequest, NextResponse } from 'next/server';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { ApiError } from '@/types/agents';

/**
 * GET /api/agents/[agentId]
 * Returns detailed information about a specific agent
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { agentId: string } }
) {
  try {
    const { agentId } = params;

    if (!agentId) {
      const errorResponse: ApiError = {
        error: 'Bad Request',
        message: 'Agent ID is required',
        code: 'AGENT_ID_REQUIRED'
      };
      return NextResponse.json(errorResponse, { status: 400 });
    }

    const agent = getAgentById(agentId);

    if (!agent) {
      const errorResponse: ApiError = {
        error: 'Not Found',
        message: `Agent '${agentId}' not found`,
        code: 'AGENT_NOT_FOUND'
      };
      return NextResponse.json(errorResponse, { status: 404 });
    }

    // Add runtime status information
    const agentWithStatus = {
      ...agent,
      isAvailable: isAgentAvailable(agentId),
      lastHealthCheck: new Date().toISOString(),
      runtime: {
        status: agent.status === 'active' ? 'healthy' : 'unavailable',
        uptime: agent.status === 'active' ? '100%' : '0%',
        version: '1.0.0'
      }
    };

    return NextResponse.json(agentWithStatus);

  } catch (error) {
    console.error(`Error fetching agent ${params.agentId}:`, error);
    
    const errorResponse: ApiError = {
      error: 'Internal Server Error',
      message: 'Failed to fetch agent details',
      code: 'AGENT_FETCH_ERROR'
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

/**
 * OPTIONS /api/agents/[agentId]
 * CORS preflight handler
 */
export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}