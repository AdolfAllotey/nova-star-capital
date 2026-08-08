NSC OPTIONS V1 - OPERATING NOTES

Main commands:
- /opt/nsc/scripts/nsc-options-check
- /opt/nsc/scripts/options-daily-run.sh
- /opt/nsc/scripts/reset-options-v1.sh
- systemctl status nsc-options-preprod.timer --no-pager
- systemctl start nsc-options-preprod.service

Main runtime files:
- data/options_status.json
- data/options_metrics.json
- data/options_positions.json
- data/options_trades.json

Main config files:
- data/options_config.json
- data/options_inputs.json

External mock input files:
- data/external_equity_positions.json
- data/external_watchlists.json
- data/external_signals.json

Logs:
- /opt/nsc/app/src/v2/logs/options_pipeline.log
- /opt/nsc/app/src/v2/logs/options_systemd.log
