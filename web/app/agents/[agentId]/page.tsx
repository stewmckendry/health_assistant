'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AgentChatInterface } from '@/components/agents/AgentChatInterface';
import { getAgentById, isAgentAvailable } from '@/config/agents.config';
import { AgentInfo } from '@/types/agents';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function AgentChatPage() {
  const params = useParams();
  const router = useRouter();
  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const agentId = params?.agentId as string;
    if (!agentId) {
      setError('No agent ID provided');
      return;
    }

    const foundAgent = getAgentById(agentId);
    if (!foundAgent) {
      setError(`Agent "${agentId}" not found`);
      return;
    }

    if (!isAgentAvailable(agentId)) {
      setError(`Agent "${foundAgent.name}" is not currently available`);
      return;
    }

    setAgent(foundAgent);
  }, [params?.agentId]);

  const handleClose = () => {
    router.push('/agents');
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-cyan-50 via-blue-50 to-green-50">
        <div className="max-w-4xl mx-auto p-8">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Error</h1>
            <p className="text-gray-700 mb-6">{error}</p>
            <Link
              href="/agents"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Agents
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-cyan-50 via-blue-50 to-green-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading agent...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-cyan-50/20">
      {/* Enhanced Fixed Header */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md border-b border-gray-200 shadow-lg">
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-cyan-500/5"></div>
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
            {/* Main Header with gradient accent */}
            <div className="flex items-center justify-between h-16">
              <Link
                href="/agents"
                className="inline-flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all group"
              >
                <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" />
                <span className="font-medium">Back to Agents</span>
              </Link>
              
              <div className="flex-1 mx-6 text-center">
                <div className="flex items-center justify-center gap-3">
                  <div className="p-2 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-xl">
                    <span className="text-2xl block">{agent.icon}</span>
                  </div>
                  <div>
                    <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                      {agent.name}
                    </h1>
                    <p className="text-xs text-gray-500">
                      {agent.tagline || agent.description}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-bold rounded-full shadow-md uppercase tracking-wider">
                  ALPHA
                </span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Enhanced Disclaimer Bar */}
        <div className="bg-gradient-to-r from-amber-500 to-orange-500">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            <div className="px-4 py-2.5">
              <p className="text-white text-center font-medium text-sm">
                ⚠️ Educational & Experimental Use Only
                <span className="hidden sm:inline opacity-90"> • Not for diagnosis, treatment, or clinical decisions</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Spacer for fixed header */}
      <div className="h-28"></div>

      {/* Chat Interface Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <AgentChatInterface 
          agent={agent}
          onClose={handleClose}
        />
      </div>
    </div>
  );
}