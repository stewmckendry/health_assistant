'use client';

import { AgentInfo } from '@/types/agents';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  MessageSquare, 
  Wrench, 
  BookOpen, 
  AlertTriangle,
  CheckCircle,
  ExternalLink,
  Calendar
} from 'lucide-react';

interface AgentDetailCardProps {
  agent: AgentInfo;
  open: boolean;
  onClose: () => void;
  onStartChat: (agentId: string) => void;
}

export function AgentDetailCard({ agent, open, onClose, onStartChat }: AgentDetailCardProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span className="text-5xl" role="img" aria-label={agent.name}>
              {agent.icon}
            </span>
            <div>
              <DialogTitle className="text-2xl">{agent.name}</DialogTitle>
              <DialogDescription className="text-base mt-1">
                {agent.description}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="mt-6">
          {/* Mission Statement */}
          <div className="bg-muted/50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Mission
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {agent.mission}
            </p>
          </div>

          {/* Tabs for detailed information */}
          <Tabs defaultValue="capabilities" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
              <TabsTrigger value="sources">Sources</TabsTrigger>
              <TabsTrigger value="limitations">Limitations</TabsTrigger>
            </TabsList>

            <TabsContent value="capabilities" className="mt-4">
              <ScrollArea className="h-[250px] pr-4">
                <div className="space-y-3">
                  <h4 className="font-medium text-sm text-muted-foreground mb-3">
                    What {agent.name} can help with:
                  </h4>
                  {agent.capabilities.map((capability, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{capability}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="tools" className="mt-4">
              <ScrollArea className="h-[250px] pr-4">
                <div className="space-y-3">
                  <h4 className="font-medium text-sm text-muted-foreground mb-3">
                    Available MCP Tools ({agent.tools.length})
                  </h4>
                  {agent.tools.map((tool, idx) => (
                    <div key={idx} className="border rounded-lg p-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Wrench className="h-4 w-4 text-muted-foreground" />
                          <span className="font-mono text-sm">{tool.name}</span>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {tool.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {tool.description}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="sources" className="mt-4">
              <ScrollArea className="h-[250px] pr-4">
                <div className="space-y-3">
                  <h4 className="font-medium text-sm text-muted-foreground mb-3">
                    Knowledge Sources ({agent.knowledgeSources.length})
                  </h4>
                  {agent.knowledgeSources.map((source, idx) => (
                    <div key={idx} className="border rounded-lg p-3 space-y-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium text-sm">{source.name}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {source.organization}
                          </p>
                        </div>
                        <Badge variant={
                          source.type === 'regulatory' ? 'default' :
                          source.type === 'clinical' ? 'secondary' :
                          'outline'
                        } className="text-xs">
                          {source.type}
                        </Badge>
                      </div>
                      {source.url && (
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-1"
                        >
                          Visit source
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                      {source.documentCount && (
                        <p className="text-xs text-muted-foreground">
                          {source.documentCount} documents indexed
                        </p>
                      )}
                      {source.lastUpdated && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Last updated: {source.lastUpdated}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="limitations" className="mt-4">
              <ScrollArea className="h-[250px] pr-4">
                <div className="space-y-3">
                  <h4 className="font-medium text-sm text-muted-foreground mb-3">
                    Important Limitations
                  </h4>
                  {agent.limitations.map((limitation, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{limitation}</span>
                    </div>
                  ))}
                  {agent.disclaimer && (
                    <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900/50 rounded-lg">
                      <p className="text-xs text-yellow-800 dark:text-yellow-300">
                        <strong>Disclaimer:</strong> {agent.disclaimer}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>

          {/* Action Buttons */}
          <div className="flex gap-3 mt-6">
            <Button 
              onClick={() => onStartChat(agent.id)}
              className="flex-1"
              size="lg"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Start Conversation
            </Button>
            <Button 
              onClick={onClose}
              variant="outline"
              size="lg"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}