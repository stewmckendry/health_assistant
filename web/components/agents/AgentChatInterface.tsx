'use client';

import { useState, useRef, useEffect } from 'react';
import { AgentInfo, Message, ToolCall, Citation } from '@/types/agents';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Send, 
  Loader2, 
  StopCircle,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { AgentMessage } from './AgentMessage';

interface AgentChatInterfaceProps {
  agent: AgentInfo;
  onClose: () => void;
}

export function AgentChatInterface({ agent, onClose }: AgentChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Initialize session when component mounts
  useEffect(() => {
    initializeSession();
  }, [agent.id]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const initializeSession = async () => {
    try {
      const response = await fetch(`/api/agents/${agent.id}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        setSessionId(data.sessionId);
        
        // Add welcome message based on agent
        let welcomeContent = '';
        if (agent.id === 'agent-97') {
          welcomeContent = `Hello! I'm here to help explain medical terms and health topics in plain language. 

I can provide educational information about conditions, symptoms, treatments, and wellness - all from trusted medical sources. 

Please remember: This is for learning only. I cannot diagnose, prescribe, or replace professional medical advice.

What would you like to understand better today?`;
        } else {
          welcomeContent = `Hello! I'm ${agent.name}. ${agent.mission} How can I assist you today?`;
        }
        
        const welcomeMessage: Message = {
          id: `welcome-${Date.now()}`,
          sessionId: data.sessionId,
          role: 'assistant',
          content: welcomeContent,
          timestamp: new Date().toISOString(),
          toolCalls: [],
          citations: []
        };
        setMessages([welcomeMessage]);
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || !sessionId || isStreaming) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sessionId,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
      toolCalls: [],
      citations: []
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    // Create assistant message placeholder
    const assistantMessage: Message = {
      id: `assistant-${Date.now()}`,
      sessionId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      toolCalls: [],
      citations: [],
      streaming: true
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      // Use fetch with streaming instead of EventSource for better control
      const response = await fetch(`/api/agents/${agent.id}/stream?` + new URLSearchParams({
        sessionId,
        query: userMessage.content
      }), {
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error('Failed to connect to agent');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response stream available');
      }

      let buffer = '';

      // Read the stream
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
              setIsStreaming(false);
              break;
            }
            try {
              const event = JSON.parse(data);
              handleStreamEvent(event, assistantMessage.id);
            } catch (e) {
              console.error('Failed to parse event:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      setIsStreaming(false);
      
      // Update message with error
      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantMessage.id 
            ? { ...msg, content: 'Sorry, I encountered an error. Please try again.', error: String(error), streaming: false }
            : msg
        )
      );
    }
  };

  const handleStreamEvent = (event: any, messageId: string) => {
    switch (event.type) {
      case 'text':
        // Handle both formats: 
        // - Agent format: {type: "text", data: {delta: "..."}}
        // - Backend format: {type: "text", content: "..."}
        const newContent = event.data?.delta || event.data?.content || event.content || '';
        setStreamingContent(prev => prev + newContent);
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: msg.content + newContent, streaming: true }
              : msg
          )
        );
        break;
        
      case 'tool_use':
      case 'tool_call_start':
        // Handle both backend formats
        const toolData = event.content || event.data || {};
        const newToolCall: ToolCall = {
          id: toolData.id || `tool_${Date.now()}`,
          name: toolData.name || toolData.input?.name || 'unknown',
          arguments: toolData.arguments || toolData.input || {},
          status: 'executing',
          startTime: toolData.startTime || new Date().toISOString()
        };
        // Update message with new tool call
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId
              ? { 
                  ...msg, 
                  toolCalls: [...(msg.toolCalls || []), newToolCall]
                }
              : msg
          )
        );
        console.log('Tool call started:', newToolCall);
        break;
        
      case 'tool_call_end':
        const updatedToolCall = {
          ...event.data,
          status: 'completed' as const,
          endTime: event.data.endTime || new Date().toISOString()
        };
        
        // Update the message with completed tool call
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId
              ? { 
                  ...msg, 
                  toolCalls: msg.toolCalls?.map(tc => 
                    tc.id === event.data.id ? updatedToolCall : tc
                  ) || []
                }
              : msg
          )
        );
        break;
        
      case 'citation':
        const citationData = event.data || event.content || {};
        const citation: Citation = {
          ...citationData,
          id: citationData.id || `citation_${Date.now()}_${Math.random()}`,
          accessDate: citationData.accessDate || new Date().toISOString()
        };
        
        // Update the message with citations (deduped by URL)
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id === messageId) {
              const existingCitations = msg.citations || [];
              const exists = existingCitations.find(c => c.url === citation.url);
              if (!exists) {
                return { ...msg, citations: [...existingCitations, citation] };
              }
            }
            return msg;
          })
        );
        break;
        
      case 'response_done':
      case 'done':
      case 'complete':
        // Extract citations from complete event if present
        const completeCitations = (event.content?.citations || event.data?.citations || []).map((c: any) => ({
          ...c,
          id: c.id || `citation_${Date.now()}_${Math.random()}`,
          accessDate: c.accessDate || new Date().toISOString(),
          isTrusted: c.isTrusted !== undefined ? c.isTrusted : true
        }));
        
        // Extract tool calls from complete event if present  
        const completeToolCalls = (event.content?.toolCalls || event.data?.toolCalls || []).map((t: any) => ({
          ...t,
          id: t.id || `tool_${Date.now()}_${Math.random()}`,
          status: 'completed' as const,
          startTime: t.startTime || new Date().toISOString(),
          endTime: t.endTime || new Date().toISOString()
        }));
        
        // Final update - mark streaming false and ensure all tool calls are completed
        setMessages(prev => 
          prev.map(msg => {
            if (msg.id === messageId) {
              // Mark all existing tool calls as completed
              const finalToolCalls = msg.toolCalls?.map(tc => ({
                ...tc,
                status: 'completed' as const,
                endTime: tc.endTime || new Date().toISOString()
              })) || [];
              
              // Add any tool calls from complete event that aren't already there
              completeToolCalls.forEach((newTool: ToolCall) => {
                if (!finalToolCalls.find(t => t.name === newTool.name)) {
                  finalToolCalls.push(newTool);
                }
              });
              
              // Add citations from complete event
              const finalCitations = [...(msg.citations || [])];
              completeCitations.forEach((newCite: Citation) => {
                if (!finalCitations.find(c => c.url === newCite.url)) {
                  finalCitations.push(newCite);
                }
              });
              
              return { 
                ...msg, 
                streaming: false,
                toolCalls: finalToolCalls,
                citations: finalCitations
              };
            }
            return msg;
          })
        );
        setIsStreaming(false);
        setStreamingContent('');
        break;
        
      case 'error':
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId
              ? { ...msg, error: event.data.error, streaming: false }
              : msg
          )
        );
        setIsStreaming(false);
        break;
    }
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsStreaming(false);
  };

  const startNewConversation = () => {
    setMessages([]);
    initializeSession();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-16rem)] bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Sticky header bar */}
        <div className="sticky top-0 z-10 bg-white border-b shadow-sm">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl" role="img" aria-label={agent.name}>
                {agent.icon}
              </span>
              <div>
                <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                <p className="text-xs text-gray-500">{agent.description}</p>
              </div>
              <Badge className="bg-green-100 text-green-700 border-green-200">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                Online
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={startNewConversation}>
              <RefreshCw className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6 py-4">
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((message) => (
              <AgentMessage
                key={message.id}
                message={message}
                agentName={agent.name}
                agentIcon={agent.icon}
                isStreaming={message.streaming}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t bg-gradient-to-b from-gray-50/50 to-white px-6 py-3">
          <div className="flex gap-2 max-w-3xl mx-auto">
            <div className="flex-1 relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={`Ask ${agent.name} anything...`}
                disabled={isStreaming}
                className="flex-1 pr-10 bg-white border-gray-200 focus:border-blue-500 focus:ring-blue-500"
              />
              {isStreaming && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                </div>
              )}
            </div>
            {isStreaming ? (
              <Button onClick={stopStreaming} variant="outline" size="icon" className="bg-white">
                <StopCircle className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleSendMessage} disabled={!input.trim()} size="icon" className="bg-blue-600 hover:bg-blue-700">
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
          {isStreaming && (
            <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 max-w-3xl mx-auto">
              {agent.name} is analyzing your question...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}