
from wallet_manager import WalletManager

def test_wallet_behavior():
    wm = WalletManager(starting_balance=10000)

    print(wm.status())

    # Trade avec gain de 100€
    wm.record_trade_result(100)
    print("\nAprès gain de 100€:")
    print(wm.status())

    # Trade avec perte de 50€
    wm.record_trade_result(-50)
    print("\nAprès perte de 50€:")
    print(wm.status())

    # Simuler une hausse du solde global pour test SAFU
    wm.global_balance = 21000
    wm.record_trade_result(0)
    print("\nAprès franchissement des 20000€:")
    print(wm.status())

if __name__ == '__main__':
    test_wallet_behavior()
