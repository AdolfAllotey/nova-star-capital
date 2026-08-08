# NSC Portfolio Input Standard — v1.5

Chaque brique branchée à l’agrégateur doit exposer un fichier:
`*_portfolio_input.json`

## Champs obligatoires
- `brick`
- `enabled`
- `portfolio_role`
- `signal_type`
- `target_weight`
- `confidence`
- `regime`
- `allocation`
- `drivers`
- `risk_flags`
- `inertia_profile`
- `execution_mode`
- `funding_pool`
- `source_file`

## Valeurs officielles pour `brick`
- `crypto`
- `equities_offensive`
- `equities_defensive`
- `bonds`
- `precious_metals`

## Valeurs officielles pour `funding_pool`
- `crypto_exchange_pool`
- `ibkr_pool`

## Valeurs officielles pour `portfolio_role`
- `alpha_aggressive`
- `alpha_directional`
- `stabilization`
- `macro_stabilizer`
- `systemic_hedge`

## Notes
- `target_weight` exprime une intention d’allocation, pas une exécution.
- `funding_pool` sert à préparer les futurs funding plans.
- `inertia_profile` sert à limiter la vitesse de réallocation.
- Les transferts inter-pools ne sont jamais supposés automatiques.
