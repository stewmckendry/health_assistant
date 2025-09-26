'use client';

import { Message, Citation, ToolCall } from '@/types/agents';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  User, 
  Bot, 
  AlertCircle, 
  ExternalLink, 
  Loader2, 
  ChevronDown, 
  ChevronUp,
  Wrench,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';

interface AgentMessageProps {
  message: Message;
  agentName?: string;
  agentIcon?: string;
  isStreaming?: boolean;
}

// Inline citations component with better styling
function InlineCitations({ citations }: { citations: Citation[] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!citations || citations.length === 0) return null;

  const displayCitations = isExpanded ? citations : citations.slice(0, 3);

  return (
    <div className="mt-4 pt-4 border-t border-border/50">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
          <ExternalLink className="h-3 w-3" />
          Sources ({citations.length})
        </h4>
        {citations.length > 3 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
          >
            {isExpanded ? 'Show less' : `Show all ${citations.length}`}
            {isExpanded ? <ChevronUp className="h-3 w-3 ml-1" /> : <ChevronDown className="h-3 w-3 ml-1" />}
          </Button>
        )}
      </div>
      
      <div className="space-y-2">
        {displayCitations.map((citation, index) => (
          <a
            key={`citation-${index}-${citation.url}`}
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-2.5 rounded-lg border border-border hover:border-primary/50 bg-muted/30 hover:bg-muted/50 transition-all group"
          >
            <div className="flex items-start gap-2">
              <span className="text-xs font-mono text-muted-foreground min-w-[1.5rem]">
                [{index + 1}]
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-medium line-clamp-1 group-hover:text-primary transition-colors">
                    {citation.title || citation.source}
                  </p>
                  <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary flex-shrink-0 transition-colors" />
                </div>
                {citation.snippet && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    "{citation.snippet}"
                  </p>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">
                    {citation.domain || new URL(citation.url).hostname.replace('www.', '')}
                  </span>
                  {citation.isTrusted && (
                    <Badge className="bg-green-100 text-green-700 text-xs px-1.5 py-0 h-4">
                      Trusted
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// Inline tool calls component
function InlineToolCalls({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!toolCalls || toolCalls.length === 0) return null;

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'failed':
        return <XCircle className="h-3 w-3 text-red-500" />;
      case 'executing':
        return <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-3 w-3 text-gray-400" />;
    }
  };

  return (
    <div className="mt-4 pt-4 border-t border-border/50">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded(!isExpanded)}
        className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
      >
        <Wrench className="h-3 w-3 mr-1" />
        {toolCalls.length} tool{toolCalls.length !== 1 ? 's' : ''} used
        {isExpanded ? <ChevronUp className="h-3 w-3 ml-1" /> : <ChevronDown className="h-3 w-3 ml-1" />}
      </Button>
      
      {isExpanded && (
        <div className="mt-2 space-y-1">
          {toolCalls.map((tool) => (
            <div 
              key={tool.id} 
              className="flex items-center gap-2 text-xs text-muted-foreground pl-4"
            >
              {getStatusIcon(tool.status)}
              <span className="font-mono">{tool.name}</span>
              {tool.status === 'executing' && (
                <span className="text-blue-500">Running...</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function AgentMessage({ message, agentName, agentIcon, isStreaming }: AgentMessageProps) {
  const isUser = message.role === 'user';
  const isError = message.error;

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-lg">
            {isError ? (
              <AlertCircle className="h-5 w-5 text-destructive" />
            ) : isStreaming ? (
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
            ) : agentIcon ? (
              <span>{agentIcon}</span>
            ) : (
              <Bot className="h-5 w-5 text-primary" />
            )}
          </div>
        </div>
      )}

      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
            <User className="h-5 w-5" />
          </div>
        </div>
      )}

      <div className={cn('flex-1 max-w-2xl')}>
        <Card
          className={cn(
            'p-4 overflow-hidden',
            isUser
              ? 'bg-muted/50'
              : 'bg-background',
            isError && 'border-destructive'
          )}
        >
          {/* Agent name for assistant messages */}
          {!isUser && agentName && (
            <div className="text-xs font-medium text-muted-foreground mb-2">
              {agentName}
            </div>
          )}

          {/* Message content */}
          <div
            className={cn(
              'prose prose-sm max-w-none break-words overflow-wrap-anywhere',
              'dark:prose-invert'
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({children}) => <p className="mb-3 leading-relaxed">{children}</p>,
                  ul: ({children}) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                  li: ({children}) => <li className="leading-relaxed">{children}</li>,
                  h1: ({children}) => <h1 className="text-lg font-bold mb-3 mt-4 first:mt-0">{children}</h1>,
                  h2: ({children}) => <h2 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
                  h3: ({children}) => <h3 className="text-sm font-bold mb-2 mt-3 first:mt-0">{children}</h3>,
                  code: ({children, className}) => {
                    const isInline = !className;
                    return isInline 
                      ? <code className="px-1 py-0.5 bg-muted rounded text-xs font-mono">{children}</code>
                      : <pre className="bg-muted p-3 rounded-lg overflow-x-auto my-3"><code className="font-mono text-xs">{children}</code></pre>;
                  },
                  blockquote: ({children}) => 
                    <blockquote className="border-l-4 border-primary/30 pl-3 italic my-3 text-muted-foreground">{children}</blockquote>,
                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                  em: ({children}) => <em className="italic">{children}</em>,
                  hr: () => <hr className="my-4 border-border" />,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Error message */}
          {isError && (
            <div className="mt-3 p-2 bg-destructive/10 text-destructive rounded text-sm">
              {message.error}
            </div>
          )}

          {/* Tool calls for assistant messages */}
          {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
            <InlineToolCalls toolCalls={message.toolCalls} />
          )}

          {/* Citations for assistant messages */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <InlineCitations citations={message.citations} />
          )}

          {/* Timestamp */}
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
            {isStreaming && !isUser && (
              <span className="text-xs text-primary flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Responding...
              </span>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}