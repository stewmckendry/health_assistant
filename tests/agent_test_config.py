"""
Agent Test Configuration

Centralized configuration for agent testing including:
- Agent configurations (import paths, creation functions)
- Default test queries for each agent
- MCP tool configurations
- API endpoint configurations
"""

# ============================================================================
# AGENT CONFIGURATIONS
# ============================================================================

AGENT_CONFIGS = {
    "dr_opa": {
        "name": "Dr. OPA",
        "description": "Ontario Practice Advisor - Policy, clinical tools, quality standards",
        "import_path": "src.ai_agents.dr_opa_agent.openai_agent_http",
        "create_function": "create_dr_opa_agent"
    },
    "dr_off": {
        "name": "Dr. OFF",
        "description": "Ontario Financial & Formulary - OHIP, ODB, ADP",
        "import_path": "src.ai_agents.dr_off_agent.openai_agent_http",
        "create_function": "create_dr_off_agent"
    },
    "agent_97": {
        "name": "Agent 97",
        "description": "Clinical evidence search - 97 trusted medical sources for clinicians",
        "import_path": "src.ai_agents.agent_97.openai_agent",
        "create_function": "create_agent_97"
    },
    "chief": {
        "name": "Chief",
        "description": "Diagnostic orchestrator",
        "import_path": "src.ai_agents.diagnostic_orchestrator.create_orchestrator_http",
        "create_function": "create_orchestrator_http"
    }
}


# ============================================================================
# DEFAULT TEST QUERIES
# ============================================================================

DEFAULT_TEST_QUERIES = {
    "dr_opa": [
        {
            "query": "What are the CPSO requirements for virtual care consent and documentation?",
            "expected_tools": ["opa_policy_check"]
        },
        {
            "query": "What CEP clinical decision tools are available for hypertension management?",
            "expected_tools": ["opa_clinical_tools"]
        },
        {
            "query": "What are the Ontario Health quality standards for diabetes care?",
            "expected_tools": ["opa_quality_standards"]
        },
        {
            "query": "What Choosing Wisely recommendations exist for avoiding unnecessary imaging in low back pain?",
            "expected_tools": ["opa_choosing_wisely"]
        },
        {
            "query": "What are the infection prevention and control requirements for sterilization in dental offices?",
            "expected_tools": ["opa_ipac_guidance"]
        },
        {
            "query": "What is the CPSO policy on how long physicians have to complete third-party medical forms?",
            "expected_tools": ["opa_policy_check"]
        }
    ],

    "dr_off": [
        {
            "query": "What are the OHIP billing codes and fees for house calls?",
            "expected_tools": ["schedule_get"]
        },
        {
            "query": "Is atorvastatin covered by ODB? What about generic alternatives?",
            "expected_tools": ["odb_get"]
        },
        {
            "query": "What ADP funding is available for power wheelchairs?",
            "expected_tools": ["adp_get"]
        },
        {
            "query": "What OHIP codes should I use for a comprehensive geriatric assessment in long-term care?",
            "expected_tools": ["schedule_get"]
        },
        {
            "query": "What are the Limited Use criteria for biologic medications for rheumatoid arthritis?",
            "expected_tools": ["odb_get"]
        },
        {
            "query": "What is the OHIP billing code for a complete physical examination?",
            "expected_tools": ["schedule_get"]
        }
    ],

    "agent_97": [
        {
            "query": "What are the current evidence-based guidelines for managing hypertension in adults?",
            "expected_tools": ["clinician_search"]
        },
        {
            "query": "Latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?",
            "expected_tools": ["clinician_search"]
        },
        {
            "query": "Recommended diagnostic workup for suspected pulmonary embolism in low-risk patients?",
            "expected_tools": ["clinician_search"]
        },
        {
            "query": "What are the latest guidelines for managing atrial fibrillation?",
            "expected_tools": ["clinician_search"]
        },
        {
            "query": "Evidence for GLP-1 agonists in cardiovascular risk reduction?",
            "expected_tools": ["clinician_search"]
        }
    ],

    "chief": [
        {
            "query": "55 year old male with chest pain, what's the differential diagnosis?",
            "expected_tools": None
        },
        {
            "query": "What tests should I order for suspected hypothyroidism?",
            "expected_tools": None
        }
    ]
}


