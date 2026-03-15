from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import relational_fraud_intelligence.manage as manage
from relational_fraud_intelligence.manage import (
    CreateOperatorArgs,
    PruneAuditArgs,
    SeedArgs,
    _build_command_args,
    _build_parser,
    _discover_project_root,
)


@dataclass(slots=True)
class FakeSettings:
    database_url: str = "sqlite+pysqlite:///./data/test.db"
    database_echo: bool = False
    audit_log_retention_days: int = 45


async def test_discover_project_root_uses_current_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "alembic").mkdir()
    (tmp_path / "alembic.ini").write_text("[alembic]\nscript_location = alembic\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RFI_PROJECT_ROOT", raising=False)

    assert _discover_project_root() == tmp_path


async def test_discover_project_root_uses_explicit_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "alembic").mkdir()
    (tmp_path / "alembic.ini").write_text("[alembic]\nscript_location = alembic\n")

    monkeypatch.setenv("RFI_PROJECT_ROOT", str(tmp_path))

    assert _discover_project_root() == tmp_path


async def test_discover_project_root_rejects_invalid_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RFI_PROJECT_ROOT", str(tmp_path))

    with pytest.raises(
        FileNotFoundError,
        match="does not contain both 'alembic.ini' and 'alembic/'",
    ):
        _discover_project_root()


async def test_main_dispatches_migrate_command(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_args = Namespace(command="migrate", revision="head")
    fake_parser = SimpleNamespace(parse_args=lambda: fake_args)
    fake_settings = FakeSettings()
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


async def test_build_parser_supports_expected_commands() -> None:
    parser = _build_parser()

    migrate_args = parser.parse_args(["migrate"])
    create_operator_args = parser.parse_args(
        [
            "create-operator",
            "--username",
            "analyst",
            "--display-name",
            "Fraud Analyst",
            "--role",
            "analyst",
            "--password",
            "super-secret-password",
        ]
    )
    prune_audit_args = parser.parse_args(["prune-audit"])

    assert migrate_args.command == "migrate"
    assert migrate_args.revision == "head"
    assert create_operator_args.command == "create-operator"
    assert create_operator_args.role == "analyst"
    assert prune_audit_args.command == "prune-audit"
    assert prune_audit_args.retention_days is None


async def test_main_dispatches_seed_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_args = _build_command_args(Namespace(command="seed"))
    assert isinstance(fake_args, SeedArgs)
    fake_settings = FakeSettings()
    fake_engine = SimpleNamespace(disposed=False)
    captured: dict[str, object] = {}

    async def async_dispose() -> None:
        fake_engine.disposed = True

    fake_engine.dispose = async_dispose

    class FakeInitializer:
        def __init__(
            self,
            engine: object,
            session_factory: object,
            scenarios: list[str],
        ) -> None:
            captured["engine"] = engine
            captured["session_factory"] = session_factory
            captured["scenarios"] = scenarios

        async def seed_if_empty(self) -> int:
            return 3

    monkeypatch.setattr(manage, "AppSettings", lambda: fake_settings)
    monkeypatch.setattr(manage, "build_engine", lambda database_url, echo: fake_engine)
    monkeypatch.setattr(manage, "build_session_factory", lambda engine: "session-factory")
    monkeypatch.setattr(manage, "build_seed_scenarios", lambda: ["scenario"])
    monkeypatch.setattr(manage, "DatabaseInitializer", FakeInitializer)

    await manage._async_main(fake_args, fake_settings)

    assert capsys.readouterr().out == "Inserted 3 scenarios.\n"
    assert captured == {
        "engine": fake_engine,
        "session_factory": "session-factory",
        "scenarios": ["scenario"],
    }
    assert fake_engine.disposed is True


@pytest.mark.parametrize(
    ("created", "expected_output"),
    [
        (True, "Created operator 'analyst'.\n"),
        (False, "Operator 'analyst' already exists.\n"),
    ],
)
async def test_main_dispatches_create_operator_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    created: bool,
    expected_output: str,
) -> None:
    fake_args = _build_command_args(
        Namespace(
            command="create-operator",
            username="analyst",
            display_name="Fraud Analyst",
            role="analyst",
            password="super-secret-password",
        )
    )
    assert isinstance(fake_args, CreateOperatorArgs)
    fake_settings = FakeSettings()
    fake_engine = SimpleNamespace(disposed=False)
    repository_calls: list[dict[str, object]] = []

    async def async_dispose() -> None:
        fake_engine.disposed = True

    fake_engine.dispose = async_dispose

    class FakeRepository:
        async def create_operator(self, **kwargs: object) -> bool:
            repository_calls.append(kwargs)
            return created

    class FakePasswordHasher:
        def hash_password(self, password: str) -> str:
            assert password == "super-secret-password"
            return "hashed-password"

    monkeypatch.setattr(manage, "AppSettings", lambda: fake_settings)
    monkeypatch.setattr(manage, "build_engine", lambda database_url, echo: fake_engine)
    monkeypatch.setattr(manage, "build_session_factory", lambda engine: "session-factory")
    monkeypatch.setattr(manage, "build_seed_scenarios", lambda: [])
    monkeypatch.setattr(manage, "DatabaseInitializer", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        manage,
        "SqlAlchemyOperatorRepository",
        lambda session_factory: FakeRepository(),
    )
    monkeypatch.setattr(manage, "PasswordHasher", FakePasswordHasher)

    await manage._async_main(fake_args, fake_settings)

    assert capsys.readouterr().out == expected_output
    assert repository_calls == [
        {
            "username": "analyst",
            "display_name": "Fraud Analyst",
            "role": "analyst",
            "password_hash": "hashed-password",
        }
    ]
    assert fake_engine.disposed is True


async def test_main_dispatches_prune_audit_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_args = _build_command_args(Namespace(command="prune-audit", retention_days=None))
    assert isinstance(fake_args, PruneAuditArgs)
    fake_settings = FakeSettings(audit_log_retention_days=45)
    fake_engine = SimpleNamespace(disposed=False)
    service_calls: list[int] = []

    async def async_dispose() -> None:
        fake_engine.disposed = True

    fake_engine.dispose = async_dispose

    class FakeAuditService:
        def __init__(self, _repository: object) -> None:
            pass

        async def prune_expired_events(self, retention_days: int) -> int:
            service_calls.append(retention_days)
            return 7

    monkeypatch.setattr(manage, "AppSettings", lambda: fake_settings)
    monkeypatch.setattr(manage, "build_engine", lambda database_url, echo: fake_engine)
    monkeypatch.setattr(manage, "build_session_factory", lambda engine: "session-factory")
    monkeypatch.setattr(manage, "build_seed_scenarios", lambda: [])
    monkeypatch.setattr(manage, "DatabaseInitializer", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(manage, "SqlAlchemyAuditLogRepository", lambda session_factory: object())
    monkeypatch.setattr(manage, "AuditService", FakeAuditService)

    await manage._async_main(fake_args, fake_settings)

    assert capsys.readouterr().out == "Pruned 7 audit events.\n"
    assert service_calls == [45]
    assert fake_engine.disposed is True


async def test_main_rejects_unsupported_command(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_parser = SimpleNamespace(parse_args=lambda: Namespace(command="unknown"))
    monkeypatch.setattr(manage, "_build_parser", lambda: fake_parser)
    with pytest.raises(ValueError, match="Unsupported command 'unknown'"):
        manage.main()
