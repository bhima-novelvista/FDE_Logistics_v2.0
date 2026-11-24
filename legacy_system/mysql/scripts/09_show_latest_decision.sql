-- =====================================================================
-- 09_show_latest_decision.sql
-- v2.0: shows the newest audited decision IN FULL, including the JSON
-- answer the caller received (Detail_JSON).
--
-- Runs as the admin (root), because the rule service itself may not read
-- the audit trail. Read-only: nothing is changed.
--
-- Run (from the project folder, Windows or macOS):
--   docker exec fde-mysql sh /scripts/run_sql.sh /scripts/09_show_latest_decision.sql
-- =====================================================================

SET NAMES utf8mb4;   -- show the audit text (for example °C) correctly

SELECT Log_ID,
       Logged_At_UTC,
       Request_ID,
       Caller,
       Caller_Role,
       Auth_Method,
       Endpoint,
       Reading_ID,
       Rules_Version,
       Outcome,
       Fired_Rules,
       JSON_PRETTY(Detail_JSON) AS Detail
FROM fde_audit.RuleDecisionLog
WHERE Outcome IN ('ACTION_REQUIRED', 'REVIEW', 'NO_ACTION')
ORDER BY Log_ID DESC
LIMIT 1\G
