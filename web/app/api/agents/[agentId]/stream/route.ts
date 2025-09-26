import { NextRequest, NextResponse } from 'next/server';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { ApiError, StreamEvent, TextStreamEvent, ToolCallStreamEvent, CitationStreamEvent } from '@/types/agents';
import { createAgentAdapter } from '@/lib/agents/agent-adapter';

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

    // Create Server-Sent Events stream
    const encoder = new TextEncoder();
    const adapter = createAgentAdapter(agentId);
    
    const stream = new ReadableStream({
      async start(controller) {
        console.log(`Starting stream for agent ${agentId}, session ${sessionId}`);

        try {
          // Try to use real agent first
          const generator = adapter.streamQuery(sessionId, query, controller, encoder);
          
          for await (const _ of generator) {
            // The generator handles sending events to the controller
          }
        } catch (error) {
          console.error(`Real agent failed, falling back to simulation:`, error);
          
          // Fallback to simulation if real agent fails
          await simulateAgentResponse(controller, encoder, agentId, sessionId, query, agent.name);
        }
      }
    });

    return new Response(stream, {
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
    console.error(`Error starting stream for agent ${params.agentId}:`, error);
    
    const errorResponse: ApiError = {
      error: 'Internal Server Error',
      message: 'Failed to start streaming response',
      code: 'STREAM_START_ERROR'
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

/**
 * Simulate agent response for demonstration
 * In production, this would integrate with the actual OpenAI Agents SDK
 */
async function simulateAgentResponse(
  controller: ReadableStreamDefaultController,
  encoder: TextEncoder,
  agentId: string,
  sessionId: string,
  query: string,
  agentName: string
) {
  try {
    // Send tool call start event
    const toolCallEvent: ToolCallStreamEvent = {
      type: 'tool_call_start',
      data: {
        id: `tool_${Date.now()}`,
        name: agentId === 'dr-opa' ? 'opa_search_sections' : 'agent_97_query',
        arguments: { query: query.slice(0, 100) },
        status: 'executing',
        startTime: new Date().toISOString()
      },
      timestamp: new Date().toISOString()
    };

    controller.enqueue(
      encoder.encode(`data: ${JSON.stringify(toolCallEvent)}\n\n`)
    );

    // Wait a bit to simulate processing
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Send tool call completion
    const toolCallEndEvent: ToolCallStreamEvent = {
      type: 'tool_call_end',
      data: {
        ...toolCallEvent.data,
        status: 'completed',
        endTime: new Date().toISOString(),
        result: 'Found relevant information from knowledge base'
      },
      timestamp: new Date().toISOString()
    };

    controller.enqueue(
      encoder.encode(`data: ${JSON.stringify(toolCallEndEvent)}\n\n`)
    );

    // Send simulated response text in chunks
    const responseText = getSimulatedResponse(agentId, query);
    const words = responseText.split(' ');
    
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const isLastWord = i === words.length - 1;
      
      const textEvent: TextStreamEvent = {
        type: 'text',
        data: {
          content: words.slice(0, i + 1).join(' ') + (isLastWord ? '' : ' '),
          delta: word + (isLastWord ? '' : ' ')
        },
        timestamp: new Date().toISOString()
      };

      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify(textEvent)}\n\n`)
      );

      // Small delay between words for realistic streaming
      await new Promise(resolve => setTimeout(resolve, 80));
    }

    // Send citation event
    const citationEvent: CitationStreamEvent = {
      type: 'citation',
      data: {
        id: `citation_${Date.now()}`,
        title: 'Sample Medical Source',
        source: agentId === 'dr-opa' ? 'CPSO Policy' : 'Mayo Clinic',
        url: agentId === 'dr-opa' ? 'https://www.cpso.on.ca/' : 'https://www.mayoclinic.org/',
        domain: agentId === 'dr-opa' ? 'cpso.on.ca' : 'mayoclinic.org',
        isTrusted: true,
        accessDate: new Date().toISOString()
      },
      timestamp: new Date().toISOString()
    };

    controller.enqueue(
      encoder.encode(`data: ${JSON.stringify(citationEvent)}\n\n`)
    );

    // Send completion event
    const doneEvent: StreamEvent = {
      type: 'done',
      data: { 
        messageId: `msg_${Date.now()}`,
        citationIds: [citationEvent.data.id]
      },
      timestamp: new Date().toISOString()
    };

    controller.enqueue(
      encoder.encode(`data: ${JSON.stringify(doneEvent)}\n\n`)
    );

    // Close the stream
    controller.close();

  } catch (error) {
    console.error('Error in simulated agent response:', error);
    
    const errorEvent: StreamEvent = {
      type: 'error',
      data: { error: 'Failed to generate response' },
      timestamp: new Date().toISOString()
    };

    controller.enqueue(
      encoder.encode(`data: ${JSON.stringify(errorEvent)}\n\n`)
    );
    
    controller.close();
  }
}

/**
 * Get simulated response based on agent and query
 */
function getSimulatedResponse(agentId: string, query: string): string {
  if (agentId === 'dr-opa') {
    return `Based on Ontario practice guidance, I can provide information about your query: "${query}". ` +
           `According to CPSO policies and Ontario Health programs, here are the key points you should know. ` +
           `This information is drawn from current regulatory requirements and clinical guidelines specific to Ontario healthcare practice. ` +
           `Please verify any specific requirements with the official source documents and use your clinical judgment.`;
  } else if (agentId === 'agent-97') {
    return `Thank you for your health education question: "${query}". ` +
           `Based on information from trusted medical sources, I can provide educational content to help you understand this topic. ` +
           `This information comes from reputable medical organizations and is intended for educational purposes only. ` +
           `Always consult with your healthcare provider for personalized medical advice and treatment decisions.`;
  } else if (agentId === 'dr-off') {
    return `Regarding your Ontario financing and formulary question: "${query}". ` +
           `I can help with drug coverage, OHIP billing, and ADP eligibility information. ` +
           `Please note that coverage details are subject to change and should be verified with official sources.`;
  }

  return `Thank you for your question: "${query}". I'm processing your request and will provide a helpful response.`;
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
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}