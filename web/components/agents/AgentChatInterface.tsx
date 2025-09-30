'use client';

import { useState, useRef, useEffect } from 'react';
import { AgentInfo, Message, ToolCall, Citation } from '@/types/agents';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Send, 
  Loader2, 
  StopCircle,
  RefreshCw,
  Sparkles,
  RotateCcw,
  Plus,
  MessageSquare,
  ChevronDown,
  ArrowUpDown
} from 'lucide-react';
import { AgentMessage } from './AgentMessage';
import { getActiveAgents } from '@/config/agents.config';

interface AgentChatInterfaceProps {
  agent: AgentInfo;
  onClose: () => void;
  onAgentSwitch?: (agentId: string) => void;
}

export function AgentChatInterface({ agent, onClose, onAgentSwitch }: AgentChatInterfaceProps) {
  const [availableAgents, setAvailableAgents] = useState<AgentInfo[]>([]);
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
    
    // Load available agents
    const agents = getActiveAgents();
    setAvailableAgents(agents);
  }, [agent.id]);

  // Auto-scroll to bottom when messages change (but not on initial load)
  useEffect(() => {
    // Only scroll if there are user messages (not just the welcome message)
    const hasUserMessages = messages.some(m => m.role === 'user');
    if (hasUserMessages) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
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
        } else if (agent.id === 'dr-off') {
          welcomeContent = `Hello! I'm Dr. OFF (Ontario Finance & Formulary), your assistant for Ontario healthcare financing and coverage.

I can help you with OHIP billing codes and fee schedules, Ontario Drug Benefit (ODB) formulary coverage, Assistive Devices Program (ADP) eligibility, and finding generic alternatives for cost-effective prescribing.

How can I assist with your coverage or billing questions today?`;
        } else if (agent.id === 'orchestrator') {
          welcomeContent = `Hello! I'm The Chief, your Ontario healthcare coordinator.

I bring together guidance from Ontario's medical systems by coordinating three specialist agents: Dr. OPA for CPSO policies and Ontario Health programs, Dr. OFF for OHIP billing and drug coverage, and Agent 97 for medical education from trusted sources.

What Ontario healthcare question can I help you with today?`;
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

  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || input.trim();
    if (!textToSend || !sessionId || isStreaming) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sessionId,
      role: 'user',
      content: textToSend,
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

      // Use fetch with streaming - send as POST to include userId
      const response = await fetch(`/api/agents/${agent.id}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId,
          query: userMessage.content,
          userId: sessionId, // Use sessionId as userId for now
          stream: true
        }),
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
        // Extract trace ID from event if present
        const traceId = event.data?.traceId || event.metadata?.trace_id || null;
        
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
                  finalToolCalls.push({
                    ...newTool,
                    status: 'completed' as const,
                    endTime: newTool.endTime || new Date().toISOString()
                  });
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
                citations: finalCitations,
                traceId: traceId // Add trace ID for feedback
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

  const handleFeedback = async (feedback: {
    traceId: string;
    sessionId: string;
    rating?: number;
    comment?: string;
    thumbsUp?: boolean;
  }) => {
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback),
      });
      
      if (!response.ok) {
        console.error('Failed to submit feedback');
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    initializeSession();
  };
  
  const regenerateLastMessage = async () => {
    if (messages.length < 2 || isStreaming) return;
    
    // Find the last user message
    const lastUserMessageIndex = messages.findLastIndex(msg => msg.role === 'user');
    if (lastUserMessageIndex === -1) return;
    
    const lastUserMessage = messages[lastUserMessageIndex];
    
    // Remove all messages after the last user message
    setMessages(prev => prev.slice(0, lastUserMessageIndex + 1));
    
    // Directly resend the last user message
    // We need to handle this directly instead of using setInput + handleSendMessage
    // because React state updates are async
    const messageContent = lastUserMessage.content;
    
    setIsStreaming(true);
    setStreamingContent('');

    // Create assistant message placeholder
    const assistantMessage: Message = {
      id: `assistant-${Date.now()}`,
      sessionId: sessionId!,
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

      // Use fetch with streaming - send as POST to include userId
      const response = await fetch(`/api/agents/${agent.id}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: sessionId!,
          query: messageContent,
          userId: sessionId!, // Use sessionId as userId for now
          stream: true
        }),
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
      console.error('Failed to regenerate message:', error);
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div 
      className="flex flex-col h-full bg-white rounded-lg lg:rounded-2xl shadow-lg lg:shadow-2xl overflow-hidden border border-gray-100"
      style={{
        /* Force white background in Chrome dark mode */
        backgroundColor: '#ffffff',
        color: '#000000',
      }}
    >
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-white to-gray-50/50 overflow-hidden">
        {/* Enhanced Fixed header bar */}
        <div className="sticky top-0 z-20 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-cyan-500/5"></div>
            <div className="relative flex items-center justify-between px-3 sm:px-6 py-2 sm:py-3">
              <div className="flex items-center gap-2 sm:gap-4">
                <Badge className="bg-gradient-to-r from-green-500 to-emerald-500 text-white border-0 shadow-md px-2 sm:px-4 py-1 sm:py-2 text-xs sm:text-sm">
                  <span className="inline-block w-1.5 h-1.5 sm:w-2 sm:h-2 bg-white rounded-full mr-1 sm:mr-2 animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.8)]"></span>
                  Online
                </Badge>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={startNewConversation}
                className="border-2 hover:bg-blue-50 hover:border-blue-300 font-medium sm:font-semibold text-xs sm:text-sm"
              >
                <Plus className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">New Chat</span>
                <span className="sm:hidden">New</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Enhanced Messages Area */}
        <ScrollArea className="flex-1 px-3 sm:px-6 py-3 sm:py-4 overflow-y-auto bg-gradient-to-b from-transparent to-gray-50/30">
          <div className="space-y-6 max-w-4xl mx-auto">
            {messages.map((message) => (
              <AgentMessage
                key={message.id}
                message={message}
                agentName={agent.name}
                agentIcon={agent.icon}
                isStreaming={message.streaming}
                onFeedback={handleFeedback}
              />
            ))}
            
            {/* Action buttons shown after the last message */}
            {messages.length > 1 && !isStreaming && messages[messages.length - 1].role === 'assistant' && (
              <div className="flex gap-2 pt-2 pb-3 sm:pb-4">
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={regenerateLastMessage}
                  className="text-gray-500 hover:text-gray-700 text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
                >
                  <RotateCcw className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">Regenerate</span>
                  <span className="sm:hidden">Redo</span>
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={startNewConversation}
                  className="text-gray-500 hover:text-gray-700 text-xs sm:text-sm px-2 sm:px-3 py-1 sm:py-1.5"
                >
                  <RefreshCw className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">New Chat</span>
                  <span className="sm:hidden">New</span>
                </Button>
              </div>
            )}
            
            {/* Enhanced Starter Prompts */}
            {messages.length === 1 && messages[0].role === 'assistant' && agent.starterPrompts && !isStreaming && (
              <div className="mt-6 sm:mt-8">
                <div className="flex items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
                  <div className="p-1.5 sm:p-2 bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg">
                    <Sparkles className="h-3 w-3 sm:h-4 sm:w-4 text-purple-600" />
                  </div>
                  <span className="font-semibold text-gray-700 text-sm sm:text-base">Suggested questions</span>
                </div>
                <div className="grid gap-2 sm:gap-3 sm:grid-cols-2">
                  {agent.starterPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(prompt)}
                      className="text-left p-3 sm:p-4 bg-gradient-to-br from-white to-blue-50/50 hover:from-blue-50 hover:to-cyan-50 rounded-lg sm:rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200 group"
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-1.5 bg-blue-100 rounded-lg mt-0.5">
                          <MessageSquare className="h-3 w-3 text-blue-600" />
                        </div>
                        <p className="text-sm text-gray-700 group-hover:text-gray-900 leading-relaxed font-medium">
                          {prompt}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Enhanced Input Area - Mobile responsive */}
        <div className="border-t border-gray-200 bg-white/95 backdrop-blur-sm px-3 sm:px-6 py-2 sm:py-3">
          <div className="flex gap-2 sm:gap-3 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={agent.id === 'dr-off' 
                  ? `Ask about OHIP billing, ODB coverage, or ADP eligibility...`
                  : `Ask ${agent.name} anything...`}
                disabled={isStreaming}
                className="flex-1 h-10 sm:h-12 px-3 sm:px-4 pr-10 sm:pr-12 bg-white border-2 border-gray-200 rounded-lg sm:rounded-xl focus:border-blue-400 focus:ring-2 sm:focus:ring-4 focus:ring-blue-100 transition-all text-sm sm:text-base text-gray-700 placeholder:text-gray-400"
                style={{
                  /* Force colors in Chrome dark mode */
                  backgroundColor: '#ffffff',
                  color: '#374151',
                }}
              />
              {isStreaming && (
                <div className="absolute right-4 top-1/2 -translate-y-1/2">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                </div>
              )}
            </div>
            {isStreaming ? (
              <Button 
                onClick={stopStreaming} 
                variant="outline" 
                size="icon" 
                className="h-10 w-10 sm:h-12 sm:w-12 border-2 hover:bg-red-50 hover:border-red-300 hover:text-red-600 transition-all"
              >
                <StopCircle className="h-4 w-4 sm:h-5 sm:w-5" />
              </Button>
            ) : (
              <Button 
                onClick={() => handleSendMessage()} 
                disabled={!input.trim()} 
                size="icon" 
                className="h-10 w-10 sm:h-12 sm:w-12 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white shadow-lg hover:shadow-xl disabled:opacity-50 disabled:shadow-none transition-all"
              >
                <Send className="h-4 w-4 sm:h-5 sm:w-5" />
              </Button>
            )}
          </div>
          {isStreaming && (
            <div className="flex items-center justify-center gap-2 mt-2 sm:mt-3 max-w-4xl mx-auto">
              <div className="flex items-center gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-blue-50 rounded-full">
                <div className="flex gap-0.5 sm:gap-1">
                  <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce"></span>
                </div>
                <span className="text-xs sm:text-sm text-blue-700 font-medium">{agent.name} is thinking...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}