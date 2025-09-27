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
    <div className="min-h-screen bg-gradient-to-br from-cyan-50 via-blue-50 to-green-50">
      {/* Fixed Header */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          {/* Main Header */}
          <div className="flex items-center justify-between h-14">
            <Link
              href="/agents"
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Back to Agents</span>
              <span className="sm:hidden">Back</span>
            </Link>
            
            <div className="flex-1 mx-4 text-center">
              <h1 className="text-lg font-bold text-gray-900 truncate">
                {agent.name}
              </h1>
              <p className="text-xs text-gray-500 hidden sm:block truncate">
                {agent.id === 'dr-off' 
                  ? 'Ontario Finance & Formulary Assistant - OHIP, ODB, ADP Coverage'
                  : agent.tagline}
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium px-2 py-1 bg-blue-100 text-blue-700 rounded uppercase">
                ALPHA
              </span>
            </div>
          </div>
          
          {/* Disclaimer Bar */}
          <div className="bg-amber-50 border-t border-amber-100 px-3 py-2">
            <p className="text-xs text-amber-800 text-center">
              <span className="font-semibold">⚠️ Educational Use Only</span>
              <span className="hidden sm:inline"> - Not for diagnosis or treatment. Consult healthcare providers for medical decisions.</span>
              <span className="sm:hidden"> - Not for medical advice</span>
            </p>
          </div>
        </div>
      </div>

      {/* Spacer for fixed header */}
      <div className="h-24"></div>

      {/* Chat Interface */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <AgentChatInterface 
          agent={agent}
          onClose={handleClose}
        />
      </div>
    </div>
  );
}