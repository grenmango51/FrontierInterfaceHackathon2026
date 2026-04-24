import ftplib
import ipaddress
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_known_ip(ip):
    config = load_config()
    config["known_emotibit_ip"] = ip
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _is_reachable(ip: str, timeout: float = 0.5) -> bool:
    """Ping a single IP; returns True if it responds."""
    flag = "-n" if sys.platform == "win32" else "-c"
    result = subprocess.run(
        ["ping", flag, "1", "-w", str(int(timeout * 1000)) if sys.platform == "win32" else str(timeout), ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _try_ftp(ip: str, port: int, user: str, password: str, timeout: float = 3.0) -> bool:
    """Try to authenticate to FTP; returns True on success."""
    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, port, timeout=timeout)
        ftp.login(user, password)
        ftp.quit()
        return True
    except Exception:
        return False


def _check_host(ip: str, config: dict) -> str | None:
    if _is_reachable(ip) and _try_ftp(ip, config["ftp_port"], config["ftp_user"], config["ftp_password"]):
        return ip
    return None


def find_emotibit() -> str | None:
    config = load_config()

    # Try cached IP first
    cached = config.get("known_emotibit_ip")
    if cached:
        print(f"Trying cached IP {cached} ...")
        if _try_ftp(cached, config["ftp_port"], config["ftp_user"], config["ftp_password"]):
            print(f"EmotiBit found at cached IP {cached}")
            return cached
        print("Cached IP no longer responds, scanning subnet ...")
        save_known_ip(None)

    subnet = config["subnet_scan_range"]
    hosts = [str(ip) for ip in ipaddress.ip_network(subnet, strict=False).hosts()]
    print(f"Scanning {len(hosts)} hosts in {subnet} ...")

    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {executor.submit(_check_host, ip, config): ip for ip in hosts}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"EmotiBit found at {result}")
                save_known_ip(result)
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                return result

    print("No EmotiBit found on network.")
    return None


if __name__ == "__main__":
    ip = find_emotibit()
    if ip:
        print(f"EmotiBit IP: {ip}")
    else:
        print("EmotiBit not detected.")
