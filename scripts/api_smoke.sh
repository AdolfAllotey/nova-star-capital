#!/usr/bin/env bash
set -euo pipefail

API_LOCAL="http://127.0.0.1:8000"
DOMAIN="${NSC_API_DOMAIN:-api.preprod.novastarcapital.fr}"
API_VIA_CADDY="https://${DOMAIN}"

pass() { echo -e "✅ $*"; }
fail() { echo -e "❌ $*"; exit 1; }

jq -V >/dev/null 2>&1 || fail "jq est requis (sudo apt-get install -y jq)"

echo "== Local =="
curl -fsS "${API_LOCAL}/health" | jq . >/dev/null && pass "/health OK (local)" || fail "/health KO (local)"

# Endpoints “lecture fichiers”
curl -fsS "${API_LOCAL}/api/market/regime"     | jq . >/dev/null && pass "/api/market/regime OK (local)"     || fail "/api/market/regime KO (local)"
curl -fsS "${API_LOCAL}/api/signals/sentiment" | jq . >/dev/null && pass "/api/signals/sentiment OK (local)" || fail "/api/signals/sentiment KO (local)"
curl -fsS "${API_LOCAL}/api/status/pnl"        | jq . >/dev/null && pass "/api/status/pnl OK (local)"        || fail "/api/status/pnl KO (local)"
curl -fsS "${API_LOCAL}/api/monitor/whales"    | jq . >/dev/null && pass "/api/monitor/whales OK (local)"    || fail "/api/monitor/whales KO (local)"
curl -fsS "${API_LOCAL}/api/trades"            | jq . >/dev/null && pass "/api/trades OK (local)"            || fail "/api/trades KO (local)"

# Metrics protégés (local direct: non protégé par Caddy, donc on check seulement Caddy ensuite)
echo
echo "== Via Caddy (${DOMAIN}) =="
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/health" | jq . >/dev/null && pass "/health OK (caddy)" || fail "/health KO (caddy)"
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/api/market/regime"     | jq . >/dev/null && pass "/api/market/regime OK (caddy)"     || fail "/api/market/regime KO (caddy)"
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/api/signals/sentiment" | jq . >/dev/null && pass "/api/signals/sentiment OK (caddy)" || fail "/api/signals/sentiment KO (caddy)"
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/api/status/pnl"        | jq . >/dev/null && pass "/api/status/pnl OK (caddy)"        || fail "/api/status/pnl KO (caddy)"
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/api/monitor/whales"    | jq . >/dev/null && pass "/api/monitor/whales OK (caddy)"    || fail "/api/monitor/whales KO (caddy)"
curl -ksS --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/api/trades"            | jq . >/dev/null && pass "/api/trades OK (caddy)"            || fail "/api/trades KO (caddy)"

# Metrics: 401 sans auth / 200 avec auth
echo
echo "== Metrics (via Caddy) =="
CODE401=$(curl -ks -o /dev/null -w '%{http_code}' --resolve "${DOMAIN}:443:127.0.0.1" "${API_VIA_CADDY}/metrics" || true)
[[ "${CODE401}" == "401" ]] && pass "/metrics renvoie 401 sans auth" || fail "/metrics devrait renvoyer 401 sans auth (reçu ${CODE401})"

CODE200=$(curl -ks -o /dev/null -w '%{http_code}' \
  --resolve "${DOMAIN}:443:127.0.0.1" \
  -u metrics:'NSC-Metrics#Preprod-233#' \
  "${API_VIA_CADDY}/metrics" || true)
[[ "${CODE200}" == "200" ]] && pass "/metrics renvoie 200 avec auth" || fail "/metrics devrait renvoyer 200 avec auth (reçu ${CODE200})"

echo
pass "SMOKE TEST OK ✅"
