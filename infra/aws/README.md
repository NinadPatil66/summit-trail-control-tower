# AWS setup (Step 6)

- Bucket: summit-trail-np-landing (region us-west-2), public access blocked
- Prefixes: erp/master, erp/m5, erp_unload, wms/events, tms/events, docs/invoices, docs/invoice_headers, docs/text
- IAM policy: summit-snowflake-s3-access (snowflake_s3_policy.json)
- IAM role: summit-snowflake-role, trust is a placeholder (external ID 0000) until Module 2
- Budget: summit-trail-monthly, $5
- labels/ is the answer key and is never uploaded