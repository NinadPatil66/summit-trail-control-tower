-- 02_databases.sql: storage layout. Safe to rerun.
USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS raw COMMENT = 'Landed data, as received from S3';
ALTER DATABASE raw SET DATA_RETENTION_TIME_IN_DAYS = 1;
CREATE SCHEMA IF NOT EXISTS raw.erp;
CREATE SCHEMA IF NOT EXISTS raw.wms;
CREATE SCHEMA IF NOT EXISTS raw.tms;
CREATE SCHEMA IF NOT EXISTS raw.docs;

CREATE DATABASE IF NOT EXISTS erp_sim COMMENT = 'In-Snowflake history generator';
ALTER DATABASE erp_sim SET DATA_RETENTION_TIME_IN_DAYS = 1;
CREATE SCHEMA IF NOT EXISTS erp_sim.sim;

CREATE DATABASE IF NOT EXISTS analytics COMMENT = 'dbt output. dbt creates its own schemas';

CREATE DATABASE IF NOT EXISTS governance COMMENT = 'Tags and policies';
CREATE SCHEMA IF NOT EXISTS governance.tags;
CREATE SCHEMA IF NOT EXISTS governance.policies;

CREATE DATABASE IF NOT EXISTS ops_app COMMENT = 'Streamlit app and alerts';
CREATE SCHEMA IF NOT EXISTS ops_app.app;

SHOW DATABASES;