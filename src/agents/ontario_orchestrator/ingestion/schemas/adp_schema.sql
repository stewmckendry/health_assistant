-- ADP (Assistive Devices Program) Tables Migration
-- V1: Light SQL models for funding rules and exclusions
-- Everything else lives in embeddings

-- Client share & CEP leasing (minimal, scenario-driven)
CREATE TABLE IF NOT EXISTS adp_funding_rule (
  rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
  adp_doc TEXT NOT NULL,              -- 'comm_aids' | 'mobility' | 'core_manual'
  section_ref TEXT,                   -- e.g., '405.02' or 'Part 7: 705'
  scenario TEXT NOT NULL,             -- 'purchase' | 'lease' | 'repair' | 'accessories' (extend if needed)
  client_share_percent DECIMAL(5,2),  -- e.g., 25.00; NULL if N/A (e.g., lease)
  details TEXT,                       -- short narrative (CEP terms, exceptions)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(adp_doc, section_ref, scenario)
);

-- Canonical exclusions (fast-fail)
CREATE TABLE IF NOT EXISTS adp_exclusion (
  exclusion_id INTEGER PRIMARY KEY AUTOINCREMENT,
  adp_doc TEXT NOT NULL,              -- 'comm_aids' | 'mobility' | 'core_manual'
  section_ref TEXT,                   -- if we can capture it; else NULL
  phrase TEXT NOT NULL,               -- canonicalized exclusion wording
  applies_to TEXT,                    -- optional: 'mobility','communication_aids','power_wheelchair', etc.
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(adp_doc, phrase, section_ref)
);

-- Helpful indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_adp_funding_rule_doc ON adp_funding_rule(adp_doc, scenario);
CREATE INDEX IF NOT EXISTS idx_adp_exclusion_phrase ON adp_exclusion(phrase);
CREATE INDEX IF NOT EXISTS idx_adp_exclusion_doc ON adp_exclusion(adp_doc, applies_to);

-- Trigger to update updated_at timestamp on updates
CREATE TRIGGER IF NOT EXISTS update_adp_funding_rule_timestamp
AFTER UPDATE ON adp_funding_rule
BEGIN
  UPDATE adp_funding_rule SET updated_at = CURRENT_TIMESTAMP WHERE rule_id = NEW.rule_id;
END;

CREATE TRIGGER IF NOT EXISTS update_adp_exclusion_timestamp
AFTER UPDATE ON adp_exclusion
BEGIN
  UPDATE adp_exclusion SET updated_at = CURRENT_TIMESTAMP WHERE exclusion_id = NEW.exclusion_id;
END;