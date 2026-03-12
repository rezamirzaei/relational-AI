from pathlib import Path

import pytest

from relational_fraud_intelligence.manage import _discover_project_root


def test_discover_project_root_uses_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "alembic").mkdir()
    (tmp_path / "alembic.ini").write_text("[alembic]\nscript_location = alembic\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RFI_PROJECT_ROOT", raising=False)

    assert _discover_project_root() == tmp_path


def test_discover_project_root_uses_explicit_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "alembic").mkdir()
    (tmp_path / "alembic.ini").write_text("[alembic]\nscript_location = alembic\n")

    monkeypatch.setenv("RFI_PROJECT_ROOT", str(tmp_path))

    assert _discover_project_root() == tmp_path
