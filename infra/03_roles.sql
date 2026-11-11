-- 03_roles.sql: who can do what. Safe to rerun (grants are no-ops the second time).

----------------------------------------------------------------
-- 1. Job roles (account roles)
----------------------------------------------------------------
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS loader;
CREATE ROLE IF NOT EXISTS transformer;
CREATE ROLE IF NOT EXISTS analyst;
CREATE ROLE IF NOT EXISTS procurement;
CREATE ROLE IF NOT EXISTS finance;
CREATE ROLE IF NOT EXISTS app_role;
CREATE ROLE IF NOT EXISTS dc_manager_ont;
CREATE ROLE IF NOT EXISTS dc_manager_rno;
CREATE ROLE IF NOT EXISTS dc_manager_dal;
CREATE ROLE IF NOT EXISTS dc_manager_atl;
CREATE ROLE IF NOT EXISTS dc_manager_cmh;
CREATE ROLE IF NOT EXISTS dc_manager_abe;

-- Every custom role rolls up to SYSADMIN, so SYSADMIN can manage what they create.
GRANT ROLE loader TO ROLE sysadmin;
GRANT ROLE transformer TO ROLE sysadmin;
GRANT ROLE analyst TO ROLE sysadmin;
GRANT ROLE procurement TO ROLE sysadmin;
GRANT ROLE finance TO ROLE sysadmin;
GRANT ROLE app_role TO ROLE sysadmin;
GRANT ROLE dc_manager_ont TO ROLE sysadmin;
GRANT ROLE dc_manager_rno TO ROLE sysadmin;
GRANT ROLE dc_manager_dal TO ROLE sysadmin;
GRANT ROLE dc_manager_atl TO ROLE sysadmin;
GRANT ROLE dc_manager_cmh TO ROLE sysadmin;
GRANT ROLE dc_manager_abe TO ROLE sysadmin;

----------------------------------------------------------------
-- 2. Access roles (database roles). The database owner creates them.
----------------------------------------------------------------
USE ROLE SYSADMIN;

CREATE DATABASE ROLE IF NOT EXISTS raw.read_only;
CREATE DATABASE ROLE IF NOT EXISTS raw.read_write;
CREATE DATABASE ROLE IF NOT EXISTS erp_sim.read_only;
CREATE DATABASE ROLE IF NOT EXISTS erp_sim.read_write;
CREATE DATABASE ROLE IF NOT EXISTS analytics.read_only;
CREATE DATABASE ROLE IF NOT EXISTS ops_app.read_only;
CREATE DATABASE ROLE IF NOT EXISTS ops_app.read_write;

-- A writer can also read.
GRANT DATABASE ROLE raw.read_only TO DATABASE ROLE raw.read_write;
GRANT DATABASE ROLE erp_sim.read_only TO DATABASE ROLE erp_sim.read_write;
GRANT DATABASE ROLE ops_app.read_only TO DATABASE ROLE ops_app.read_write;

----------------------------------------------------------------
-- 3. Put permissions into the access roles.
-- Future grants need MANAGE GRANTS, which SECURITYADMIN has.
----------------------------------------------------------------
USE ROLE SECURITYADMIN;

-- RAW: read
GRANT USAGE ON DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT USAGE ON ALL SCHEMAS IN DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT SELECT ON ALL TABLES IN DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT SELECT ON FUTURE TABLES IN DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT SELECT ON ALL VIEWS IN DATABASE raw TO DATABASE ROLE raw.read_only;
GRANT SELECT ON FUTURE VIEWS IN DATABASE raw TO DATABASE ROLE raw.read_only;
-- RAW: write
GRANT INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN DATABASE raw TO DATABASE ROLE raw.read_write;
GRANT INSERT, UPDATE, DELETE, TRUNCATE ON FUTURE TABLES IN DATABASE raw TO DATABASE ROLE raw.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STAGE, CREATE FILE FORMAT, CREATE PIPE, CREATE STREAM, CREATE TASK
  ON ALL SCHEMAS IN DATABASE raw TO DATABASE ROLE raw.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STAGE, CREATE FILE FORMAT, CREATE PIPE, CREATE STREAM, CREATE TASK
  ON FUTURE SCHEMAS IN DATABASE raw TO DATABASE ROLE raw.read_write;

-- ERP_SIM: same pattern
GRANT USAGE ON DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT USAGE ON ALL SCHEMAS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT SELECT ON ALL TABLES IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT SELECT ON FUTURE TABLES IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT SELECT ON ALL VIEWS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT SELECT ON FUTURE VIEWS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_only;
GRANT INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_write;
GRANT INSERT, UPDATE, DELETE, TRUNCATE ON FUTURE TABLES IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STAGE, CREATE FILE FORMAT, CREATE PROCEDURE, CREATE TASK
  ON ALL SCHEMAS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STAGE, CREATE FILE FORMAT, CREATE PROCEDURE, CREATE TASK
  ON FUTURE SCHEMAS IN DATABASE erp_sim TO DATABASE ROLE erp_sim.read_write;

