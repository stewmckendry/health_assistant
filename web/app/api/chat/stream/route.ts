import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

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

    // Call Python backend streaming endpoint
    const response = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        sessionId,
        userId,
        mode,
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    // Return the streaming response from backend
    return new NextResponse(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Stream API error:', error);
    return NextResponse.json(
      { error: 'Failed to process streaming request' },
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