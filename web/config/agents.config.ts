/**
 * Configuration for Clinical AI Agents
 */

import { AgentInfo } from '@/types/agents';

export const AGENTS_CONFIG: Record<string, AgentInfo> = {
  'dr-opa': {
    id: 'dr-opa',
    name: 'Dr. OPA',
    description: 'Ontario Practice Advice - Regulatory and clinical guidance',
    fullDescription: 'AI assistant providing Ontario-specific primary care and practice guidance from trusted healthcare authorities.',
    mission: 'To provide accurate, current practice guidance from Ontario healthcare authorities including CPSO policies, Ontario Health programs, PHO infection control, and CEP clinical tools.',
    status: 'active',
    icon: '🩺',
    color: '#2563eb', // blue-600
    endpoint: '/api/agents/dr-opa',
    tools: [
      {
        name: 'opa_policy_check',
        description: 'Search CPSO regulatory policies and expectations',
        category: 'search'
      },
      {
        name: 'opa_program_lookup', 
        description: 'Access Ontario Health clinical programs via web search',
        category: 'retrieval'
      },
      {
        name: 'opa_ipac_guidance',
        description: 'Retrieve PHO infection prevention and control guidance',
        category: 'retrieval'
      },
      {
        name: 'opa_search_sections',
        description: 'Hybrid vector and keyword search across all sources',
        category: 'search'
      },
      {
        name: 'opa_get_section',
        description: 'Fetch full section text with citations',
        category: 'retrieval'
      },
      {
        name: 'opa_freshness_probe',
        description: 'Check for guideline updates',
        category: 'validation'
      }
    ],
    knowledgeSources: [
      {
        name: 'CPSO Policies',
        organization: 'College of Physicians and Surgeons of Ontario',
        type: 'regulatory',
        url: 'https://www.cpso.on.ca',
        documentCount: 366
      },
      {
        name: 'Ontario Health Programs',
        organization: 'Ontario Health',
        type: 'clinical',
        url: 'https://www.ontariohealth.ca',
        lastUpdated: '2025-01'
      },
      {
        name: 'PHO IPAC Guidelines',
        organization: 'Public Health Ontario',
        type: 'clinical',
        url: 'https://www.publichealthontario.ca',
        documentCount: 132
      },
      {
        name: 'CEP Clinical Tools',
        organization: 'Centre for Effective Practice',
        type: 'clinical',
        url: 'https://cep.health',
        documentCount: 57
      }
    ],
    capabilities: [
      'Regulatory compliance guidance',
      'Ontario health program eligibility',
      'Infection control protocols',
      'Clinical decision support',
      'Policy interpretation',
      'Practice standards advice'
    ],
    limitations: [
      'Ontario-specific guidance only',
      'Not for emergency medical advice',
      'Requires verification with official sources',
      'Does not replace professional judgment'
    ],
    disclaimer: 'This tool provides Ontario practice guidance based on official sources. Always verify critical information with the original source documents and use clinical judgment.'
  },
  
  'agent-97': {
    id: 'agent-97',
    name: 'Agent 97',
    description: 'Explains medical terms in plain language using trusted sources',
    fullDescription: 'AI-powered medical education assistant that helps you understand health information by explaining medical terms and concepts in plain, accessible language.',
    mission: 'To help patients and the public understand medical information by translating complex medical terms into plain language, providing educational context from 97 trusted medical sources with proper citations.',
    status: 'active',
    icon: '🎯',
    color: '#10b981', // green-500
    endpoint: '/api/agents/agent-97',
    tools: [
      {
        name: 'agent_97_query',
        description: 'Process medical education queries with guardrails',
        category: 'analysis'
      },
      {
        name: 'agent_97_get_trusted_domains',
        description: 'Retrieve list of 97 trusted medical sources',
        category: 'retrieval'
      },
      {
        name: 'agent_97_health_check',
        description: 'Verify system component status',
        category: 'validation'
      },
      {
        name: 'agent_97_get_disclaimers',
        description: 'Get medical disclaimers and emergency resources',
        category: 'retrieval'
      },
      {
        name: 'agent_97_query_stream',
        description: 'Stream responses in real-time',
        category: 'analysis'
      }
    ],
    knowledgeSources: [
      {
        name: 'Canadian Healthcare',
        organization: 'Multiple Canadian Authorities',
        type: 'educational',
        documentCount: 24
      },
      {
        name: 'US Medical Centers',
        organization: 'Mayo, Johns Hopkins, Cleveland Clinic',
        type: 'educational',
        documentCount: 18
      },
      {
        name: 'Medical Journals',
        organization: 'NEJM, Lancet, JAMA, BMJ',
        type: 'research',
        documentCount: 15
      },
      {
        name: 'Global Health Organizations',
        organization: 'WHO, CDC, NIH',
        type: 'educational',
        documentCount: 12
      },
      {
        name: 'Disease Organizations',
        organization: 'Various specialized foundations',
        type: 'educational',
        documentCount: 28
      }
    ],
    capabilities: [
      'General health education',
      'Medication information',
      'Symptom education (not diagnosis)',
      'Preventive care guidance',
      'Emergency detection and redirection',
      'Mental health resources',
      'Evidence-based information'
    ],
    limitations: [
      'No medical diagnosis',
      'No treatment prescriptions',
      'Educational purposes only',
      'Not for emergencies',
      'Requires professional consultation'
    ],
    disclaimer: 'This information is for educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider.'
  },
  
  'dr-off': {
    id: 'dr-off',
    name: 'Dr. OFF',
    description: 'Ontario Finance & Formulary guidance',
    fullDescription: 'AI assistant specialized in Ontario drug formulary, OHIP billing, and healthcare financing guidance for clinicians.',
    mission: 'To provide comprehensive guidance on Ontario drug coverage, OHIP billing codes, ADP eligibility, and healthcare financing for optimal patient care and practice management.',
    status: 'coming-soon',
    icon: '💊',
    color: '#8b5cf6', // violet-500
    endpoint: '/api/agents/dr-off',
    tools: [
      {
        name: 'odb_get',
        description: 'Ontario Drug Benefit formulary lookup',
        category: 'search'
      },
      {
        name: 'schedule_get',
        description: 'OHIP Schedule of Benefits lookup',
        category: 'search'
      },
      {
        name: 'adp_get',
        description: 'Assistive Devices Program eligibility check',
        category: 'retrieval'
      },
      {
        name: 'coverage_answer',
        description: 'Clinical coverage questions orchestrator',
        category: 'analysis'
      }
    ],
    knowledgeSources: [
      {
        name: 'ODB Formulary',
        organization: 'Ontario Ministry of Health',
        type: 'regulatory',
        url: 'https://www.ontario.ca/page/check-medication-coverage/',
        lastUpdated: '2025-01'
      },
      {
        name: 'OHIP Schedule of Benefits',
        organization: 'Ontario Ministry of Health',
        type: 'regulatory',
        url: 'https://www.ontario.ca/page/ohip-schedule-benefits-and-fees'
      },
      {
        name: 'ADP Guidelines',
        organization: 'Assistive Devices Program',
        type: 'regulatory',
        url: 'https://www.ontario.ca/page/assistive-devices-program'
      }
    ],
    capabilities: [
      'Drug coverage verification',
      'Limited Use criteria',
      'OHIP billing code lookup',
      'Fee schedule guidance',
      'ADP eligibility assessment',
      'Prior authorization help',
      'Generic alternatives'
    ],
    limitations: [
      'Ontario coverage only',
      'Subject to policy changes',
      'Requires eligibility verification',
      'Not for private insurance'
    ],
    disclaimer: 'Coverage information is subject to change. Always verify current coverage criteria and patient eligibility with official sources before prescribing or billing.',
    launchDate: '2025-02'
  }
};

/**
 * Get all active agents
 */
export const getActiveAgents = (): AgentInfo[] => {
  return Object.values(AGENTS_CONFIG).filter(agent => agent.status === 'active');
};

/**
 * Get coming soon agents
 */
export const getComingSoonAgents = (): AgentInfo[] => {
  return Object.values(AGENTS_CONFIG).filter(agent => agent.status === 'coming-soon');
};

/**
 * Get agent by ID
 */
export const getAgentById = (agentId: string): AgentInfo | undefined => {
  return AGENTS_CONFIG[agentId];
};

/**
 * Check if agent is available
 */
export const isAgentAvailable = (agentId: string): boolean => {
  const agent = AGENTS_CONFIG[agentId];
  return agent && agent.status === 'active';
};