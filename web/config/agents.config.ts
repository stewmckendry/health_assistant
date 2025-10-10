/**
 * Configuration for Clinical AI Agents
 */

import { AgentInfo } from '@/types/agents';

export const AGENTS_CONFIG: Record<string, AgentInfo> = {
  'dr-opa': {
    id: 'dr-opa',
    name: 'Dr. OPA',
    tagline: 'Ontario Practice Advisor - CPSO Policies, Ontario Health Programs, Quality Standards',
    description: 'Ontario Practice Advice - Regulatory, clinical guidance, and quality standards',
    fullDescription: 'AI assistant providing Ontario-specific primary care and practice guidance from trusted healthcare authorities.',
    mission: 'Provides accurate practice guidance from CPSO policies, Ontario Health programs and quality standards, PHO infection control, CEP clinical tools, and Choosing Wisely recommendations for Ontario healthcare clinicians.',
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
      },
      {
        name: 'opa_clinical_tools',
        description: 'CEP clinical decision support tools',
        category: 'retrieval'
      },
      {
        name: 'opa_quality_standards',
        description: 'Ontario Health quality standards search',
        category: 'search'
      },
      {
        name: 'opa_choosing_wisely',
        description: 'Choosing Wisely recommendations',
        category: 'retrieval'
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
      },
      {
        name: 'Ontario Health Quality Standards',
        organization: 'Health Quality Ontario',
        type: 'clinical',
        url: 'https://www.hqontario.ca',
        documentCount: 40
      },
      {
        name: 'Choosing Wisely Canada',
        organization: 'Choosing Wisely Canada',
        type: 'clinical',
        url: 'https://choosingwiselycanada.org',
        documentCount: 400
      }
    ],
    capabilities: [
      'Regulatory compliance guidance',
      'Ontario health program eligibility',
      'Quality standards and statements',
      'Infection control protocols',
      'Clinical decision support',
      'Policy interpretation',
      'Practice standards advice',
      'Evidence-based care recommendations',
      'Choosing Wisely recommendations (unnecessary tests and procedures to avoid)'
    ],
    limitations: [
      'Ontario-specific guidance only',
      'Not for emergency medical advice',
      'Requires verification with official sources',
      'Does not replace professional judgment'
    ],
    disclaimer: 'This tool provides Ontario practice guidance based on official sources. Always verify critical information with the original source documents and use clinical judgment.',
    starterPrompts: [
      'What are the CPSO requirements for virtual care documentation?',
      'Is there an Ontario screening program for colorectal cancer?',
      'What unnecessary tests should I avoid ordering for lower back pain?',
      'What are the quality standards for diabetes in pregnancy?'
    ]
  },
  
  'agent-97': {
    id: 'agent-97',
    name: 'Agent 97',
    tagline: 'Clinical Evidence Search - 97 Trusted Medical Sources',
    description: 'Evidence-based clinical guidance from trusted medical literature',
    fullDescription: 'AI-powered clinical evidence search assistant that provides healthcare clinicians with evidence-based guidance from 97 trusted medical sources including journals, guidelines, and academic medical centers.',
    mission: 'Provides healthcare clinicians with evidence-based clinical guidance by searching 97 trusted medical sources including medical journals (NEJM, Lancet, JAMA), clinical guidelines, academic medical centers, and health authorities.',
    status: 'active',
    icon: '🎯',
    color: '#10b981', // green-500
    endpoint: '/api/agents/agent-97',
    tools: [
      {
        name: 'clinician_search',
        description: 'Search 97 trusted medical sources for clinical evidence',
        category: 'search'
      },
      {
        name: 'clinician_search_get_domains',
        description: 'Retrieve list of 97 trusted medical sources',
        category: 'retrieval'
      },
      {
        name: 'clinician_search_health_check',
        description: 'Verify system component status',
        category: 'validation'
      }
    ],
    knowledgeSources: [
      {
        name: 'Medical Journals',
        organization: 'NEJM, Lancet, JAMA, BMJ, Nature Medicine',
        type: 'research',
        documentCount: 15
      },
      {
        name: 'Clinical Guidelines',
        organization: 'NICE, AHA, ACC, ADA, Medical Societies',
        type: 'clinical',
        documentCount: 20
      },
      {
        name: 'Academic Medical Centers',
        organization: 'Mayo Clinic, Johns Hopkins, Cleveland Clinic, Harvard',
        type: 'clinical',
        documentCount: 24
      },
      {
        name: 'Health Authorities',
        organization: 'WHO, CDC, NIH, Health Canada',
        type: 'clinical',
        documentCount: 12
      },
      {
        name: 'Canadian Healthcare',
        organization: 'Ontario Health, CPSO, Canadian Medical Associations',
        type: 'clinical',
        documentCount: 26
      }
    ],
    capabilities: [
      'Evidence-based clinical guidance',
      'Latest medical research and guidelines',
      'Diagnostic approach recommendations',
      'Treatment protocol information',
      'Pharmacotherapy evidence',
      'Systematic review synthesis',
      'Clinical decision support',
      'Differential diagnosis considerations'
    ],
    limitations: [
      'Evidence-based guidance only',
      'Not for emergency medical decisions',
      'Requires clinical judgment',
      'Should verify with primary literature'
    ],
    disclaimer: 'Agent 97 provides evidence-based clinical guidance from trusted medical sources for healthcare professionals. Information is for educational purposes only and should be used in conjunction with clinical judgment.',
    starterPrompts: [
      'What are the current hypertension treatment guidelines?',
      'Latest evidence on SGLT2 inhibitors for heart failure?',
      'Recommended diagnostic workup for suspected PE?',
      'What are the latest guidelines for managing atrial fibrillation?'
    ]
  },
  
  'dr-off': {
    id: 'dr-off',
    name: 'Dr. OFF',
    tagline: 'Ontario Finance & Formulary Assistant - OHIP, ODB, ADP Coverage',
    description: 'Ontario Finance & Formulary guidance',
    fullDescription: 'AI assistant specialized in Ontario drug formulary, OHIP billing, and healthcare financing guidance for clinicians.',
    mission: 'To provide comprehensive guidance on Ontario drug coverage, OHIP billing codes, ADP eligibility, and healthcare financing for optimal patient care and practice management.',
    status: 'active',
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
    launchDate: '2025-02',
    starterPrompts: [
      'What OHIP codes can I bill for a diabetes follow-up?',
      'Is Ozempic covered by ODB for weight loss?',
      'Can my patient get ADP funding for a CPAP machine?',
      'What are the generic alternatives to Januvia?'
    ]
  },

  'orchestrator': {
    id: 'orchestrator',
    name: 'The Chief',
    tagline: 'Ontario Healthcare Coordinator - Unified Clinical & Administrative Guidance',
    description: 'Ontario Medical Coordinator - Connects you to the right Ontario healthcare guidance',
    fullDescription: 'Like a Chief Medical Officer directing cases to appropriate specialists, The Chief coordinates Ontario-specific medical guidance by intelligently routing queries to Dr. OPA (Ontario regulations), Dr. OFF (Ontario coverage), and Agent 97 (clinical evidence search) for complete clinical answers.',
    mission: 'To help Ontario clinicians get complete answers quickly by orchestrating Dr. OPA, Dr. OFF, and Agent 97 - connecting you to billing codes, drug coverage, practice policies, and evidence-based clinical guidelines all in one place.',
    status: 'active',
    icon: '🧠',
    color: '#f59e0b', // amber-500
    endpoint: '/api/agents/orchestrator',
    tools: [
      {
        name: 'dr_opa',
        description: 'Consult Dr. OPA for practice guidance and regulations',
        category: 'orchestration'
      },
      {
        name: 'dr_off',
        description: 'Consult Dr. OFF for financing and coverage',
        category: 'orchestration'
      },
      {
        name: 'agent_97',
        description: 'Consult Agent 97 for evidence-based clinical guidance',
        category: 'orchestration'
      }
    ],
    knowledgeSources: [
      {
        name: 'Dr. OPA Knowledge Base',
        organization: 'CPSO, Ontario Health, PHO, CEP',
        type: 'regulatory',
        description: 'Access to all Dr. OPA sources'
      },
      {
        name: 'Dr. OFF Knowledge Base',
        organization: 'Ontario Ministry of Health',
        type: 'financial',
        description: 'Access to all Dr. OFF sources'
      },
      {
        name: 'Agent 97 Knowledge Base',
        organization: '97 Trusted Medical Sources',
        type: 'clinical',
        description: 'Access to all Agent 97 sources'
      }
    ],
    capabilities: [
      'Unified Ontario healthcare guidance',
      'Combines OHIP billing with clinical best practices',
      'Links drug coverage to treatment guidelines',
      'Coordinates regulatory and financial advice',
      'Synthesizes multiple Ontario-specific sources',
      'Provides complete clinical-administrative answers',
      'Reduces time searching multiple databases',
      'Deduplicates overlapping information'
    ],
    limitations: [
      'Ontario-focused (OHIP, ODB, CPSO)',
      'Educational guidance only',
      'Not for emergency medical decisions',
      'Requires verification with official sources'
    ],
    disclaimer: 'The Chief coordinates Ontario healthcare guidance from Dr. OPA (regulations), Dr. OFF (coverage), and Agent 97 (clinical evidence). Information is for educational purposes only. Always verify with official Ontario sources and use clinical judgment.',
    launchDate: '2025-02',
    starterPrompts: [
      'Can I prescribe medical cannabis and how is it covered in Ontario?',
      'What are the billing codes and clinical guidelines for managing hypertension?',
      'How do I set up virtual care and what can I bill for it?',
      'What diabetes medications are covered and what are the prescribing guidelines?'
    ]
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