# ============================================================================
# MCP TOOL CONFIGURATIONS
# ============================================================================

MCP_TOOL_CONFIGS = {
    "dr_opa": {
        "opa_policy_check": {
            "import_path": "src.ai_agents.dr_opa_agent.dr_opa_mcp.server",
            "function_name": "policy_check",
            "test_requests": [
                {
                    "query": "virtual care consent requirements",
                    "k": 5,
                    "filters": {"policy_type": "cpso"}
                },
                {
                    "query": "prescribing controlled substances",
                    "k": 5,
                    "filters": {"policy_type": "cpso"}
                }
            ]
        },
        "opa_clinical_tools": {
            "import_path": "src.ai_agents.dr_opa_agent.dr_opa_mcp.server",
            "function_name": "clinical_tools",
            "test_requests": [
                {
                    "query": "hypertension management",
                    "k": 5,
                    "filters": {}
                },
                {
                    "query": "diabetes screening",
                    "k": 5,
                    "filters": {}
                }
            ]
        },
        "opa_quality_standards": {
            "import_path": "src.ai_agents.dr_opa_agent.dr_opa_mcp.server",
            "function_name": "quality_standards",
            "test_requests": [
                {
                    "query": "diabetes care standards",
                    "k": 5,
                    "filters": {}
                }
            ]
        },
        "opa_choosing_wisely": {
            "import_path": "src.ai_agents.dr_opa_agent.dr_opa_mcp.server",
            "function_name": "choosing_wisely",
            "test_requests": [
                {
                    "query": "unnecessary imaging low back pain",
                    "k": 5,
                    "filters": {}
                }
            ]
        }
    },

    "dr_off": {
        "schedule_get": {
            "import_path": "src.ai_agents.dr_off_agent.mcp.tools.schedule",
            "function_name": "schedule_get",
            "test_requests": [
                {
                    "query": "house call",
                    "k": 5,
                    "filters": {}
                },
                {
                    "query": "comprehensive assessment geriatric",
                    "k": 5,
                    "filters": {"specialty": "family_practice"}
                },
                {
                    "query": "complete physical examination",
                    "k": 5,
                    "filters": {}
                },
                # Medical condition + service type tests (query processor extraction)
                {
                    "query": "diabetes follow-up",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test - should find K046, K045, Q040"
                },
                {
                    "query": "asthma management",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test"
                },
                {
                    "query": "hypertension assessment",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test"
                },
                {
                    "query": "COPD consultation",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test"
                },
                {
                    "query": "prenatal care",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test - should find P005, A920"
                },
                {
                    "query": "palliative care visit",
                    "k": 5,
                    "filters": {},
                    "description": "Medical condition extraction test"
                }
            ]
        },
        "odb_get": {
            "import_path": "src.ai_agents.dr_off_agent.mcp.tools.odb",
            "function_name": "odb_get",
            "test_requests": [
                {
                    "query": "atorvastatin",
                    "k": 5,
                    "filters": {}
                },
                {
                    "query": "metformin",
                    "k": 5,
                    "filters": {}
                },
                {
                    "query": "biologic rheumatoid arthritis",
                    "k": 5,
                    "filters": {"check": ["lu_criteria"]}
                },
                # Enhanced query processor test cases
                {
                    "query": "GLP-1 agonist",
                    "k": 5,
                    "filters": {},
                    "description": "Clinical term expansion test"
                },
                {
                    "query": "Is Ozempic covered?",
                    "k": 5,
                    "filters": {},
                    "description": "Yes/no coverage question"
                },
                {
                    "query": "alternatives to Lipitor",
                    "k": 5,
                    "filters": {},
                    "description": "Therapeutic alternatives"
                },
                {
                    "query": "blood pressure medications",
                    "k": 5,
                    "filters": {},
                    "description": "Drug class search"
                },
                {
                    "query": "semaglutide limited use criteria",
                    "k": 5,
                    "filters": {},
                    "description": "LU criteria extraction"
                }
            ]
        },
        "adp_get": {
            "import_path": "src.ai_agents.dr_off_agent.mcp.tools.adp",
            "function_name": "adp_get",
            "test_requests": [
                # Category 1: Basic Device Queries
                {
                    "query": "What funding is available for power wheelchair?",
                    "k": 5,
                    "filters": {},
                    "description": "Basic power wheelchair funding query"
                },
                {
                    "query": "Is a walker covered by ADP?",
                    "k": 5,
                    "filters": {},
                    "description": "Walker coverage yes/no"
                },
                {
                    "query": "CPAP machine funding",
                    "k": 5,
                    "filters": {},
                    "description": "Respiratory device funding"
                },

                # Category 2: CEP Eligibility (CRITICAL)
                {
                    "query": "My patient needs power wheelchair, income is $19,000. Does she qualify for CEP?",
                    "k": 5,
                    "filters": {},
                    "description": "CEP eligibility - low income (CRITICAL TEST)"
                },
                {
                    "query": "Patient income $35,000, needs walker. CEP eligible?",
                    "k": 5,
                    "filters": {},
                    "description": "CEP eligibility - above threshold"
                },
                {
                    "query": "Family income $32,000, scooter for spouse. CEP?",
                    "k": 5,
                    "filters": {},
                    "description": "CEP family income threshold"
                },

                # Category 3: Exclusions (CRITICAL)
                {
                    "query": "Does ADP cover wheelchair batteries?",
                    "k": 5,
                    "filters": {},
                    "description": "Batteries exclusion (CRITICAL TEST)"
                },
                {
                    "query": "Scooter needs repair, is this covered by ADP?",
                    "k": 5,
                    "filters": {},
                    "description": "Repairs exclusion"
                },
                {
                    "query": "Does ADP cover walker accessories like bags?",
                    "k": 5,
                    "filters": {},
                    "description": "Accessories exclusion"
                },

                # Category 4: Clinical Terminology (Synonym Mapping)
                {
                    "query": "Patient needs ambulation aid for home use",
                    "k": 5,
                    "filters": {},
                    "description": "Clinical synonym: ambulation aid → walker"
                },
                {
                    "query": "gait aid funding",
                    "k": 5,
                    "filters": {},
                    "description": "Clinical synonym: gait aid → walker"
                },
                {
                    "query": "speech generating device for ALS patient",
                    "k": 5,
                    "filters": {},
                    "description": "Clinical synonym: speech generating device"
                },
                {
                    "query": "continuous positive airway pressure machine coverage",
                    "k": 5,
                    "filters": {},
                    "description": "Clinical synonym: CPAP full name"
                },

                # Category 5: Complex Scenarios
                {
                    "query": "Patient with MS, income $21,000, needs power wheelchair for daily outdoor use. Eligible? What's the cost?",
                    "k": 5,
                    "filters": {},
                    "description": "Complex multi-part question"
                },
                {
                    "query": "Scooter or power wheelchair - which does ADP prefer?",
                    "k": 5,
                    "filters": {},
                    "description": "Device comparison"
                },
                {
                    "query": "Patient already has wheelchair, needs replacement cushion. Covered?",
                    "k": 5,
                    "filters": {},
                    "description": "Replacement vs initial coverage"
                },

                # Category 6: Edge Cases
                {
                    "query": "mobility device",
                    "k": 5,
                    "filters": {},
                    "description": "Vague query"
                },
                {
                    "query": "Does ADP cover Hoveround scooter?",
                    "k": 5,
                    "filters": {},
                    "description": "Brand name query"
                },
                {
                    "query": "Patient needs walker AND wheelchair",
                    "k": 5,
                    "filters": {},
                    "description": "Multiple devices"
                }
            ]
        }
    },

    "agent_97": {
        "clinician_search": {
            "import_path": "src.ai_agents.agent_97.mcp.clinician_search_server",
            "function_name": "clinician_search_handler",
            "test_requests": [
                {
                    "query": "What are the current evidence-based guidelines for managing hypertension in adults?",
                    "max_web_search_uses": 2,
                    "max_web_fetch_uses": 5,
                    "description": "Hypertension guidelines search"
                },
                {
                    "query": "Latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?",
                    "max_web_search_uses": 2,
                    "max_web_fetch_uses": 5,
                    "description": "SGLT2 inhibitor evidence"
                },
                {
                    "query": "Recommended diagnostic workup for suspected pulmonary embolism in low-risk patients?",
                    "max_web_search_uses": 2,
                    "max_web_fetch_uses": 5,
                    "description": "PE diagnostic workup"
                },
                {
                    "query": "Evidence for GLP-1 agonists in cardiovascular risk reduction?",
                    "max_web_search_uses": 2,
                    "max_web_fetch_uses": 5,
                    "description": "GLP-1 cardiovascular evidence"
                },
                {
                    "query": "Current atrial fibrillation management guidelines?",
                    "max_web_search_uses": 2,
                    "max_web_fetch_uses": 3,
                    "description": "AFib management - fewer fetches"
                }
            ]
        },
        "clinician_search_get_domains": {
            "import_path": "src.ai_agents.agent_97.mcp.clinician_search_server",
            "function_name": "clinician_search_get_domains_handler",
            "test_requests": [
                {
                    "include_categories": False,
                    "description": "Get domains without categories"
                },
                {
                    "include_categories": True,
                    "description": "Get domains with categories"
                }
            ]
        },
        "clinician_search_health_check": {
            "import_path": "src.ai_agents.agent_97.mcp.clinician_search_server",
            "function_name": "clinician_search_health_check_handler",
            "test_requests": [
                {
                    "description": "Basic health check"
                }
            ]
        }
    }
}


