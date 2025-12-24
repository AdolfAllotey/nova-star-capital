import os
import sys

# ✅ Correction : ajout du dossier racine dans les chemins d'import Python
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import glob
import base64
import io
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app_config.config_loader import load_config
from backtester import fetch_ohlcv
from backtester.run_backtest import run_backtest
from backtester.momentum_strategy import backtest_momentum_strategy
from backtester.rsi_strategy import backtest_rsi_strategy
from backtester.macd_strategy import backtest_macd_strategy
from backtester.export_results_to_csv import append_to_historique
from analytics.strategy_analyzer import analyze_strategy_performance, get_best_strategies
from analytics.best_strategy_selector import best_strategy_per_token
from social.telegram_scraper import extract_tokens_from_csv
from social.reddit_scraper import extract_reddit_tokens
from utils.utils_volume import get_token_volume
from social.social_score import compute_social_score

st.set_page_config(layout="wide")

if "filtered_tokens" not in st.session_state:
    st.session_state.filtered_tokens = []

st.title("📊 Tableau de bord Crypto Bot")
st.sidebar.title("⚙️ Menu principal")

strategies = ["ema", "rsi", "macd", "shitcoin", "momentum", "telegram", "reddit"]

def get_latest_result_csv(prefix):
    pattern = f"data/results/{prefix}_*.csv"
    files = glob.glob(pattern)
    return max(files, key=os.path.getctime) if files else None

def plot_cumulative_returns(df):
    if "timestamp" not in df.columns or "return_pct" not in df.columns:
        st.warning("⚠️ Données incomplètes pour le graphique.")
        return
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['cumulative_return'] = (1 + df['return_pct'] / 100).cumprod()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df['timestamp'], df['cumulative_return'], linewidth=2)
    ax.set_title("📈 Rendement cumulé")
    ax.set_xlabel("Date")
    ax.set_ylabel("Multiplicateur")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    st.pyplot(fig)

def display_latest_results(prefix, label):
    file = get_latest_result_csv(prefix)
    if not file:
        st.warning(f"Aucun fichier trouvé pour {label}.")
        return
    df = pd.read_csv(file)
    st.subheader(f"📊 Résultats {label}")
    if "return_pct" not in df.columns:
        st.warning("'return_pct' manquant.")
        st.dataframe(df.tail(20))
    else:
        st.dataframe(df)
        plot_cumulative_returns(df)

def download_latest_pdf():
    pdfs = sorted(glob.glob("data/reports/*.pdf"), key=os.path.getctime, reverse=True)
    if pdfs:
        with open(pdfs[0], "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            href = f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(pdfs[0])}">📄 Télécharger le rapport PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

# === Tabs Streamlit ===
tabs = st.tabs([
    "📨 Telegram", 
    "👽 Reddit", 
    "🧠 Comparatif", 
    "⚙️ Backtest manuel", 
    "📂 Historique", 
    "🤖 Résultats Auto-Trading"
])

with tabs[0]:
    display_latest_results("telegram_shitcoin", "Telegram (shitcoin)")

with tabs[1]:
    display_latest_results("reddit_shitcoin", "Reddit (shitcoin)")

with tabs[2]:
    telegram = get_latest_result_csv("telegram_shitcoin")
    reddit = get_latest_result_csv("reddit_shitcoin")

    dfs = []
    for source, file in [("Telegram", telegram), ("Reddit", reddit)]:
        if file:
            df = pd.read_csv(file)
            if "return_pct" in df.columns:
                df["source"] = source
                dfs.append(df)

    if dfs:
        combined = pd.concat(dfs)
        st.subheader("📊 Comparatif des performances")
        st.dataframe(combined[["timestamp", "return_pct", "source"]].tail(50))
        fig, ax = plt.subplots(figsize=(10, 4))
        for source, group in combined.groupby("source"):
            group = group.copy()
            group["timestamp"] = pd.to_datetime(group["timestamp"])
            group["cumulative_return"] = (1 + group["return_pct"] / 100).cumprod()
            ax.plot(group["timestamp"], group["cumulative_return"], label=source)
        ax.set_title("📈 Rendement cumulé comparé")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig)
    else:
        st.warning("Aucune donnée valide pour la comparaison.")

