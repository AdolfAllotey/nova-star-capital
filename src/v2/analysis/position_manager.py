"""
DEPRECATED / LEGACY.
Compat historique : l’implémentation canonique est côté trading, appelée par trading_kernel.

Source officielle :
- src.v2.trading.position_manager
"""
from src.v2.trading.position_manager import main  # noqa: F401

if __name__ == "__main__":
    main()
