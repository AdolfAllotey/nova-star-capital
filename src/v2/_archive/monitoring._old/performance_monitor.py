from performance_alerts import evaluate_performance

def fetch_current_balances():
    """
    Récupère les soldes actuels des sous-comptes.
    À remplacer par appels API réels ou lecture fichiers.
    """
    # Exemple statique pour test
    return {
        "trading": 10000,
        "securite": 15000,
        "impots": 3000
    }

def main():
    current_balances = fetch_current_balances()
    evaluate_performance(current_balances)

if __name__ == "__main__":
    main()