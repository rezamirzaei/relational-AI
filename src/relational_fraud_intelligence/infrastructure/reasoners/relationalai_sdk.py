"""Direct RelationalAI SDK imports with tracing disabled for local repository runs."""

from relationalai.config import Config, create_config  # type: ignore[import-untyped]
from relationalai.util.tracing import StubTracer, set_tracer  # type: ignore[import-untyped]

set_tracer(StubTracer())

from relationalai.semantics import Model  # type: ignore[import-untyped]  # noqa: E402

__all__ = ["Config", "Model", "create_config"]
