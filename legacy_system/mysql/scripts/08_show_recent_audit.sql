-- =====================================================================
-- 08_show_recent_audit.sql
-- v2.0: shows the 10 newest rows of the rule service's audit trail.
--
-- Runs as the admin (root), because the rule service itself is not
-- allowed to read audit rows (it can only add them). Read-only: nothing
-- is changed. The full decision (Detail_JSON) is left out to keep the
-- table readable; 09_show_latest_decision.sql shows one decision in full.
--
-- Run (from the project folder, Windows or macOS):
--   docker exec fde-mysql sh /scripts/run_sql.sh /scripts/08_show_recent_audit.sql
-- =====================================================================

SET NAMES utf8mb4;   -- show the audit text (for example °C) correctly

SELECT COUNT(*) AS audit_rows_in_total
FROM fde_audit.RuleDecisionLog;

SELECT Log_ID,
       Logged_At_UTC,
       Caller,
       Caller_Role,
       Auth_Method,
       Endpoint,
       Reading_ID,
       Outcome,
       Fired_Rules
FROM fde_audit.RuleDecisionLog
ORDER BY Log_ID DESC
LIMIT 10;
