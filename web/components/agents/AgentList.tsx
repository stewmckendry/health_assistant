'use client';

import { AgentInfo } from '@/types/agents';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronRight, Clock, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentListProps {
  agents: AgentInfo[];
  onAgentClick: (agent: AgentInfo) => void;
  disabled?: boolean;
}

export function AgentList({ agents, onAgentClick, disabled = false }: AgentListProps) {
  const getStatusBadge = (status: AgentInfo['status']) => {
    switch (status) {
      case 'active':
        return (
          <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
            <CheckCircle className="h-3 w-3 mr-1" />
            Active
          </Badge>
        );
      case 'coming-soon':
        return (
          <Badge variant="secondary">
            <Clock className="h-3 w-3 mr-1" />
            Coming Soon
          </Badge>
        );
      case 'beta':
        return (
          <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
            Beta
          </Badge>
        );
      case 'maintenance':
        return (
          <Badge variant="outline" className="text-yellow-600">
            Maintenance
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {agents.map((agent) => (
        <Card
          key={agent.id}
          className={cn(
            "relative transition-all duration-200 hover:shadow-lg cursor-pointer",
            disabled || agent.status === 'coming-soon' 
              ? "opacity-60 cursor-not-allowed" 
              : "hover:scale-[1.02]",
            "border-2"
          )}
          style={{
            borderColor: agent.status === 'active' ? `${agent.color}20` : undefined
          }}
          onClick={() => !disabled && agent.status === 'active' && onAgentClick(agent)}
        >
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-4xl" role="img" aria-label={agent.name}>
                  {agent.icon}
                </span>
                <div>
                  <CardTitle className="text-lg">{agent.name}</CardTitle>
                  {getStatusBadge(agent.status)}
                </div>
              </div>
              {agent.status === 'active' && !disabled && (
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <CardDescription className="mb-4">
              {agent.description}
            </CardDescription>
            
            {/* Key Capabilities Preview */}
            <div className="space-y-2 text-sm">
              <div className="font-medium text-muted-foreground">Key Features:</div>
              <ul className="space-y-1">
                {agent.capabilities.slice(0, 3).map((capability, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-muted-foreground">•</span>
                    <span className="text-muted-foreground">{capability}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Knowledge Sources Count */}
            <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
              <span>{agent.knowledgeSources.length} knowledge sources</span>
              <span>•</span>
              <span>{agent.tools.length} tools</span>
            </div>

            {/* Launch Date for Coming Soon */}
            {agent.status === 'coming-soon' && agent.launchDate && (
              <div className="mt-4 text-sm text-muted-foreground">
                Expected: {agent.launchDate}
              </div>
            )}

            {/* Action Button */}
            {agent.status === 'active' && !disabled && (
              <Button 
                className="w-full mt-4"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  onAgentClick(agent);
                }}
              >
                View Details & Start Chat
              </Button>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}