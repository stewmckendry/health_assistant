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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col bg-white border-0 shadow-2xl">
        <DialogHeader className="relative border-b pb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-5">
              <div className="p-4 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-2xl shadow-lg">
                <span className="text-5xl block" role="img" aria-label={agent.name}>
                  {agent.icon}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="px-3 py-1 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-bold rounded-full shadow-md uppercase tracking-wider">CLINICAL</span>
                  <span className="px-3 py-1 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold rounded-full shadow-md">ACTIVE</span>
                </div>
                <DialogTitle className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                  {agent.name}
                </DialogTitle>
                <p className="text-gray-600 mt-2 font-medium">
                  {agent.description}
                </p>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {/* Enhanced Mission Statement */}
          <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl p-5 mb-6 shadow-lg">
            <h3 className="font-bold text-white mb-2 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Mission
            </h3>
            <p className="text-white/95 leading-relaxed">
              {agent.mission}
            </p>
          </div>

          {/* Enhanced Tabs */}
          <Tabs defaultValue="capabilities" className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-gradient-to-r from-gray-100 to-gray-200 p-1 rounded-xl shadow-inner">
              <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
              <TabsTrigger value="sources">Sources</TabsTrigger>
              <TabsTrigger value="limitations">Important</TabsTrigger>
            </TabsList>

            <TabsContent value="capabilities" className="mt-6">
              <ScrollArea className="h-[320px]">
                <div className="space-y-3 pr-4">
                  <p className="text-gray-600 font-medium mb-5">
                    What {agent.name} can help with:
                  </p>
                  {agent.capabilities.map((capability, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg hover:bg-green-50 transition-colors">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{capability}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="tools" className="mt-6">
              <ScrollArea className="h-[320px]">
                <div className="space-y-3 pr-4">
                  <p className="text-gray-600 font-medium mb-5">
                    Available MCP Tools ({agent.tools.length})
                  </p>
                  {agent.tools.map((tool, idx) => (
                    <div key={idx} className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-4 space-y-2 hover:shadow-md transition-shadow">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-purple-100 rounded-lg">
                            <Wrench className="h-4 w-4 text-purple-600" />
                          </div>
                          <span className="font-mono font-semibold text-gray-900">{tool.name}</span>
                        </div>
                        <Badge className="bg-gradient-to-r from-purple-500 to-pink-500 text-white border-0">
                          {tool.category}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 ml-11">
                        {tool.description}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="sources" className="mt-6">
              <ScrollArea className="h-[320px]">
                <div className="space-y-3 pr-4">
                  <p className="text-gray-600 font-medium mb-5">
                    Knowledge Sources ({agent.knowledgeSources.length})
                  </p>
                  {agent.knowledgeSources.map((source, idx) => (
                    <div key={idx} className="bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-4 space-y-3 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-100 rounded-lg">
                              <BookOpen className="h-4 w-4 text-blue-600" />
                            </div>
                            <span className="font-semibold text-gray-900">{source.name}</span>
                          </div>
                          <p className="text-sm text-gray-600 mt-2 ml-11">
                            {source.organization}
                          </p>
                        </div>
                        <Badge 
                          className={source.type === 'regulatory' 
                            ? 'bg-gradient-to-r from-red-500 to-orange-500 text-white border-0' 
                            : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white border-0'
                          }
                        >
                          {source.type}
                        </Badge>
                      </div>
                      {source.url && (
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 font-medium ml-11"
                        >
                          Visit source
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                      <div className="flex items-center gap-4 text-sm text-gray-500 ml-11">
                        {source.documentCount && (
                          <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            {source.documentCount} documents
                          </span>
                        )}
                        {source.lastUpdated && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            Updated: {source.lastUpdated}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="limitations" className="mt-6">
              <ScrollArea className="h-[320px]">
                <div className="space-y-3 pr-4">
                  <p className="text-gray-600 font-medium mb-5">
                    Important Limitations & Disclaimers
                  </p>
                  {agent.limitations.map((limitation, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg hover:bg-amber-50 transition-colors">
                      <div className="p-1.5 bg-amber-100 rounded-lg">
                        <AlertTriangle className="h-4 w-4 text-amber-600" />
                      </div>
                      <span className="text-gray-700">{limitation}</span>
                    </div>
                  ))}
                  {agent.disclaimer && (
                    <div className="mt-6 p-4 bg-gradient-to-r from-amber-100 to-orange-100 border border-amber-300 rounded-xl">
                      <p className="text-amber-900">
                        <strong className="font-bold">Disclaimer:</strong> {agent.disclaimer}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        {/* Enhanced Disclaimer Notice */}
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl p-4 mt-6 shadow-lg">
          <p className="text-white text-center font-medium">
            <span className="font-bold">⚠️ Educational & Experimental Use Only</span>
            <span className="mx-3 opacity-60">•</span>
            <span className="opacity-95">Not for clinical decisions or patient care</span>
          </p>
        </div>

        {/* Enhanced Action Buttons */}
        <div className="flex gap-4 pt-6 mt-auto border-t border-gray-200">
          <Button 
            onClick={() => onStartChat(agent.id)}
            className="flex-1 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all"
            size="lg"
          >
            <MessageSquare className="h-5 w-5 mr-2" />
            Start Conversation
          </Button>
          <Button 
            onClick={onClose}
            variant="outline"
            size="lg"
            className="border-2 hover:bg-gray-50 font-semibold"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}