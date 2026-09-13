"""
Servidor Streamlit aislado + helpers de Playwright para e2e de conversaciones.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_http(url: str, timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code < 500:
                return
        except requests.RequestException as exc:
            last_err = exc
        time.sleep(0.4)
    raise RuntimeError(f"Streamlit no arrancó en {url}: {last_err}")


@pytest.fixture
def live_server(tmp_path):
    port = _free_port()
    db_path = tmp_path / "conversations.db"
    env = os.environ.copy()
    env["CHATPDP_E2E"] = "1"
    env["CHATPDP_DB_PATH"] = str(db_path)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env.pop("STREAMLIT_SERVER_HEADLESS", None)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "streamlit_app.py"),
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(f"{url}/_stcore/health", timeout=60.0)
        time.sleep(1.5)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1600, "height": 1000},
    }


def _expand_sidebar(page) -> None:
    toggle = page.locator('[data-testid="stExpandSidebarButton"]')
    if toggle.count() and toggle.first.is_visible():
        toggle.first.click()
        page.locator("[class*='st-key-nueva_conversacion']").wait_for()


@pytest.fixture
def app_page(page, live_server):
    page.set_default_timeout(30_000)
    page.goto(live_server, wait_until="domcontentloaded")
    page.get_by_test_id("stChatInput").wait_for(timeout=45_000)
    _expand_sidebar(page)
    page.locator("[class*='st-key-nueva_conversacion']").wait_for()
    return page


def chat_messages(page):
    return page.get_by_test_id("stChatMessage")


def chat_has(page, text: str) -> bool:
    return chat_messages(page).filter(has_text=text).count() > 0


def send_chat(page, text: str) -> None:
    chat = page.get_by_test_id("stChatInput").locator("textarea")
    chat.click()
    chat.fill(text)
    chat.press("Enter")
    page.get_by_test_id("stChatMessage").filter(has_text=f"E2E: {text}").wait_for(
        timeout=25_000
    )
    page.locator("[class*='st-key-load_']").filter(has_text=text[:30]).first.wait_for()


def click_new_conversation(page) -> None:
    page.locator("[class*='st-key-nueva_conversacion']").locator("button").click()
    page.get_by_test_id("stChatInput").wait_for()


def history_buttons(page):
    return page.locator("[class*='st-key-load_']").locator("button")


def open_history(page, title_substr: str) -> None:
    history_buttons(page).filter(has_text=title_substr).first.click()
    page.get_by_test_id("stChatMessage").filter(has_text=title_substr).first.wait_for(
        timeout=20_000
    )


def select_tutor(page, name: str) -> None:
    box = page.locator("[class*='st-key-selector_tutor']")
    box.click()
    page.locator('[data-baseweb="menu"] li, [role="option"]').filter(has_text=name).first.click()


def delete_history(page, title_substr: str) -> None:
    import re

    wrapper = page.locator("[class*='st-key-load_']").filter(has_text=title_substr).first
    classes = wrapper.get_attribute("class") or ""
    match = re.search(r"st-key-load_(\S+)", classes)
    if not match:
        raise AssertionError(f"No se encontró key de historial para {title_substr!r}: {classes}")
    conv_id = match.group(1)
    page.locator(f"[class*='st-key-del_{conv_id}']").locator("button").click()
    page.locator("[class*='st-key-load_']").filter(has_text=title_substr).wait_for(
        state="detached", timeout=15_000
    )
