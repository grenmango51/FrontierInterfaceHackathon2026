import ftplib
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def download_new_files(ip: str, output_subdir: Path) -> list[Path]:
    config = load_config()
    output_subdir = Path(output_subdir)
    output_subdir.mkdir(parents=True, exist_ok=True)

    existing = {p.name for p in output_subdir.iterdir() if p.is_file()}
    downloaded = []

    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, config["ftp_port"], timeout=10)
        ftp.login(config["ftp_user"], config["ftp_password"])
        ftp.set_pasv(True)

        remote_files = ftp.nlst()
        print(f"Found {len(remote_files)} file(s) on EmotiBit.")

        # Download .csv files and matching _info.json files
        targets = [
            f for f in remote_files
            if (f.endswith(".csv") or f.endswith("_info.json")) and f not in existing
        ]

        if not targets:
            print("No new files to download.")
            ftp.quit()
            return []

        for filename in targets:
            dest = output_subdir / filename
            print(f"Downloading {filename} ...", end=" ", flush=True)
            with open(dest, "wb") as fh:
                ftp.retrbinary(f"RETR {filename}", fh.write)
            print("done")
            if filename.endswith(".csv"):
                downloaded.append(dest)

        ftp.quit()
    except ftplib.all_errors as e:
        print(f"FTP error: {e}")

    return downloaded
