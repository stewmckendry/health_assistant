import { NextRequest, NextResponse } from 'next/server';
import { pythonBackend } from '@/lib/python-backend';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { query, sessionId, userId, mode = 'patient' } = body;

    // Validate required fields
    if (!query || !sessionId) {
      return NextResponse.json(
        { error: 'Query and sessionId are required' },
        { status: 400 }
      );
    }

    // Validate mode
    if (mode && !['patient', 'provider'].includes(mode)) {
      return NextResponse.json(
        { error: 'Invalid mode. Must be "patient" or "provider"' },
        { status: 400 }
      );
    }

    // Call Python backend (which handles all Langfuse tracing)
    const response = await pythonBackend.chat({
      query,
      sessionId,
      userId,
      mode,  // Pass mode to backend
    });

    return NextResponse.json(response);
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Failed to process chat request' },
      { status: 500 }
    );
  }
}

export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}