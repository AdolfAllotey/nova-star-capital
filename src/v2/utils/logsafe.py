# -*- coding: utf-8 -*-
"""
logsafe.py – récupère le logger centralisé si présent, sinon fallback python logging.
"""
import logging

def get_logger(name: str):
    try:
        # Ton logger centralisé
        from src.v2.utils.logger import get_logger as nsc_logger  # type: ignore
        return nsc_logger(name)
    except Exception:
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            h = logging.StreamHandler()
            fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            h.setFormatter(fmt)
            logger.addHandler(h)
        return logger
