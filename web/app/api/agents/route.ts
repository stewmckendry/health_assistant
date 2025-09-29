import { NextRequest, NextResponse } from 'next/server';
import { AGENTS_CONFIG, getActiveAgents, getComingSoonAgents } from '@/config/agents.config';
import { AgentInfo, ApiError } from '@/types/agents';

/**
 * GET /api/agents
 * Returns list of all configured agents with their metadata
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const status = searchParams.get('status');
    const includeInactive = searchParams.get('includeInactive') === 'true';

    let agents: AgentInfo[];

    if (status === 'active') {
      agents = getActiveAgents();
    } else if (status === 'coming-soon') {
      agents = getComingSoonAgents();
    } else if (includeInactive) {
      agents = Object.values(AGENTS_CONFIG);
    } else {
      // Default: return only active agents
      agents = getActiveAgents();
    }

    // Sort agents by status (active first) and then by name
    const sortedAgents = agents.sort((a, b) => {
      if (a.status === 'active' && b.status !== 'active') return -1;
      if (a.status !== 'active' && b.status === 'active') return 1;
      return a.name.localeCompare(b.name);
    });

    return NextResponse.json({
      agents: sortedAgents,
      total: sortedAgents.length,
      active: getActiveAgents().length,
      comingSoon: getComingSoonAgents().length
    });

  } catch (error) {
    console.error('Error fetching agents:', error);
    
    const errorResponse: ApiError = {
      error: 'Internal Server Error',
      message: 'Failed to fetch agents configuration',
      code: 'AGENTS_FETCH_ERROR'
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

/**
 * OPTIONS /api/agents
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