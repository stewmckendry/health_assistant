
# MCP Tool Functions for Health Insurance Act Data Access

def mcp_get_act_eligibility(section_ref: str = None, population: str = None) -> list:
    '''Get eligibility rules from Health Insurance Act.
    
    Args:
        section_ref: Specific section reference (e.g., "1.8(1)")
        population: Filter by population (student, worker, CF, RCMP, diplomat, spouse, dependant)
    
    Returns:
        List of eligibility rules with conditions and effects
    '''
    query = '''
        SELECT * FROM v_act_eligibility
        WHERE 1=1
    '''
    if section_ref:
        query += ' AND section_ref = ?'
    if population:
        query += ' AND population_type = ?'
    # Returns eligibility rules with parsed conditions

def mcp_check_physical_presence(days_in_ontario: int, period_months: int = 12) -> dict:
    '''Check if physical presence requirements are met.
    
    Args:
        days_in_ontario: Number of days physically present in Ontario
        period_months: Period to check (default 12 months)
    
    Returns:
        Dict with eligibility status and applicable rules
    '''
    # Check against 153 days in 12 months rule
    # Check exemptions (student, worker, CF, etc.)
    
def mcp_get_act_section(section_ref: str) -> dict:
    '''Get specific section from Health Insurance Act with all related rules.
    
    Args:
        section_ref: Section reference (e.g., "1.3", "1.8(1)")
    
    Returns:
        Section text from Chroma + all SQL rules for that section
    '''
    # Query Chroma for section text
    # Query SQL for structured rules
    # Combine results
    
def mcp_search_act_rules(query: str, rule_type: str = None) -> list:
    '''Search Act rules by keyword or type.
    
    Args:
        query: Search terms
        rule_type: Filter by type (eligibility, status_extension, dependant_carryover, health_card, uninsured)
    
    Returns:
        Matching rules from all Act tables
    '''
    sql = '''
        SELECT * FROM v_act_all_rules
        WHERE (title LIKE ? OR effect LIKE ?)
    '''
    if rule_type:
        sql += ' AND rule_type = ?'
    # Returns matching rules across all tables

def mcp_get_dependant_rules(anchor: str) -> list:
    '''Get rules for dependants of specific populations.
    
    Args:
        anchor: Anchor population (student, worker, CF, RCMP, diplomat)
    
    Returns:
        Rules for spouse/dependant carry-over
    '''
    query = '''
        SELECT * FROM act_dependant_carryover
        WHERE anchor_population = ?
    '''
    # Returns carry-over rules for dependants

def mcp_get_health_card_obligations() -> list:
    '''Get all health card obligations and rules.'''
    query = 'SELECT * FROM act_health_card_rule'
    # Returns health card requirements

def mcp_get_uninsured_services() -> list:
    '''Get references to uninsured services and exclusions.'''
    query = '''
        SELECT 
            ur.*,
            fs.description as schedule_description
        FROM act_uninsured_reference ur
        LEFT JOIN ohip_fee_schedule fs ON ur.schedule_pointer = fs.fee_code
    '''
    # Returns uninsured service references with Schedule links
