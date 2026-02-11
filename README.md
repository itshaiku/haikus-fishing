# Haiku Fishing

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/87HgYm2APJ)

Haiku Fishing is a open-source Windows macro for Grand Piece Online that automates the fishing minigame and common prep/recovery actions.

## Download

**Download (latest release): [HaikuFishing_v2.1.0.exe](https://github.com/itshaiku/haikus-fishing/releases/download/v2.1.0/HaikuFishing_v2.1.0.exe)**

[View all releases](https://github.com/itshaiku/haikus-fishing/releases)

**Steps:**
1. Click the download link above
2. Run `HaikuFishing_v2.1.0.exe`

If the UI does not open, install Microsoft Edge WebView2 Runtime:
https://developer.microsoft.com/microsoft-edge/webview2/

## Features

- PD-style control for fishing minigame input
- Auto-buy/select bait and other pre-cast helpers
- OCR-based devil fruit detection (EasyOCR)
- Watchdog + auto-recovery
- Discord webhook notifications
- Live session stats overlay

## Quick start

1. Press `F2` and place/resize the fishing area box over the minigame bar
2. Set the water/cast point in the Controls tab
3. Press `F1` to start/stop

## Troubleshooting

- UI does not open: install WebView2 Runtime (link above), then try again
- OCR not working: run `HaikuFishing_v2.1.0.exe --ocr-selftest` and check the output
- Macro won't start: try running as Administrator and verify the area box + water point

## Run from source

Prereqs: Python 3.9–3.13

```bash
pip install -r requirements.txt
python src\main.py
```

## Support

Discord: https://discord.gg/87HgYm2APJ
