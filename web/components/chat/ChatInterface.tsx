'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from './Message';
import { FeedbackButtons } from './FeedbackButtons';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Send, Loader2, AlertTriangle } from 'lucide-react';
import { Message as MessageType } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

interface ChatInterfaceProps {
  sessionId: string;
  userId?: string;
}

export function ChatInterface({ sessionId, userId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Add initial system message
  useEffect(() => {
    setMessages([
      {
        id: uuidv4(),
        role: 'system',
        content: 'Welcome to the AI Health Assistant. I can provide educational health information to help you better understand medical topics. Please note that this information is for educational purposes only and is not a substitute for professional medical advice. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: MessageType = {
      id: uuidv4(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage.content,
          sessionId,
          userId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      const assistantMessage: MessageType = {
        id: uuidv4(),
        role: 'assistant',
        content: data.content,
        citations: data.citations,
        timestamp: new Date().toISOString(),
        traceId: data.traceId,
        guardrailTriggered: data.guardrailTriggered,
      };

      setMessages((prev) => [...prev, assistantMessage]);
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
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">AI Health Assistant</h2>
            <p className="text-sm text-muted-foreground">
              Educational health information powered by trusted medical sources
            </p>
          </div>
          <Badge variant="outline" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Not Medical Advice
          </Badge>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id}>
              <Message message={message} />
              {message.role === 'assistant' && message.traceId && (
                <div className="ml-11">
                  <FeedbackButtons
                    traceId={message.traceId}
                    sessionId={sessionId}
                    onFeedback={handleFeedback}
                  />
                </div>
              )}
            </div>
          ))}
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
      <div className="border-t p-4 flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a health-related question..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={!input.trim() || isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
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