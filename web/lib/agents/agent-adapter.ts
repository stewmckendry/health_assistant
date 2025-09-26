/**
 * Agent Adapter - Interfaces with actual OpenAI Agent implementations
 * Handles the bridge between web API and Python agent implementations
 */

import { ToolCall, Citation, StreamEvent } from '@/types/agents';

export interface AgentResponse {
  response: string;
  tool_calls: Array<{
    name: string;
    arguments: string;
  }>;
  tools_used: string[];
  error?: string;
}

export interface AgentStreamEvent {
  type: 'text' | 'tool_call_start' | 'tool_call_end' | 'citation' | 'done' | 'error';
  data: any;
  timestamp: string;
}

export class AgentAdapter {
  private agentId: string;
  private pythonAgentUrl: string;

  constructor(agentId: string) {
    this.agentId = agentId;
    // URL to Python backend where agents are running
    this.pythonAgentUrl = process.env.PYTHON_AGENT_URL || 'http://localhost:8000';
  }

  /**
   * Send a query to the agent and get streaming response
   */
  async *streamQuery(
    sessionId: string,
    query: string,
    controller: ReadableStreamDefaultController,
    encoder: TextEncoder
  ): AsyncGenerator<void, void, unknown> {
    try {
      // Call the Python agent
      const response = await fetch(`${this.pythonAgentUrl}/agents/${this.agentId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          query,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`Agent request failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              break;
            }

            try {
              const event = JSON.parse(data);
              yield this.processAgentEvent(event, controller, encoder);
            } catch (e) {
              console.error('Failed to parse agent event:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error(`Error streaming from agent ${this.agentId}:`, error);
      
      // Send error event to client
      const errorEvent: StreamEvent = {
        type: 'error',
        data: { error: `Failed to connect to ${this.agentId}: ${error}` },
        timestamp: new Date().toISOString()
      };

      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify(errorEvent)}\n\n`)
      );
    }
  }

  /**
   * Process events from the Python agent and convert to web format
   */
  private processAgentEvent(
    event: any,
    controller: ReadableStreamDefaultController,
    encoder: TextEncoder
  ): void {
    switch (event.type) {
      case 'response_start':
        // Agent started responding
        break;

      case 'text':
        const plainTextEvent: StreamEvent = {
          type: 'text',
          data: {
            content: event.data.content || '',
            delta: event.data.delta || ''
          },
          timestamp: new Date().toISOString()
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(plainTextEvent)}\n\n`)
        );
        break;

      case 'text_delta':
        const textEvent: StreamEvent = {
          type: 'text',
          data: {
            content: event.data.content || '',
            delta: event.data.delta || ''
          },
          timestamp: new Date().toISOString()
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(textEvent)}\n\n`)
        );
        break;

      case 'tool_call':
        const toolCall: ToolCall = {
          id: event.data.id || `tool_${Date.now()}`,
          name: event.data.name || event.data.function?.name || 'unknown',
          arguments: this.parseToolArguments(event.data.arguments || event.data.function?.arguments),
          status: event.data.status || 'executing',
          startTime: event.data.start_time || new Date().toISOString(),
          endTime: event.data.end_time,
          result: event.data.result,
          error: event.data.error
        };

        const toolEvent: StreamEvent = {
          type: toolCall.status === 'completed' ? 'tool_call_end' : 'tool_call_start',
          data: toolCall,
          timestamp: new Date().toISOString()
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(toolEvent)}\n\n`)
        );
        break;

      case 'citation':
        const citation = this.extractCitation(event.data);
        if (citation) {
          const citationEvent: StreamEvent = {
            type: 'citation',
            data: citation,
            timestamp: new Date().toISOString()
          };

          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(citationEvent)}\n\n`)
          );
        }
        break;

      case 'response_done':
        const doneEvent: StreamEvent = {
          type: 'done',
          data: {
            messageId: event.data.message_id || `msg_${Date.now()}`,
            citationIds: event.data.citation_ids || []
          },
          timestamp: new Date().toISOString()
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(doneEvent)}\n\n`)
        );
        break;

      case 'error':
        const errorEvent: StreamEvent = {
          type: 'error',
          data: { error: event.data.error || 'Unknown error' },
          timestamp: new Date().toISOString()
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(errorEvent)}\n\n`)
        );
        break;
    }
  }

  /**
   * Parse tool call arguments from various formats
   */
  private parseToolArguments(args: any): Record<string, any> {
    if (typeof args === 'string') {
      try {
        return JSON.parse(args);
      } catch {
        return { query: args };
      }
    }
    return args || {};
  }

  /**
   * Extract citation information from agent response
   */
  private extractCitation(data: any): Citation | null {
    if (!data) return null;

    try {
      return {
        id: data.id || `citation_${Date.now()}`,
        title: data.title || data.source || 'Unknown Source',
        source: data.source || data.organization || 'Unknown',
        url: data.url || '',
        domain: data.domain || this.extractDomain(data.url || ''),
        isTrusted: this.isTrustedSource(data.url || data.domain || ''),
        snippet: data.snippet || data.excerpt,
        publishedDate: data.published_date || data.date,
        accessDate: new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to extract citation:', error);
      return null;
    }
  }

  /**
   * Extract domain from URL
   */
  private extractDomain(url: string): string {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return url;
    }
  }

  /**
   * Check if a source is trusted based on domain
   */
  private isTrustedSource(urlOrDomain: string): boolean {
    const trustedDomains = [
      // Canadian Healthcare
      'ontario.ca', 'cpso.on.ca', 'publichealthontario.ca', 'ontariohealth.ca',
      'cep.health', 'canada.ca', 'phac-aspc.gc.ca',
      
      // US Medical Centers
      'mayoclinic.org', 'clevelandclinic.org', 'hopkinsmedicine.org',
      'stanfordmedicine.stanford.edu', 'ucsfhealth.org',
      
      // Medical Journals
      'nejm.org', 'thelancet.com', 'jamanetwork.com', 'bmj.com',
      'nature.com', 'cell.com',
      
      // Global Health Organizations
      'who.int', 'cdc.gov', 'nih.gov', 'nhs.uk', 'health.gov.au',
      
      // Professional Organizations
      'ama-assn.org', 'rcpsc.edu', 'cfpc.ca', 'cma.ca'
    ];

    const domain = this.extractDomain(urlOrDomain);
    return trustedDomains.some(trusted => domain.includes(trusted));
  }

  /**
   * Non-streaming query for simple responses
   */
  async query(sessionId: string, query: string): Promise<AgentResponse> {
    try {
      const response = await fetch(`${this.pythonAgentUrl}/agents/${this.agentId}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          query
        })
      });

      if (!response.ok) {
        throw new Error(`Agent request failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`Error querying agent ${this.agentId}:`, error);
      return {
        response: `I apologize, but I'm having trouble connecting to the ${this.agentId} service. Please try again later.`,
        tool_calls: [],
        tools_used: [],
        error: String(error)
      };
    }
  }
}

/**
 * Factory function to create agent adapters
 */
export function createAgentAdapter(agentId: string): AgentAdapter {
  return new AgentAdapter(agentId);
}