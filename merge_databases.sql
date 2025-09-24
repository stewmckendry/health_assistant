-- Attach the dr_off database
ATTACH DATABASE 'data/processed/dr_off/dr_off.db' AS dr_off;

-- Copy tables that don't exist in ohip.db
CREATE TABLE IF NOT EXISTS ohip_fee_schedule AS SELECT * FROM dr_off.ohip_fee_schedule;
CREATE TABLE IF NOT EXISTS odb_drugs AS SELECT * FROM dr_off.odb_drugs;
CREATE TABLE IF NOT EXISTS odb_interchangeable_groups AS SELECT * FROM dr_off.odb_interchangeable_groups;
CREATE TABLE IF NOT EXISTS ohip_diagnostic_codes AS SELECT * FROM dr_off.ohip_diagnostic_codes;
CREATE TABLE IF NOT EXISTS adp_device_rules AS SELECT * FROM dr_off.adp_device_rules;
CREATE TABLE IF NOT EXISTS adp_eligibility_criteria AS SELECT * FROM dr_off.adp_eligibility_criteria;
CREATE TABLE IF NOT EXISTS chunk_fee_codes AS SELECT * FROM dr_off.chunk_fee_codes;
CREATE TABLE IF NOT EXISTS document_chunks AS SELECT * FROM dr_off.document_chunks;
CREATE TABLE IF NOT EXISTS ingestion_log AS SELECT * FROM dr_off.ingestion_log;

-- Detach the database
DETACH DATABASE dr_off;
