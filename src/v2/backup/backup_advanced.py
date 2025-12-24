import os
import shutil
import datetime
import tarfile
import logging

BACKUP_BASE_DIR = "data/v2/backups"
FOLDERS_TO_BACKUP = [
    "data/v2/logs",
    "data/v2/reports",
    # Ajouter d'autres dossiers si besoin
]
RETENTION_DAYS = 30
LOG_FILE = "data/v2/backups/backup_advanced.log"

# Configuration du logging
os.makedirs(BACKUP_BASE_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def create_backup():
    now = datetime.datetime.now()
    backup_folder = os.path.join(BACKUP_BASE_DIR, f"backup_{now.strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(backup_folder, exist_ok=True)
        for folder in FOLDERS_TO_BACKUP:
            if os.path.exists(folder):
                dest = os.path.join(backup_folder, os.path.basename(folder))
                shutil.copytree(folder, dest)
                logging.info(f"Sauvegarde réussie : {folder}")
            else:
                logging.warning(f"Dossier non trouvé : {folder}")

        archive_path = backup_folder + ".tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_folder, arcname=os.path.basename(backup_folder))
        logging.info(f"Compression terminée : {archive_path}")

        # Suppression du dossier temporaire non compressé
        shutil.rmtree(backup_folder)
        logging.info(f"Dossier temporaire supprimé : {backup_folder}")

    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde : {e}")
        print(f"❌ Erreur lors de la sauvegarde : {e}")

def cleanup_old_backups():
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=RETENTION_DAYS)
    try:
        if not os.path.exists(BACKUP_BASE_DIR):
            logging.warning(f"Dossier de backup non trouvé : {BACKUP_BASE_DIR}")
            return
        for entry in os.listdir(BACKUP_BASE_DIR):
            full_path = os.path.join(BACKUP_BASE_DIR, entry)
            if os.path.isfile(full_path) and entry.endswith(".tar.gz"):
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                if mtime < cutoff:
                    os.remove(full_path)
                    logging.info(f"Suppression de l'ancien backup : {entry}")
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des backups : {e}")
        print(f"❌ Erreur lors du nettoyage des backups : {e}")

if __name__ == "__main__":
    create_backup()
    cleanup_old_backups()