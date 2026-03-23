from __future__ import annotations

import argparse
import http.client
import logging
import os
import socket
import subprocess
import sys
import threading
import time

from logging.handlers import RotatingFileHandler

from jiuwenclaw.utils import USER_WORKSPACE_DIR, get_logs_dir


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 19000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5173
APP_CHILD_FLAG = "--desktop-run-app"
WEB_CHILD_FLAG = "--desktop-run-web"
STARTUP_TIMEOUT_SECONDS = 45.0

DESKTOP_BRIDGE_SCRIPT = r"""
(() => {
  if (window.__jiuwenclawDesktopControlsMounted) {
    return;
  }
  window.__jiuwenclawDesktopControlsMounted = true;

  const style = document.createElement('style');
  style.textContent = `
    #__jiuwenclaw_desktop_controls {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: 8px;
      padding: 4px;
      border-radius: 999px;
      background: rgba(17, 24, 39, 0.72);
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.26);
      pointer-events: auto;
      user-select: none;
      flex-shrink: 0;
    }
    #__jiuwenclaw_desktop_controls button {
      width: 34px;
      height: 34px;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      font: 600 14px/1 sans-serif;
      color: #e5e7eb;
      background: rgba(255, 255, 255, 0.12);
      transition: transform 120ms ease, background 120ms ease;
    }
    #__jiuwenclaw_desktop_controls button:hover {
      transform: translateY(-1px);
      background: rgba(255, 255, 255, 0.2);
    }
    #__jiuwenclaw_desktop_controls button[data-action="close"] {
      background: rgba(239, 68, 68, 0.82);
      color: #fff;
    }
    #__jiuwenclaw_desktop_controls.__floating {
      position: fixed;
      top: 14px;
      right: 14px;
      z-index: 2147483647;
      padding: 8px;
      margin-left: 0;
    }
  `;

  const container = document.createElement('div');
  container.id = '__jiuwenclaw_desktop_controls';
  container.innerHTML = `
    <button type="button" data-action="minimize" title="Minimize">_</button>
    <button type="button" data-action="fullscreen" title="Toggle fullscreen">[]</button>
    <button type="button" data-action="close" title="Close">X</button>
  `;

  const callApi = (methodName) => {
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api[methodName] !== 'function') {
      return Promise.resolve(false);
    }
    try {
      return Promise.resolve(api[methodName]());
    } catch (error) {
      console.error('[desktop-controls]', error);
      return Promise.resolve(false);
    }
  };

  container.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const action = target.dataset.action;
    if (action === 'minimize') {
      void callApi('minimize_window');
    } else if (action === 'fullscreen') {
      void callApi('toggle_fullscreen_window');
    } else if (action === 'close') {
      void callApi('close_window');
    }
  });

  const mountControls = () => {
    const topbar = document.querySelector('.topbar');
    if (topbar instanceof HTMLElement) {
      const rightZone = topbar.lastElementChild;
      if (rightZone instanceof HTMLElement) {
        rightZone.appendChild(container);
        container.classList.remove('__floating');
        return true;
      }
      topbar.appendChild(container);
      container.classList.remove('__floating');
      return true;
    }

    container.classList.add('__floating');
    document.body.appendChild(container);
    return false;
  };

  document.head.appendChild(style);

  if (!mountControls()) {
    const observer = new MutationObserver(() => {
      if (mountControls()) {
        observer.disconnect();
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('beforeunload', () => observer.disconnect(), { once: true });
  }
})();
"""


def _setup_logger() -> logging.Logger:
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("jiuwenclaw.desktop")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=logs_dir / "desktop.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


logger = _setup_logger()


def _creationflags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _build_child_command(name: str, extra_args: list[str] | None = None) -> list[str]:
    if getattr(sys, "frozen", False):
        base = [sys.executable, APP_CHILD_FLAG if name == "app" else WEB_CHILD_FLAG]
    elif name == "app":
        base = [sys.executable, "-m", "jiuwenclaw.app"]
    else:
        base = [sys.executable, "-m", "jiuwenclaw.app_web"]
    if extra_args:
        base.extend(extra_args)
    return base


def _build_child_env(name: str) -> dict[str, str]:
    env = os.environ.copy()
    if name == "app":
        env["WEB_HOST"] = BACKEND_HOST
        env["WEB_PORT"] = str(BACKEND_PORT)
    return env


def _start_process(name: str, command: list[str]) -> subprocess.Popen[bytes]:
    logger.info("[desktop] starting %s: %s", name, command)
    return subprocess.Popen(
        command,
        env=_build_child_env(name),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )


def _wait_for_tcp(
    host: str,
    port: int,
    timeout: float,
    process: subprocess.Popen[bytes] | None = None,
) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None

    while time.monotonic() < deadline:
        if process is not None:
            _ensure_process_running(f"service on tcp://{host}:{port}", process)
        try:
            with socket.create_connection((host, port), timeout=1.5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.35)

    raise RuntimeError(f"Timed out waiting for tcp://{host}:{port}: {last_error}")


def _ensure_process_running(name: str, process: subprocess.Popen[bytes]) -> None:
    code = process.poll()
    if code is None:
        return
    raise RuntimeError(f"{name} exited early with code {code}")


