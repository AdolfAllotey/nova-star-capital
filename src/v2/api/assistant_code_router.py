# /opt/nsc/app/src/v2/api/assistant_code_router.py

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

logger = logging.getLogger("nsc_api")

router = APIRouter(
    prefix="/assistant",
    tags=["assistant-code"],
)


# ---------- Modèles Pydantic ----------

class CodeFile(BaseModel):
    path: str          # chemin relatif depuis la racine du projet app (ex: "src/v2/analysis/foo.py")
    content: str       # contenu complet du fichier


class CardInfo(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None


class CodeApplyRequest(BaseModel):
    message: str
    dry_run: bool = True
    files: List[CodeFile]
    card: Optional[CardInfo] = None


class CodeApplyFileResult(BaseModel):
    path: str
    absolute_path: str
    existed_before: bool
    changed: bool
    previous_size: Optional[int] = None
    new_size: Optional[int] = None
    backup_path: Optional[str] = None


class CodeApplyResponse(BaseModel):
    ok: bool
    dry_run: bool
    base_dir: str
    files: List[CodeApplyFileResult]
    card: Optional[CardInfo] = None
    message: str


# ---------- Sécurité (token optionnel) ----------

def verify_assistant_token(
    x_assistant_token: Optional[str] = Header(default=None),
) -> None:
    """
    Vérifie (optionnellement) le token assistant.
    - Si NSC_ASSISTANT_TOKEN n'est pas défini => pas de check (mode dev).
    - Si défini => le header X-Assistant-Token doit être présent et identique.
    """
    expected = os.environ.get("NSC_ASSISTANT_TOKEN")
    if not expected:
        # Pas de token configuré -> on laisse passer
        return

    if not x_assistant_token:
        raise HTTPException(status_code=401, detail="Missing X-Assistant-Token")

    if x_assistant_token != expected:
        raise HTTPException(status_code=401, detail="Invalid X-Assistant-Token")


# ---------- Helpers ----------

def get_app_root() -> Path:
    """
    Racine du projet /opt/nsc/app.
    On part du fichier actuel: src/v2/api/assistant_code_router.py
    parents:
      0 -> api
      1 -> v2
      2 -> src
      3 -> app   <-- racine projet
    """
    return Path(__file__).resolve().parents[3]


def resolve_target_path(base_dir: Path, relative_path: str) -> Path:
    """
    Résout un chemin relatif vers un chemin absolu sécurisé.
    Empêche d’écrire en dehors de la racine de projet.
    """
    target = (base_dir / relative_path).resolve()

    # On vérifie que target est bien sous base_dir
    try:
        target.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Chemin en dehors du projet: {relative_path}",
        )
    return target


def compute_file_change(target: Path, new_content: str) -> Dict[str, Any]:
    """
    Compare l’ancien contenu (si le fichier existe) avec le nouveau.
    Retourne un dict avec existed_before, changed, previous_size, new_size.
    """
    existed_before = target.exists()
    previous_size = None
    old_content = None

    if existed_before and target.is_file():
        try:
            old_content = target.read_text(encoding="utf-8")
            previous_size = len(old_content.encode("utf-8"))
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Impossible de lire le fichier existant %s: %s",
                target,
                exc,
            )

    new_size = len(new_content.encode("utf-8"))
    changed = (old_content != new_content)

    return {
        "existed_before": existed_before,
        "changed": changed,
        "previous_size": previous_size,
        "new_size": new_size,
    }


def write_file_with_backup(target: Path, content: str) -> Optional[Path]:
    """
    Écrit le fichier en créant un backup si le fichier existait.
    Retourne le chemin du backup ou None.
    """
    backup_path: Optional[Path] = None

    if target.exists() and target.is_file():
        backup_path = target.with_suffix(target.suffix + ".bak")
        try:
            target.replace(backup_path)
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Impossible de créer le backup %s pour %s: %s",
                backup_path,
                target,
                exc,
            )
            # On ne bloque pas pour autant, mais on log l’erreur

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(content, encoding="utf-8")
    except Exception as exc:
        # Si l’écriture échoue, on essaie de restaurer le backup
        if backup_path and backup_path.exists():
            backup_path.replace(target)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'écriture du fichier {target}: {exc}",
        )

    return backup_path


# ---------- Endpoint principal ----------

@router.post(
    "/code/apply",
    response_model=CodeApplyResponse,
    summary="Appliquer ou simuler l'application d'un batch de fichiers (assistant)",
)
def apply_code_batch(
    payload: CodeApplyRequest,
    _: None = Depends(verify_assistant_token),
) -> CodeApplyResponse:
    """
    Endpoint utilisé par le pont assistant pour proposer ou appliquer des modifications de code.

    - Si dry_run = True -> ne fait qu'analyser les changements (existe / change / tailles).
    - Si dry_run = False -> écrit réellement les fichiers, avec backup.
    """
    base_dir = get_app_root()
    logger.info(
        "[assistant-code] Reçu batch (dry_run=%s, files=%d, card=%s)",
        payload.dry_run,
        len(payload.files),
        payload.card.dict() if payload.card else None,
    )

    results: List[CodeApplyFileResult] = []

    for f in payload.files:
        target = resolve_target_path(base_dir, f.path)
        change_info = compute_file_change(target, f.content)

        backup_path_str: Optional[str] = None

        if not payload.dry_run and change_info["changed"]:
            backup_path = write_file_with_backup(target, f.content)
            backup_path_str = str(backup_path) if backup_path else None

            logger.info(
                "[assistant-code] Fichier écrit: %s (backup=%s)",
                target,
                backup_path_str,
            )
        else:
            logger.info(
                "[assistant-code] DRY_RUN ou pas de changement pour: %s",
                target,
            )

        results.append(
            CodeApplyFileResult(
                path=f.path,
                absolute_path=str(target),
                existed_before=change_info["existed_before"],
                changed=change_info["changed"],
                previous_size=change_info["previous_size"],
                new_size=change_info["new_size"],
                backup_path=backup_path_str,
            )
        )

    return CodeApplyResponse(
        ok=True,
        dry_run=payload.dry_run,
        base_dir=str(base_dir),
        files=results,
        card=payload.card,
        message=payload.message,
    )
