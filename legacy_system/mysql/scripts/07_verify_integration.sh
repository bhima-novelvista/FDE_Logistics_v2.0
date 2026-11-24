#!/bin/sh
# =====================================================================
# 07_verify_integration.sh - self-test of the v2.0 data integration layer.
#
# Logs in AS THE RULE SERVICE (not as root) and proves three things:
#   A. it can do the two things it needs:
#        read the view, add an audit row
#   B. it is refused everything else:
#        legacy table, changing data, reading/changing/deleting audit
#        rows, creating tables
#   C. the view gives the same numbers as the legacy data for each SOP
#      rule (these are the counts the Step 4 rule engine must reproduce)
#
# Each check prints PASS or FAIL. The last line says how many passed.
# Check 5 adds one audit row marked SELF_TEST each time it runs (the
# service login cannot delete it, by design).
#
# Runs INSIDE the fde-mysql container; the password comes from .env via
# docker compose and is never printed.
# Run (from the project folder, Windows or macOS):
#   docker exec fde-mysql sh /scripts/07_verify_integration.sh
# =====================================================================
set -u

: "${RULE_SVC_USER:?RULE_SVC_USER is not set in the container - see Step 3, Parts B and C}"
if [ -z "${RULE_SVC_PASSWORD:-}" ]; then
  echo "RULE_SVC_PASSWORD is not set in the container - see Step 3, Parts B and C" >&2
  exit 1
fi

umask 077
CNF="$(mktemp 2>/dev/null || echo "/tmp/.verify_integration_$$.cnf")"
trap 'rm -f "$CNF"' EXIT INT TERM
printf '[client]\nuser=%s\npassword="%s"\n' "$RULE_SVC_USER" "$RULE_SVC_PASSWORD" > "$CNF"

N=0
PASSED=0

q() {
  # Run one SQL statement as the rule service; print the result or the error.
  mysql --defaults-extra-file="$CNF" -N -B -e "$1" 2>&1
}

report() {
  # $1 = PASS/FAIL, $2 = check name, $3 = detail
  N=$((N + 1))
  [ "$1" = "PASS" ] && PASSED=$((PASSED + 1))
  printf '%2d. %-4s  %-46s %s\n' "$N" "$1" "$2" "$3"
}

expect_value() {
  # $1 = check name, $2 = SQL, $3 = expected value
  out="$(q "$2")"
  if [ "$out" = "$3" ]; then
    report PASS "$1" "$out"
  else
    report FAIL "$1" "got: $out | expected: $3"
  fi
}

expect_ok() {
  # $1 = check name, $2 = SQL that must succeed
  out="$(q "$2")"
  case "$out" in
    *ERROR*) report FAIL "$1" "$out" ;;
    *)       report PASS "$1" "allowed" ;;
  esac
}

expect_denied() {
  # $1 = check name, $2 = SQL that must be refused by MySQL's grants
  out="$(q "$2")"
  case "$out" in
    *"ERROR 1142"*|*"ERROR 1143"*|*"ERROR 1044"*) report PASS "$1" "refused (as expected)" ;;
    *) report FAIL "$1" "NOT refused: $out" ;;
  esac
}

echo "Self-test of the data integration layer, logged in as '${RULE_SVC_USER}'"
echo
echo "A. What the rule service may do"
expect_value  "Log in as the service login"            "SELECT CURRENT_USER()" "${RULE_SVC_USER}@%"
expect_value  "Read the view: number of readings"      "SELECT COUNT(*) FROM fde_views.vw_fleet_readings" "32065"
expect_value  "Read the view: number of columns"       "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='fde_views' AND TABLE_NAME='vw_fleet_readings'" "11"
expect_value  "Read the view: latest reading time"     "SELECT MAX(\`Timestamp\`) FROM fde_views.vw_fleet_readings" "2024-08-29 00:00:00"
expect_ok     "Add an audit row (marked SELF_TEST)"    "INSERT INTO fde_audit.RuleDecisionLog (Request_ID, Caller, Caller_Role, Auth_Method, Endpoint, Outcome) VALUES (CONCAT('selftest-', UNIX_TIMESTAMP()), '${RULE_SVC_USER}', 'service', 'self_test', '07_verify_integration.sh', 'SELF_TEST')"
echo
echo "B. What the rule service must NOT be able to do"
expect_denied "Read the legacy table directly"         "SELECT COUNT(*) FROM legacy_fleet.TBL_SC_FLEET_HIST_RAW"
expect_denied "Change data through the view"           "UPDATE fde_views.vw_fleet_readings SET Current_Temperature_C = Current_Temperature_C WHERE Reading_ID = 0"
expect_denied "Read audit rows"                        "SELECT COUNT(*) FROM fde_audit.RuleDecisionLog"
expect_denied "Change an audit row"                    "UPDATE fde_audit.RuleDecisionLog SET Outcome = 'X' WHERE Log_ID = 0"
expect_denied "Delete audit rows"                      "DELETE FROM fde_audit.RuleDecisionLog WHERE Log_ID = 0"
expect_denied "Create a table"                         "CREATE TABLE fde_views.not_allowed (x INT)"
echo
echo "C. SOP rule counts through the view (Step 4 must reproduce these)"
expect_value  "R1  temperature > 4.0 C (breach)"       "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Current_Temperature_C > 4.0" "8674"
expect_value  "R2  breach and > 1 h late (divert)"     "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Current_Temperature_C > 4.0 AND ETA_Variation_Hours > 1.0" "6621"
expect_value  "R3  port congestion > 7.0 (divert)"     "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Port_Congestion_Level > 7.0" "19566"
expect_value  "R4  High Risk and delay > 0.65 (Tier 2)" "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Risk_Classification = 'High Risk' AND Delay_Probability > 0.65" "15440"
expect_value  "G1  temperature < 0.0 C (SOP gap)"      "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Current_Temperature_C < 0.0" "21817"
expect_value  "    inside 0.0 to 4.0 C (in range)"     "SELECT COUNT(*) FROM fde_views.vw_fleet_readings WHERE Current_Temperature_C BETWEEN 0.0 AND 4.0" "1574"

echo
if [ "$PASSED" -eq "$N" ]; then
  echo "RESULT: ${PASSED} of ${N} checks passed. The integration layer is ready for the rule service."
  exit 0
else
  echo "RESULT: ${PASSED} of ${N} checks passed. Fix the FAIL lines (see Step 3, Part H) and run this again."
  exit 1
fi