-- ANALYTICS: read only. dbt (TRANSFORMER) owns what it builds.
GRANT USAGE ON DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT USAGE ON ALL SCHEMAS IN DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT SELECT ON ALL TABLES IN DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT SELECT ON FUTURE TABLES IN DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT SELECT ON ALL VIEWS IN DATABASE analytics TO DATABASE ROLE analytics.read_only;
GRANT SELECT ON FUTURE VIEWS IN DATABASE analytics TO DATABASE ROLE analytics.read_only;

-- OPS_APP: read and write for the app
GRANT USAGE ON DATABASE ops_app TO DATABASE ROLE ops_app.read_only;
GRANT USAGE ON ALL SCHEMAS IN DATABASE ops_app TO DATABASE ROLE ops_app.read_only;
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE ops_app TO DATABASE ROLE ops_app.read_only;
GRANT SELECT ON ALL TABLES IN DATABASE ops_app TO DATABASE ROLE ops_app.read_only;
GRANT SELECT ON FUTURE TABLES IN DATABASE ops_app TO DATABASE ROLE ops_app.read_only;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN DATABASE ops_app TO DATABASE ROLE ops_app.read_write;
GRANT INSERT, UPDATE, DELETE ON FUTURE TABLES IN DATABASE ops_app TO DATABASE ROLE ops_app.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STREAMLIT ON ALL SCHEMAS IN DATABASE ops_app TO DATABASE ROLE ops_app.read_write;
GRANT CREATE TABLE, CREATE VIEW, CREATE STREAMLIT ON FUTURE SCHEMAS IN DATABASE ops_app TO DATABASE ROLE ops_app.read_write;

----------------------------------------------------------------
-- 4. Give access roles to job roles
----------------------------------------------------------------
GRANT DATABASE ROLE raw.read_write TO ROLE loader;
GRANT DATABASE ROLE erp_sim.read_write TO ROLE loader;

GRANT DATABASE ROLE raw.read_only TO ROLE transformer;
GRANT DATABASE ROLE erp_sim.read_only TO ROLE transformer;
GRANT USAGE, CREATE SCHEMA ON DATABASE analytics TO ROLE transformer;

GRANT DATABASE ROLE analytics.read_only TO ROLE analyst;
GRANT DATABASE ROLE analytics.read_only TO ROLE procurement;
GRANT DATABASE ROLE analytics.read_only TO ROLE finance;
GRANT DATABASE ROLE analytics.read_only TO ROLE app_role;
GRANT DATABASE ROLE ops_app.read_write TO ROLE app_role;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_ont;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_rno;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_dal;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_atl;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_cmh;
GRANT DATABASE ROLE analytics.read_only TO ROLE dc_manager_abe;

----------------------------------------------------------------
-- 5. Warehouses (database roles can't hold these, so job roles get them directly)
----------------------------------------------------------------
GRANT USAGE ON WAREHOUSE load_wh TO ROLE loader;
GRANT USAGE ON WAREHOUSE transform_wh TO ROLE transformer;
GRANT USAGE ON WAREHOUSE ai_wh TO ROLE transformer;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE analyst;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE procurement;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE finance;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE app_role;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_ont;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_rno;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_dal;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_atl;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_cmh;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE dc_manager_abe;

----------------------------------------------------------------
-- 6. Users
----------------------------------------------------------------
-- dbt's own login: key pair only, no password.
CREATE USER IF NOT EXISTS dbt_svc
  TYPE = SERVICE
  DEFAULT_ROLE = transformer
  DEFAULT_WAREHOUSE = transform_wh
  COMMENT = 'dbt runs. Key-pair auth only';
ALTER USER dbt_svc SET RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxCsUrv2B5eCc3EzaOahxrVikwJjTu9xlP8uzRyCh/pzwBOO2BQb3ZtHjxfLCri5VOrDdsqcBk7miV5UeYur6WZEdyNmytYbY00ZBV0aGVKBBiDyja8k9LX33Cus3gh7sLNELc1ygN/XNBQFlhRI6oF7MJgT+5thttRQMBPUcq5l4ASHLtf+coSwO9H+p/eiPf4ba+qdAYG964tX9w61WWSf3kqdkOQxC10cOHJVCaCjIcLHaMSoMNQgP4tW2oPR4YjsyFuowSqNg2ec8+kzL/as6rM/QWxGw4CwUEsQuZWLWyGUnvUmNKWP82kUUR6SIfrEWjhZ8OzIMQYZ/6OI6+QIDAQAB';
GRANT ROLE transformer TO USER dbt_svc;

-- You: get every job role so you can test as each one.
SET me = CURRENT_USER();
GRANT ROLE loader TO USER IDENTIFIER($me);
GRANT ROLE transformer TO USER IDENTIFIER($me);
GRANT ROLE analyst TO USER IDENTIFIER($me);
GRANT ROLE procurement TO USER IDENTIFIER($me);
GRANT ROLE finance TO USER IDENTIFIER($me);
GRANT ROLE app_role TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_ont TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_rno TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_dal TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_atl TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_cmh TO USER IDENTIFIER($me);
GRANT ROLE dc_manager_abe TO USER IDENTIFIER($me);

SHOW GRANTS TO ROLE transformer;