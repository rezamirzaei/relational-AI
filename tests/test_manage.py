from pathlib import Path
from types import SimpleNamespace

import pytest

import relational_fraud_intelligence.manage as manage
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


def test_discover_project_root_rejects_invalid_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RFI_PROJECT_ROOT", str(tmp_path))

    with pytest.raises(
        FileNotFoundError,
        match="does not contain both 'alembic.ini' and 'alembic/'",
    ):
        _discover_project_root()


def test_main_dispatches_migrate_command(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_args = SimpleNamespace(command="migrate", revision="head")
    fake_parser = SimpleNamespace(parse_args=lambda: fake_args)
    fake_settings = SimpleNamespace(database_url="sqlite+pysqlite:///./data/test.db")
    fake_config = object()
    called: dict[str, object] = {}

    monkeypatch.setattr(manage, "_build_parser", lambda: fake_parser)
    monkeypatch.setattr(manage, "AppSettings", lambda: fake_settings)
    monkeypatch.setattr(manage, "_build_alembic_config", lambda settings: fake_config)
    monkeypatch.setattr(
        "relational_fraud_intelligence.manage.command.upgrade",
        lambda config, revision: called.update({"config": config, "revision": revision}),
    )

    manage.main()

    assert called == {"config": fake_config, "revision": "head"}
