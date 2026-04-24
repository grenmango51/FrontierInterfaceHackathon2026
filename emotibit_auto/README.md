# EmotiBit Auto-Transfer

Automatically detects your EmotiBit on the local network, downloads raw recordings via FTP, and runs EmotiBit DataParser on them.

## Prerequisites

- Python 3.9+
- EmotiBit ESP32 Feather Huzzah
- EmotiBit DataParser installed at `C:\Program Files\EmotiBit\EmotiBit DataParser\EmotiBitDataParser.exe`

## Putting EmotiBit in FTP Mode

1. Plug the EmotiBit into USB.
2. Open Arduino Serial Monitor (or any serial terminal).
3. Set baud rate to **2000000** and line ending to **No line ending**.
4. Send the character `F`.
5. The EmotiBit will enter FTP mode — normal recording is paused until you reset.

## Configuration

Edit `config.json` before first run:

| Key | Default | Description |
|-----|---------|-------------|
| `ftp_user` | `ftp` | FTP username (EmotiBit default) |
| `ftp_password` | `ftp` | FTP password (EmotiBit default) |
| `ftp_port` | `21` | FTP port |
| `output_dir` | see file | Where to save downloaded + parsed data |
| `data_parser_path` | see file | Path to `EmotiBitDataParser.exe` |
| `scan_interval_seconds` | `30` | How often to poll when EmotiBit is not found |
| `subnet_scan_range` | `192.168.1.0/24` | Change to match your network (e.g. `192.168.0.0/24`) |
| `known_emotibit_ip` | `null` | Auto-filled after first discovery; clear if IP changes |

To find your subnet, run `ipconfig` and look at the IPv4 address + subnet mask for your active adapter.

## Running

```
cd emotibit_auto
python watcher.py
```

The watcher loops forever. Press **Ctrl+C** to stop.

You can also run individual modules:

```
python discover.py   # scan network and print EmotiBit IP
```

## Output Structure

```
emotibit_data/
  YYYY-MM-DD/
    <recording>.csv          # raw EmotiBit data
    <recording>_info.json    # metadata
    <recording>_EA.csv       # parsed — EDA
    <recording>_HR.csv       # parsed — heart rate
    ... (other parsed streams)
```

Parsed files are written by EmotiBit DataParser next to the raw `.csv`.

## Troubleshooting

- **No EmotiBit found**: confirm FTP mode is active and `subnet_scan_range` matches your network.
- **DataParser not found**: verify the install path in `config.json`.
- **IP changes between sessions**: delete `known_emotibit_ip` from `config.json` (set to `null`) to force a fresh scan.
