'use client';

import { ToolCall } from '@/types/agents';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Wrench, 
  Loader2, 
  CheckCircle, 
  XCircle, 
  Clock,
  ChevronDown,
  ChevronRight,
  Code,
  Play
} from 'lucide-react';
import { useState } from 'react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
  compact?: boolean;
}

export function ToolCallDisplay({ toolCalls, compact = false }: ToolCallDisplayProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  if (toolCalls.length === 0) return null;

  const toggleExpanded = (toolId: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolId)) {
      newExpanded.delete(toolId);
    } else {
      newExpanded.add(toolId);
    }
    setExpandedTools(newExpanded);
  };

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-3 w-3 text-gray-500" />;
      case 'executing':
        return <Loader2 className="h-3 w-3 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'failed':
        return <XCircle className="h-3 w-3 text-red-500" />;
    }
  };

  const getStatusColor = (status: ToolCall['status']) => {
    switch (status) {
      case 'pending':
        return 'gray';
      case 'executing':
        return 'blue';
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  const formatDuration = (start: string, end?: string) => {
    if (!end) return null;
    const duration = new Date(end).getTime() - new Date(start).getTime();
    return `${Math.round(duration / 10) / 100}s`;
  };

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1">
        {toolCalls.map((toolCall) => (
          <Badge 
            key={toolCall.id} 
            variant="outline" 
            className="text-xs flex items-center gap-1"
          >
            {getStatusIcon(toolCall.status)}
            {toolCall.name}
          </Badge>
        ))}
      </div>
    );
  }

  return (
    <Card className="bg-muted/30">
      <CardContent className="pt-3 pb-3">
        <div className="flex items-center gap-2 mb-3">
          <Wrench className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">MCP Tools</span>
          <Badge variant="secondary" className="text-xs">
            {toolCalls.length} {toolCalls.length === 1 ? 'call' : 'calls'}
          </Badge>
        </div>
        
        <div className="space-y-2">
          {toolCalls.map((toolCall, index) => {
            const isExpanded = expandedTools.has(toolCall.id);
            const duration = formatDuration(toolCall.startTime, toolCall.endTime);
            
            return (
              <Collapsible key={toolCall.id} open={isExpanded} onOpenChange={() => toggleExpanded(toolCall.id)}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="w-full justify-between p-2 h-auto">
                    <div className="flex items-center gap-2 text-left">
                      {getStatusIcon(toolCall.status)}
                      <span className="font-mono text-sm">{toolCall.name}</span>
                      <Badge 
                        variant="outline" 
                        className={`text-xs text-${getStatusColor(toolCall.status)}-700`}
                      >
                        {toolCall.status}
                      </Badge>
                      {duration && (
                        <span className="text-xs text-muted-foreground">
                          {duration}
                        </span>
                      )}
                    </div>
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                
                <CollapsibleContent className="px-2 pb-2">
                  <div className="border rounded-lg p-3 bg-background/50 space-y-2">
                    {/* Arguments */}
                    {Object.keys(toolCall.arguments).length > 0 && (
                      <div>
                        <div className="flex items-center gap-1 mb-2">
                          <Code className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs font-medium text-muted-foreground">Arguments</span>
                        </div>
                        <div className="bg-muted rounded p-2 font-mono text-xs overflow-x-auto">
                          <pre>{JSON.stringify(toolCall.arguments, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                    
                    {/* Result */}
                    {toolCall.result && (
                      <div>
                        <div className="flex items-center gap-1 mb-2">
                          <CheckCircle className="h-3 w-3 text-green-500" />
                          <span className="text-xs font-medium text-muted-foreground">Result</span>
                        </div>
                        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/50 rounded p-2 text-xs">
                          {typeof toolCall.result === 'string' ? (
                            <p>{toolCall.result}</p>
                          ) : (
                            <pre className="font-mono overflow-x-auto">
                              {JSON.stringify(toolCall.result, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Error */}
                    {toolCall.error && (
                      <div>
                        <div className="flex items-center gap-1 mb-2">
                          <XCircle className="h-3 w-3 text-red-500" />
                          <span className="text-xs font-medium text-muted-foreground">Error</span>
                        </div>
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded p-2 text-xs text-red-700 dark:text-red-400">
                          {toolCall.error}
                        </div>
                      </div>
                    )}
                    
                    {/* Timing */}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>Started: {new Date(toolCall.startTime).toLocaleTimeString()}</span>
                      {toolCall.endTime && (
                        <span>Completed: {new Date(toolCall.endTime).toLocaleTimeString()}</span>
                      )}
                      {duration && <span>Duration: {duration}</span>}
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}