#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Provider Registry V1
"""

from __future__ import annotations

from provider_base import MarketDataProvider
from provider_massive import MassiveProvider
from provider_yfinance import YFinanceProvider


def build_provider_registry() -> dict[str, MarketDataProvider]:
    return {
        "yfinance": YFinanceProvider(),
        "massive": MassiveProvider(),
        # Alias de compatibilité avec l'ancien nom.
        "polygon": MassiveProvider(),
    }


def configured_providers() -> dict[str, MarketDataProvider]:
    registry = build_provider_registry()

    return {
        name: provider
        for name, provider in registry.items()
        if provider.is_configured()
    }


def provider_metadata() -> dict[str, dict]:
    registry = build_provider_registry()

    return {
        name: provider.metadata()
        for name, provider in registry.items()
    }
