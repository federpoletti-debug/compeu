"""HTTP session shared by collectors: retries, timeouts, an honest User-Agent."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import __version__

REPO_URL = "https://github.com/federpoletti-debug/compeu"
USER_AGENT = f"CompEU/{__version__} (+{REPO_URL}; price research)"
TIMEOUT = 60


def use_system_trust_store() -> None:
    """Use the OS certificate store (needed behind TLS-inspecting antivirus on Windows).

    Verification stays on; only the source of trusted roots changes.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:  # pragma: no cover - truststore is a declared dependency
        pass


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers["User-Agent"] = USER_AGENT
    return s