with tabs[3]:
    st.sidebar.subheader("🎯 Backtest manuel")
    strategy = st.sidebar.selectbox("Stratégie", strategies)
    symbol = st.sidebar.text_input("Symbole (ex: BTC/USDT ou PEPE_KU)", "BTC/USDT")
    timeframe = st.sidebar.selectbox("Timeframe", ["1h", "4h", "1d"])
    start_date = st.sidebar.date_input("Date de début")
    end_date = st.sidebar.date_input("Date de fin")

    if strategy == "momentum":
        window = st.sidebar.number_input("Window (n bougies)", min_value=1, value=3)
        threshold = st.sidebar.number_input("Seuil variation (%)", min_value=0.1, value=10.0)

    if st.sidebar.button("⚙️ Lancer le backtest"):
        config = load_config()
        config.update({
            "strategy": strategy,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": str(start_date),
            "end_date": str(end_date),
        })

        if strategy == "momentum":
            config["momentum_window"] = window
            config["momentum_threshold_pct"] = threshold

        st.write("📌 Configuration utilisée :", config)

        try:
            df = fetch_ohlcv(config)

            if df is None or df.empty:
                st.error("❌ Aucune donnée OHLCV récupérée.")
            else:
                st.write("🧾 Données OHLCV chargées :", df.head())

                if strategy == "momentum":
                    results, df = backtest_momentum_strategy(df, config)
                elif strategy == "rsi":
                    results, df = backtest_rsi_strategy(df, config)
                elif strategy == "macd":
                    results, df = backtest_macd_strategy(df, config)
                else:
                    results, df = run_backtest(df, config)

                st.success(f"✅ Résultat : {results['total_return_%']}% | Trades : {results['nb_trades']} | Win rate : {results['win_rate_%']}%")

                if "return_pct" in df.columns:
                    st.write(df.head())
                    plot_cumulative_returns(df)

                symbol_name = symbol.replace("/", "").replace("_KU", "")
                filename = f"data/results/manual_{symbol_name}_{strategy}_{timeframe}_{start_date}_{end_date}.csv"
                os.makedirs("data/results", exist_ok=True)
                df.to_csv(filename, index=False)
                st.success(f"📤 Résultat sauvegardé dans : {filename}")

                append_to_historique({
                    "source": "Manuel",
                    "strategy": strategy,
                    "token": symbol,
                    "timeframe": timeframe,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "return_pct": results["total_return_%"],
                    "nb_trades": results["nb_trades"],
                    "win_rate_pct": results["win_rate_%"]
                })
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

    st.sidebar.markdown("---")
    if st.sidebar.button("📥 Télécharger le rapport PDF"):
        download_latest_pdf()


def highlight_return(val):
    if val > 0:
        return 'background-color: #d4edda; color: black'  # vert
    elif val < 0:
        return 'background-color: #f8d7da; color: black'  # rouge
    return ''

with tabs[4]:
    st.subheader("📈 Analyse des stratégies (auto-apprentissage)")
    stats = analyze_strategy_performance()
    if "error" in stats:
        st.warning(stats["error"])
    else:
        df_stats = pd.DataFrame.from_dict(stats, orient="index")
        st.dataframe(df_stats)
        best_strats = get_best_strategies(stats, top_n=3)
        st.success("🏆 Meilleures stratégies :")
        for name, data in best_strats:
            st.write(f"🔹 {name.upper()} ➜ {data['avg_return_pct']}% moyen | Win rate : {data['win_rate_pct']}%")

    st.header("📂 Historique des backtests")
    path = "data/historique/historique_backtests.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date_backtest"])
        sources = st.multiselect("Filtrer par source", sorted(df["source"].unique()), default=list(df["source"].unique()))
        strategies_sel = st.multiselect("Stratégies", sorted(df["strategy"].unique()), default=list(df["strategy"].unique()))
        filtered = df[df["source"].isin(sources) & df["strategy"].isin(strategies_sel)]
        styled_df = filtered.sort_values("date_backtest", ascending=False).style.applymap(highlight_return, subset=["return_pct"])
        st.dataframe(styled_df)
        
        try:
            filtered = filtered.sort_values("date_backtest")
            fig, ax = plt.subplots(figsize=(10, 4))

            for strategy_name, group in filtered.groupby("strategy"):
                group = group.copy()
                group["cumulative_return"] = (1 + group["return_pct"] / 100).cumprod()
                ax.plot(group["date_backtest"], group["cumulative_return"], label=strategy_name)

            ax.set_title("📊 Rendement cumulé par stratégie")
            ax.set_xlabel("Date")
            ax.set_ylabel("Multiplicateur")
            ax.legend()
            fig.autofmt_xdate()
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"Graphique comparatif indisponible : {e}")

    # ✅ Ajoute ceci maintenant :
    with open(path, "rb") as f:
        st.download_button("📥 Télécharger le CSV", f, file_name="historique_backtests.csv")

