# LanguageTool — Spell Check Server Setup

Text Index can use **LanguageTool** for spell-checking in two ways:

1. **Public API** — no setup; uses LanguageTool’s free online API (rate limits may apply).
2. **Local server** — you run LanguageTool on your machine for unlimited checks and no data sent online.

This guide explains how to install and run the **local server** so you can use “LanguageTool (Local Server)” in the Check Spelling dialog.

---

## Option A: macOS (Homebrew, recommended)

### 1. Install LanguageTool

If you use [Homebrew](https://brew.sh):

```bash
brew install languagetool
```

This installs the `languagetool-server` binary (e.g. under `/opt/homebrew/bin/` on Apple Silicon or `/usr/local/bin/` on Intel).

### 2. Start the server

**From the script (easiest):**

1. In Text Index, click **Check Spelling**.
2. Choose **LanguageTool (Local Server)**.
3. Click **Start server**.  
   The script will try `brew services start languagetool` or start `languagetool-server` directly. Wait a few seconds, then click **Refresh** — status should show “Server is running”.

**From the terminal (manual):**

```bash
# Start and keep running in foreground (default port 8081)
languagetool-server

# Or run as a background service (macOS)
brew services start languagetool
```

To stop:

- In the script: choose Local Server and click **Stop server**.
- Terminal: `brew services stop languagetool`, or stop the process (e.g. Ctrl+C if running in foreground).

### 3. Connect in Text Index

- Server: **LanguageTool (Local Server)**.
- Language: choose your text language (e.g. en-US, ru-RU).
- Click **Check Spelling** to run the check. The script uses `http://localhost:8081` by default.

---

## Option B: Other systems (Java / Docker)

If you are on **Windows** or **Linux**, or prefer not to use Homebrew, you can run the official LanguageTool server yourself.

### 1. Download LanguageTool

- **Standalone (Java):**  
  [LanguageTool releases](https://github.com/languagetool-org/languagetool/releases) — download the “LanguageTool-x.x.zip” that includes the server (or the “standalone” package).  
  Unzip and run the server (see official docs for the exact command, usually something like):

  ```bash
  java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081
  ```

- **Docker:**

  ```bash
  docker run -p 8081:8010 erikvl87/languagetool
  ```

  The server will be available at `http://localhost:8081` (port 8010 inside the container is mapped to 8081 on the host).

### 2. Connect in Text Index

- In the Check Spelling dialog, choose **LanguageTool (Local Server)**.
- The script expects the server at **http://localhost:8081** (default). If your server runs on another port, you would need to change the URL in the script (the current UI assumes port 8081 for the local server).
- Select **Language** and run **Check Spelling**.

---

## Troubleshooting

| Issue | What to do |
|--------|------------|
| “LanguageTool not installed” (macOS) | Install with `brew install languagetool`. Ensure Homebrew is in your PATH or use the full path to `brew`. |
| “Server not running” | Start the server (script: **Start server**, or terminal: `languagetool-server` / `brew services start languagetool`). Wait a few seconds, then **Refresh**. |
| “Connection refused” / “Unreachable” | Server is not listening. Check that nothing else uses port 8081; start LanguageTool and try **Refresh** again. |
| Can’t stop server (macOS) | If **Stop server** doesn’t work, run in terminal: `brew services stop languagetool`. If the server was started manually, stop that process or run: `lsof -ti:8081 | xargs kill -9`. |

---

## Links

- [LanguageTool](https://languagetool.org/)
- [LanguageTool HTTP server (developer)](https://dev.languagetool.org/http-server)
- [Homebrew](https://brew.sh) (macOS)
