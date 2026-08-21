from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PROFILE_DIR = REPO / ".chrome-profile"
DISCOVERY_DIR = REPO / "discovery"
DOCS_DIR = REPO / "docs"
SHOTS_DIR = REPO / "shots"
LOGS_DIR = REPO / "logs"

CONFIG_PATH = REPO / "config.yaml"
CONFIG_EXAMPLE_PATH = REPO / "config.example.yaml"
ENV_PATH = REPO / ".env"

# 손으로 관리하는 확정 엔드포인트. 녹화기는 여기를 덮어쓰지 않는다.
ENDPOINTS_PATH = REPO / "endpoints.yaml"
GUESS_ENDPOINTS_PATH = DISCOVERY_DIR / "endpoints.guess.yaml"


def ensure_dirs() -> None:
    for d in (PROFILE_DIR, DISCOVERY_DIR, DOCS_DIR, SHOTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
