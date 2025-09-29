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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-cyan-50/20">
      {/* Enhanced Header with vibrant gradient background */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-500">
        {/* Animated gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-tr from-blue-600/20 via-transparent to-cyan-400/20 animate-pulse"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(59,130,246,0.2),transparent_50%)] animate-pulse"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,rgba(6,182,212,0.2),transparent_50%)] animate-pulse delay-150"></div>
        
        <div className="relative text-center py-10 text-white">
          <h1 className="text-4xl md:text-5xl font-bold mb-3">
            <span className="text-white">Ontario Healthcare</span>
            <span className="block mt-2 bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent">AI Registry</span>
          </h1>
          <p className="text-lg text-white/90 max-w-2xl mx-auto font-light">
            Specialized AI agents for OHIP billing, drug coverage, practice guidelines, and medical education
          </p>
        </div>
      </div>

      {/* Enhanced Disclaimer Banner */}
      <div className="bg-gradient-to-r from-amber-500 to-orange-500">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-center gap-4">
            <div className="flex-shrink-0">
              <div className="p-2 bg-white/20 backdrop-blur-sm rounded-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
            <p className="text-white font-medium">
              <span className="font-bold">Educational & Experimental Use Only</span>
              <span className="mx-3 opacity-60">•</span>
              <span className="opacity-90">Not for clinical decision-making. Always consult healthcare providers and verify with official sources.</span>
            </p>
          </div>
        </div>
      </div>

      {/* Enhanced Section Header */}
      <div className="max-w-7xl mx-auto px-6 mt-12 mb-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Choose Your <span className="bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">AI Assistant</span>
          </h2>
          <p className="text-gray-600">
            Select an agent specialized in Ontario healthcare to start your conversation
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <span className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-full text-sm font-semibold shadow-lg shadow-green-500/30">
            <span className="text-lg">✓</span>
            {activeAgents.length} Active
          </span>
          {comingSoonAgents.length > 0 && (
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-gray-400 to-gray-500 text-white rounded-full text-sm font-semibold shadow-lg shadow-gray-500/20">
              <span className="text-lg">⏳</span>
              {comingSoonAgents.length} Coming Soon
            </span>
          )}
        </div>
      </div>

      {/* Enhanced Agent Grid */}
      <div className="max-w-7xl mx-auto px-6 pb-20">
        <div className="grid gap-8 md:grid-cols-2">
          {activeAgents.map(agent => (
            <button
              key={agent.id}
              onClick={() => handleAgentSelect(agent)}
              className="agent-card-explicit group relative bg-white rounded-2xl shadow-lg hover:shadow-2xl transform hover:scale-[1.02] transition-all duration-300 text-left overflow-hidden"
              style={{
                background: 'white',
                borderRadius: '1rem',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
              }}
            >
              {/* Animated gradient background */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-cyan-600/5 to-purple-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl opacity-0 group-hover:opacity-100 blur transition duration-300"></div>
              
              {/* Card content with enhanced styling */}
              <div className="relative bg-white rounded-2xl p-8 border border-gray-100">
                {/* Enhanced top section with animated icon */}
                <div className="flex items-start gap-5 mb-5">
                  <div className="p-4 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-2xl group-hover:from-blue-200 group-hover:to-cyan-200 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3">
                    <span className="text-4xl block">{agent.icon}</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-3 py-1 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-bold rounded-full shadow-md">ACTIVE</span>
                      {agent.id === 'orchestrator' && (
                        <span className="px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white text-xs font-bold rounded-full shadow-md">ORCHESTRATOR</span>
                      )}
                    </div>
                    <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent group-hover:from-blue-600 group-hover:to-cyan-600 transition-all duration-300">
                      {agent.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1 font-medium">
                      {agent.tagline}
                    </p>
                  </div>
                </div>
                
                {/* Enhanced Mission with better typography */}
                <p className="text-gray-600 leading-relaxed mb-6 line-clamp-3">
                  {agent.mission}
                </p>
                
                {/* Enhanced bottom stats with badges */}
                <div className="flex items-center justify-between pt-6 border-t border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-sm font-semibold text-blue-900">{agent.knowledgeSources.length}</span>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 rounded-lg">
                      <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                      </svg>
                      <span className="text-sm font-semibold text-purple-900">{agent.tools.length}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-blue-600 font-semibold group-hover:text-cyan-600 transition-colors">
                    <span className="text-sm">Start chat</span>
                    <svg className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            </button>
          ))}

          {/* Enhanced Coming Soon Agents */}
          {comingSoonAgents.map(agent => (
            <div
              key={agent.id}
              className="relative bg-gradient-to-br from-gray-100/50 to-gray-200/30 rounded-2xl border-2 border-gray-300 border-dashed overflow-hidden"
            >
              {/* Enhanced overlay with pattern */}
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(0,0,0,0.03),transparent_50%)] pointer-events-none"></div>
              <div className="absolute inset-0 opacity-5" style={{
                backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.1) 10px, rgba(0,0,0,0.1) 20px)`
              }}></div>
              
              <div className="relative p-8 opacity-60">
                {/* Enhanced coming soon top section */}
                <div className="flex items-start gap-5 mb-5">
                  <div className="p-4 bg-gray-200 rounded-2xl">
                    <span className="text-4xl block grayscale opacity-50">{agent.icon}</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-3 py-1 bg-gray-300 text-gray-600 text-xs font-bold rounded-full">COMING SOON</span>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-600">
                      {agent.name}
                    </h3>
                    {agent.tagline && (
                      <p className="text-sm text-gray-400 mt-1 font-medium">
                        {agent.tagline}
                      </p>
                    )}
                  </div>
                </div>
                
                {/* Coming soon mission */}
                <p className="text-gray-500 leading-relaxed mb-6 line-clamp-3">
                  {agent.mission}
                </p>
                
                {/* Enhanced coming soon bottom section */}
                <div className="flex items-center justify-between pt-6 border-t border-gray-200">
                  <span className="text-sm font-medium text-gray-400">Under Development</span>
                  <button className="flex items-center gap-2 px-3 py-1.5 bg-gray-200 text-gray-600 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                    <span>Notify me</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Enhanced Footer Section */}
      <div className="mt-auto border-t border-gray-200 bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="text-center">
            <p className="text-white font-semibold mb-6 text-lg">
              Powered by Ontario healthcare knowledge bases and 97 trusted medical sources
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap text-sm">
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">OHIP</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">ODB</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">CPSO</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">Ontario Health</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">PHO</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">CEP</span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white/90 font-medium">MOH</span>
            </div>
            <div className="mt-6 text-white/60 text-sm">
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