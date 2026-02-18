# Text Index — Installing Python Dependencies

This script requires Python packages that are **not** included with DaVinci Resolve. Install them into the Python interpreter used by Resolve.

---

## Required packages

| Package    | Purpose                     | Install command           |
|-----------|-----------------------------|----------------------------|
| **PySide6**  | GUI (Qt)                    | `pip install PySide6`      |
| **requests** | HTTP (spell-check API)      | `pip install requests`     |

---

## Standard library (no installation)

These modules come with Python and do not need to be installed:

`sys`, `os`, `datetime`, `fractions`, `tempfile`, `csv`, `re`, `shutil`, `webbrowser`, `xml.etree.ElementTree`

---

## Step-by-step installation

### 1. Locate Resolve’s Python

DaVinci Resolve uses its own bundled Python. You must install packages into **that** interpreter, not your system Python.

**macOS:**

```bash
# Resolve 18/19 (typical path; version number may vary)
/Applications/DaVinci\ Resolve/DaVinci\ Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/3.*/bin/python3 -m pip install PySide6 requests
```

If the above fails, find the exact path:

```bash
# List Python versions inside Resolve.app
ls "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/"
# Then use the full path, e.g.:
# .../Versions/3.10/bin/python3 -m pip install PySide6 requests
```

**Windows:**

```cmd
"C:\Program Files\Blackmagic Design\DaVinci Resolve\python.exe" -m pip install PySide6 requests
```

Adjust the path if you use a different Resolve version or install location (e.g. `DaVinci Resolve 19`).

**Linux:**

```bash
# Path depends on your installation; examples:
/opt/resolve/python3 -m pip install PySide6 requests
# or
/opt/resolve/libs/python3 -m pip install PySide6 requests
```

### 2. Install the packages

Run the `pip install` command with Resolve’s Python as shown above. Example for macOS:

```bash
/Applications/DaVinci\ Resolve/DaVinci\ Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/3.10/bin/python3 -m pip install PySide6 requests
```

### 3. Verify

Run this with the **same** Python that Resolve uses:

```bash
.../python3 -c "import PySide6; import requests; print('OK')"
```

If you see `OK`, dependencies are installed correctly.

---

## Install the script

1. Copy `text-index.py` into Resolve’s Fusion Scripts folder:
   - **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/` (or a subfolder, e.g. `Utility/TextPlus/`)
   - **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\`
2. Restart Resolve if it was open.
3. Run the script from **Workspace → Scripts** (menu path depends on where you placed the file).

---

## Troubleshooting

| Problem | What to do |
|--------|-------------|
| `No module named 'PySide6'` | Install PySide6 into Resolve’s Python (see paths above). Do not use system `pip` unless Resolve is set to use system Python. |
| `No module named 'requests'` | Same: install requests with Resolve’s Python. |
| Script not in Workspace menu | Check that the script is in the Fusion Scripts folder (or a subfolder). Restart Resolve. |
| Wrong Python in use | In Resolve: **Preferences → System → General → External scripting** — note which Python is selected and install packages there. |

---

## Optional: requirements.txt

From the folder containing this README, you can install with Resolve’s Python:

```bash
/path/to/Resolve's/python3 -m pip install -r requirements.txt
```

Replace `/path/to/Resolve's/python3` with the actual path for your OS (see above).
