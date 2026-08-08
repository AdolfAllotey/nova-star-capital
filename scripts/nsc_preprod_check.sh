#!/usr/bin/env bash

echo "=============================="
echo "NSC PREPROD DAILY CHECK"
echo "=============================="
date
echo

echo "----- API HEALTH -----"
curl -s http://127.0.0.1:8000/health
echo
echo

echo "----- TIMERS -----"
systemctl list-timers | grep nsc
echo
echo

echo "----- MARKET -----"
echo "Top Movers update:"
curl -s http://127.0.0.1:8000/market/top-movers | jq '.updated_at'
echo
echo

echo "----- POSITIONS -----"
curl -s http://127.0.0.1:8000/portfolio/open | jq '.'
echo
echo

echo "----- WORST TRADES -----"
curl -s http://127.0.0.1:8000/risk/worst-trades/summary | jq '.'
echo
echo

echo "----- FILE UPDATES -----"
ls -l --full-time /opt/nsc/data/preprod/market/crypto_spot_prices.json
ls -l --full-time /opt/nsc/data/preprod/trading/open_positions.json
ls -l --full-time /opt/nsc/data/preprod/trading/exit_events.json
echo
echo

echo "----- KERNEL LOGS -----"
journalctl -u nsc-kernel.service -n 20 --no-pager
echo
echo

echo "----- PIPELINE LOGS -----"
journalctl -u nsc-preprod-pipeline.service -n 20 --no-pager
echo
echo

echo "----- ERROR SCAN -----"
journalctl -u nsc-kernel.service -n 200 --no-pager | grep -Ei "error|exception|traceback|permission denied"
journalctl -u nsc-preprod-pipeline.service -n 200 --no-pager | grep -Ei "error|exception|traceback|permission denied"
echo
echo

echo "----- GOVERNANCE EVENTS -----"
tail -n 10 /opt/nsc/data/preprod/telemetry/event_bus.jsonl
echo
echo "=============================="
echo "END NSC CHECK"
echo "=============================="
