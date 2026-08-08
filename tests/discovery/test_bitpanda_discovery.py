from src.v2.discovery.bitpanda_discovery import (
    build_document,
    normalize_ticker_item,
)


def test_normalize_ticker_item_crypto() -> None:
    row = {
        "id": "btc-id",
        "symbol": "btc",
        "name": "Bitcoin",
        "type": "cryptocoin",
        "group": "coin",
        "currency": "EUR",
        "price": "98250.50",
        "price_change_day": "4.25",
    }

    item = normalize_ticker_item(row)

    assert item is not None
    assert item["symbol"] == "BTC"
    assert item["price"] == 98250.50
    assert item["chg_24h"] == 4.25
    assert item["source"] == "bitpanda"
    assert item["observation_only"] is True
    assert item["tradable_by_nsc"] is False


def test_rejects_non_crypto_asset() -> None:
    row = {
        "symbol": "AAPL",
        "type": "equity_security",
        "currency": "EUR",
        "price": "200",
        "price_change_day": "1.5",
    }

    assert normalize_ticker_item(row) is None


def test_rejects_stablecoin() -> None:
    row = {
        "symbol": "USDT",
        "type": "cryptocoin",
        "group": "token",
        "currency": "EUR",
        "price": "0.99",
        "price_change_day": "0.01",
    }

    assert normalize_ticker_item(row) is None


def test_build_document_orders_absolute_movers() -> None:
    rows = [
        {
            "id": "a",
            "symbol": "AAA",
            "name": "AAA",
            "type": "cryptocoin",
            "group": "coin",
            "currency": "EUR",
            "price": "10",
            "price_change_day": "5",
        },
        {
            "id": "b",
            "symbol": "BBB",
            "name": "BBB",
            "type": "cryptocoin",
            "group": "token",
            "currency": "EUR",
            "price": "2",
            "price_change_day": "-12",
        },
    ]

    doc = build_document(rows)

    assert doc["status"] == "ok"
    assert doc["count"] == 2
    assert doc["items"][0]["symbol"] == "BBB"
    assert doc["gainers_count"] == 1
    assert doc["losers_count"] == 1