# ============================================================================
# API ENDPOINT CONFIGURATIONS
# ============================================================================

API_CONFIGS = {
    "dr_opa": {
        "url": "http://localhost:8001/api/dr-opa/query",
        "timeout": 60
    },
    "dr_off": {
        "url": "http://localhost:8001/api/dr-off/query",
        "timeout": 60
    },
    "agent_97": {
        "url": "http://localhost:8001/api/agent-97/query",
        "timeout": 60
    },
    "chief": {
        "url": "http://localhost:8001/api/chief/query",
        "timeout": 60
    }
}


# ============================================================================
# EVALUATION CRITERIA
# ============================================================================

EVALUATION_CRITERIA = {
    "dr_opa": {
        "min_confidence": 0.7,
        "min_citations": 1,
        "expected_response_length": 200,
        "required_fields": ["response", "tools_used", "citations", "confidence"]
    },
    "dr_off": {
        "min_confidence": 0.7,
        "min_citations": 1,
        "expected_response_length": 150,
        "required_fields": ["response", "tools_used", "citations", "confidence"]
    }
}


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

PERFORMANCE_BENCHMARKS = {
    "dr_opa": {
        "max_response_time_seconds": 10.0,
        "target_success_rate": 0.95
    },
    "dr_off": {
        "max_response_time_seconds": 8.0,
        "target_success_rate": 0.95
    },
    "agent_97": {
        "max_response_time_seconds": 15.0,
        "target_success_rate": 0.90
    },
    "chief": {
        "max_response_time_seconds": 20.0,
        "target_success_rate": 0.90
    }
}
