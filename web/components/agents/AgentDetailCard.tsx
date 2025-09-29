'use client';

import { useState } from 'react';
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
  Calendar,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface AgentDetailCardProps {
  agent: AgentInfo;
  open: boolean;
  onClose: () => void;
  onStartChat: (agentId: string) => void;
}

export function AgentDetailCard({ agent, open, onClose, onStartChat }: AgentDetailCardProps) {
  const [expandedSections, setExpandedSections] = useState<{
    capabilities: boolean;
    tools: boolean;
    sources: boolean;
  }>({
    capabilities: false,
    tools: false,
    sources: false,
  });

  const toggleSection = (section: 'capabilities' | 'tools' | 'sources') => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col bg-white border-0 shadow-2xl">
        <DialogHeader className="relative border-b pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-xl shadow-md">
                <span className="text-3xl block" role="img" aria-label={agent.name}>
                  {agent.icon}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-[10px] font-bold rounded-full uppercase tracking-wider">CLINICAL</span>
                  <span className="px-2 py-0.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-[10px] font-bold rounded-full">ACTIVE</span>
                </div>
                <DialogTitle className="text-2xl font-bold text-gray-900">
                  {agent.name}
                </DialogTitle>
                <p className="text-gray-600 mt-1 text-sm">
                  {agent.description}
                </p>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {/* Mission Statement - Compact */}
          <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg p-4 mb-4 shadow">
            <h3 className="font-semibold text-white text-sm mb-1 flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Mission
            </h3>
            <p className="text-white/95 text-sm leading-relaxed">
              {agent.mission}
            </p>
          </div>

          {/* Compact Tabs */}
          <Tabs defaultValue="capabilities" className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-gray-100 p-0.5 rounded-lg h-9 text-xs">
              <TabsTrigger value="capabilities" className="text-xs">Capabilities</TabsTrigger>
              <TabsTrigger value="tools" className="text-xs">Tools</TabsTrigger>
              <TabsTrigger value="sources" className="text-xs">Sources</TabsTrigger>
              <TabsTrigger value="limitations" className="text-xs">Important</TabsTrigger>
            </TabsList>

            <TabsContent value="capabilities" className="mt-3">
              <div className="space-y-2">
                <p className="text-gray-600 font-medium text-sm mb-3">
                  What {agent.name} can help with:
                </p>
                {expandedSections.capabilities ? (
                  <ScrollArea className="h-[350px] pr-2">
                    <div className="space-y-2">
                      {agent.capabilities.map((capability, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-2 rounded hover:bg-green-50 transition-colors">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-sm text-gray-700">{capability}</span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  agent.capabilities.slice(0, 6).map((capability, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-2 rounded hover:bg-green-50 transition-colors">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{capability}</span>
                    </div>
                  ))
                )}
                {agent.capabilities.length > 6 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('capabilities')}
                    className="w-full justify-center text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                  >
                    {expandedSections.capabilities ? (
                      <>Show less <ChevronUp className="ml-1 h-3 w-3" /></>
                    ) : (
                      <>Show all {agent.capabilities.length} capabilities <ChevronDown className="ml-1 h-3 w-3" /></>
                    )}
                  </Button>
                )}
              </div>
            </TabsContent>

            <TabsContent value="tools" className="mt-3">
              <div className="space-y-2">
                <p className="text-gray-600 font-medium text-sm mb-3">
                  Available MCP Tools ({agent.tools.length})
                </p>
                {(expandedSections.tools ? agent.tools : agent.tools.slice(0, 5)).map((tool, idx) => (
                  <div key={idx} className="bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Wrench className="h-3.5 w-3.5 text-purple-600" />
                        <span className="font-mono text-sm font-semibold text-gray-900">{tool.name}</span>
                      </div>
                      <Badge className="bg-purple-500 text-white border-0 text-[10px] px-2 py-0.5">
                        {tool.category}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600 ml-5">
                      {tool.description}
                    </p>
                  </div>
                ))}
                {agent.tools.length > 5 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('tools')}
                    className="w-full justify-center text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                  >
                    {expandedSections.tools ? (
                      <>Show less <ChevronUp className="ml-1 h-3 w-3" /></>
                    ) : (
                      <>Show all {agent.tools.length} tools <ChevronDown className="ml-1 h-3 w-3" /></>
                    )}
                  </Button>
                )}
              </div>
            </TabsContent>

            <TabsContent value="sources" className="mt-3">
              <div className="space-y-2">
                <p className="text-gray-600 font-medium text-sm mb-3">
                  Knowledge Sources ({agent.knowledgeSources.length})
                </p>
                {(expandedSections.sources ? agent.knowledgeSources : agent.knowledgeSources.slice(0, 4)).map((source, idx) => (
                  <div key={idx} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-3.5 w-3.5 text-blue-600" />
                        <div>
                          <span className="font-semibold text-sm text-gray-900">{source.name}</span>
                          <p className="text-xs text-gray-600">{source.organization}</p>
                        </div>
                      </div>
                      <Badge 
                        className={source.type === 'regulatory' 
                          ? 'bg-red-500 text-white border-0 text-[10px] px-2 py-0.5' 
                          : 'bg-blue-500 text-white border-0 text-[10px] px-2 py-0.5'
                        }
                      >
                        {source.type}
                      </Badge>
                    </div>
                    {source.documentCount && (
                      <p className="text-xs text-gray-500 mt-1 ml-5">
                        {source.documentCount} documents
                      </p>
                    )}
                  </div>
                ))}
                {agent.knowledgeSources.length > 4 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('sources')}
                    className="w-full justify-center text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                  >
                    {expandedSections.sources ? (
                      <>Show less <ChevronUp className="ml-1 h-3 w-3" /></>
                    ) : (
                      <>Show all {agent.knowledgeSources.length} sources <ChevronDown className="ml-1 h-3 w-3" /></>
                    )}
                  </Button>
                )}
              </div>
            </TabsContent>

            <TabsContent value="limitations" className="mt-3">
              <div className="space-y-2">
                <p className="text-gray-600 font-medium text-sm mb-3">
                  Important Limitations
                </p>
                {agent.limitations.slice(0, 5).map((limitation, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-2 rounded hover:bg-amber-50 transition-colors">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-600 mt-0.5" />
                    <span className="text-sm text-gray-700">{limitation}</span>
                  </div>
                ))}
                {agent.disclaimer && (
                  <div className="mt-3 p-3 bg-amber-100 border border-amber-300 rounded-lg">
                    <p className="text-xs text-amber-900">
                      <strong className="font-semibold">Note:</strong> {agent.disclaimer}
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 mt-auto border-t border-gray-200">
          <Button 
            onClick={() => onStartChat(agent.id)}
            className="flex-1 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold"
            size="default"
          >
            <MessageSquare className="h-4 w-4 mr-2" />
            Start Conversation
          </Button>
          <Button 
            onClick={onClose}
            variant="outline"
            size="default"
            className="hover:bg-gray-50 font-semibold"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}