import os
import sys
from pathlib import Path

import pytest

import pytest

from mcp_server import knowledge

# make repo-root imports work (mcp_server.knowledge) from tests/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point garage-knowledge at a temp dir for every test."""
    d = tmp_path / "garage"
    (d / "knowledge").mkdir(parents=True)
    monkeypatch.setenv("GARAGE_DATA_DIR", str(d))
    yield d


@pytest.fixture()
def con(isolated_data_dir):
    conn = knowledge.connect()
    yield conn
    conn.close()
