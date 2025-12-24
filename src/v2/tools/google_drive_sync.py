# /opt/nsc/app/src/v2/tools/google_drive_sync.py

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.v2.utils.logger import get_logger

log = get_logger("google_drive_sync")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

BASE_DIR = Path("/opt/nsc")
SECRETS_DIR = BASE_DIR / "secrets"
DATA_DIR = BASE_DIR / "src" / "v2" / "data"

TOKEN_FILE = SECRETS_DIR / "google-oauth-token.json"


def get_credentials() -> Credentials:
    """
    Sur le serveur, on N'OUVRE PAS de navigateur.
    On suppose qu'un token OAuth a été généré ailleurs (sur ton Mac)
    et copié dans TOKEN_FILE.
    """
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token OAuth introuvable : {TOKEN_FILE}\n"
            ">> Génère d'abord le token sur ta machine locale, puis copie-le sur le serveur."
        )

    creds: Optional[Credentials] = Credentials.from_authorized_user_file(
        str(TOKEN_FILE), SCOPES
    )

    # Si le token est expiré mais a un refresh_token, on le rafraîchit silencieusement
    if creds and not creds.valid and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            log.info("[drive] token rafraîchi avec succès")
        except Exception as e:
            raise RuntimeError(
                f"Échec du refresh token. Regénère le token localement. Détail : {e}"
            )

        # On réécrit le token mis à jour
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TOKEN_FILE.open("w") as f:
            f.write(creds.to_json())
        os.chmod(TOKEN_FILE, 0o600)

    if not creds or not creds.valid:
        raise RuntimeError(
            "Token OAuth invalide. Regénère le token sur ta machine locale."
        )

    return creds


def upload_file(local_path: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier local introuvable : {local_path}")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata: Dict[str, Any] = {"name": path.name}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(str(path), resumable=True)

    log.info(f"[drive] upload → {path} (folder={folder_id or 'root'})")
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name, parents")
        .execute()
    )

    return file


def main():
    parser = argparse.ArgumentParser(description="Sync fichiers NSC vers Google Drive")
    parser.add_argument(
        "--local",
        required=True,
        help="Chemin du fichier local à envoyer (ex: src/v2/data/reports/market_regime.json)",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="ID du dossier Drive cible (optionnel)",
    )
    args = parser.parse_args()

    try:
        log.info(f"[drive] préparation upload → {args.local}")
        result = upload_file(args.local, folder_id=args.folder)
        log.info(f"[drive] upload OK : {result}")
        print(json.dumps({"status": "ok", "file": result}, ensure_ascii=False))
    except Exception as e:
        log.exception("[drive] erreur lors de l'upload")
        print(json.dumps({"error": str(e)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
