# DeepCurrent

**DeepCurrent** is a minimal, privacy-first browser built on QtWebEngine.

It is designed for **session-only use**:
nothing is saved, nothing is remembered, nothing persists after exit.

Use it, close it, and it is gone.

---

## Philosophy

DeepCurrent is not a replacement for mainstream browsers.

It is a **temporary thinking window**.

- No history
- No persistent cookies
- No cache on disk
- No saved accounts
- No browser memory

If something matters, write it down yourself.

---

## Features

- Session-only browsing (off-the-record behavior)
- No disk persistence (cookies, cache, storage)
- Simple address bar + toolbar
- One-click navigation:
  - 🌀 ChatGPT
  - 🎵 aisland.uk
- Proxy via environment variables (no in-app configuration)
- Clean exit: everything disappears

---

## Requirements

- macOS
- Python 3.9+
- PyQt5
- PyQtWebEngine

Install dependencies:

```bash
pip install -U PyQt5 PyQtWebEngine

This repository intentionally does not include a `.gitignore`.
If you need one, please create it locally according to your own workflow.