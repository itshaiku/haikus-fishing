# Haiku Fishing

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/6bGw8HDuYV)

Haiku Fishing is a open-source Windows macro for Grand Piece Online that automates the fishing minigame and common prep/recovery actions.

## Download

Download (latest release):
[Download Haiku Fishing.exe][download-latest]

Release page:
[View latest release][releases-latest]

1. Download `Haiku Fishing.exe`
2. Run it

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
- OCR not working: run `Haiku Fishing.exe --ocr-selftest` and check the output
- Macro won't start: run as Administrator and verify the area box + water point

## Run from source

Prereqs: Python 3.9–3.13

```bash
pip install -r requirements.txt
python src\main.py
```

## Support

Discord: https://discord.gg/6bGw8HDuYV

[download-latest]: https://github.com/haikuhub/haikus-fishing/releases/latest/download/Haiku_Fishing.exe
[releases-latest]: https://github.com/haikuhub/haikus-fishing/releases/latest
