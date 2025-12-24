# ============================================
#  Nova Star Capital - API Makefile (preprod)
# ============================================

API_BASE_LOCAL = http://127.0.0.1:8000
API_BASE_DOMAIN = https://api.preprod.novastarcapital.fr
RESOLVE = --resolve api.preprod.novastarcapital.fr:443:127.0.0.1

.PHONY: openapi health metrics401 metrics200 smoke reload-api logs-api fmt-caddy reload-caddy

# --- Vérifie les routes exposées dans OpenAPI ---
openapi:
	curl -ksS $(RESOLVE) $(API_BASE_DOMAIN)/openapi.json | jq '.paths | keys'

# --- Vérifie la santé locale ---
health:
	curl -sS $(API_BASE_LOCAL)/health | jq .

# --- Vérifie que /metrics renvoie 401 sans auth ---
metrics401:
	@curl -ks -o /dev/null -w 'code=%{http_code}\n' $(RESOLVE) $(API_BASE_DOMAIN)/metrics

# --- Vérifie que /metrics renvoie 200 avec auth ---
metrics200:
	@curl -ks -o /dev/null -w 'code=%{http_code}\n' $(RESOLVE) \
		-u metrics:'NSC-Metrics#Preprod-233#' \
		$(API_BASE_DOMAIN)/metrics

# --- Lancement complet des smoke-tests ---
smoke:
	bash scripts/api_smoke.sh

# --- Redémarre proprement le service systemd ---
reload-api:
	sudo systemctl daemon-reload
	sudo systemctl restart nsc-api
	journalctl -u nsc-api -n 20 --no-pager -o cat

# --- Affiche les logs récents de l'API ---
logs-api:
	journalctl -u nsc-api -n 100 --no-pager -o cat

# --- Formate et valide la config Caddy ---
fmt-caddy:
	sudo caddy fmt --overwrite /etc/caddy/Caddyfile
	sudo caddy validate --config /etc/caddy/Caddyfile

# --- Recharge proprement Caddy ---
reload-caddy: fmt-caddy
	sudo systemctl reload caddy
	journalctl -u caddy -n 50 --no-pager -o cat
