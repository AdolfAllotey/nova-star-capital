
from src.v2.config.user_mode import set_user_mode
from src.v2.users.strategy_profiles import list_profiles

def display_menu():
    print("🔧 Changement de mode utilisateur")
    print("1. Mode manuel")
    print("2. Mode automatique")
    choice = input("👉 Choix (1 ou 2) : ")

    if choice == "1":
        mode = "manuel"
    elif choice == "2":
        mode = "automatique"
    else:
        print("❌ Choix invalide.")
        return

    print("📊 Profils disponibles :")
    for i, name in enumerate(list_profiles(), start=1):
        print(f"{i}. {name.capitalize()}")

    profile_choice = input("👉 Sélection du profil (1-3) : ")
    try:
        profile = list_profiles()[int(profile_choice) - 1]
    except:
        print("❌ Sélection invalide.")
        return

    set_user_mode(mode, profile)
    print(f"✅ Mode défini sur : {mode} - Profil : {profile}")

if __name__ == "__main__":
    display_menu()
