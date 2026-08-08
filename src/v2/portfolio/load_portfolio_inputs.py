import glob
import json


def load_portfolio_inputs(input_dir: str):
    files = sorted(glob.glob(f"{input_dir}/*_portfolio_input.json"))
    payloads = []

    for path in files:
        try:
            with open(path, "r") as f:
                payloads.append(json.load(f))
        except Exception:
            continue

    return payloads


if __name__ == "__main__":
    data = load_portfolio_inputs("/opt/nsc/data/preprod/portfolio/inputs")
    print(json.dumps(data, indent=2))
