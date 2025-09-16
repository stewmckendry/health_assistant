import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import { pythonBackend } from '@/lib/python-backend';

// In-memory session store (for demo purposes)
// In production, use a database or Redis
const sessions = new Map<string, any>();

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const sessionId = url.searchParams.get('sessionId');

    if (!sessionId) {
      return NextResponse.json(
        { error: 'SessionId is required' },
        { status: 400 }
      );
    }

    // Try to get from Python backend first
    try {
      const session = await pythonBackend.getSession(sessionId);
      return NextResponse.json(session);
    } catch (error) {
      // Fallback to in-memory store
      const session = sessions.get(sessionId);
      if (!session) {
        return NextResponse.json(
          { error: 'Session not found' },
          { status: 404 }
        );
      }
      return NextResponse.json(session);
    }
  } catch (error) {
    console.error('Sessions GET API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch session' },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { userId } = body;

    // Generate new session ID
    const sessionId = uuidv4();
    const session = {
      id: sessionId,
      userId: userId || 'anonymous',
      createdAt: new Date().toISOString(),
      messages: [],
      metadata: {
        source: 'web-app',
        userAgent: req.headers.get('user-agent'),
      },
    };

    // Store in memory
    sessions.set(sessionId, session);

    return NextResponse.json({
      sessionId,
      userId: session.userId,
      createdAt: session.createdAt,
    });
  } catch (error) {
    console.error('Sessions POST API error:', error);
    return NextResponse.json(
      { error: 'Failed to create session' },
      { status: 500 }
    );
  }
}

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