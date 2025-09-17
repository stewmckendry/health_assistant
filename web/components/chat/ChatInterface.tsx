'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from './Message';
import { FeedbackButtons } from './FeedbackButtons';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Send, Loader2, AlertTriangle, Zap, RefreshCw, Plus } from 'lucide-react';
import { Message as MessageType } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

interface ChatInterfaceProps {
  sessionId: string;
  userId?: string;
  mode?: 'patient' | 'provider';
}

export function ChatInterface({ sessionId, userId, mode = 'patient' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true); // Default to true
  const [streamingContent, setStreamingContent] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingContent]);

  // Load session settings to determine streaming preference
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`/api/sessions/${sessionId}/settings`);
        if (response.ok) {
          const data = await response.json();
          if (data.settings && typeof data.settings.enable_streaming !== 'undefined') {
            setUseStreaming(data.settings.enable_streaming);
          }
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    };
    loadSettings();
  }, [sessionId]);

  // Add initial system message based on mode
  useEffect(() => {
    const systemMessage = mode === 'provider' 
      ? 'Welcome to the AI Health Assistant - Provider Mode. I can provide evidence-based clinical information, treatment guidelines, and decision support for healthcare professionals. How can I assist you today?'
      : 'Welcome to the AI Health Assistant. I can provide educational health information to help you better understand medical topics. Please note that this information is for educational purposes only and is not a substitute for professional medical advice. How can I help you today?';
    
    setMessages([
      {
        id: uuidv4(),
        role: 'system',
        content: systemMessage,
        timestamp: new Date().toISOString(),
        mode,
      },
    ]);
  }, [mode]);

  const handleSubmit = async (e?: React.FormEvent, messageContent?: string, isRegenerate: boolean = false) => {
    if (e) e.preventDefault();
    const content = messageContent || input.trim();
    if (!content || isLoading) return;

    const userMessage: MessageType = {
      id: uuidv4(),
      role: 'user',
      content: content,
      timestamp: new Date().toISOString(),
      mode,
    };

    // Only add user message if not regenerating (it's already in history)
    if (!isRegenerate) {
      setMessages((prev) => [...prev, userMessage]);
    }
    if (!messageContent) setInput('');
    setIsLoading(true);
    setStreamingContent(''); // Reset streaming content

    try {
      console.log('Using streaming?', useStreaming); // Debug log
      if (useStreaming) {
        // Use streaming endpoint
        await handleStreamingResponse(userMessage);
      } else {
        // Use non-streaming endpoint
        await handleNonStreamingResponse(userMessage);
      }
    } catch (error) {
      console.error('Chat error:', error);
      
      const errorMessage: MessageType = {
        id: uuidv4(),
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again later.',
        timestamp: new Date().toISOString(),
        error: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = () => {
    // Find the last user message
    const lastUserMessage = [...messages].reverse().find(msg => msg.role === 'user');
    if (lastUserMessage) {
      // Find the index of the last assistant message
      const lastAssistantIndex = messages.findLastIndex(msg => msg.role === 'assistant');
      const lastUserIndex = messages.findLastIndex(msg => msg.role === 'user');
      
      // Only remove the last assistant message if it came after the last user message
      if (lastAssistantIndex > -1 && lastAssistantIndex > lastUserIndex) {
        // Keep all messages up to (but not including) the last assistant message
        setMessages(prev => prev.slice(0, lastAssistantIndex));
      }
      
      // Wait a bit for state to update, then resend with the preserved history
      setTimeout(() => {
        handleSubmit(undefined, lastUserMessage.content, true); // Pass true for isRegenerate
      }, 100);
    }
  };

  const handleNewSession = () => {
    // Reset messages to initial system message
    const systemMessage = mode === 'provider' 
      ? 'Welcome to the AI Health Assistant - Provider Mode. I can provide evidence-based clinical information, treatment guidelines, and decision support for healthcare professionals. How can I assist you today?'
      : 'Welcome to the AI Health Assistant. I can provide educational health information to help you better understand medical topics. Please note that this information is for educational purposes only and is not a substitute for professional medical advice. How can I help you today?';
    
    setMessages([
      {
        id: uuidv4(),
        role: 'system',
        content: systemMessage,
        timestamp: new Date().toISOString(),
        mode,
      },
    ]);
    setInput('');
    setStreamingContent('');
  };

  const handleNonStreamingResponse = async (userMessage: MessageType) => {
    // Include message history for context
    const conversationHistory = messages.filter(msg => msg.role !== 'system').map(msg => ({
      role: msg.role,
      content: msg.content
    }));
    
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: userMessage.content,
        sessionId,
        userId,
        mode,
        messages: conversationHistory, // Include conversation history
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to get response');
    }

    const data = await response.json();
    console.log('Response data from /api/chat:', data); // Debug log

    const assistantMessage: MessageType = {
      id: uuidv4(),
      role: 'assistant',
      content: data.content,
      citations: data.citations,
      timestamp: new Date().toISOString(),
      traceId: data.traceId,
      guardrailTriggered: data.guardrailTriggered,
      mode: data.mode || mode,
    };
    console.log('Assistant message with traceId:', assistantMessage.traceId); // Debug log

    setMessages((prev) => [...prev, assistantMessage]);
  };

  const handleStreamingResponse = async (userMessage: MessageType) => {
    let accumulatedText = '';
    const citations: any[] = [];
    let traceId = '';
    const assistantMessageId = uuidv4();

    // Include message history for context
    const conversationHistory = messages.filter(msg => msg.role !== 'system').map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: userMessage.content,
        sessionId,
        userId,
        mode,
        messages: conversationHistory, // Include conversation history
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to get response');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    // Add placeholder message for streaming
    const placeholderMessage: MessageType = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      mode,
    };
    setMessages((prev) => [...prev, placeholderMessage]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'start') {
              traceId = data.traceId;
              console.log('Streaming started with traceId:', traceId); // Debug log
            } else if (data.type === 'text') {
              accumulatedText += data.content;
              setStreamingContent(accumulatedText);
              // Update the message in place
              setMessages((prev) => 
                prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: accumulatedText }
                    : msg
                )
              );
            } else if (data.type === 'citation') {
              citations.push(data.content);
            } else if (data.type === 'complete' || data.type === 'end') {
              // Extract traceId from complete event if we don't have it
              if (!traceId && data.traceId) {
                traceId = data.traceId;
              }
              // Final update with all metadata
              console.log('Stream complete, setting traceId:', traceId); // Debug log
              setMessages((prev) => 
                prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { 
                        ...msg, 
                        content: accumulatedText,
                        citations: citations.length > 0 ? citations : undefined,
                        traceId,
                        guardrailTriggered: data.guardrailTriggered,
                      }
                    : msg
                )
              );
              setStreamingContent('');
            }
          } catch (error) {
            console.error('Failed to parse SSE data:', error);
          }
        }
      }
    }
  };

  const handleFeedback = async (feedback: any) => {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedback),
      });
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  return (
    <Card className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b p-4 flex-shrink-0">
        {/* Research Disclaimer */}
        <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-3">
          <p className="text-xs text-blue-700 dark:text-blue-300 font-medium">
            🔬 Research Project: This is an experimental AI health assistant created for learning and research purposes only. 
            Not intended for real medical use. Always consult qualified healthcare professionals for medical advice.
          </p>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              AI Health Assistant {mode === 'provider' && '- Provider Mode'}
            </h2>
            <p className="text-sm text-muted-foreground">
              {mode === 'provider' 
                ? 'Evidence-based clinical information for healthcare professionals'
                : 'Educational health information powered by trusted medical sources'
              }
            </p>
          </div>
          <div className="flex items-center gap-2">
            {mode === 'patient' ? (
              <Badge variant="outline" className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Not Medical Advice
              </Badge>
            ) : (
              <Badge variant="secondary" className="flex items-center gap-1">
                🔬 Professional Use
              </Badge>
            )}
            {useStreaming && (
              <Badge variant="default" className="flex items-center gap-1">
                <Zap className="h-3 w-3" />
                Streaming
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((message, index) => {
            console.log('Rendering message:', message.role, 'traceId:', message.traceId); // Debug log
            // Check if this is the last assistant message
            const isLastAssistantMessage = 
              message.role === 'assistant' && 
              index === messages.findLastIndex(msg => msg.role === 'assistant');
            
            return (
              <div key={message.id}>
                <Message message={message} />
                {message.role === 'assistant' && (
                  <div className="ml-11 space-y-2">
                    {message.traceId && (
                      <FeedbackButtons
                        traceId={message.traceId}
                        sessionId={sessionId}
                        onFeedback={handleFeedback}
                      />
                    )}
                    {isLastAssistantMessage && !isLoading && (
                      <div className="flex gap-2 mt-2">
                        <Button
                          onClick={handleRegenerate}
                          variant="ghost"
                          size="sm"
                          className="flex items-center gap-1 text-muted-foreground hover:text-foreground h-7 text-xs"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Regenerate
                        </Button>
                        <Button
                          onClick={handleNewSession}
                          variant="ghost"
                          size="sm"
                          className="flex items-center gap-1 text-muted-foreground hover:text-foreground h-7 text-xs"
                        >
                          <Plus className="h-3 w-3" />
                          New session
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {isLoading && (
            <div className="flex gap-3 p-4">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              </div>
              <Card className="p-4 bg-muted/50">
                <p className="text-sm text-muted-foreground">
                  Searching trusted medical sources...
                </p>
              </Card>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t bg-muted/30 p-4 flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              messages.length > 1 
                ? "Ask a follow-up question or start a new topic..." 
                : "Ask a health-related question..."
            }
            disabled={isLoading}
            className="flex-1 bg-background border-2 focus:border-primary transition-colors"
          />
          <Button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            className="min-w-[100px]"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Send className="h-4 w-4 mr-1" />
                Send
              </>
            )}
          </Button>
        </form>
        <p className="text-xs text-muted-foreground mt-2">
          This assistant provides educational information only. Always consult healthcare professionals for medical advice.
        </p>
      </div>
    </Card>
  );
}