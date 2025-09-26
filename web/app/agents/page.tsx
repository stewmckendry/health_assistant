'use client';

import { useState } from 'react';
import { AgentDetailCard } from '@/components/agents/AgentDetailCard';
import { getActiveAgents, getComingSoonAgents } from '@/config/agents.config';
import { AgentInfo } from '@/types/agents';

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [showDetailCard, setShowDetailCard] = useState(false);
  
  const activeAgents = getActiveAgents();
  const comingSoonAgents = getComingSoonAgents();

  const handleAgentSelect = (agent: AgentInfo) => {
    if (agent.status === 'active') {
      setSelectedAgent(agent);
      setShowDetailCard(true);
    }
  };

  const handleStartChat = (agentId: string) => {
    // Navigate to the agent-specific chat page
    window.location.href = `/agents/${agentId}`;
  };

  // Agent selection grid
  return (
    <div className="min-h-screen bg-white">
      {/* Header with gradient background */}
      <div className="bg-gradient-to-br from-cyan-50 via-blue-50 to-green-50">
        <div className="text-center py-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Clinical AI Agents</h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Ontario healthcare AI assistants powered by trusted medical knowledge bases
          </p>
        </div>
      </div>

      {/* Displaying count - on white background */}
      <div className="max-w-6xl mx-auto px-6 mt-8 mb-4">
        <p className="text-sm text-gray-600">
          Showing <strong>{activeAgents.length}</strong> available agents
          {comingSoonAgents.length > 0 && ` and ${comingSoonAgents.length} coming soon`}
        </p>
      </div>

      {/* Agent Grid - on white background */}
      <div className="max-w-6xl mx-auto px-6 pb-16">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {activeAgents.map(agent => (
            <button
              key={agent.id}
              onClick={() => handleAgentSelect(agent)}
              className="bg-white rounded-lg p-6 shadow hover:shadow-lg transition-all duration-200 text-left border border-gray-100 hover:border-blue-200"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">{agent.icon}</div>
                  <div>
                    <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider mb-1">
                      <span>CLINICAL</span>
                      <span className="text-gray-400">|</span>
                      <span className="text-green-600">ACTIVE</span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {agent.name}
                    </h3>
                  </div>
                </div>
              </div>
              
              <p className="text-sm text-gray-600 leading-relaxed">
                {agent.mission}
              </p>
            </button>
          ))}

          {/* Coming Soon Agents */}
          {comingSoonAgents.map(agent => (
            <div
              key={agent.id}
              className="bg-gray-50 rounded-lg p-6 shadow-sm border border-gray-100 opacity-60"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-3xl grayscale">{agent.icon}</div>
                  <div>
                    <div className="flex items-center gap-2 text-xs text-gray-400 uppercase tracking-wider mb-1">
                      <span>CLINICAL</span>
                      <span className="text-gray-400">|</span>
                      <span>COMING SOON</span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-700">
                      {agent.name}
                    </h3>
                  </div>
                </div>
              </div>
              
              <p className="text-sm text-gray-500 leading-relaxed">
                {agent.mission}
              </p>

              <div className="mt-4 text-xs text-gray-400 font-medium">
                Coming Soon
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Detail Modal */}
      {showDetailCard && selectedAgent && (
        <AgentDetailCard
          agent={selectedAgent}
          open={showDetailCard}
          onClose={() => setShowDetailCard(false)}
          onStartChat={handleStartChat}
        />
      )}
    </div>
  );
}