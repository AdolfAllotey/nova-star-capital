import numpy as np

class DynamicStopLoss:
    def __init__(self, price_history, min_stop_pct=0.10, lookback=20, vol_multiplier=1.5, method='historical'):
        """
        price_history : liste ou np.array des prix historiques (chronologiques)
        min_stop_pct : stop loss minimal (ex 10%)
        lookback : nombre de jours pour calculer volatilité
        vol_multiplier : facteur multiplicateur sur la volatilité
        method : 'historical' (écart-type simple) ou 'ewma' (volatilité exponentielle)
        """
        self.price_history = np.array(price_history)
        self.min_stop_pct = min_stop_pct
        self.lookback = lookback
        self.vol_multiplier = vol_multiplier
        self.method = method

    def calculate_volatility(self):
        if len(self.price_history) < self.lookback + 1:
            print("⚠️ Pas assez de données pour calculer la volatilité.")
            return 0.0
        returns = np.diff(np.log(self.price_history[-(self.lookback+1):]))
        if self.method == 'ewma':
            # EWMA volatility
            lambda_ = 0.94
            squared_returns = returns**2
            ewma_var = np.zeros_like(squared_returns)
            ewma_var[0] = squared_returns[0]
            for t in range(1, len(squared_returns)):
                ewma_var[t] = lambda_ * ewma_var[t-1] + (1 - lambda_) * squared_returns[t]
            volatility = np.sqrt(ewma_var[-1])
        else:
            # Historical volatility
            volatility = np.std(returns)
        print(f"Volatilité ({self.method}) calculée : {volatility:.5f}")
        return volatility

    def calculate_stop_loss(self):
        volatility = self.calculate_volatility()
        adjusted_vol = volatility * self.vol_multiplier
        stop_pct = max(self.min_stop_pct, adjusted_vol)
        current_price = self.price_history[-1]
        trailing_stop = current_price * (1 - stop_pct)
        print(f"Stop loss dynamique calculé : {trailing_stop:.4f} (stop_pct={stop_pct:.4f})")
        return trailing_stop

    def should_sell(self, current_price, trailing_stop):
        decision = current_price < trailing_stop
        print(f"Prix actuel: {current_price}, Stop loss: {trailing_stop}, Vente recommandée: {decision}")
        return decision

if __name__ == "__main__":
    prices = [100, 102, 105, 103, 107, 110, 108, 107, 111, 115, 113, 112, 110, 108, 109, 111, 114, 115, 116, 118, 117]
    dsl = DynamicStopLoss(prices, min_stop_pct=0.1, lookback=10, vol_multiplier=1.5, method='ewma')
    stop = dsl.calculate_stop_loss()
    current = prices[-1]
    if dsl.should_sell(current, stop):
        print("➡️ Vente recommandée")
    else:
        print("➡️ Maintenir la position")