# ✅ Initialisation des variables nécessaires
token_strategies = {}
batch_results = []  # ✅ Ajout requis pour éviter l'erreur NameError

# ⬇️ Ce qui suit reste tel quel
if token_strategies:
    st.subheader("🧠 Stratégies appliquées par token")
    for token in st.session_state.filtered_tokens:
        strat = token_strategies.get(token, strategy)
        st.write(f"🪙 {token} ➜ {strat.upper()}")

total_allocated = sum([r.get("capital_allocated", 0) for r in batch_results])
total_pnl = sum([r.get("pnl_usd", 0) for r in batch_results])
total_return_pct = (total_pnl / total_allocated * 100) if total_allocated else 0

st.subheader("📈 Résumé global de la simulation")
st.write(f"💸 Capital total investi : ${total_allocated:,.2f}")
st.write(f"📊 PnL global : ${total_pnl:,.2f}")
st.write(f"📈 Rendement global : {total_return_pct:.2f}%")

# ✅ Bloc de téléchargement du CSV historique
path = "data/historique/historique_backtests.csv"
if os.path.exists(path):
    with open(path, "rb") as f:
        st.download_button("📥 Télécharger le CSV", f, file_name="historique_backtests.csv", key="download_historique")
else:
    st.warning("Aucun historique trouvé.")

with tabs[5]:
    # filtered_tokens is now managed by st.session_state
    # 🚀 Simulation MACD par lot
    st.subheader("🧪 Simulation MACD par lot")

    from trading.simulate_strategy import simulate_strategy_on_token
    from auto_trading.batch_simulator import simulate_batch

    if st.session_state.filtered_tokens and st.button("🚀 Lancer la simulation MACD par lot"):
        with st.spinner("Simulation en cours..."):
            batch_results = simulate_batch(st.session_state.filtered_tokens, simulate_macd_on_token, batch_size=3)

        st.success("✅ Simulation terminée")
for result in batch_results:
    if result["status"] == "ok":
        st.write(f"🪙 {result['token']} ➜ {result['return_pct']}% | {result['nb_trades']} trade(s)")

        append_to_historique({
            "source": "Auto-Trading",
            "strategy": strategy,
            "token": result["token"],
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-05-01",
            "date_backtest": datetime.now().strftime("%Y-%m-%d"),
            "return_pct": result["return_pct"],
            "nb_trades": result["nb_trades"],
            "capital_allocated": capital_per_token,
            "pnl_usd": round(capital_per_token * result["return_pct"] / 100, 2),
            "win_rate_pct": 0
        })

    elif result["status"] == "no_trades":
        st.warning(f"❌ {result['token']} : aucun trade exécuté")

    else:
        st.error(f"⚠️ {result['token']} : erreur - {result.get('error', 'inconnue')}")


import io

if batch_results:
    df_export = pd.DataFrame(batch_results)
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)

    
if token_strategies:
    st.subheader("🧠 Stratégies appliquées par token")
    for token in st.session_state.filtered_tokens:
        strat = token_strategies.get(token, strategy)
        st.write(f"🪙 {token} ➜ {strat.upper()}")

