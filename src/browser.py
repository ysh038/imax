"""전용 프로필 Chrome을 직접 띄우고 Selenium을 CDP로 붙인다.

ChromeDriver가 브라우저를 실행하면 navigator.webdriver가 켜지고 Cloudflare에
걸린다. 대신 평범한 Chrome 프로세스를 우리가 띄운 뒤 debuggerAddress로 붙으면
브라우저 입장에서는 사용자가 켠 창과 구분되지 않는다.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from . import cdp
from .paths import PROFILE_DIR, SHOTS_DIR

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_PORT = 9222

CGV_HOME = "https://cgv.co.kr/"
BOOKING_URL = "https://cgv.co.kr/cnm/movieBook"


class BrowserError(RuntimeError):
    pass


def launch_chrome(
    port: int = DEFAULT_PORT,
    profile_dir: Path = PROFILE_DIR,
    url: str = CGV_HOME,
    wait_sec: float = 40.0,
) -> subprocess.Popen | None:
    """Chrome을 띄우고 CDP 포트가 열릴 때까지 기다린다. 이미 떠 있으면 재사용."""
    if cdp.is_up(port):
        _ensure_tab(port, url)
        return None

    if not Path(CHROME_BIN).exists():
        raise BrowserError(f"Chrome을 찾을 수 없습니다: {CHROME_BIN}")

    profile_dir.mkdir(parents=True, exist_ok=True)
    args = [
        CHROME_BIN,
        f"--remote-debugging-port={port}",
        # Chrome 111+ 에서 ChromeDriver가 Origin 헤더를 보내며 붙기 때문에 필요하다.
        "--remote-allow-origins=*",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--window-size=1440,1000",
    ]
    if url:
        args.append(url)

    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if cdp.is_up(port):
            return proc
        if proc.poll() is not None:
            raise BrowserError(f"Chrome이 즉시 종료되었습니다 (exit={proc.returncode})")
        time.sleep(0.3)

    raise BrowserError(f"{wait_sec:.0f}초 안에 CDP 포트 {port}가 열리지 않았습니다")


def _ensure_tab(port: int, url: str = CGV_HOME) -> None:
    """탭이 하나도 없으면 만든다.

    맥에서 Chrome 창을 닫아도 프로세스는 남는다. 그 상태에서는 CDP 포트가 열려
    있는데도 붙을 페이지가 없어서 ChromeDriver가 세션 생성에 실패한다.
    """
    try:
        if cdp.list_page_targets(port):
            return
        cdp.new_tab(port, url or CGV_HOME)
        time.sleep(1.5)
    except Exception as exc:
        raise BrowserError(f"Chrome에 새 탭을 열지 못했습니다: {exc}") from exc


def attach_driver(port: int = DEFAULT_PORT) -> webdriver.Chrome:
    if not cdp.is_up(port):
        raise BrowserError(f"127.0.0.1:{port}에 열린 Chrome이 없습니다. 먼저 launch_chrome을 호출하세요.")
    _ensure_tab(port)
    options = Options()
    options.debugger_address = f"127.0.0.1:{port}"
    return webdriver.Chrome(options=options)


def start(port: int = DEFAULT_PORT, url: str = CGV_HOME) -> tuple[webdriver.Chrome, subprocess.Popen | None]:
    proc = launch_chrome(port=port, url=url)
    return attach_driver(port), proc


def screenshot(driver: webdriver.Chrome, name: str) -> Path:
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SHOTS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}.png"
    driver.save_screenshot(str(path))
    return path


def wait_for_login(driver: webdriver.Chrome, is_logged_in, poll_sec: float = 3.0) -> None:
    """로그인될 때까지 기다린다. 판정은 호출자가 넘긴 함수에 맡긴다.

    CGV는 checkScrenUrlValid 응답의 custLginYn 으로 로그인 여부를 알려주므로
    DOM을 뒤지는 것보다 그쪽이 정확하다.
    """
    if driver.current_url.rstrip("/") in ("", "about:blank", "data:,"):
        driver.get(CGV_HOME)
        time.sleep(2)

    # 판정 함수는 네트워크가 튀면 예외를 던진다. 첫 확인이 실패했다고
    # 죽을 이유는 없고, 아래 폴링 루프가 알아서 다시 본다.
    try:
        if is_logged_in():
            return
    except Exception as exc:
        print(f"[로그인 확인] 첫 확인 실패, 계속 시도합니다: {exc}")

    print("\n[로그인 필요] 열려 있는 Chrome 창에서 CGV에 로그인해 주세요.")
    print("             로그인하면 자동으로 감지하고 이어서 진행합니다. (Ctrl+C로 중단)\n")
    while True:
        time.sleep(poll_sec)
        try:
            if is_logged_in():
                break
        except Exception:
            continue
    print("[로그인 확인] 세션이 전용 프로필에 저장되어 다음 실행부터 재사용됩니다.\n")
