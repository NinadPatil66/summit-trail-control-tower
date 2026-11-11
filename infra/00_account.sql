-- 00_account.sql: account-level guardrails. Safe to rerun.
USE ROLE ACCOUNTADMIN;

-- One credit budget for the whole trial. FREQUENCY = NEVER means it never resets.
CREATE RESOURCE MONITOR IF NOT EXISTS rm_account WITH
  CREDIT_QUOTA = 120
  FREQUENCY = NEVER
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 50 PERCENT DO NOTIFY
           ON 80 PERCENT DO NOTIFY
           ON 95 PERCENT DO SUSPEND
           ON 100 PERCENT DO SUSPEND_IMMEDIATE;

-- If the monitor already existed, force the quota back to what this file says.
ALTER RESOURCE MONITOR rm_account SET CREDIT_QUOTA = 120;

-- Attach the budget to the whole account.
ALTER ACCOUNT SET RESOURCE_MONITOR = rm_account;

-- Pipelines think in UTC. You convert to DC local time in dbt.
ALTER ACCOUNT SET TIMEZONE = 'UTC';

-- No single query may run longer than 1 hour.
ALTER ACCOUNT SET STATEMENT_TIMEOUT_IN_SECONDS = 3600;

-- Quick checks
SHOW RESOURCE MONITORS;
SHOW PARAMETERS LIKE 'TIMEZONE' IN ACCOUNT;