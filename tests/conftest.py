from pathlib import Path

import pytest

from sentinel.database.repositories import IncidentRepository


@pytest.fixture
def repository(tmp_path: Path) -> IncidentRepository:
    repo = IncidentRepository(tmp_path / "sentinel.db")
    repo.initialize()
    return repo
