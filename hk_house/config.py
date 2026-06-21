"""Central configuration.

Secrets (auth tokens, cookies) are read from environment variables so they are
never committed. Browser-captured values go here:

    export MIDLAND_TOKEN="Bearer eyJ..."          # midland Authorization header
    export HSE28_COOKIE="cf_clearance=...; ..."    # 28hse Cloudflare cookies
    export HSE28_API="https://.../api/..."         # 28hse data endpoint (if found)
    export HOUSE730_LIST_API="https://.../..."     # house730 search/list endpoint

Network-behaviour knobs (delays, retries, proxies) also live here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("HKHOUSE_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


@dataclass(frozen=True)
class NetworkConfig:
    """Anti-blocking / throttling behaviour shared by every fetcher."""

    # Polite delay between requests to the same host (seconds). Jitter is added
    # on top of this so the cadence is not perfectly regular.
    min_delay: float = float(os.getenv("HKHOUSE_MIN_DELAY", "1.0"))
    max_jitter: float = float(os.getenv("HKHOUSE_MAX_JITTER", "1.5"))

    # Retry policy for transient failures (429 / 5xx / network errors).
    max_retries: int = int(os.getenv("HKHOUSE_MAX_RETRIES", "5"))
    backoff_base: float = float(os.getenv("HKHOUSE_BACKOFF_BASE", "2.0"))
    backoff_max: float = float(os.getenv("HKHOUSE_BACKOFF_MAX", "60.0"))

    timeout: float = float(os.getenv("HKHOUSE_TIMEOUT", "30.0"))

    # Optional proxy rotation. Comma-separated list, e.g.
    #   export HKHOUSE_PROXIES="http://u:p@h1:port,http://u:p@h2:port"
    proxies: list[str] = field(
        default_factory=lambda: [
            p.strip() for p in os.getenv("HKHOUSE_PROXIES", "").split(",") if p.strip()
        ]
    )


@dataclass(frozen=True)
class SourceSecrets:
    """Browser-captured credentials, pulled from the environment."""

    midland_token: str | None = os.getenv("MIDLAND_TOKEN")
    hse28_cookie: str | None = os.getenv("HSE28_COOKIE")
    hse28_api: str | None = os.getenv("HSE28_API")
    house730_list_api: str | None = os.getenv("HOUSE730_LIST_API")


NETWORK = NetworkConfig()
SECRETS = SourceSecrets()

# A small pool of realistic desktop User-Agents. Rotated per request.
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
