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
                  p: ({children}) => <p className="mb-4 leading-relaxed">{children}</p>,
                  ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-2">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-2">{children}</ol>,
                  li: ({children}) => <li className="leading-relaxed">{children}</li>,
                  h1: ({children}) => <h1 className="text-xl font-bold mb-4 mt-6 first:mt-0">{children}</h1>,
                  h2: ({children}) => <h2 className="text-lg font-bold mb-3 mt-5 first:mt-0">{children}</h2>,
                  h3: ({children}) => <h3 className="text-base font-bold mb-2 mt-4 first:mt-0">{children}</h3>,
                  h4: ({children}) => <h4 className="text-sm font-bold mb-2 mt-3 first:mt-0">{children}</h4>,
                  code: ({children, className}) => {
                    const isInline = !className;
                    return isInline 
                      ? <code className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-sm font-mono">{children}</code>
                      : <pre className="bg-slate-100 dark:bg-slate-800 p-4 rounded-lg overflow-x-auto my-4"><code className="font-mono text-sm">{children}</code></pre>;
                  },
                  blockquote: ({children}) => 
                    <blockquote className="border-l-4 border-blue-200 dark:border-blue-800 pl-4 italic my-4 bg-blue-50 dark:bg-blue-950/20 py-2 rounded-r">{children}</blockquote>,
                  strong: ({children}) => <strong className="font-bold text-slate-900 dark:text-slate-100">{children}</strong>,
                  em: ({children}) => <em className="italic text-slate-700 dark:text-slate-300">{children}</em>,
                  table: ({children}) => <table className="w-full border-collapse border border-slate-300 dark:border-slate-700 my-4">{children}</table>,
                  th: ({children}) => <th className="border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-left font-semibold">{children}</th>,
                  td: ({children}) => <td className="border border-slate-300 dark:border-slate-700 px-3 py-2">{children}</td>,
                  hr: () => <hr className="my-6 border-slate-200 dark:border-slate-700" />,
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