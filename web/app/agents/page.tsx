'use client';

import { useState } from 'react';
import { AgentList } from '@/components/agents/AgentList';
import { AgentDetailCard } from '@/components/agents/AgentDetailCard';
import { AgentChatInterface } from '@/components/agents/AgentChatInterface';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { AGENTS_CONFIG, getActiveAgents, getComingSoonAgents } from '@/config/agents.config';
import { AgentInfo } from '@/types/agents';
import { ThemeToggle } from '@/components/theme-toggle';

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [showDetailCard, setShowDetailCard] = useState(false);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  
  const activeAgents = getActiveAgents();
  const comingSoonAgents = getComingSoonAgents();

  const handleAgentClick = (agent: AgentInfo) => {
    if (agent.status === 'active') {
      setSelectedAgent(agent);
      setShowDetailCard(true);
    }
  };

  const handleStartChat = (agentId: string) => {
    setShowDetailCard(false);
    setActiveChat(agentId);
    const agent = AGENTS_CONFIG[agentId];
    if (agent) {
      setSelectedAgent(agent);
    }
  };

  const handleBackToList = () => {
    setActiveChat(null);
    setSelectedAgent(null);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background border-b flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {activeChat ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleBackToList}
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back to Agents
                </Button>
              ) : (
                <Link href="/">
                  <Button variant="ghost" size="sm" className="gap-2">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Health Assistant
                  </Button>
                </Link>
              )}
              <div>
                <h1 className="text-2xl font-bold">
                  {activeChat && selectedAgent 
                    ? `${selectedAgent.name} - ${selectedAgent.description}`
                    : 'Clinical AI Agents'
                  }
                </h1>
                <p className="text-sm text-muted-foreground">
                  {activeChat 
                    ? selectedAgent?.mission
                    : 'Select an AI agent to assist with clinical queries'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 text-xs font-semibold bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded">
                ALPHA
              </span>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Disclaimer Banner */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-900/50 px-4 py-3">
        <div className="container mx-auto flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800 dark:text-yellow-300">
            <strong>Important:</strong> This is a prerelease prototype for interested parties - Not ready for production use. 
            Information provided is for educational purposes only and should not replace professional medical advice. 
            Always consult qualified healthcare providers for clinical decisions.
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 flex-1">
        {activeChat && selectedAgent ? (
          // Show chat interface
          <AgentChatInterface 
            agent={selectedAgent}
            onClose={handleBackToList}
          />
        ) : (
          // Show agent list
          <div className="space-y-8">
            {/* Active Agents Section */}
            <div>
              <h2 className="text-xl font-semibold mb-4">Available Agents</h2>
              <AgentList 
                agents={activeAgents}
                onAgentClick={handleAgentClick}
              />
            </div>

            {/* Coming Soon Section */}
            {comingSoonAgents.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold mb-4 text-muted-foreground">Coming Soon</h2>
                <AgentList 
                  agents={comingSoonAgents}
                  onAgentClick={handleAgentClick}
                  disabled
                />
              </div>
            )}
          </div>
        )}
      </main>

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