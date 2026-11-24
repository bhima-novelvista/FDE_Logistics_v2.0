#!/usr/bin/env bash
# =====================================================================
# update_env.sh - adds the settings of newer project versions to your
# EXISTING .env on macOS (or Linux). On Windows use update_env.ps1.
# Works with the bash 3.2 that ships with macOS.
#
#   bash legacy_system/update_env.sh
#
# - Never changes or removes a setting that already has a value.
# - Adds only what is missing; fills a setting only if it is empty.
# - Asks for new passwords without showing them; creates random secrets
#   itself. Never prints a password or secret.
# - Safe to run again: the second time it says "nothing to add".
#
# Allowed password characters: letters, digits and  _ @ % + = . -
# =====================================================================
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found."
  echo "       Create it first (Step 1, D1):  bash legacy_system/create_env.sh"
  exit 1
fi

# ---------------------------------------------------------------------
# The settings each version needs. One line per setting:
#   KEY|kind|text
#   kind = value    -> written as  KEY=text
#          password -> you are asked for it (text = what it is for)
#          secret   -> a random value is created (text = what it is for)
# A line starting with # is a section heading, written once.
# ---------------------------------------------------------------------
SETTINGS='
# ---- v2.0 Step 3: data integration layer (rule service database login) ----
FDE_VIEWS_DB|value|fde_views
FDE_AUDIT_DB|value|fde_audit
RULE_SVC_USER|value|rule_svc
RULE_SVC_PASSWORD|password|the rule service database login (rule_svc)
# ---- v2.0 Step 4: rule service API (port, login keys, API users) ----
RULE_API_PORT|value|8101
JWT_SECRET|secret|the key that signs login tokens
JWT_EXPIRE_MINUTES|value|30
RULE_API_KEY|secret|the API key for machine clients
API_USER_DISPATCHER_PASSWORD|password|the API user dispatcher
API_USER_SUPERVISOR_PASSWORD|password|the API user supervisor
API_USER_ADMIN_PASSWORD|password|the API user admin
'

ask_password() {
  # $1 = what the password is for. Result is left in NEW_PASSWORD.
  local first second
  while true; do
    printf 'New password for %s (hidden): ' "$1"
    IFS= read -r -s first; echo
    printf 'Type it again: '
    IFS= read -r -s second; echo
    if [ "$first" != "$second" ]; then
      echo "  x The two entries are different. Please try again."
      continue
    fi
    if [ "${#first}" -lt 8 ]; then
      echo "  x Use at least 8 characters. Please try again."
      continue
    fi
    case "$first" in
      *[!A-Za-z0-9_@%+=.-]*)
        echo "  x Use only letters, digits and  _ @ % + = . -  Please try again."
        continue
        ;;
    esac
    NEW_PASSWORD="$first"
    return 0
  done
}

new_secret() {
  # 64 random hexadecimal characters.
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 64
  fi
}

umask 077
TMP="$(mktemp "$ROOT_DIR/.env.update.XXXXXX")"
trap 'rm -f "$TMP"' EXIT INT TERM
cat "$ENV_FILE" > "$TMP"
# make sure the file ends with a new line before anything is appended
if [ -n "$(tail -c 1 "$TMP")" ]; then printf '\n' >> "$TMP"; fi

CHANGED=0
HEADING=""
echo "Updating $ENV_FILE"
echo

# Loop over the lines of SETTINGS without using standard input, so the
# password prompts below still read from your keyboard.
set -f
OLD_IFS="$IFS"
IFS='
'
for spec in $SETTINGS; do
  IFS="$OLD_IFS"
  [ -z "$spec" ] && continue
  case "$spec" in
    \#*) HEADING="$spec"; continue ;;
  esac
  key="${spec%%|*}"; rest="${spec#*|}"
  kind="${rest%%|*}"; text="${rest#*|}"

  line="$(grep -E "^${key}=" "$TMP" | head -n 1 || true)"
  current="${line#*=}"
  if [ -n "$line" ] && [ -n "$current" ]; then
    echo "  kept    $key (already set)"
    continue
  fi

  case "$kind" in
    value)    val="$text" ;;
    password) echo; ask_password "$text"; val="$NEW_PASSWORD" ;;
    secret)   val="$(new_secret)" ;;
    *)        echo "ERROR: unknown kind '$kind' for $key"; exit 1 ;;
  esac

  if [ -n "$line" ]; then
    # the setting exists but is empty: fill in that one line
    K="$key" V="$val" awk 'BEGIN { k = ENVIRON["K"]; v = ENVIRON["V"] }
      $0 == k "=" { print k "=" v; next } { print }' "$TMP" > "$TMP.2"
    cat "$TMP.2" > "$TMP"; rm -f "$TMP.2"
    echo "  filled  $key (was empty)"
  else
    if [ -n "$HEADING" ] && ! grep -Fxq "$HEADING" "$TMP"; then
      printf '\n%s\n' "$HEADING" >> "$TMP"
    fi
    printf '%s=%s\n' "$key" "$val" >> "$TMP"
    echo "  added   $key"
  fi
  CHANGED=$((CHANGED + 1))
done
IFS="$OLD_IFS"
set +f
unset val NEW_PASSWORD 2>/dev/null || true

echo
if [ "$CHANGED" -eq 0 ]; then
  echo "OK: nothing to add - .env already has every setting."
else
  cat "$TMP" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "OK: $CHANGED setting(s) added to .env (passwords and secrets not shown)."
fi
echo "Settings in the file:"
sed -E 's/^([A-Z_]*(PASSWORD|SECRET|API_KEY))=.+$/\1=******** (set)/' "$ENV_FILE" | grep -E '^[A-Z_]+='
