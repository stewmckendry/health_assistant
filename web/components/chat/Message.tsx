'use client';

import { Message as MessageType, Citation } from '@/types/chat';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { User, Bot, AlertCircle, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageProps {
  message: MessageType;
  onFeedback?: (traceId: string, feedback: any) => void;
}

function CitationsList({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-4 space-y-2">
      <h4 className="text-sm font-semibold text-muted-foreground">Sources:</h4>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <a
            key={index}
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg border border-border hover:border-primary/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {citation.title}
                </p>
                <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                  {citation.snippet}
                </p>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export function Message({ message, onFeedback }: MessageProps) {
  const isUser = message.role === 'user';
  const isError = message.error;

  return (
    <div
      className={cn(
        'flex gap-3 p-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            {isError ? (
              <AlertCircle className="h-5 w-5 text-destructive" />
            ) : (
              <Bot className="h-5 w-5 text-primary" />
            )}
          </div>
        </div>
      )}

      <div className={cn('flex-1 max-w-2xl', isUser && 'flex justify-end')}>
        <Card
          className={cn(
            'p-4 overflow-hidden',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/50',
            isError && 'border-destructive'
          )}
        >
          {message.guardrailTriggered && (
            <Badge variant="outline" className="mb-2">
              Response modified by safety guardrails
            </Badge>
          )}

          <div
            className={cn(
              'prose prose-sm max-w-none break-words overflow-wrap-anywhere',
              isUser && 'prose-invert',
              'dark:prose-invert'
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({children}) => <p className="mb-3">{children}</p>,
                  ul: ({children}) => <ul className="list-disc ml-4 mb-3">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal ml-4 mb-3">{children}</ol>,
                  li: ({children}) => <li className="mb-1">{children}</li>,
                  h1: ({children}) => <h1 className="text-xl font-bold mb-3">{children}</h1>,
                  h2: ({children}) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
                  h3: ({children}) => <h3 className="text-base font-bold mb-2">{children}</h3>,
                  code: ({inline, children}) => 
                    inline 
                      ? <code className="px-1 py-0.5 bg-muted rounded text-sm">{children}</code>
                      : <pre className="bg-muted p-3 rounded overflow-x-auto"><code>{children}</code></pre>,
                  blockquote: ({children}) => 
                    <blockquote className="border-l-4 border-primary/20 pl-4 italic">{children}</blockquote>,
                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                  em: ({children}) => <em className="italic">{children}</em>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {message.citations && !isUser && (
            <CitationsList citations={message.citations} />
          )}

          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </Card>
      </div>

      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
            <User className="h-5 w-5 text-primary-foreground" />
          </div>
        </div>
      )}
    </div>
  );
}