def _wait_for_http(
    host: str,
    port: int,
    path: str,
    timeout: float,
    process: subprocess.Popen[bytes] | None = None,
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        if process is not None:
            _ensure_process_running(f"service on http://{host}:{port}{path}", process)
        conn = http.client.HTTPConnection(host, port, timeout=2)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            response.read()
            if response.status < 500:
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        finally:
            conn.close()
        time.sleep(0.35)

    raise RuntimeError(f"Timed out waiting for http://{host}:{port}{path}: {last_error}")


class _WindowApi:
    def __init__(self, runtime: "DesktopRuntime") -> None:
        self._runtime = runtime

    def minimize_window(self) -> bool:
        return self._runtime.minimize_window()

    def toggle_fullscreen_window(self) -> bool:
        return self._runtime.toggle_fullscreen_window()

    def close_window(self) -> bool:
        return self._runtime.close_window()


class DesktopRuntime:
    def __init__(self, frontend_host: str, frontend_port: int, backend_port: int) -> None:
        self.frontend_host = frontend_host
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.processes: dict[str, subprocess.Popen[bytes]] = {}
        self.window = None
        self._lock = threading.Lock()
        self._is_shutting_down = False

    @property
    def frontend_url(self) -> str:
        return f"http://{self.frontend_host}:{self.frontend_port}"

    def start_services(self) -> None:
        self.processes["app"] = _start_process("app", _build_child_command("app"))
        _ensure_process_running("app", self.processes["app"])
        _wait_for_tcp(
            BACKEND_HOST,
            self.backend_port,
            STARTUP_TIMEOUT_SECONDS,
            process=self.processes["app"],
        )

        web_command = _build_child_command(
            "web",
            [
                "--host",
                self.frontend_host,
                "--port",
                str(self.frontend_port),
                "--proxy-target",
                f"http://{BACKEND_HOST}:{self.backend_port}",
            ],
        )
        self.processes["web"] = _start_process("web", web_command)
        _ensure_process_running("web", self.processes["web"])
        _wait_for_http(
            self.frontend_host,
            self.frontend_port,
            "/",
            STARTUP_TIMEOUT_SECONDS,
            process=self.processes["web"],
        )
        logger.info("[desktop] services ready: %s", self.frontend_url)

    def minimize_window(self) -> bool:
        if self.window is None or not hasattr(self.window, "minimize"):
            return False
        self.window.minimize()
        return True

    def toggle_fullscreen_window(self) -> bool:
        if self.window is None:
            return False
        if hasattr(self.window, "toggle_fullscreen"):
            self.window.toggle_fullscreen()
            return True
        if hasattr(self.window, "maximize"):
            self.window.maximize()
            return True
        return False

    def close_window(self) -> bool:
        if self.window is None or not hasattr(self.window, "destroy"):
            return False
        self.window.destroy()
        return True

    def shutdown(self) -> None:
        with self._lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True

        deadline = time.monotonic() + 8.0
        logger.info("[desktop] shutting down child processes")

        for process in self.processes.values():
            if process.poll() is None:
                process.terminate()

        while time.monotonic() < deadline:
            if all(process.poll() is not None for process in self.processes.values()):
                break
            time.sleep(0.2)

        for process in self.processes.values():
            if process.poll() is None:
                process.kill()

        self.processes.clear()

    def run(self, window_title: str, width: int, height: int, debug: bool) -> None:
        self.start_services()

        try:
            import webview
        except ImportError as exc:
            raise SystemExit(
                "pywebview is required for desktop mode. Install with `uv sync --extra dev` or `pip install jiuwenclaw[desktop]`."
            ) from exc

        storage_path = USER_WORKSPACE_DIR / "tmp" / "webview"
        storage_path.mkdir(parents=True, exist_ok=True)

        self.window = webview.create_window(
            window_title,
            self.frontend_url,
            js_api=_WindowApi(self),
            width=width,
            height=height,
            min_size=(1100, 720),
            frameless=True,
            easy_drag=True,
            text_select=True,
            background_color="#0f172a",
        )

        self.window.events.loaded += self._on_loaded
        self.window.events.closed += self._on_closed

        gui = "edgechromium" if os.name == "nt" else None
        logger.info("[desktop] opening window: %s", self.frontend_url)
        webview.start(
            debug=debug,
            gui=gui,
            private_mode=False,
            storage_path=str(storage_path),
        )

    def _on_loaded(self) -> None:
        if self.window is None:
            return
        try:
            self.window.evaluate_js(DESKTOP_BRIDGE_SCRIPT)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[desktop] failed to inject desktop controls: %s", exc)

    def _on_closed(self) -> None:
        self.shutdown()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch JiuwenClaw desktop window.")
    parser.add_argument("--title", default="JiuwenClaw", help="Desktop window title.")
    parser.add_argument("--width", type=int, default=1440, help="Initial window width.")
    parser.add_argument("--height", type=int, default=960, help="Initial window height.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable pywebview debug mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    runtime = DesktopRuntime(
        frontend_host=FRONTEND_HOST,
        frontend_port=FRONTEND_PORT,
        backend_port=BACKEND_PORT,
    )
    try:
        runtime.run(
            window_title=args.title,
            width=args.width,
            height=args.height,
            debug=args.debug,
        )
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
