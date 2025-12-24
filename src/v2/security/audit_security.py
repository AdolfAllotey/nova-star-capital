import os
import stat

def check_file_permissions(file_path):
    try:
        st = os.stat(file_path)
        permissions = stat.filemode(st.st_mode)
        print(f"{file_path} : permissions {permissions}")
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé : {file_path}")

def main():
    files_to_check = [
        ".env",
        "src/v2/.env",
        # ajoute d'autres fichiers sensibles ici
    ]
    for file in files_to_check:
        check_file_permissions(file)

if __name__ == "__main__":
    main()