# src/v2/integrations/ibkr_investor.py

import os
import datetime
from ib_insync import IB, Stock, MarketOrder
from src.utils.telegram_bot import send_telegram_message

# Configuration Interactive Brokers
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", "7497"))  # Port TWS ou IB Gateway
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "1"))

# ETF à acheter (nom IBKR + quantité ou pourcentage du capital à investir)
TARGET_ETF = [
    {"symbol": "SPY", "exchange": "ARCA", "currency": "USD", "amount": 1000},
    {"symbol": "QQQ", "exchange": "ARCA", "currency": "USD", "amount": 500},
]

def invest_ibkr():
    ib = IB()
    try:
        ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
    except Exception as e:
        send_telegram_message(f"❌ Connexion à IBKR échouée : {e}")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    report_lines = [f"📈 **Investissements IBKR - {today}**\n"]

    for etf in TARGET_ETF:
        contract = Stock(etf["symbol"], etf["exchange"], etf["currency"])
        ib.qualifyContracts(contract)

        # Récupération du prix de marché
        market_data = ib.reqMktData(contract, "", False, False)
        ib.sleep(2)
        price = market_data.last if market_data.last else market_data.close

        if price is None or price == 0:
            report_lines.append(f"❌ Impossible d'obtenir le prix de {etf['symbol']}")
            continue

        quantity = int(etf["amount"] // price)
        if quantity < 1:
            report_lines.append(f"⚠️ Montant trop faible pour {etf['symbol']}")
            continue

        order = MarketOrder("BUY", quantity)
        trade = ib.placeOrder(contract, order)
        ib.sleep(3)

        report_lines.append(f"✅ Ordre passé : {etf['symbol']} x{quantity} à ~{price:.2f} USD")

    ib.disconnect()
    send_telegram_message("\n".join(report_lines))

if __name__ == "__main__":
    invest_ibkr()