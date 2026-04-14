"""Direct RelationalAI SDK imports with tracing disabled for local repository runs."""

from relationalai.config import Config, create_config  # type: ignore[import-untyped]
from relationalai.util.tracing import StubTracer, set_tracer  # type: ignore[import-untyped]

set_tracer(StubTracer())

from relationalai.semantics import (  # type: ignore[import-untyped]  # noqa: E402
    Model,
    Number,
    String,
)

__all__ = ["Config", "Model", "Number", "String", "create_config"]
