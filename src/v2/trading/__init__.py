"""
Package trading – Nova Star Capital V2.

Ce package contient :
- trading_kernel.py
- position_manager.py
- daily_trading_loop.py
- governor_system_light.py
et autres modules de trading.

On ne fait volontairement **aucun import** ici pour éviter
les imports circulaires (daily_trading_loop <-> __init__).
"""

__all__ = []
