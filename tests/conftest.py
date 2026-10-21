import shutil
from pathlib import Path

import pytest

from compeu import fx

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_root(tmp_path, monkeypatch):
    """A throwaway repository root with the real registry and an empty ledger."""
    shutil.copytree(REPO / "registry", tmp_path / "registry")
    monkeypatch.setenv("COMPEU_ROOT", str(tmp_path))
    fx.rates.cache_clear()
    yield tmp_path
    fx.rates.cache_clear()
