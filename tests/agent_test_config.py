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
        "description": "General medical knowledge agent",
        "import_path": "src.ai_agents.agent_97.openai_agent",
        "create_function": "create_agent_97"
    },
    "chief": {
        "name": "Chief",
        "description": "Diagnostic orchestrator",
        "import_path": "src.ai_agents.diagnostic_orchestrator.orchestrator_agent_http",
        "create_function": "create_chief_agent"
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
            "query": "What are the diagnostic criteria for type 2 diabetes?",
            "expected_tools": None
        },
        {
            "query": "Explain the mechanism of action of ACE inhibitors",
            "expected_tools": None
        },
        {
            "query": "What are the common side effects of metformin?",
            "expected_tools": None
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
                {
                    "query": "power wheelchair",
                    "k": 5,
                    "filters": {
                        "device": {
                            "category": "mobility",
                            "type": "power wheelchair"
                        },
                        "check": ["eligibility", "funding", "cep"]
                    }
                },
                {
                    "query": "hearing aid",
                    "k": 5,
                    "filters": {
                        "device": {
                            "category": "hearing_devices",
                            "type": "hearing aid"
                        },
                        "check": ["eligibility", "funding"]
                    }
                },
                {
                    "query": "Does my patient qualify for ADP funding for a scooter? Income is $19,000",
                    "k": 5,
                    "filters": {}
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
