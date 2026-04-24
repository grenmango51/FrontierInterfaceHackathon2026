# EmotiBit Auto-Transfer Plan

## Goal
When the EmotiBit and the user's computer end up on the same network (home WiFi, phone hotspot, etc.), automatically:
1. Detect the EmotiBit on the network
2. Pull the day's recorded raw data files from the EmotiBit SD card via FTP
3. Run the EmotiBit DataParser on the downloaded files
4. Store parsed data in a known location

## Assumptions
- EmotiBit hardware is **ESP32 Feather Huzzah** (required for onboard FTP server)
- EmotiBit firmware is stock (supports FTP mode via `F` command on serial, but we will rely on auto-enabling FTP at boot if possible — see Step 2)
- EmotiBit Oscilloscope and DataParser are installed at default Windows paths:
  - Oscilloscope: `C:\Program Files\EmotiBit\EmotiBit Oscilloscope\`
  - DataParser: `C:\Program Files\EmotiBit\EmotiBit DataParser\EmotiBitDataParser.exe`
- Python 3.9+ is installed
- User accepts that EmotiBit must be in **FTP mode** for this to work. FTP mode is triggered by either:
  - Plugging into USB and sending `F` via Serial Monitor, OR
  - A future firmware that auto-enters FTP when idle (not currently default)

## Output Location
Save all downloaded + parsed files to:
```
D:\Hoai Anh\Aalto\Hobbies\FrontierInterface\emotibit_data\YYYY-MM-DD\
```

---

## Build Steps for Sonnet

### Step 1: Project Scaffold
Create this folder structure in `D:\Hoai Anh\Aalto\Hobbies\FrontierInterface\`:
```
emotibit_auto/
  config.json         # Stores EmotiBit IP, FTP creds, output dir
  discover.py         # Find EmotiBit on local network
  transfer.py         # FTP download logic
  parse.py            # Run DataParser on downloaded files
  watcher.py          # Main loop: detect → transfer → parse
  requirements.txt    # python-ftplib (stdlib), requests, scapy (optional)
  README.md
```

### Step 2: `config.json`
```json
{
  "ftp_user": "ftp",
  "ftp_password": "ftp",
  "ftp_port": 21,
  "output_dir": "D:/Hoai Anh/Aalto/Hobbies/FrontierInterface/emotibit_data",
  "data_parser_path": "C:/Program Files/EmotiBit/EmotiBit DataParser/EmotiBitDataParser.exe",
  "scan_interval_seconds": 30,
  "known_emotibit_ip": null,
  "subnet_scan_range": "192.168.1.0/24"
}
```

### Step 3: `discover.py`
Write a function `find_emotibit()` that:
- Reads `subnet_scan_range` from config
- Pings each IP in the range with a short timeout (use `concurrent.futures` for parallelism)
- For each reachable IP, attempts an FTP connection on port 21 with `ftp`/`ftp` credentials
- Returns the IP of the first host that successfully authenticates (that's the EmotiBit)
- Returns `None` if no EmotiBit found
- Caches the result to `config.json` under `known_emotibit_ip` for faster subsequent scans

### Step 4: `transfer.py`
Write a function `download_new_files(ip, output_subdir)` that:
- Connects via FTP using credentials from config
- Lists all files in the EmotiBit's root directory
- Filters for `.csv` files (raw data) and matching `_info.json` files
- Downloads only files **not already present** in `output_subdir` (check by filename)
- Uses binary mode (`retrbinary`)
- Returns a list of newly downloaded `.csv` file paths
- Logs progress to console

### Step 5: `parse.py`
Write a function `parse_files(csv_paths)` that:
- For each `.csv` path, runs:
  ```
  subprocess.run([data_parser_path, csv_path], check=True)
  ```
- The DataParser writes parsed output files next to the raw csv automatically
- Logs success/failure per file
- Returns list of successfully parsed files

### Step 6: `watcher.py` (main entry point)
Main loop:
```python
while True:
    ip = find_emotibit()
    if ip:
        today_dir = Path(output_dir) / datetime.now().strftime("%Y-%m-%d")
        today_dir.mkdir(parents=True, exist_ok=True)
        new_files = download_new_files(ip, today_dir)
        if new_files:
            parse_files(new_files)
            print(f"Transferred and parsed {len(new_files)} files")
    time.sleep(scan_interval_seconds)
```
- Runs forever until Ctrl+C
- On startup, tries `known_emotibit_ip` first before scanning the subnet
- Gracefully handles network errors (EmotiBit not reachable, FTP timeout, etc.)

### Step 7: `requirements.txt`
```
# All stdlib — no external deps strictly required
# Optional for faster scanning:
# scapy
```

### Step 8: `README.md`
Document:
- How to put EmotiBit in FTP mode (plug into USB, send `F` via Arduino Serial Monitor at baud 2000000, no line ending)
- How to configure `subnet_scan_range` to match the user's network
- How to run: `python watcher.py`
- Expected output structure

---

## Testing Checklist
1. Verify DataParser path exists on user's system
2. Verify Python and `ftplib` work (stdlib, should always work)
3. Test `discover.py` alone on a known network
4. Manually put EmotiBit in FTP mode and confirm FileZilla can connect (sanity check)
5. Run `watcher.py` end-to-end with a short test recording

## Known Limitations
- EmotiBit must be **manually put into FTP mode** (USB + serial `F` command). This is a firmware limitation.
- FTP mode disables normal recording — user must reset EmotiBit to resume recording.
- Subnet scanning takes 10-30 seconds depending on range; caching the IP helps.
- If the user's network uses DHCP and EmotiBit's IP changes, cache will miss once and re-scan.

## Future Improvements (not in scope for v1)
- Custom firmware that auto-enables FTP on charging detect
- mDNS/Bonjour discovery instead of subnet ping
- Cloud upload after parse (S3, Google Drive)
- Desktop notification on successful transfer
