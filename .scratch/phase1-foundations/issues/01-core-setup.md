# 01: Core FastAPI Setup & OpenTelemetry Bootstrap

**What to build:** A running FastAPI server that exposes a `/health` endpoint and successfully emits OpenTelemetry traces to the console/OTLP. Includes a basic Dockerfile and GitHub Actions CI to ensure the build stays green.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] FastAPI application starts and serves `/health` returning 200 OK
- [ ] OpenTelemetry is configured and emits traces for incoming HTTP requests
- [ ] Dockerfile builds a runnable image of the application
- [ ] GitHub Actions workflow (or similar CI script) runs and passes
