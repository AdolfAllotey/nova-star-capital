# src/v2/tests/test_api.py
import os
import pytest
import requests

BASE = "http://127.0.0.1:8000"
TOKEN = os.getenv("NSC_API_TOKEN", "2d9624fb5808628625fa9cd4e500a5a86152bc794a66ef23")


def test_health():
    """Vérifie que le /health répond correctement"""
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True


def test_api_ohlcv_bearer():
    """Test de la route /api/ohlcv avec authentification Bearer"""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(f"{BASE}/api/ohlcv?symbol=BTCUSDT&tf=1h&limit=1", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert "symbol" in data[0]
    assert data[0]["symbol"] == "BTCUSDT"


def test_internal_ohlcv_token():
# DISABLED LEGACY:     """Test de la route legacy /internal/ohlcv avec ?token="""
    r = requests.get(
# DISABLED LEGACY:         f"{BASE}/internal/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=json&token={TOKEN}"
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert "symbol" in data[0]
    assert data[0]["symbol"] == "BTCUSDT"


def test_internal_ohlcv_access_token():
# DISABLED LEGACY:     """Test de la route legacy /internal/ohlcv avec ?access_token="""
    r = requests.get(
# DISABLED LEGACY:         f"{BASE}/internal/ohlcv?symbol=ETHUSDT&tf=15m&days=1&format=json&access_token={TOKEN}"
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert "symbol" in data[0]
    assert data[0]["symbol"] == "ETHUSDT"


def test_internal_ohlcv_header_token():
# DISABLED LEGACY:     """Test de la route legacy /internal/ohlcv avec X-API-Token en header"""
    headers = {"X-API-Token": TOKEN}
    r = requests.get(
# DISABLED LEGACY:         f"{BASE}/internal/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=json", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert "symbol" in data[0]
    assert data[0]["symbol"] == "BTCUSDT"