total_allocated = sum([r.get("capital_allocated", 0) for r in batch_results])
total_pnl = sum([r.get("pnl_usd", 0) for r in batch_results])
total_return_pct = (total_pnl / total_allocated * 100) if total_allocated else 0

st.subheader("📈 Résumé global de la simulation")
st.write(f"💸 Capital total investi : ${total_allocated:,.2f}")
st.write(f"📊 PnL global : ${total_pnl:,.2f}")
st.write(f"📈 Rendement global : {total_return_pct:.2f}%")

# ✅ Téléchargement du CSV des résultats
if batch_results:
    import io
    df_export = pd.DataFrame(batch_results)
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)

    st.download_button(
        label="📥 Télécharger le CSV des résultats",
        data=csv_buffer.getvalue(),
        file_name="resultats_auto_trading_batch.csv",
        mime="text/csv"
    )

    if st.button("Lancer le filtrage avec progression"):
        st.session_state.filtered_tokens = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        total = len(tokens_detectes)

        for i, token in enumerate(scored_tokens):
            symbol = f"{token}/USDT"
            volume = get_token_volume(symbol)
            status_text.text(f"⏳ Vérification de {symbol} : {volume:,.2f} USD")

            if volume >= min_volume:
                st.session_state.filtered_tokens.append(token)

            progress_bar.progress((i + 1) / total)

        


st.subheader("🚀 Simulation par lot")
strategy = st.selectbox("Stratégie à utiliser", ["macd", "rsi", "ema", "momentum"])
auto_mode = st.checkbox("🧠 Utiliser la meilleure stratégie automatiquement")

if auto_mode:
    stats = analyze_strategy_performance()
    best = get_best_strategies(stats, top_n=1)
    if best:
        strategy = best[0][0]
        st.info(f"💡 Stratégie sélectionnée automatiquement : {strategy.upper()}")

stop_loss_pct = st.number_input("🔒 Stop Loss (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
trailing_stop_pct = st.number_input("📉 Trailing Stop (%)", min_value=0.0, max_value=50.0, value=0.0, step=0.5)

if st.session_state.filtered_tokens:
    lancer = st.button("Lancer la simulation MACD par lot")
    if lancer:
        with st.spinner("Simulation en cours..."):
            st.subheader("💰 Gestion du capital simulé")
            total_capital = st.number_input("Capital virtuel total ($)", min_value=1000, max_value=100000, value=10000, step=500)
            capital_per_token = total_capital / len(st.session_state.filtered_tokens) if st.session_state.filtered_tokens else 0

            batch_results = []

            token_strategies = {}
            if auto_mode:
                token_strategies = best_strategy_per_token()

if st.session_state.filtered_tokens:
    lancer = st.button("Lancer la simulation MACD par lot")
    if lancer:
        with st.spinner("Simulation en cours..."):
            st.subheader("💰 Gestion du capital simulé")
            total_capital = st.number_input(
                "Capital virtuel total ($)", 
                min_value=1000, 
                max_value=100000, 
                value=10000, 
                step=500
            )
            capital_per_token = total_capital / len(st.session_state.filtered_tokens) if st.session_state.filtered_tokens else 0

            batch_results = []
            token_strategies = best_strategy_per_token() if auto_mode else {}

            # Chargement des données historiques
            historique_data = []
            try:
                hist_df = pd.read_csv("data/historique/historique_backtests.csv")
                historique_data = hist_df.to_dict(orient="records")
            except:
                pass

            st.info("💡 Stratégies optimales appliquées par token (auto-learning)")
            total = len(st.session_state.filtered_tokens)
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, token in enumerate(st.session_state.filtered_tokens):
                status_text.text(f"⏳ Traitement de {token} ({i+1}/{total})")
                try:
                    strat = token_strategies.get(token, strategy)

                    # Vérification des performances historiques
                    token_history = [
                        row for row in historique_data
                        if row["token"] == token and row["strategy"] == strat
                    ]

                    avg_return = sum([row["return_pct"] for row in token_history]) / len(token_history) if token_history else 0
                    win_rate = sum([1 for row in token_history if row["return_pct"] > 0]) / len(token_history) * 100 if token_history else 0

                    if avg_return < 0 or win_rate < 40:
                        st.warning(f"⛔ {token} ignoré : {strat.upper()} → return moyen = {avg_return:.2f}%, win rate = {win_rate:.1f}%")
                        continue

                    result = simulate_strategy_on_token(
                        token,
                        strat,
                        stop_loss_pct=stop_loss_pct,
                        trailing_stop_pct=trailing_stop_pct
                    )
                    batch_results.append(result)

                except Exception as e:
                    batch_results.append({
                        "token": token,
                        "status": "error",
                        "error": str(e),
                        "return_pct": 0,
                        "nb_trades": 0
                    })

                progress_bar.progress((i + 1) / total)

            st.success("✅ Simulation terminée")

        for result in batch_results:
            if result["status"] == "ok":
                st.write(f"🪙 {result['token']} ➜ {result['return_pct']}% | {result['nb_trades']} trade(s)")

        st.success("✅ Simulation terminée")
for result in batch_results:
    if result["status"] == "ok":
        st.write(f"🪙 {result['token']} ➜ {result['return_pct']}% | {result['nb_trades']} trade(s)")

        append_to_historique({
            "source": "Auto-Trading",
            "strategy": strategy,
            "token": result["token"],
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-05-01",
            "date_backtest": datetime.now().strftime("%Y-%m-%d"),
            "return_pct": result["return_pct"],
            "nb_trades": result["nb_trades"],
            "capital_allocated": capital_per_token,
            "pnl_usd": round(capital_per_token * result["return_pct"] / 100, 2),
            "win_rate_pct": 0
        })

    elif result["status"] == "no_trades":
        st.warning(f"❌ {result['token']} : aucun trade exécuté")

    else:
        st.error(f"⚠️ {result['token']} : erreur - {result.get('error', 'inconnue')}")

if batch_results:
    df_export = pd.DataFrame(batch_results)
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)

