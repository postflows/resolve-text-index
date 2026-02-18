# Text Index

> Part of [PostFlows](https://github.com/postflows) toolkit for DaVinci Resolve

Manage and navigate text elements (Text+, MultiText, Subtitles) on the timeline with search, replace, CSV export/import, and spell-check.

## What it does

Provides a PySide6 UI to list text elements by type and timecode, edit in place, run regex search/replace, export to CSV and re-import with apply. Supports Yandex/LanguageTool spell-check in a background thread. Handles frame-accurate timecode and fractional FPS.

## Requirements

- DaVinci Resolve 18+
- Python 3.6+ (Resolve’s bundled)
- PySide6, requests (see installation instructions)

## Installation

Copy the script to:

- **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/`
- **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\`

Install PySide6 and requests in the environment Resolve uses for scripting.

## Usage

Run from Workspace > Scripts. Open timeline, run script. Use tree to select elements, edit text, use Search/Replace and CSV Export/Import as needed.

## License

MIT © PostFlows
