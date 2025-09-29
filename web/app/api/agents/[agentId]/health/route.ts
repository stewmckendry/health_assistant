import { NextRequest, NextResponse } from 'next/server';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { AgentHealthCheck, ApiError } from '@/types/agents';

/**
 * GET /api/agents/[agentId]/health
 * Returns health status of a specific agent
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

    // Perform basic health checks
    const isAvailable = isAgentAvailable(agentId);
    let healthStatus: AgentHealthCheck['status'] = 'unavailable';
    let message = '';

    if (agent.status === 'coming-soon') {
      healthStatus = 'unavailable';
      message = `Agent is in development. Expected launch: ${agent.launchDate || 'TBD'}`;
    } else if (agent.status === 'maintenance') {
      healthStatus = 'degraded';
      message = 'Agent is under maintenance';
    } else if (isAvailable) {
      healthStatus = 'healthy';
      message = 'Agent is operational and ready to serve requests';
    } else {
      healthStatus = 'degraded';
      message = 'Agent configuration found but service may be degraded';
    }

    // Mock component health checks (in production, these would be real checks)
    const components = {
      mcp: agent.status === 'active', // MCP server availability
      llm: agent.status === 'active', // LLM model availability  
      knowledgeBase: agent.knowledgeSources.length > 0 // Knowledge base availability
    };

    const healthCheck: AgentHealthCheck = {
      agentId,
      status: healthStatus,
      lastChecked: new Date().toISOString(),
      components,
      message
    };

    return NextResponse.json(healthCheck);

  } catch (error) {
    console.error(`Error checking health for agent ${params.agentId}:`, error);
    
    // Return degraded status on error
    const healthCheck: AgentHealthCheck = {
      agentId: params.agentId,
      status: 'degraded',
      lastChecked: new Date().toISOString(),
      components: {
        mcp: false,
        llm: false,
        knowledgeBase: false
      },
      message: 'Health check failed due to internal error'
    };

    return NextResponse.json(healthCheck, { status: 500 });
  }
}

/**
 * OPTIONS /api/agents/[agentId]/health
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