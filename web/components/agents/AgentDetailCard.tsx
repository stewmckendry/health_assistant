'use client';

import { AgentInfo } from '@/types/agents';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <span className="text-5xl" role="img" aria-label={agent.name}>
                {agent.icon}
              </span>
              <div>
                <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider mb-1">
                  <span>CLINICAL</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-green-600">ACTIVE</span>
                </div>
                <DialogTitle className="text-2xl font-semibold text-gray-900">
                  {agent.name}
                </DialogTitle>
                <p className="text-sm text-gray-600 mt-1">
                  {agent.description}
                </p>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {/* Mission Statement */}
          <div className="bg-blue-50/50 rounded-lg p-4 mb-6 border border-blue-100">
            <h3 className="font-medium text-sm text-gray-900 mb-2">Mission</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              {agent.mission}
            </p>
          </div>

          {/* Detailed Information Tabs */}
          <Tabs defaultValue="capabilities" className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-gray-100">
              <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
              <TabsTrigger value="sources">Sources</TabsTrigger>
              <TabsTrigger value="limitations">Important</TabsTrigger>
            </TabsList>

            <TabsContent value="capabilities" className="mt-4">
              <ScrollArea className="h-[280px]">
                <div className="space-y-3 pr-4">
                  <p className="text-sm text-gray-500 mb-4">
                    What {agent.name} can help with:
                  </p>
                  {agent.capabilities.map((capability, idx) => (
                    <div key={idx} className="flex items-start gap-3">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{capability}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="tools" className="mt-4">
              <ScrollArea className="h-[280px]">
                <div className="space-y-3 pr-4">
                  <p className="text-sm text-gray-500 mb-4">
                    Available MCP Tools ({agent.tools.length})
                  </p>
                  {agent.tools.map((tool, idx) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Wrench className="h-4 w-4 text-gray-400" />
                          <span className="font-mono text-sm text-gray-900">{tool.name}</span>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {tool.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-600">
                        {tool.description}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="sources" className="mt-4">
              <ScrollArea className="h-[280px]">
                <div className="space-y-3 pr-4">
                  <p className="text-sm text-gray-500 mb-4">
                    Knowledge Sources ({agent.knowledgeSources.length})
                  </p>
                  {agent.knowledgeSources.map((source, idx) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-gray-400" />
                            <span className="font-medium text-sm text-gray-900">{source.name}</span>
                          </div>
                          <p className="text-xs text-gray-600 mt-1">
                            {source.organization}
                          </p>
                        </div>
                        <Badge 
                          variant={source.type === 'regulatory' ? 'default' : 'secondary'} 
                          className="text-xs"
                        >
                          {source.type}
                        </Badge>
                      </div>
                      {source.url && (
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                        >
                          Visit source
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        {source.documentCount && (
                          <span>{source.documentCount} documents</span>
                        )}
                        {source.lastUpdated && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Updated: {source.lastUpdated}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="limitations" className="mt-4">
              <ScrollArea className="h-[280px]">
                <div className="space-y-3 pr-4">
                  <p className="text-sm text-gray-500 mb-4">
                    Important Limitations & Disclaimers
                  </p>
                  {agent.limitations.map((limitation, idx) => (
                    <div key={idx} className="flex items-start gap-3">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{limitation}</span>
                    </div>
                  ))}
                  {agent.disclaimer && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-xs text-yellow-800">
                        <strong>Disclaimer:</strong> {agent.disclaimer}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        {/* Action Buttons - Fixed at bottom */}
        <div className="flex gap-3 pt-6 mt-auto border-t bg-white">
          <Button 
            onClick={() => onStartChat(agent.id)}
            className="flex-1 bg-blue-600 hover:bg-blue-700"
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
      </DialogContent>
    </Dialog>
  );
}