#!/usr/bin/env python3
"""
Valide les handles Telegram listés dans src/v2/data/social/groups.txt
- Normalise (@foo -> foo, supprime blancs/duplicats)
- Vérifie le format via regex
- Vérifie l'existence via Telethon (ResolveUsername)
- Écrit:
  - groups_valid.txt (un handle/ligne, sans @)
  - groups_invalid.txt (avec raison)
  - groups_validation_report.json (détails)
Option --apply : remplace src/v2/data/social/groups.txt par la version filtrée (valides).
Variables requises dans l'env (.env v2):
  TELEGRAM_API_ID, TELEGRAM_API_HASH
Optionnel: TELEGRAM_SESSION_NAME (défaut: nova_star_session)
"""

import os
import re
import json
import time
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

from telethon import TelegramClient, functions, errors

ROOT      = Path("/root/Bot_crypto_ultra")
DATA_DIR  = ROOT / "src/v2/data/social"
IN_FILE   = DATA_DIR / "groups.txt"
VALID_OUT = DATA_DIR / "groups_valid.txt"
INVALID_OUT= DATA_DIR / "groups_invalid.txt"
REPORT    = DATA_DIR / "groups_validation_report.json"

USERNAME_RE = re.compile(r"^[A-Za-z][\w\d]{3,30}[A-Za-z\d]$")  # règle Telegram

def load_env_v2():
    env_file = ROOT / "src/v2/.env"
    if env_file.exists():
        with env_file.open() as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k,v = line.split("=",1)
                os.environ.setdefault(k.strip(), v.strip())

def read_groups() -> List[str]:
    if not IN_FILE.exists():
        raise FileNotFoundError(f"Fichier introuvable: {IN_FILE}")
    seen = set()
    out  = []
    for raw in IN_FILE.read_text(encoding="utf-8").splitlines():
        g = raw.strip()
        if not g: 
            continue
        if g.startswith("@"):
            g = g[1:]
        # Telegram n'autorise pas les espaces
        g = g.replace(" ", "")
        if g and g not in seen:
            seen.add(g)
            out.append(g)
    return out

def quick_format_check(g: str) -> Tuple[bool,str]:
    if not USERNAME_RE.match(g):
        return False, "format_invalide"
    return True, "ok"

def resolve_with_telethon_sync(client: TelegramClient, g: str) -> Tuple[bool,str]:
    """
    Appel synchrone sûr: on exécute la coroutine via loop.run_until_complete.
    """
    try:
        r = client.loop.run_until_complete(
            client(functions.contacts.ResolveUsernameRequest(g))
        )
        has_any = bool(r.users or r.chats)
        return has_any, "ok" if has_any else "username_inexistant_ou_non_occupe"
    except errors.rpcerrorlist.UsernameNotOccupiedError:
        return False, "username_non_occupe"
    except errors.FloodWaitError as e:
        # En cas de flood wait, on attend puis on retente une fois
        time.sleep(e.seconds + 1)
        try:
            r = client.loop.run_until_complete(
                client(functions.contacts.ResolveUsernameRequest(g))
            )
            has_any = bool(r.users or r.chats)
            return has_any, "ok_after_wait" if has_any else "username_inexistant_ou_non_occupe"
        except Exception as e2:
            return False, f"floodwait_retry_fail:{type(e2).__name__}"
    except Exception as e:
        return False, f"exception:{type(e).__name__}"

def main():
    load_env_v2()
    api_id  = os.getenv("TELEGRAM_API_ID")
    api_hash= os.getenv("TELEGRAM_API_HASH")
    session = os.getenv("TELEGRAM_SESSION_NAME","nova_star_session")

    if not api_id or not api_hash:
        print("❌ TELEGRAM_API_ID / TELEGRAM_API_HASH manquants (dans src/v2/.env).")
        raise SystemExit(1)

    groups = read_groups()
    print(f"📥 {len(groups)} handles lus depuis {IN_FILE.name}")

    client = TelegramClient(session=session, api_id=int(api_id), api_hash=api_hash)
    client.start()
    print("✅ Client Telegram prêt")

    valid: List[str] = []
    invalid: List[Tuple[str,str]] = []
    details: Dict[str, Dict[str,str]] = {}

    for i,g in enumerate(groups, 1):
        ok_fmt, reason = quick_format_check(g)
        if not ok_fmt:
            invalid.append((g, reason))
            details[g] = {"status":"invalid", "reason":reason}
            print(f"[{i}/{len(groups)}] ❌ {g:<30} {reason}")
            continue

        ok_res, reason2 = resolve_with_telethon_sync(client, g)
        if ok_res:
            valid.append(g)
            details[g] = {"status":"valid", "reason":"ok"}
            print(f"[{i}/{len(groups)}] ✅ {g}")
        else:
            invalid.append((g, reason2))
            details[g] = {"status":"invalid", "reason":reason2}
            print(f"[{i}/{len(groups)}] ❌ {g:<30} {reason2}")

        time.sleep(0.4)  # petite pause anti flood

    VALID_OUT.write_text("\n".join(valid) + ("\n" if valid else ""), encoding="utf-8")
    with INVALID_OUT.open("w", encoding="utf-8") as f:
        for g,rsn in invalid:
            f.write(f"{g}\t{rsn}\n")
    REPORT.write_text(json.dumps({
        "in_file": str(IN_FILE),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "valid": valid,
        "invalid": [{"handle": h, "reason": r} for h,r in invalid],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📊 Résumé:")
    print(f"  Valides : {len(valid)}  -> {VALID_OUT.name}")
    print(f"  Invalides : {len(invalid)} -> {INVALID_OUT.name}")
    print(f"  Rapport : {REPORT.name}")

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Remplace groups.txt par la liste validée")
    args, _ = ap.parse_known_args()
    if args.apply:
        backup = IN_FILE.with_suffix(".txt.bak")
        shutil.copy2(IN_FILE, backup)
        IN_FILE.write_text("\n".join(valid) + ("\n" if valid else ""), encoding="utf-8")
        print(f"🛠️  groups.txt mis à jour ({len(valid)} valides). Backup: {backup.name}")

if __name__ == "__main__":
    main()
