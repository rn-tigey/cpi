import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["CPI_DRY_RUN"] = "1"  # no real LLM calls in tests, ever


@pytest.fixture()
def cpi_home(tmp_path, monkeypatch):
    """Isolated CPI home seeded from the packaged templates, empty data/."""
    templates = PROJECT_ROOT / "cpi" / "templates"
    for sub in ("context", "config", "prompts"):
        shutil.copytree(templates / sub, tmp_path / sub)
    # The package ships only the template; a working home needs a pcm.yaml.
    shutil.copy(tmp_path / "context" / "pcm.template.yaml",
                tmp_path / "context" / "pcm.yaml")
    monkeypatch.setenv("CPI_HOME", str(tmp_path))
    from cpi import paths

    paths.ensure_layout()
    return tmp_path
