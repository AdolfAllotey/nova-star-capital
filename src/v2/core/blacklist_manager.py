
def get_blacklisted_tokens():
    """
    Retourne une liste de tokens à exclure (rug pulls, scams, comportements suspects, blacklist manuelle, etc.)
    À terme, cette liste pourra être construite dynamiquement ou chargée depuis un fichier externe.
    """
    # Exemple : tokens à exclure manuellement
    return {"RUG1", "FAKETOKEN", "SCAMCOIN"}

# Exemple d’utilisation :
# blacklist = get_blacklisted_tokens()
# if "RUG1" in blacklist: print("⚠️ Token exclu")
