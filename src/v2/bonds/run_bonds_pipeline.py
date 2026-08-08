from src.v2.bonds.rate_engine import run_rate_engine
from src.v2.bonds.inflation_engine import run_inflation_engine
from src.v2.bonds.yield_curve_engine import run_yield_curve_engine
from src.v2.bonds.recession_detector import run_recession_detector
from src.v2.bonds.credit_spread_engine import run_credit_spread_engine
from src.v2.bonds.liquidity_engine import run_liquidity_engine
from src.v2.bonds.bond_volatility_engine import run_bond_volatility_engine
from src.v2.bonds.duration_engine import run_duration_engine
from src.v2.bonds.bond_signal_engine import run_bond_signal_engine
from src.v2.bonds.bond_portfolio_adapter import export_bond_signal_to_portfolio_input
from src.v2.bonds.bond_state_updater import main as update_bond_state

try:
    from src.v2.utils.logger import get_logger
    logger = get_logger("bonds_pipeline")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bonds_pipeline")


DATA_DIR = "/opt/nsc/data/preprod/bonds"
PORTFOLIO_INPUT_DIR = "/opt/nsc/data/preprod/portfolio/inputs"


def run_bonds_pipeline():
    try:
        logger.info("Starting bonds pipeline")
        input_path = f"{DATA_DIR}/macro_inputs.json"

        logger.info("Running rate_engine")
        run_rate_engine(input_path, f"{DATA_DIR}/rate_signal.json")

        logger.info("Running inflation_engine")
        run_inflation_engine(input_path, f"{DATA_DIR}/inflation_signal.json")

        logger.info("Running yield_curve_engine")
        run_yield_curve_engine(input_path, f"{DATA_DIR}/curve_signal.json")

        logger.info("Running recession_detector")
        run_recession_detector(input_path, f"{DATA_DIR}/recession_signal.json")

        logger.info("Running credit_spread_engine")
        run_credit_spread_engine(input_path, f"{DATA_DIR}/credit_signal.json")

        logger.info("Running liquidity_engine")
        run_liquidity_engine(input_path, f"{DATA_DIR}/liquidity_signal.json")

        logger.info("Running bond_volatility_engine")
        run_bond_volatility_engine(input_path, f"{DATA_DIR}/bond_vol_signal.json")

        logger.info("Running duration_engine")
        run_duration_engine(
            f"{DATA_DIR}/rate_signal.json",
            f"{DATA_DIR}/inflation_signal.json",
            f"{DATA_DIR}/bond_vol_signal.json",
            f"{DATA_DIR}/duration_signal.json",
        )

        logger.info("Running bond_signal_engine")
        result = run_bond_signal_engine(DATA_DIR, f"{DATA_DIR}/bond_signal.json")

        logger.info("Exporting bond signal to portfolio input")
        portfolio_payload = export_bond_signal_to_portfolio_input(
            f"{DATA_DIR}/bond_signal.json",
            f"{PORTFOLIO_INPUT_DIR}/bonds_portfolio_input.json"
        )

        logger.info("Updating bonds state")
        update_bond_state()

        logger.info("Bonds pipeline completed successfully")
        logger.info(f"Final bond signal: {result}")
        logger.info(f"Portfolio payload: {portfolio_payload}")
        return result

    except Exception as e:
        logger.exception(f"Bonds pipeline failed: {e}")
        raise


if __name__ == "__main__":
    result = run_bonds_pipeline()
    print(result)
