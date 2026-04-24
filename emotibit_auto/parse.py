import json
import subprocess
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def parse_files(csv_paths: list[Path]) -> list[Path]:
    config = load_config()
    parser = Path(config["data_parser_path"])

    if not parser.exists():
        print(f"DataParser not found at: {parser}")
        print("Skipping parsing step. Download completed successfully.")
        return []

    parsed = []
    for csv_path in csv_paths:
        csv_path = Path(csv_path)
        print(f"Parsing {csv_path.name} ...", end=" ", flush=True)
        try:
            subprocess.run([str(parser), str(csv_path)], check=True)
            print("done")
            parsed.append(csv_path)
        except subprocess.CalledProcessError as e:
            print(f"FAILED (exit code {e.returncode})")
        except Exception as e:
            print(f"ERROR: {e}")

    return parsed
