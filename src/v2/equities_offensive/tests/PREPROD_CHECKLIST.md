# EQU-010 — Préprod checklist (Actions Offensives)

## A. Sécurité / Gouvernance
- [ ] action_policy = SIMULATED_ONLY en préprod (pas de LIVE)
- [ ] kill-switch hard_block => orders=0
- [ ] caps (max_positions / max_total_notional / concentration) définis et testés

## B. Pipeline idempotent
- [ ] relancer 2 fois de suite => mêmes outputs, pas de doublons (fills/audit)
- [ ] state.json présent et stable

## C. Artefacts UI (contrat stable)
- [ ] ui_bundle.json contient kpis/exposure/limits/plan/recent_fills
- [ ] audit_trail.jsonl append à chaque run

## D. Market Calendar / gating
- [ ] market_calendar_gate fonctionne (week-end/holidays)
- [ ] us_holidays.json auto-généré si absent

## E. Canary run (end-to-end)
- [ ] run loop complet => check OK
- [ ] logs OK, pas d'exception

## Commande unique
`python src/v2/equities_offensive/tests/preprod_check.py`
