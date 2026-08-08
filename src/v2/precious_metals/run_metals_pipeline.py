from src.v2.precious_metals.inflation_hedge_engine import (
    run_inflation_hedge_engine,
)
from src.v2.precious_metals.real_rate_engine import (
    run_real_rate_engine,
)
from src.v2.precious_metals.systemic_stress_engine import (
    run_systemic_stress_engine,
)
from src.v2.precious_metals.usd_engine import run_usd_engine
from src.v2.precious_metals.metals_signal_engine import (
    run_metals_signal_engine,
)
from src.v2.precious_metals.metals_portfolio_adapter import (
    export_metals_signal_to_portfolio_input,
)
from src.v2.precious_metals.metals_state_updater import (
    main as update_metals_state,
)
from src.v2.precious_metals.metals_utils import (
    load_and_validate_macro_inputs,
)

try:
    from src.v2.utils.logger import get_logger
    logger = get_logger("precious_metals_pipeline")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("precious_metals_pipeline")


DATA_DIR = "/opt/nsc/data/preprod/metals"
PORTFOLIO_INPUT_DIR = "/opt/nsc/data/preprod/portfolio/inputs"


def run_metals_pipeline():
    try:
        logger.info("Starting precious metals pipeline")
        input_path = f"{DATA_DIR}/macro_inputs.json"

        logger.info(
            "Validating precious-metals macro input contract"
        )
        load_and_validate_macro_inputs(input_path)

        logger.info("Running inflation_hedge_engine")
        run_inflation_hedge_engine(
            input_path,
            f"{DATA_DIR}/inflation_signal.json",
        )

        logger.info("Running real_rate_engine")
        run_real_rate_engine(
            input_path,
            f"{DATA_DIR}/real_rate_signal.json",
        )

        logger.info("Running systemic_stress_engine")
        run_systemic_stress_engine(
            input_path,
            f"{DATA_DIR}/systemic_stress_signal.json",
        )

        logger.info("Running usd_engine")
        run_usd_engine(
            input_path,
            f"{DATA_DIR}/usd_signal.json",
        )

        logger.info("Running metals_signal_engine")
        result = run_metals_signal_engine(
            DATA_DIR,
            f"{DATA_DIR}/metals_signal.json",
        )

        logger.info(
            "Exporting metals signal to portfolio input"
        )
        portfolio_payload = (
            export_metals_signal_to_portfolio_input(
                f"{DATA_DIR}/metals_signal.json",
                (
                    f"{PORTFOLIO_INPUT_DIR}/"
                    "precious_metals_portfolio_input.json"
                ),
            )
        )

        logger.info("Updating precious metals state")
        update_metals_state()

        logger.info(
            "Precious metals pipeline completed successfully"
        )
        logger.info(f"Final metals signal: {result}")
        logger.info(
            f"Portfolio payload: {portfolio_payload}"
        )

        return result

    except Exception as exc:
        logger.exception(
            f"Precious metals pipeline failed: {exc}"
        )
        raise


if __name__ == "__main__":
    result = run_metals_pipeline()
    print(result)