if token_strategies:
    st.subheader("🧠 Stratégies appliquées par token")
    for token in st.session_state.filtered_tokens:
        strat = token_strategies.get(token, strategy)
        st.write(f"🪙 {token} ➜ {strat.upper()}")

total_allocated = sum([r.get("capital_allocated", 0) for r in batch_results])
total_pnl = sum([r.get("pnl_usd", 0) for r in batch_results])
total_return_pct = (total_pnl / total_allocated * 100) if total_allocated else 0

st.subheader("📈 Résumé global de la simulation")
st.write(f"💸 Capital total investi : ${total_allocated:,.2f}")
st.write(f"📊 PnL global : ${total_pnl:,.2f}")
st.write(f"📈 Rendement global : {total_return_pct:.2f}%")

import io

if batch_results:
    df_export = pd.DataFrame(batch_results)
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)

    # ✅ Bouton de téléchargement (correctement indenté et syntaxiquement juste)
    st.download_button(
        label="📥 Télécharger le CSV des résultats",
        data=csv_buffer.getvalue(),
        file_name="resultats_auto_trading_batch.csv",
        mime="text/csv"
    )

    st.success(f"✅ {len(st.session_state.filtered_tokens)} token(s) retenu(s) :")
    st.write(st.session_state.filtered_tokens)

# === Résultats auto-trading ===
auto_dir = "data/auto_trading"
files = sorted(glob.glob(os.path.join(auto_dir, "auto_macd_*.csv")), key=os.path.getctime, reverse=True)

if not files:
    st.info("Aucun résultat d’auto-trading MACD trouvé.")
else:
    selected_file = st.selectbox("📄 Fichier de résultats", files)
    df = pd.read_csv(selected_file, parse_dates=["entry_time", "exit_time"])

    st.subheader("📈 Détails des trades exécutés")
    st.dataframe(df)

    try:
        df["cumulative_return"] = (1 + df["return_pct"] / 100).cumprod()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df["exit_time"], df["cumulative_return"], marker='o')
        ax.set_title("📊 Rendement cumulé Auto-Trading (MACD)")
        ax.set_xlabel("Date de sortie")
        ax.set_ylabel("Multiplicateur")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Erreur graphique : {e}")