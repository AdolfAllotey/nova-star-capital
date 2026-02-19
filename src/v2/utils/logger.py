import logging
import os
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

_LOG_LEVEL = os.getenv("NSC_LOG_LEVEL", "INFO").upper()

def _get_log_dir(default_dir: str) -> Path:
    """Respecte NSC_LOG_DIR si défini, sinon fallback sur default_dir."""
    env_dir = (os.getenv("NSC_LOG_DIR") or "").strip()
    return Path(env_dir) if env_dir else Path(default_dir)

def _setup_root_handlers() -> None:
    """
    Configure une fois :
    - console handler (stdout)
    - file handler rotatif (quotidien) dans NSC_LOG_DIR
    """
    root = logging.getLogger()
    level = getattr(logging, _LOG_LEVEL, logging.INFO)
    root.setLevel(level)

    # 🔒 Pipeline-safe: ensure we don't accumulate handlers from other libs/process init
    # (uvicorn/basicConfig/systemd etc.). Without this, logs may appear twice.
    if not getattr(root, "_nsc_configured", False):
        for h in list(root.handlers):
            try:
                root.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass
            except Exception:
                pass

    # Si déjà configuré (handlers existants), ne pas dupliquer.
    if getattr(root, "_nsc_configured", False):
        return

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # 1) Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # 2) Fichier (rotation quotidienne)
    default_dir = str(Path(__file__).resolve().parents[1] / "logs")  # src/v2/logs (fallback)
    log_dir = _get_log_dir(default_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_path = log_dir / "nsc.log"  # un fichier global + rotation
    fh = TimedRotatingFileHandler(
        filename=str(file_path),
        when="midnight",
        interval=1,
        backupCount=14,
        utc=True,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    root._nsc_configured = True  # type: ignore[attr-defined]

def get_logger(name: str) -> logging.Logger:
    _setup_root_handlers()
    return logging.getLogger(name)
