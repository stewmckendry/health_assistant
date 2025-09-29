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
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header with enhanced gradient */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-cyan-600 opacity-5"></div>
        <div className="absolute inset-0 bg-gradient-to-tr from-cyan-400 via-blue-400 to-indigo-400 opacity-[0.03]"></div>
        
        <div className="relative text-center py-10">
          {/* Compact Header */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-full shadow-sm border border-gray-200/50">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-gray-600 uppercase tracking-wider">Ontario Health Network</span>
            </div>
          </div>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            <span className="bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">Ontario Healthcare</span>
            <span className="text-gray-900"> AI Registry</span>
          </h1>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            Specialized AI agents for OHIP billing, drug coverage, practice guidelines, and medical education
          </p>
          
          {/* Compact Stats */}
          <div className="flex items-center justify-center gap-6 mt-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">4</span>
              <span className="text-gray-500">Active Agents</span>
            </div>
            <span className="text-gray-300">•</span>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">100+</span>
              <span className="text-gray-500">Knowledge Sources</span>
            </div>
            <span className="text-gray-300">•</span>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">Ontario</span>
              <span className="text-gray-500">Focused</span>
            </div>
          </div>
        </div>
      </div>

      {/* Refined Disclaimer Banner */}
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-200/50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-center gap-3">
            <div className="flex-shrink-0">
              <div className="p-1.5 bg-amber-100 rounded-lg">
                <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
            <p className="text-sm text-amber-900">
              <span className="font-semibold">Educational & Experimental Use Only</span>
              <span className="mx-2 text-amber-600">•</span>
              <span className="text-amber-800">Not for clinical decision-making. Always consult healthcare providers and verify with official sources.</span>
            </p>
          </div>
        </div>
      </div>

      {/* Section Header */}
      <div className="max-w-6xl mx-auto px-6 mt-8 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Available Agents</h2>
            <p className="text-sm text-gray-500 mt-1">
              Select an agent to start a conversation
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 bg-green-50 border border-green-200 rounded-full text-xs font-medium text-green-700">
              {activeAgents.length} Active
            </span>
            {comingSoonAgents.length > 0 && (
              <span className="px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-full text-xs font-medium text-gray-500">
                {comingSoonAgents.length} Coming Soon
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Agent Grid */}
      <div className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
          {activeAgents.map(agent => (
            <button
              key={agent.id}
              onClick={() => handleAgentSelect(agent)}
              className="group relative bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 text-left border border-gray-200 hover:border-transparent overflow-hidden"
            >
              {/* Gradient border on hover */}
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              
              {/* Card content */}
              <div className="relative bg-white m-[1px] rounded-xl p-6">
                {/* Top section with icon and name */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="p-3 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl group-hover:from-blue-50 group-hover:to-cyan-50 transition-colors duration-300">
                    <span className="text-3xl block">{agent.icon}</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">ACTIVE</span>
                      {agent.id === 'orchestrator' && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">ORCHESTRATOR</span>
                      )}
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                      {agent.name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {agent.tagline}
                    </p>
                  </div>
                </div>
                
                {/* Mission */}
                <p className="text-sm text-gray-600 leading-relaxed mb-4">
                  {agent.mission}
                </p>
                
                {/* Bottom stats or features */}
                <div className="flex items-center gap-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>{agent.knowledgeSources.length} sources</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                    </svg>
                    <span>{agent.tools.length} tools</span>
                  </div>
                  <div className="ml-auto">
                    <span className="text-blue-600 text-xs font-medium group-hover:underline">Start chat →</span>
                  </div>
                </div>
              </div>
            </button>
          ))}

          {/* Coming Soon Agents */}
          {comingSoonAgents.map(agent => (
            <div
              key={agent.id}
              className="relative bg-gray-50/50 rounded-xl border border-gray-200 border-dashed overflow-hidden"
            >
              {/* Coming Soon overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-gray-100/20 to-gray-200/20 pointer-events-none"></div>
              
              <div className="relative p-6 opacity-60">
                {/* Top section with icon and name */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="p-3 bg-gray-100 rounded-xl">
                    <span className="text-3xl block grayscale opacity-50">{agent.icon}</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-medium rounded">COMING SOON</span>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-600">
                      {agent.name}
                    </h3>
                    {agent.tagline && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {agent.tagline}
                      </p>
                    )}
                  </div>
                </div>
                
                {/* Mission */}
                <p className="text-sm text-gray-500 leading-relaxed mb-4">
                  {agent.mission}
                </p>
                
                {/* Bottom section */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                  <span className="text-xs text-gray-400">Under Development</span>
                  <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Notify me</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Section */}
      <div className="mt-auto border-t border-gray-200 bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-center">
            <p className="text-sm text-gray-600 font-medium mb-3">
              Powered by Ontario healthcare knowledge bases and 97 trusted medical sources
            </p>
            <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
              <span>OHIP</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>ODB</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>CPSO</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>Ontario Health</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>PHO</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>CEP</span>
              <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
              <span>MOH</span>
            </div>
            <div className="mt-4 text-xs text-gray-400">
              Plus Mayo Clinic, Johns Hopkins, WHO, CDC, and 90+ more trusted sources
            </div>
          </div>
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