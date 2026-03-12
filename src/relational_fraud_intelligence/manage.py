from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from alembic.config import Config

from alembic import command
from relational_fraud_intelligence.application.services.audit_service import AuditService
from relational_fraud_intelligence.infrastructure.persistence.security_repository import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyOperatorRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.seed import DatabaseInitializer
from relational_fraud_intelligence.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from relational_fraud_intelligence.infrastructure.security.passwords import PasswordHasher
from relational_fraud_intelligence.infrastructure.seed.scenarios import build_seed_scenarios
from relational_fraud_intelligence.settings import AppSettings


def main() -> None:
    args = _build_parser().parse_args()
    settings = AppSettings()

    if args.command == "migrate":
        command.upgrade(_build_alembic_config(settings), args.revision)
        return

    engine = build_engine(settings.database_url, echo=settings.database_echo)
    session_factory = build_session_factory(engine)
    initializer = DatabaseInitializer(
        engine=engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )

    try:
        if args.command == "seed":
            inserted = initializer.seed_if_empty()
            print(f"Inserted {inserted} scenarios.")
            return
        if args.command == "create-operator":
            repository = SqlAlchemyOperatorRepository(session_factory)
            created = repository.create_operator(
                username=args.username,
                display_name=args.display_name,
                role=args.role,
                password_hash=PasswordHasher().hash_password(args.password),
            )
            if created:
                print(f"Created operator '{args.username}'.")
            else:
                print(f"Operator '{args.username}' already exists.")
            return
        if args.command == "prune-audit":
            service = AuditService(SqlAlchemyAuditLogRepository(session_factory))
            retention_days = (
                args.retention_days
                if args.retention_days is not None
                else settings.audit_log_retention_days
            )
            pruned_events = service.prune_expired_events(retention_days)
            print(f"Pruned {pruned_events} audit events.")
            return
        raise ValueError(f"Unsupported command '{args.command}'.")
    finally:
        engine.dispose()


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="rfi-manage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Apply Alembic migrations to the configured database.",
    )
    migrate_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Alembic revision target. Defaults to head.",
    )

    subparsers.add_parser(
        "seed",
        help="Seed the database with realistic investigation scenarios if it is empty.",
    )

    create_operator_parser = subparsers.add_parser(
        "create-operator",
        help="Create an operator account for interactive access.",
    )
    create_operator_parser.add_argument("--username", required=True)
    create_operator_parser.add_argument("--display-name", required=True)
    create_operator_parser.add_argument(
        "--role",
        choices=["admin", "analyst"],
        required=True,
    )
    create_operator_parser.add_argument("--password", required=True)

    prune_audit_parser = subparsers.add_parser(
        "prune-audit",
        help="Delete audit events older than the configured retention window.",
    )
    prune_audit_parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
    )
    return parser


def _build_alembic_config(settings: AppSettings) -> Config:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config
