# Text Index — Installing Python Dependencies

This script needs **PySide6** and **requests**. Resolve may use your system Python or its own bundled one — try the simple method first.

---

## Required packages

| Package    | Purpose                | Install command           |
|-----------|------------------------|----------------------------|
| **PySide6**  | GUI (Qt)               | `pip install PySide6`      |
| **requests** | HTTP (spell-check API) | `pip install requests`     |

---

## System Python (recommended)

Using a **single** Python installed on your machine (and, if needed, pointing Resolve to it in **Preferences → System → General → External scripting**) keeps things simple: install packages once with `pip3`, and the script runs in Resolve without extra paths.

**Recommended version:** Python **3.11**, **3.12**, or **3.13**. On the author’s machine: **Python 3.13** from [python.org](https://www.python.org/downloads/) (`/Library/Frameworks/Python.framework` on macOS).

**Install:**

- **macOS:** Download the installer from [python.org/downloads](https://www.python.org/downloads/) (choose “macOS 64-bit universal2” or Apple Silicon). Or with Homebrew: `brew install python@3.12` (then use `python3.12` and `pip3.12`). Make sure “Install certificates” and “Update Shell Profile” are checked if the installer offers them.
- **Windows:** Download from [python.org](https://www.python.org/downloads/), run the installer, and **check “Add python.exe to PATH”** so that `pip` works in the terminal.

After installation, open a new terminal and run `python3 --version` (macOS/Linux) or `py -3 --version` (Windows) to confirm. Then use that Python’s pip for **Method 1** below.

---

## Method 1: Standard install (try this first)

On many systems, Resolve uses the same Python you use in the terminal (or one that sees your user-installed packages). In that case a normal install is enough:

```bash
pip3 install PySide6 requests
```

Or, if you use `pip`:

```bash
pip install PySide6 requests
```

Then run the script from **Workspace → Scripts** in Resolve. If it opens without “No module named 'PySide6'” (or similar), you’re done.

**Tip:** In Resolve, **Preferences → System → General → External scripting** shows which Python interpreter Resolve uses. If it points to your system or user Python, Method 1 is the right one.

---

## Method 2: Install into Resolve’s Python (if Method 1 fails)

If the script reports **No module named 'PySide6'** (or **requests**), Resolve is likely using its **bundled** Python, which doesn’t see packages you installed with `pip3` in the terminal. Install into that interpreter instead.

**macOS:**

```bash
# Resolve 18/19 — path may vary (e.g. 3.10, 3.11)
/Applications/DaVinci\ Resolve/DaVinci\ Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/3.10/bin/python3 -m pip install PySide6 requests
```

To find the exact version folder:

```bash
ls "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/"
```

Then use that path, e.g. `.../Versions/3.11/bin/python3 -m pip install PySide6 requests`.

**Windows:**

```cmd
"C:\Program Files\Blackmagic Design\DaVinci Resolve\python.exe" -m pip install PySide6 requests
```

Adjust if your Resolve is in a different folder (e.g. `DaVinci Resolve 19`).

**Linux:**

```bash
# Path depends on your install; examples:
/opt/resolve/python3 -m pip install PySide6 requests
```

---

## Verify

With the **same** Python that Resolve uses (system one for Method 1, or Resolve’s path for Method 2):

```bash
python3 -c "import PySide6; import requests; print('OK')"
```

If you see `OK`, the script should run in Resolve.

---

## Install the script

1. Copy `text-index.py` into Resolve’s Fusion Scripts folder:
   - **macOS:** `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/` (or a subfolder)
   - **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\`
2. Restart Resolve if it was open.
3. Run from **Workspace → Scripts**.

---

## Troubleshooting

| Problem | What to do |
|--------|------------|
| `No module named 'PySide6'` or `requests` | You’re on Resolve’s bundled Python. Use **Method 2** and install with Resolve’s Python path. |
| Script not in Workspace menu | Check the script is inside the Fusion Scripts folder (or a subfolder). Restart Resolve. |
| Which Python does Resolve use? | **Preferences → System → General → External scripting** — the path shown there is the one that must have PySide6 and requests. |

---

## Optional: requirements.txt

If you use Method 1 (system/user Python):

```bash
pip3 install -r requirements.txt
```

If you use Method 2 (Resolve’s Python), replace `python3` with Resolve’s interpreter path, e.g.:

```bash
/Applications/DaVinci\ Resolve/DaVinci\ Resolve.app/Contents/Libraries/Frameworks/Python.framework/Versions/3.10/bin/python3 -m pip install -r requirements.txt
```
