import { NextRequest, NextResponse } from 'next/server';
import { pythonBackend } from '@/lib/python-backend';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { traceId, sessionId, userId, rating, comment, thumbsUp } = body;

    // Validate required fields
    if (!traceId || !sessionId) {
      return NextResponse.json(
        { error: 'TraceId and sessionId are required' },
        { status: 400 }
      );
    }

    // Submit to Python backend which handles Langfuse integration
    const response = await pythonBackend.submitFeedback({
      traceId,
      sessionId,
      userId,
      rating,
      comment,
      thumbsUp,
    });

    return NextResponse.json(response);
  } catch (error) {
    console.error('Feedback API error:', error);
    return NextResponse.json(
      { error: 'Failed to submit feedback' },
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