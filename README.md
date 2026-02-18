# Text Index

> Part of [PostFlows](https://github.com/postflows) toolkit for DaVinci Resolve

Manage and navigate text elements (Text+, MultiText, Subtitles) on the timeline with search, replace, CSV export/import, and spell-check.

## What it does

Provides a PySide6 UI to list text elements by type and timecode, edit in place, run regex search/replace, export to CSV and re-import with apply. Supports Yandex/LanguageTool spell-check in a background thread. Handles frame-accurate timecode and fractional FPS.

## Requirements

- DaVinci Resolve 18+
- Python 3.6+
- PySide6, requests (see [INSTALL_DEPENDENCIES.md](INSTALL_DEPENDENCIES.md) — standard pip first)

## Installation

1. **Copy the script** to Resolve’s Fusion Scripts folder:
   - **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/`
   - **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\`

2. **Install Python dependencies** (required): PySide6 and requests. If you don’t have Python, install **3.11–3.13** from [python.org](https://www.python.org/downloads/) (recommended). See **[INSTALL_DEPENDENCIES.md](INSTALL_DEPENDENCIES.md)** — standard `pip3 install PySide6 requests` first; use Resolve’s Python path only if the script reports a missing module.

## Usage

Run from Workspace > Scripts. Open timeline, run script. Use tree to select elements, edit text, use Search/Replace and CSV Export/Import as needed.

## License

MIT © PostFlows
