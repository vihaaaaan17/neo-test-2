from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from contextvars import ContextVar

# A global context variable to hold the explicit application-level correlation ID
neosis_run_id: ContextVar[str] = ContextVar("neosis_run_id", default="")
neosis_task_id: ContextVar[str] = ContextVar("neosis_task_id", default="")
neosis_request_id: ContextVar[str] = ContextVar("neosis_request_id", default="")

def setup_telemetry():
    # Sets the global default tracer provider
    provider = TracerProvider()
    
    # Export traces to console
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
