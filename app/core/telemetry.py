import re
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from contextvars import ContextVar

# Application-level correlation ID context variables
neosis_run_id: ContextVar[str] = ContextVar("neosis_run_id", default="")
neosis_task_id: ContextVar[str] = ContextVar("neosis_task_id", default="")
neosis_request_id: ContextVar[str] = ContextVar("neosis_request_id", default="")
neosis_workspace_id: ContextVar[str] = ContextVar("neosis_workspace_id", default="")
neosis_conversation_id: ContextVar[str] = ContextVar("neosis_conversation_id", default="")
neosis_turn_id: ContextVar[str] = ContextVar("neosis_turn_id", default="")
neosis_timeline_epoch: ContextVar[int] = ContextVar("neosis_timeline_epoch", default=1)

# Secret sanitization patterns
SECRET_PATTERNS = [
    # Authorization header tokens: Bearer <token>
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.]+", re.IGNORECASE), r"\1[REDACTED]"),
    # JWT tokens: eyJ...
    (re.compile(r"eyJ[A-Za-z0-9-_]{10,}\.eyJ[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,}"), "[REDACTED_JWT]"),
    # DB passwords in connection strings: ://user:password@host
    (re.compile(r"(://[^:\s]+):([^@\s]+)@"), r"\1:[REDACTED]@"),
    # API key or secret query / json params
    (
        re.compile(
            r"""(?i)(api[_-]?key|secret|password|access_token|private_key|jwt_secret)\s*[:=]\s*['"]?([A-Za-z0-9\-_./+=]{8,})['"]?"""
        ),
        r'\1="[REDACTED]"',
    ),
]


def sanitize_log_message(msg: str) -> str:
    """Sanitizes sensitive tokens, passwords, and API keys from log strings."""
    if not isinstance(msg, str):
        return msg
    sanitized = msg
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SecretSanitizingFilter(logging.Filter):
    """
    Logging filter that intercepts log records and redacts any credentials,
    bearer tokens, and connection passwords before emission.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_log_message(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: sanitize_log_message(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


def setup_telemetry():
    """Sets up OpenTelemetry and attaches secret sanitization to the logging root."""
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Attach secret sanitizing filter to root logger and standard handlers
    root_logger = logging.getLogger()
    sanitizer = SecretSanitizingFilter()
    root_logger.addFilter(sanitizer)
    for handler in root_logger.handlers:
        handler.addFilter(sanitizer)
