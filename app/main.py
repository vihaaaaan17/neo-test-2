from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.core.telemetry import setup_telemetry

# Set up global telemetry configuration
setup_telemetry()

app = FastAPI(title="NeosisLM API")

# Instrument the FastAPI app with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

@app.get("/health")
def health_check():
    return {"status": "ok"}

from app.api.routes.workspaces import router as workspaces_router
app.include_router(workspaces_router)
