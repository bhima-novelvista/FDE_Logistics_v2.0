#!/bin/sh
# =====================================================================
# 06_create_rule_svc_login.sh - creates the database login of the v2.0
# rule service (least privilege).
#
# The login gets exactly two rights and nothing else:
#   1. SELECT on fde_views.vw_fleet_readings   (read the readable view)
#   2. INSERT on fde_audit.RuleDecisionLog      (add audit rows)
# It cannot read the legacy table, cannot change any data, and cannot
# read, change or delete audit rows.
#
# Runs INSIDE the fde-mysql container. The user name and password come
# from .env (docker compose passes them in); they are never printed.
# Safe to re-run: it resets the password to the value in .env and
# re-applies exactly the two rights above (any extra right is removed).
#
# Run (from the project folder, Windows or macOS):
#   docker exec fde-mysql sh /scripts/06_create_rule_svc_login.sh
# =====================================================================
set -eu

: "${RULE_SVC_USER:?RULE_SVC_USER is not set in the container - run update_env, then restart MySQL with docker compose (Step 3, Parts B and C)}"
if [ -z "${RULE_SVC_PASSWORD:-}" ]; then
  echo "RULE_SVC_PASSWORD is not set in the container - run update_env, then restart MySQL with docker compose (Step 3, Parts B and C)" >&2
  exit 1
fi

sh /scripts/run_sql.sh <<SQL
CREATE USER IF NOT EXISTS '${RULE_SVC_USER}'@'%' IDENTIFIED BY '${RULE_SVC_PASSWORD}';
ALTER USER '${RULE_SVC_USER}'@'%' IDENTIFIED BY '${RULE_SVC_PASSWORD}';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '${RULE_SVC_USER}'@'%';
GRANT SELECT ON fde_views.vw_fleet_readings TO '${RULE_SVC_USER}'@'%';
GRANT INSERT ON fde_audit.RuleDecisionLog   TO '${RULE_SVC_USER}'@'%';
SELECT '${RULE_SVC_USER} can now log in (read the view, add audit rows - nothing else)' AS status;
SHOW GRANTS FOR '${RULE_SVC_USER}'@'%';
SQL
