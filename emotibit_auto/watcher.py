import json
import time
from datetime import datetime
from pathlib import Path

from discover import find_emotibit
from parse import parse_files
from transfer import download_new_files

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def main():
    print("EmotiBit Auto-Transfer watcher started. Press Ctrl+C to stop.\n")

    while True:
        config = load_config()
        output_dir = Path(config["output_dir"])
        interval = config["scan_interval_seconds"]

        try:
            ip = find_emotibit()
            if ip:
                today_dir = output_dir / datetime.now().strftime("%Y-%m-%d")
                today_dir.mkdir(parents=True, exist_ok=True)

                new_files = download_new_files(ip, today_dir)
                if new_files:
                    parsed = parse_files(new_files)
                    print(f"Transferred {len(new_files)} file(s), parsed {len(parsed)}.\n")
                    
                    # --- EmoMirror Hook ---
                    if parsed:
                        try:
                            from emomirror.hook import on_new_data
                            print("Triggering EmoMirror pipeline...")
                            on_new_data(today_dir, parsed)
                        except ImportError:
                            print("EmoMirror module not found. Skipping hook.")
                        except Exception as e:
                            print(f"EmoMirror hook failed: {e}")
                    # ----------------------
                else:
                    print("No new files this cycle.\n")
            else:
                print("EmotiBit not on network. Retrying in", interval, "seconds.\n")

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}\n")

        time.sleep(interval)


if __name__ == "__main__":
    main()
