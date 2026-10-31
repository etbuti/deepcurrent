#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepCurrent Browser (macOS-friendly v5 - simple mode)

Goals (per user request):
- Single-view minimal browser (no right-side AI panel content).
- AI and Music are "jump" actions that navigate within the same browser view (no external browser).
- Privacy-first: off-the-record profile, memory cache, no persistence.
- Address bar prefers direct URL navigation; searches only when input looks like a query.
"""

import os
import sys
import json
import re
from pathlib import Path

from PyQt5.QtCore import QUrl, Qt
from deepcurrent_music_player import MusicPlayer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QToolBar, QAction, QMessageBox, QDialog,
    QLabel, QPushButton, QFormLayout, QComboBox, QCheckBox, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
)

# ---- QWebEngineUrlRequestInterceptor import: varies across PyQt5 builds ----
RequestInterceptorBase = None
try:
    from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor as RequestInterceptorBase  # type: ignore
except Exception:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineUrlRequestInterceptor as RequestInterceptorBase  # type: ignore
    except Exception:
        RequestInterceptorBase = None


APP_NAME = "DeepCurrent"
CONFIG_FILE = "deepcurrent_config.json"

DEFAULT_HOME = "about:blank"
DEFAULT_SEARCH = "https://duckduckgo.com/?q={query}"

# Jump targets (in-app navigation)
DEFAULT_AI = "https://chatgpt.com/"
DEFAULT_MUSIC = "https://music.evanbei.com/library"


def resource_path(*parts: str) -> str:
    here = Path(__file__).resolve().parent
    return str(here.joinpath(*parts))


def load_config() -> dict:
    cfg_path = Path(resource_path(CONFIG_FILE))
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    cfg_path = Path(resource_path(CONFIG_FILE))
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def looks_like_url(text: str) -> bool:
    """
    Heuristic: treat as URL if:
    - has a scheme
    - contains a dot (example.com)
    - is localhost / 127.0.0.1 / ::1
    - contains a colon with port (example:8080)
    """
    t = text.strip()
    if not t:
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", t):
        return True
    if t.startswith(("localhost", "127.0.0.1", "[::1]", "::1")):
        return True
    if re.match(r"^[^/\s:]+:\d{2,5}(/|$)", t):
        return True
    host = t.split("/")[0]
    if "." in host and " " not in host:
        return True
    return False


def normalize_to_url(text: str) -> QUrl:
    """
    Convert user input into a QUrl for navigation.
    If no scheme is provided, default to https://
    """
    t = text.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", t):
        return QUrl(t)
    if re.match(r"^(about:|file:|chrome:|qrc:)", t):
        return QUrl(t)
    return QUrl("https://" + t)


# ---------- Request Interceptor (mac-safe) ----------
if RequestInterceptorBase:
    class RequestInterceptor(RequestInterceptorBase):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.block_trackers = True

        def interceptRequest(self, info):  # noqa: N802
            if not self.block_trackers:
                return
            url = info.requestUrl().toString()
            if any(k in url for k in [
                "doubleclick.net", "google-analytics.com", "googletagmanager.com",
                "facebook.com/tr", "connect.facebook.net"
            ]):
                info.block(True)
else:
    class RequestInterceptor(object):
        def __init__(self, *args, **kwargs):
            self.block_trackers = False


class MyWebEnginePage(QWebEnginePage):
    """Handle target=_blank and popups by opening in the same view."""
    def createWindow(self, _type):  # noqa: N802
        page = QWebEnginePage(self.profile(), self)
        page.urlChanged.connect(lambda u: self.view().setUrl(u) if self.view() else None)
        return page


class ProxyDialog(QDialog):
    """
    Proxy dialog: saves config and recommends restart to apply.
    QtWebEngine proxy behavior is most reliable when passed via Chromium flags.
    """
    def __init__(self, parent=None, cfg=None):
        super().__init__(parent)
        self.setWindowTitle("Proxy Settings")
        self.cfg = cfg or {}

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(["No Proxy", "HTTP Proxy", "SOCKS5 Proxy"])
        form.addRow("Mode", self.mode)

        self.host = QLineEdit()
        self.port = QLineEdit()
        form.addRow("Host", self.host)
        form.addRow("Port", self.port)

        self.block_trackers = QCheckBox("Block common trackers (lightweight)")
        form.addRow("", self.block_trackers)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)

        proxy = self.cfg.get("proxy", {})
        mode = proxy.get("mode", "none")
        if mode == "http":
            self.mode.setCurrentText("HTTP Proxy")
        elif mode == "socks5":
            self.mode.setCurrentText("SOCKS5 Proxy")
        else:
            self.mode.setCurrentText("No Proxy")

        self.host.setText(proxy.get("host", ""))
        self.port.setText(str(proxy.get("port", "")) if proxy.get("port") else "")
        self.block_trackers.setChecked(bool(self.cfg.get("block_trackers", True)))

    def on_save(self):
        mode_text = self.mode.currentText()
        if mode_text == "No Proxy":
            self.cfg["proxy"] = {"mode": "none"}
        else:
            host = self.host.text().strip()
            port = self.port.text().strip()
            if not host or not port.isdigit():
                QMessageBox.warning(self, "Invalid", "Please provide a valid host and numeric port.")
                return
            self.cfg["proxy"] = {
                "mode": "http" if mode_text == "HTTP Proxy" else "socks5",
                "host": host,
                "port": int(port),
            }
        self.cfg["block_trackers"] = bool(self.block_trackers.isChecked())
        save_config(self.cfg)
        self.accept()


class DeepCurrentBrowser(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg or {}

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 820)

        # ---- Profile (privacy-first) ----
        # Off-the-record profile => no disk persistence (cookies/cache/storage)
        self.profile = QWebEngineProfile(self)
        # Some PyQt5 builds don't expose setOffTheRecord(); rely on non-persistent policies.
        if hasattr(self.profile, 'setOffTheRecord'):
            self.profile.setOffTheRecord(True)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)

        # Interceptor (optional)
        if RequestInterceptorBase:
            self.interceptor = RequestInterceptor(self)
            self.interceptor.block_trackers = bool(self.cfg.get("block_trackers", True))
            self.profile.setUrlRequestInterceptor(self.interceptor)
        else:
            self.interceptor = None

        # ---- Main view ----
        self.page = MyWebEnginePage(self.profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser, 1)
        self.music_player = MusicPlayer(self)
        layout.addWidget(self.music_player)
        self.setCentralWidget(central)

        # ---- Toolbar ----
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL (or search query)…")
        self.url_input.returnPressed.connect(self.load_url_from_input)
        toolbar.addWidget(self.url_input)

        toolbar.addAction(self._act("←", self.browser.back))
        toolbar.addAction(self._act("→", self.browser.forward))
        toolbar.addAction(self._act("⟳", self.browser.reload))
        toolbar.addAction(self._act("🏠", self.go_home))

        # Jump actions (in the same view)
        toolbar.addAction(self._act("🌀", self.open_ai))
        toolbar.addAction(self._act("🎵", self.open_music))

        toolbar.addAction(self._act("🕸️", self.open_proxy_dialog))
        toolbar.addAction(self._act("ⓒ", self.show_about))

        # ---- Status ----
        self.status_left = QLabel("ready")
        self.status_left.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.statusBar().addWidget(self.status_left, 1)

        self.browser.urlChanged.connect(self.on_url_changed)

        # start simple
        self.go_home()

    def _act(self, text: str, fn):
        a = QAction(text, self)
        a.triggered.connect(fn)
        return a

    def on_url_changed(self, url: QUrl):
        u = url.toString()
        self.status_left.setText(u)
        self.url_input.setText(u)

    def go_home(self):
        home = self.cfg.get("home", DEFAULT_HOME) or DEFAULT_HOME
        self.browser.setUrl(QUrl(home))

    def open_music(self):
        self.browser.setUrl(QUrl(DEFAULT_MUSIC))

    def open_ai(self):
        # "Jump" in the same browser view (like the Music button)
        self.browser.setUrl(QUrl(DEFAULT_AI))

    def show_about(self):
        QMessageBox.information(
            self, "About",
            "DeepCurrent Browser\n"
            "Minimal privacy-first build.\n"
            "AI and Music buttons navigate within the same view.\n\n"
            "© Goldisle Light Org (UK)"
        )

    def open_proxy_dialog(self):
        dlg = ProxyDialog(self, cfg=self.cfg)
        if dlg.exec_():
            QMessageBox.information(
                self, "Saved",
                "Proxy settings saved.\n\n"
                "For QtWebEngine on macOS, proxy is most reliable after restart."
            )
            if self.interceptor is not None:
                self.interceptor.block_trackers = bool(self.cfg.get("block_trackers", True))

    def load_url_from_input(self):
        text = self.url_input.text().strip()
        if not text:
            return

        if looks_like_url(text) and " " not in text:
            self.browser.setUrl(normalize_to_url(text))
            return

        q = QUrl.toPercentEncoding(text).data().decode("ascii", errors="ignore")
        self.browser.setUrl(QUrl(DEFAULT_SEARCH.format(query=q)))


def build_chromium_flags_from_cfg(cfg: dict) -> str:
    proxy = (cfg or {}).get("proxy", {}) or {}
    mode = proxy.get("mode", "none")
    if mode == "none":
        return ""
    host = proxy.get("host", "")
    port = proxy.get("port", "")
    if not host or not port:
        return ""
    if mode == "http":
        return f'--proxy-server=http://{host}:{port}'
    if mode == "socks5":
        return f'--proxy-server=socks5://{host}:{port}'
    return ""


def main():
    # --- macOS stability tweak: must be before QApplication ---
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    cfg = load_config()

    flags = build_chromium_flags_from_cfg(cfg)
    if flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags

    app = QApplication(sys.argv)
    win = DeepCurrentBrowser(cfg)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
