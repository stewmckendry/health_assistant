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
  Settings,
  MessageSquare,
  StopCircle,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { ToolCallDisplay } from './ToolCallDisplay';
import { CitationList } from './CitationList';
import { StreamingMessage } from './StreamingMessage';

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
  const [showToolPanel, setShowToolPanel] = useState(true);
  
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
        
        // Add welcome message
        const welcomeMessage: Message = {
          id: `welcome-${Date.now()}`,
          sessionId: data.sessionId,
          role: 'assistant',
          content: `Hello! I'm ${agent.name}. ${agent.mission} How can I assist you today?`,
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

      // Start streaming response
      const eventSource = new EventSource(
        `/api/agents/${agent.id}/stream?` + new URLSearchParams({
          sessionId,
          query: input.trim()
        })
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleStreamEvent(data, assistantMessage.id);
      };

      eventSource.onerror = (error) => {
        console.error('Streaming error:', error);
        setIsStreaming(false);
        eventSource.close();
      };

      // Store event source for cleanup
      const cleanup = () => {
        eventSource.close();
        setIsStreaming(false);
      };

      // Set timeout for long-running requests
      setTimeout(() => {
        if (isStreaming) {
          cleanup();
        }
      }, 120000); // 2 minutes timeout

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
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId 
              ? { ...msg, content: msg.content + event.data.delta }
              : msg
          )
        );
        break;
        
      case 'tool_call_start':
        const newToolCall: ToolCall = {
          ...event.data,
          status: 'executing',
          startTime: new Date().toISOString()
        };
        setCurrentToolCalls(prev => [...prev, newToolCall]);
        break;
        
      case 'tool_call_end':
        setCurrentToolCalls(prev => 
          prev.map(tc => 
            tc.id === event.data.id 
              ? { ...tc, ...event.data, status: 'completed', endTime: new Date().toISOString() }
              : tc
          )
        );
        break;
        
      case 'citation':
        const citation: Citation = {
          ...event.data,
          accessDate: new Date().toISOString()
        };
        setAllCitations(prev => {
          // Deduplicate citations
          if (prev.find(c => c.url === citation.url)) return prev;
          return [...prev, citation];
        });
        break;
        
      case 'done':
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId 
              ? { 
                  ...msg, 
                  streaming: false, 
                  toolCalls: currentToolCalls,
                  citations: allCitations.filter(c => event.data.citationIds?.includes(c.id))
                }
              : msg
          )
        );
        setIsStreaming(false);
        setCurrentToolCalls([]);
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
    initializeSession();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] max-h-[800px]">
      {/* Agent Header */}
      <Card className="flex-shrink-0 mb-4">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl" role="img" aria-label={agent.name}>
                {agent.icon}
              </span>
              <div>
                <h3 className="font-semibold">{agent.name}</h3>
                <p className="text-sm text-muted-foreground">{agent.description}</p>
              </div>
              <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                Online
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={startNewConversation}>
                <RefreshCw className="h-4 w-4 mr-2" />
                New Chat
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <Card className="flex-1 flex flex-col min-h-0">
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((message, index) => (
                  <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                      <div className={`flex items-start gap-3 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          message.role === 'user' 
                            ? 'bg-primary text-primary-foreground' 
                            : 'bg-muted'
                        }`}>
                          {message.role === 'user' ? (
                            <User className="h-4 w-4" />
                          ) : (
                            <Bot className="h-4 w-4" />
                          )}
                        </div>
                        <div className={`rounded-lg p-3 ${
                          message.role === 'user'
                            ? 'bg-primary text-primary-foreground ml-4'
                            : 'bg-muted mr-4'
                        }`}>
                          {message.streaming ? (
                            <StreamingMessage content={message.content} />
                          ) : (
                            <div className="prose prose-sm dark:prose-invert max-w-none">
                              {message.content}
                            </div>
                          )}
                          {message.error && (
                            <div className="text-red-500 text-xs mt-2">
                              Error: {message.error}
                            </div>
                          )}
                        </div>
                      </div>
                      {/* Tool calls for this message */}
                      {message.toolCalls && message.toolCalls.length > 0 && (
                        <div className="mt-2 ml-11">
                          <ToolCallDisplay toolCalls={message.toolCalls} />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {/* Current streaming tool calls */}
                {currentToolCalls.length > 0 && (
                  <div className="flex justify-start">
                    <div className="max-w-[80%] ml-11">
                      <ToolCallDisplay toolCalls={currentToolCalls} />
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 border-t">
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={`Ask ${agent.name} anything...`}
                  disabled={isStreaming}
                  className="flex-1"
                />
                {isStreaming ? (
                  <Button onClick={stopStreaming} variant="outline">
                    <StopCircle className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button onClick={handleSendMessage} disabled={!input.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </div>
              {isStreaming && (
                <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {agent.name} is thinking...
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Side Panel */}
        <div className="w-80 flex-shrink-0">
          <Tabs defaultValue="citations" className="h-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="citations">Citations</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
            </TabsList>
            <TabsContent value="citations" className="mt-4 h-[calc(100%-3rem)]">
              <CitationList citations={allCitations} />
            </TabsContent>
            <TabsContent value="tools" className="mt-4 h-[calc(100%-3rem)]">
              <Card className="h-full">
                <CardHeader className="pb-3">
                  <h4 className="font-medium">Available Tools</h4>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[calc(100%-4rem)]">
                    <div className="space-y-2">
                      {agent.tools.map((tool, idx) => (
                        <div key={idx} className="border rounded p-2 text-sm">
                          <div className="font-mono text-xs">{tool.name}</div>
                          <div className="text-muted-foreground text-xs mt-1">
                            {tool.description}
                          </div>
                          <Badge variant="outline" className="text-xs mt-1">
                            {tool.category}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}