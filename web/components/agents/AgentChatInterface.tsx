'use client';

import { useState, useRef, useEffect } from 'react';
import { AgentInfo, Message, ToolCall, Citation, ConversationSession } from '@/types/agents';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Send, 
  Loader2, 
  Bot, 
  User,
  StopCircle,
  RefreshCw,
  ExternalLink,
  Wrench,
  Brain,
  FileText,
  Sparkles
} from 'lucide-react';
import { ToolCallDisplay } from './ToolCallDisplay';
import { CitationList } from './CitationList';
import { StreamingMessage } from './StreamingMessage';
import ReactMarkdown from 'react-markdown';

interface AgentChatInterfaceProps {
  agent: AgentInfo;
  onClose: () => void;
}

export function AgentChatInterface({ agent, onClose }: AgentChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [allCitations, setAllCitations] = useState<Citation[]>([]);
  const [allToolCalls, setAllToolCalls] = useState<ToolCall[]>([]);
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
        let welcomeContent = `Hello! I'm ${agent.name}. ${agent.mission} How can I assist you today?`;
        
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
    setCurrentToolCalls([]);
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
        const newContent = (event.data.delta || event.data.content || '');
        setStreamingContent(prev => prev + newContent);
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: msg.content + newContent, streaming: true }
              : msg
          )
        );
        break;
        
      case 'tool_call_start':
        const newToolCall: ToolCall = {
          id: event.data.id || `tool_${Date.now()}`,
          name: event.data.name,
          arguments: event.data.arguments || {},
          status: 'executing',
          startTime: event.data.startTime || new Date().toISOString()
        };
        setCurrentToolCalls(prev => {
          // Avoid duplicates
          if (prev.find(t => t.id === newToolCall.id)) return prev;
          return [...prev, newToolCall];
        });
        setAllToolCalls(prev => {
          if (prev.find(t => t.id === newToolCall.id)) return prev;
          return [...prev, newToolCall];
        });
        console.log('Tool call started:', newToolCall);
        break;
        
      case 'tool_call_end':
        const updatedToolCall = {
          ...event.data,
          status: 'completed' as const,
          endTime: event.data.endTime || new Date().toISOString()
        };
        setCurrentToolCalls(prev => 
          prev.map(tc => 
            tc.id === event.data.id ? updatedToolCall : tc
          )
        );
        setAllToolCalls(prev => 
          prev.map(tc => 
            tc.id === event.data.id ? updatedToolCall : tc
          )
        );
        
        // Also update the message with tool calls
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId
              ? { ...msg, toolCalls: [...(msg.toolCalls || []), updatedToolCall] }
              : msg
          )
        );
        break;
        
      case 'citation':
        const citation: Citation = {
          ...event.data,
          accessDate: event.data.accessDate || new Date().toISOString()
        };
        setAllCitations(prev => {
          // Deduplicate citations by URL
          const exists = prev.find(c => c.url === citation.url);
          if (exists) return prev;
          return [...prev, citation];
        });
        
        // Also update the message with citations
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId
              ? { ...msg, citations: [...(msg.citations || []), citation] }
              : msg
          )
        );
        break;
        
      case 'response_done':
      case 'done':
        // Final update with all accumulated data
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId 
              ? { 
                  ...msg, 
                  streaming: false,
                  toolCalls: currentToolCalls.length > 0 ? currentToolCalls : msg.toolCalls,
                  citations: allCitations.length > 0 ? allCitations : msg.citations
                }
              : msg
          )
        );
        setIsStreaming(false);
        setStreamingContent('');
        // Don't clear currentToolCalls here - keep them for display
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
    setCurrentToolCalls([]);
  };

  const startNewConversation = () => {
    setMessages([]);
    setAllCitations([]);
    setCurrentToolCalls([]);
    setAllToolCalls([]);
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
          <div className="space-y-3 max-w-3xl mx-auto">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                  <div className={`flex items-start gap-2 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gradient-to-br from-violet-500 to-purple-600 text-white'
                    }`}>
                      {message.role === 'user' ? (
                        <User className="h-3.5 w-3.5" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                    </div>
                    <div className={`rounded-2xl px-4 py-2.5 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200'
                    }`}>
                      {message.streaming && !message.content ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          <span className="text-sm italic">Thinking...</span>
                        </div>
                      ) : (
                        <div className="text-sm leading-relaxed prose prose-sm max-w-none" style={{overflowWrap: 'break-word', wordBreak: 'break-word'}}>
                          <ReactMarkdown
                            components={{
                              h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2">{children}</h1>,
                              h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-2">{children}</h2>,
                              h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
                              p: ({ children }) => <p className="mb-2">{children}</p>,
                              ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                              ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                              li: ({ children }) => <li className="mb-1">{children}</li>,
                              code: ({ inline, children }) => 
                                inline ? (
                                  <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">{children}</code>
                                ) : (
                                  <pre className="bg-gray-100 p-2 rounded overflow-x-auto"><code>{children}</code></pre>
                                ),
                              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                              em: ({ children }) => <em className="italic">{children}</em>,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      )}
                      {message.error && (
                        <div className="text-red-500 text-xs mt-2">
                          Error: {message.error}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
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

      {/* Right Side Panel - Reasoning & Citations */}
      {messages.length > 0 && (
      <div className="w-96 border-l bg-gray-50 flex flex-col">
        <Tabs defaultValue="reasoning" className="flex-1 flex flex-col">
          <TabsList className="mx-4 mt-4 grid w-[calc(100%-2rem)] grid-cols-2">
            <TabsTrigger value="reasoning" className="text-xs">
              <Brain className="h-3 w-3 mr-1" />
              Reasoning
            </TabsTrigger>
            <TabsTrigger value="citations" className="text-xs">
              <FileText className="h-3 w-3 mr-1" />
              Citations
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="reasoning" className="flex-1 px-4 pb-4 mt-4">
            <div className="bg-white rounded-lg border h-full flex flex-col">
              <div className="p-3 border-b">
                <h4 className="text-sm font-medium text-gray-900">Tool Calls & Reasoning</h4>
                <p className="text-xs text-gray-500 mt-1">
                  See how {agent.name} processes your request
                </p>
              </div>
              <ScrollArea className="flex-1 p-3">
                {(currentToolCalls.length > 0 || allToolCalls.length > 0) ? (
                  <div className="space-y-3">
                    {/* Current active tool calls */}
                    {currentToolCalls.filter(tc => tc.status === 'executing').map((toolCall) => (
                      <div key={toolCall.id} className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                        <div className="flex items-center gap-2 mb-2">
                          <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                          <span className="text-xs font-medium text-blue-900">Executing</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Wrench className="h-3 w-3 text-blue-600" />
                          <span className="font-mono text-xs text-blue-800">{toolCall.name}</span>
                        </div>
                        {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
                          <div className="mt-2 text-xs text-blue-700 bg-white/50 rounded p-2">
                            <pre className="whitespace-pre-wrap">
                              {JSON.stringify(toolCall.arguments, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* Completed tool calls */}
                    {allToolCalls.filter(tc => tc.status === 'completed').map((toolCall) => (
                      <div key={toolCall.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                          <span className="text-xs text-gray-600">Completed</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Wrench className="h-3 w-3 text-gray-500" />
                          <span className="font-mono text-xs text-gray-700">{toolCall.name}</span>
                        </div>
                        {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
                          <div className="mt-2 text-xs text-gray-600 bg-white/50 rounded p-2">
                            <pre className="whitespace-pre-wrap">
                              {JSON.stringify(toolCall.arguments, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : isStreaming ? (
                  <div className="text-center py-8">
                    <Loader2 className="h-8 w-8 text-gray-400 mx-auto mb-3 animate-spin" />
                    <p className="text-xs text-gray-500">
                      Waiting for tool calls...
                    </p>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Brain className="h-8 w-8 text-gray-300 mx-auto mb-3" />
                    <p className="text-xs text-gray-500">
                      Tool calls and reasoning steps will appear here as the agent processes your questions
                    </p>
                  </div>
                )}
              </ScrollArea>
            </div>
          </TabsContent>
          
          <TabsContent value="citations" className="flex-1 px-4 pb-4 mt-4">
            <div className="bg-white rounded-lg border h-full flex flex-col">
              <div className="p-3 border-b">
                <h4 className="text-sm font-medium text-gray-900">Sources & Citations</h4>
                <p className="text-xs text-gray-500 mt-1">
                  {allCitations.length} sources referenced
                </p>
              </div>
              <ScrollArea className="flex-1">
                {allCitations.length > 0 ? (
                  <div className="p-3">
                    <CitationList citations={allCitations} />
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <FileText className="h-8 w-8 text-gray-300 mx-auto mb-3" />
                    <p className="text-xs text-gray-500">
                      Citations will appear here as the agent responds
                    </p>
                  </div>
                )}
              </ScrollArea>
            </div>
          </TabsContent>
        </Tabs>
      </div>
      )}
    </div>
  );
}