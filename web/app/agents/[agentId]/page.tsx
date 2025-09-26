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
      <div className="border-b bg-white/80 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/agents"
              className="text-gray-600 hover:text-gray-900 flex items-center gap-2 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Agents
            </Link>
            <div className="text-center flex-1 max-w-2xl mx-auto">
              <h1 className="text-xl font-semibold text-gray-900">
                {agent.name} - {agent.description}
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                {agent.mission}
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                ALPHA
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-yellow-50/80 border-b border-yellow-200 px-4 py-3">
        <div className="max-w-7xl mx-auto text-sm text-yellow-800">
          <strong>Important:</strong> This is a prerelease prototype for interested parties - Not ready for production use. 
          Information provided is for educational purposes only and should not replace professional medical advice. 
          Always consult qualified healthcare providers for clinical decisions.
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <AgentChatInterface 
          agent={agent}
          onClose={handleClose}
        />
      </div>
    </div>
  );
}