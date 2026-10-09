"""
NeosisLM Chapter 4 End-to-End Integration Testbed.

This Streamlit application acts strictly as an HTTP client communicating
exclusively through the canonical FastAPI endpoints (/api/v1/...).
It does NOT import backend engines, database models, repositories, or services,
and enforces Chapter 4 runtime verification across Ground, Research, SSE streaming,
reconnect/replay, cancellation, promotion, rollback, and timeline fencing.
"""

import os
import sys
import json
import time
import uuid
import datetime
from typing import Optional, Dict, Any, List, Generator, Tuple

import httpx
import jwt
import streamlit as st
from dotenv import dotenv_values

# -----------------------------------------------------------------------------
# Configuration & Environment Resolution
# -----------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_ui_path = os.path.join(REPO_ROOT, ".env.ui")
_env_path = os.path.join(REPO_ROOT, ".env")

_env_ui = dotenv_values(_env_ui_path) if os.path.exists(_env_ui_path) else {}
_env_main = dotenv_values(_env_path) if os.path.exists(_env_path) else {}

DEFAULT_API_BASE_URL = (
    os.environ.get("NEOSIS_API_BASE_URL")
    or _env_ui.get("API_BASE_URL")
    or "http://localhost:8000"
)

DEFAULT_AUTH_TOKEN = (
    os.environ.get("NEOSIS_AUTH_TOKEN")
    or _env_ui.get("NEOSIS_AUTH_TOKEN")
    or ""
)

DEFAULT_JWT_SECRET = (
    os.environ.get("SUPABASE_JWT_SECRET")
    or _env_main.get("SUPABASE_JWT_SECRET")
    or "super-secret-jwt-token-for-supabase-local-dev-only"
)

TERMINAL_EVENT_TYPES = frozenset({
    "done",
    "error",
    "cancelled",
    "turn.completed",
    "turn.failed",
    "turn.cancelled"
})


# -----------------------------------------------------------------------------
# API Client & SSE Stream Protocol Implementation
# -----------------------------------------------------------------------------
class APIError(Exception):
    """Encapsulates backend HTTP error responses with status and canonical detail."""

    def __init__(self, status_code: int, detail: Any, raw_body: str = "", method: str = "", url: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.raw_body = raw_body
        self.method = method
        self.url = url
        super().__init__(f"[{status_code}] {method} {url}: {detail}")


def safe_display_json(obj: Any):
    """Safely displays data in Streamlit, avoiding browser SyntaxError when obj is not valid JSON."""
    if isinstance(obj, (dict, list)):
        st.json(obj)
    elif isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            st.json(parsed)
        except Exception:
            st.code(obj)
    elif obj is not None:
        st.code(str(obj))


def generate_dev_token(user_id: str, secret: str) -> str:
    """Generate a dev JWT signed with HS256 for local testing without bypassing auth."""
    payload = {
        "sub": str(user_id),
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600 * 24 * 7,  # 7 days
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class NeosisAPIClient:
    """
    Synchronous HTTP client for NeosisLM canonical API endpoints.
    Tracks request/response traces for developer debug inspection and provides
    real SSE streaming conforming to Chapter 4 event semantics.
    """

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip() if token else None
        self.timeout = httpx.Timeout(connect=10.0, read=900.0, write=30.0, pool=30.0)

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "NeosisLM-IntegrationTestbed/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _record_debug(
        self,
        method: str,
        url: str,
        req_headers: Dict[str, str],
        req_body: Any,
        status_code: Optional[int],
        resp_headers: Optional[Dict[str, str]],
        resp_body: Any,
        duration_ms: float,
        error: Optional[str] = None,
    ):
        # Mask sensitive authorization tokens for debug output
        masked_headers = dict(req_headers)
        if "Authorization" in masked_headers:
            val = masked_headers["Authorization"]
            if len(val) > 20:
                masked_headers["Authorization"] = val[:13] + "..." + val[-5:]
            else:
                masked_headers["Authorization"] = "***"

        try:
            st.session_state["last_request_debug"] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "method": method,
                "url": url,
                "request_headers": masked_headers,
                "request_body": req_body,
                "status_code": status_code,
                "response_headers": dict(resp_headers) if resp_headers else {},
                "response_body": resp_body,
                "duration_ms": round(duration_ms, 2),
                "error": error,
            }
        except Exception:
            pass

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = self._headers(extra_headers)
        start_time = time.time()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    files=files,
                    headers=headers,
                )
                duration_ms = (time.time() - start_time) * 1000

                try:
                    parsed_resp = resp.json()
                except Exception:
                    parsed_resp = resp.text

                self._record_debug(
                    method=method,
                    url=url,
                    req_headers=headers,
                    req_body=json_data,
                    status_code=resp.status_code,
                    resp_headers=dict(resp.headers),
                    resp_body=parsed_resp,
                    duration_ms=duration_ms,
                )

                if resp.is_error:
                    detail = parsed_resp.get("detail", resp.text) if isinstance(parsed_resp, dict) else resp.text
                    raise APIError(
                        status_code=resp.status_code,
                        detail=detail,
                        raw_body=resp.text,
                        method=method,
                        url=url,
                    )
                return resp

        except httpx.RequestError as exc:
            duration_ms = (time.time() - start_time) * 1000
            self._record_debug(
                method=method,
                url=url,
                req_headers=headers,
                req_body=json_data,
                status_code=None,
                resp_headers=None,
                resp_body=None,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise APIError(
                status_code=0,
                detail=f"Network/Connection error: {str(exc)}",
                method=method,
                url=url,
            )

    # --- Health & Status ---
    def get_health(self) -> Dict[str, Any]:
        resp = self._request("GET", "/api/v1/health")
        return resp.json()

    def get_worker_pool_status(self) -> Dict[str, Any]:
        resp = self._request("GET", "/api/v1/worker-pool-status")
        return resp.json()

    def get_queue_status(self, workspace_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/research/queue-status")
        return resp.json()

    # --- Workspaces ---
    def create_workspace(self) -> Dict[str, Any]:
        resp = self._request("POST", "/api/v1/workspaces/", json_data={})
        return resp.json()

    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}")
        return resp.json()

    def delete_workspace(self, workspace_id: str) -> None:
        self._request("DELETE", f"/api/v1/workspaces/{workspace_id}")

    def get_workspace_graph(self, workspace_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/graph")
        return resp.json()

    def create_commit(self, workspace_id: str) -> Dict[str, Any]:
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/commits")
        return resp.json()

    def rollback_workspace(self, workspace_id: str, commit_id: str) -> Dict[str, Any]:
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/rollback", json_data={"commit_id": commit_id})
        return resp.json()

    # --- Source Ingestion ---
    def upload_file(self, workspace_id: str, filename: str, content: bytes, mime_type: str) -> Dict[str, Any]:
        files = {"file": (filename, content, mime_type)}
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/files", files=files)
        return resp.json()

    def get_source_status(self, workspace_id: str, source_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/sources/{source_id}/status")
        return resp.json()

    def get_projection_status(self, workspace_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/projection-status")
        return resp.json()

    def download_source_file(self, workspace_id: str, source_id: str) -> Tuple[bytes, Dict[str, str]]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/sources/{source_id}/download")
        return resp.content, dict(resp.headers)

    # --- Conversations ---
    def create_conversation(self, workspace_id: str, title: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"title": title or "New Conversation"}
        if metadata:
            body["metadata"] = metadata
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/conversations", json_data=body)
        return resp.json()

    def list_conversations(self, workspace_id: str, status_filter: str = "active", limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        params = {"status": status_filter, "limit": limit, "offset": offset}
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations", params=params)
        return resp.json()

    def get_conversation(self, workspace_id: str, conversation_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}")
        return resp.json()

    # --- Turns & Chat Execution ---
    def submit_turn_sync(self, workspace_id: str, conversation_id: str, turn_create: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns",
            params={"stream": "false"},
            json_data=turn_create,
        )
        return resp.json()

    def list_turns(self, workspace_id: str, conversation_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns", params=params)
        return resp.json()

    def get_turn(self, workspace_id: str, conversation_id: str, turn_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}")
        return resp.json()

    def cancel_turn(self, workspace_id: str, conversation_id: str, turn_id: str) -> Dict[str, Any]:
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel")
        return resp.json()

    def compile_study_report(self, workspace_id: str, conversation_id: str, request: Optional[str] = None) -> Dict[str, Any]:
        resp = self._request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/study-report",
            json_data={"request": request} if request else {},
        )
        return resp.json()

    def list_study_reports(self, workspace_id: str, conversation_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/study-reports")
        return resp.json()

    def get_turn_events_sync(self, workspace_id: str, conversation_id: str, turn_id: str, after_sequence: int = 0) -> Dict[str, Any]:
        params = {"stream": "false", "after_sequence": after_sequence}
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events", params=params)
        return resp.json()

    # --- Promotions ---
    def list_promotions(self, workspace_id: str, status_filter: Optional[str] = None, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if status_filter:
            params["status"] = status_filter
        if run_id:
            params["run_id"] = run_id
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/promotions", params=params)
        return resp.json()

    def get_promotion(self, workspace_id: str, artifact_id: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/api/v1/workspaces/{workspace_id}/promotions/{artifact_id}")
        return resp.json()

    def accept_promotion(self, workspace_id: str, artifact_id: str) -> Dict[str, Any]:
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/accept")
        return resp.json()

    def reject_promotion(self, workspace_id: str, artifact_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        payload = {"review_reason": reason} if reason else None
        resp = self._request("POST", f"/api/v1/workspaces/{workspace_id}/promotions/{artifact_id}/reject", json_data=payload)
        return resp.json()

    # --- Server-Sent Events (SSE) Streaming Engine ---
    def _parse_sse_lines(self, line_iterator) -> Generator[Dict[str, Any], None, None]:
        """
        Parses standard Server-Sent Event stream complying with HTML5 specification:
        id: <sequence>
        event: <event_type>
        data: <json or string>
        blank line ends event
        """
        current_id: Optional[int] = None
        current_event = "message"
        current_data: List[str] = []

        for raw_line in line_iterator:
            line = raw_line.rstrip("\r\n")

            # Keep raw frame in debug log (capped at 50)
            try:
                if "raw_sse_log" not in st.session_state:
                    st.session_state["raw_sse_log"] = []
                st.session_state["raw_sse_log"].append(line)
                if len(st.session_state["raw_sse_log"]) > 50:
                    st.session_state["raw_sse_log"] = st.session_state["raw_sse_log"][-50:]
            except Exception:
                pass

            # Comment or keep-alive (e.g. ": keep-alive") - ignore comment per SSE spec
            if line.startswith(":"):
                continue

            # Blank line marks event boundary -> dispatch
            if not line:
                if current_data or current_event != "message" or current_id is not None:
                    data_str = "\n".join(current_data)
                    try:
                        parsed_data = json.loads(data_str)
                    except Exception:
                        parsed_data = data_str

                    yield {
                        "id": current_id,
                        "event": current_event,
                        "data": parsed_data,
                        "raw": f"id: {current_id}\nevent: {current_event}\ndata: {data_str}",
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                    current_id = None
                    current_event = "message"
                    current_data = []
                continue

            if line.startswith("id:"):
                val = line[3:].strip()
                try:
                    current_id = int(val)
                except ValueError:
                    current_id = val  # type: ignore
            elif line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                current_data.append(line[5:].lstrip(" "))

        # Dispatch any trailing uncompleted event
        if current_data or current_event != "message" or current_id is not None:
            data_str = "\n".join(current_data)
            try:
                parsed_data = json.loads(data_str)
            except Exception:
                parsed_data = data_str
            yield {
                "id": current_id,
                "event": current_event,
                "data": parsed_data,
                "raw": f"id: {current_id}\nevent: {current_event}\ndata: {data_str}",
                "timestamp": datetime.datetime.now().isoformat(),
            }

    def stream_turn_submit(
        self,
        workspace_id: str,
        conversation_id: str,
        turn_create: Dict[str, Any],
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams turn execution directly from POST /turns?stream=true.
        """
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns?stream=true"
        headers = self._headers({"Accept": "text/event-stream"})
        start_time = time.time()

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, json=turn_create, headers=headers) as resp:
                duration_ms = (time.time() - start_time) * 1000
                self._record_debug(
                    method="POST (SSE)",
                    url=url,
                    req_headers=headers,
                    req_body=turn_create,
                    status_code=resp.status_code,
                    resp_headers=dict(resp.headers),
                    resp_body="[Streaming SSE Response]",
                    duration_ms=duration_ms,
                )

                if resp.is_error:
                    error_text = resp.read().decode("utf-8", errors="replace")
                    raise APIError(
                        status_code=resp.status_code,
                        detail=error_text,
                        raw_body=error_text,
                        method="POST (SSE)",
                        url=url,
                    )

                yield from self._parse_sse_lines(resp.iter_lines())

    def stream_turn_events(
        self,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        after_sequence: int = 0,
        last_event_id: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams or reconnects to an event stream via GET /turns/{turn_id}/events?stream=true.
        Respects the canonical Last-Event-ID header and after_sequence query parameter.
        """
        url = (
            f"{self.base_url}/api/v1/workspaces/{workspace_id}/conversations/"
            f"{conversation_id}/turns/{turn_id}/events?stream=true&after_sequence={after_sequence}"
        )
        extra_headers = {"Accept": "text/event-stream"}
        if last_event_id is not None:
            extra_headers["Last-Event-ID"] = str(last_event_id)

        headers = self._headers(extra_headers)
        start_time = time.time()

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("GET", url, headers=headers) as resp:
                duration_ms = (time.time() - start_time) * 1000
                self._record_debug(
                    method="GET (SSE)",
                    url=url,
                    req_headers=headers,
                    req_body=None,
                    status_code=resp.status_code,
                    resp_headers=dict(resp.headers),
                    resp_body="[Streaming SSE Replay/Live Response]",
                    duration_ms=duration_ms,
                )

                if resp.is_error:
                    error_text = resp.read().decode("utf-8", errors="replace")
                    raise APIError(
                        status_code=resp.status_code,
                        detail=error_text,
                        raw_body=error_text,
                        method="GET (SSE)",
                        url=url,
                    )

                yield from self._parse_sse_lines(resp.iter_lines())


# -----------------------------------------------------------------------------
# Streamlit Application State Initialization
# -----------------------------------------------------------------------------
def init_session_state():
    initial_auth_token = DEFAULT_AUTH_TOKEN or generate_dev_token(
        "00000000-0000-0000-0000-000000000001", DEFAULT_JWT_SECRET
    )
    defaults = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "auth_token": initial_auth_token,
        "jwt_secret": DEFAULT_JWT_SECRET,
        "workspaces": [
            "a12c1fa3-d3a6-4ffd-a0b1-77b8492f8ce5",
            "4f25a32a-936d-45f0-bac1-f372dbc34236",
            "457fddf2-b48d-422e-8968-97248120150c",
            "4853bbb2-b01f-4197-a68d-cb12c80aa91e",
            "ea9b73e8-c7a1-4163-9ed1-a6a177c5afca",
            "dd0f2552-7340-4aff-8177-cc0adb8ee0c6",
        ],
        "active_workspace_id": "a12c1fa3-d3a6-4ffd-a0b1-77b8492f8ce5",
        "workspace_details": None,
        "workspace_sources": {},   # workspace_id -> list of source dicts
        "workspace_commits": {},   # workspace_id -> list of commit dicts
        "conversations": [],
        "active_conversation_id": "8368832f-e723-406a-8303-c0c412932b73",
        "active_turn_id": None,
        "active_turn_mode": None,
        "active_turn_status": None,
        "last_event_sequence": 0,
        "live_events": [],
        "accumulated_answer": "",
        "provenance_status": None,
        "evidence_refs": [],
        "research_evidence": [],
        "routing": None,
        "answer_details": None,
        "turn_timings": None,
        "study_report": None,
        "raw_sse_log": [],
        "last_request_debug": None,
        "stage_timings": [],
        "turn_start_time": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_client() -> NeosisAPIClient:
    return NeosisAPIClient(
        base_url=st.session_state["api_base_url"],
        token=st.session_state["auth_token"],
    )


# -----------------------------------------------------------------------------
# UI Layout & Panels
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="NeosisLM Chapter 4 E2E Testbed",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    client = get_client()

    # --- Custom CSS Styling ---
    st.markdown(
        """
        <style>
        .testbed-header {
            font-size: 1.85rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.1rem;
        }
        .testbed-subtitle {
            font-size: 0.95rem;
            color: #64748B;
            margin-bottom: 1.2rem;
        }
        .badge-status {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }
        .badge-ok { background-color: #DCFCE7; color: #166534; }
        .badge-warn { background-color: #FEF3C7; color: #92400E; }
        .badge-err { background-color: #FEE2E2; color: #991B1B; }
        .badge-info { background-color: #E0E7FF; color: #3730A3; }
        .card-box {
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 12px 16px;
            background-color: #F8FAFC;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # SIDEBAR: Runtime Status, Workspace & Conversation Management
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### NeosisLM Runtime")

        # 1. Connection / Runtime Status
        st.markdown("#### 1. Connection & Auth")
        api_url = st.text_input("API Base URL", value=st.session_state["api_base_url"])
        if api_url != st.session_state["api_base_url"]:
            st.session_state["api_base_url"] = api_url
            st.rerun()

        token_input = st.text_input(
            "Bearer Auth Token",
            value=st.session_state["auth_token"],
            type="password",
            help="HTTP Bearer JWT token validated by get_current_user",
        )
        if token_input != st.session_state["auth_token"]:
            st.session_state["auth_token"] = token_input
            st.rerun()

        # Dev Token Generator Expander
        with st.expander("Dev JWT Generator", expanded=False):
            st.caption("Sign a valid dev JWT matching backend settings.SUPABASE_JWT_SECRET.")
            dev_user_id = st.text_input(
                "User UUID",
                value="00000000-0000-0000-0000-000000000001",
                key="dev_user_id_input",
            )
            dev_secret = st.text_input(
                "JWT Secret",
                value=st.session_state["jwt_secret"],
                type="password",
                key="dev_jwt_secret_input",
            )
            col_gen1, col_gen2 = st.columns(2)
            with col_gen1:
                if st.button("Generate Token", use_container_width=True):
                    try:
                        new_tok = generate_dev_token(dev_user_id, dev_secret)
                        st.session_state["auth_token"] = new_tok
                        st.session_state["jwt_secret"] = dev_secret
                        st.success("Dev token generated & set!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to generate: {exc}")
            with col_gen2:
                if st.button("New UUID", use_container_width=True):
                    st.session_state["dev_user_id_input"] = str(uuid.uuid4())
                    st.rerun()

        # Health & Worker Pool Check
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            if st.button("Check Health", use_container_width=True):
                try:
                    h = client.get_health()
                    status_col = "badge-ok" if h.get("status") == "ok" else "badge-warn"
                    s3_stat = h.get("s3", "unconfigured")
                    s3_col = "badge-ok" if s3_stat == "ok" else ("badge-err" if s3_stat == "failed" else "badge-warn")
                    st.markdown(
                        f"""
                        <div class="card-box">
                            <b>Health:</b> <span class="badge-status {status_col}">{h.get('status')}</span><br/>
                            Postgres: <code>{h.get('postgres')}</code><br/>
                            S3 / MinIO: <span class="badge-status {s3_col}">{s3_stat}</span><br/>
                            Neo4j: <code>{h.get('neo4j')}</code><br/>
                            Open Notebook: <code>{h.get('open_notebook')}</code>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    st.error(f"Health check failed: {exc}")

        with col_h2:
            if st.button("Worker Status", use_container_width=True):
                try:
                    w = client.get_worker_pool_status()
                    st.json(w)
                except Exception as exc:
                    st.error(f"Worker status failed: {exc}")

        st.caption("[Open MinIO Console (localhost:9001)](http://localhost:9001) · User: `minioadmin` / Pass: `minioadmin`")

        st.divider()

        # 2. Workspace Management
        st.markdown("#### 2. Workspace")
        known_workspaces = st.session_state["workspaces"]

        ws_input = st.text_input(
            "Add/Switch Workspace UUID",
            placeholder="e.g. 12345678-1234-5678-1234-567812345678",
        )
        if ws_input and ws_input not in known_workspaces:
            try:
                val_uuid = str(uuid.UUID(ws_input))
                if val_uuid not in known_workspaces:
                    known_workspaces.append(val_uuid)
                    st.session_state["workspaces"] = known_workspaces
                    st.session_state["active_workspace_id"] = val_uuid
                    st.rerun()
            except ValueError:
                st.error("Invalid UUID format")

        col_ws1, col_ws2 = st.columns(2)
        with col_ws1:
            if st.button("Create Workspace", use_container_width=True):
                try:
                    new_ws = client.create_workspace()
                    ws_id = str(new_ws.get("workspace_id"))
                    if ws_id not in known_workspaces:
                        known_workspaces.append(ws_id)
                        st.session_state["workspaces"] = known_workspaces
                    st.session_state["active_workspace_id"] = ws_id
                    st.session_state["workspace_details"] = new_ws
                    st.success(f"Created: {ws_id[:8]}...")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Create failed: {exc}")

        with col_ws2:
            if st.button("Refresh Details", use_container_width=True):
                if st.session_state["active_workspace_id"]:
                    try:
                        d = client.get_workspace(st.session_state["active_workspace_id"])
                        st.session_state["workspace_details"] = d
                        st.success("Refreshed")
                    except Exception as exc:
                        st.error(f"Refresh failed: {exc}")

        if known_workspaces:
            curr_idx = (
                known_workspaces.index(st.session_state["active_workspace_id"])
                if st.session_state["active_workspace_id"] in known_workspaces
                else 0
            )
            selected_ws = st.selectbox(
                "Active Workspace",
                options=known_workspaces,
                index=curr_idx,
                format_func=lambda x: f"Workspace {x[:8]}...",
            )
            if selected_ws != st.session_state["active_workspace_id"]:
                st.session_state["active_workspace_id"] = selected_ws
                try:
                    st.session_state["workspace_details"] = client.get_workspace(selected_ws)
                except Exception:
                    st.session_state["workspace_details"] = None
                st.rerun()
            elif not st.session_state.get("workspace_details"):
                try:
                    st.session_state["workspace_details"] = client.get_workspace(selected_ws)
                except Exception:
                    st.session_state["workspace_details"] = None

        # Display active workspace info
        ws_details = st.session_state.get("workspace_details")
        if ws_details:
            st.markdown(
                f"""
                <div class="card-box">
                    <b>ID:</b> <code>{ws_details.get('workspace_id')}</code><br/>
                    <b>Status:</b> <code>{ws_details.get('status')}</code><br/>
                    <b>Timeline Epoch:</b> <code>{ws_details.get('timeline_epoch', 1)}</code><br/>
                    <b>Active Commit:</b> <code>{str(ws_details.get('active_commit_id'))[:8] if ws_details.get('active_commit_id') else 'None'}</code><br/>
                    <b>Ground Version:</b> <code>{ws_details.get('ground_version', 1)}</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        # 3. Conversation Management
        st.markdown("#### 3. Conversation")
        active_ws_id = st.session_state.get("active_workspace_id")

        if active_ws_id:
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                conv_title_input = st.text_input("New Conversation Title", value="Test Conversation", key="conv_title_in")
            with col_c2:
                st.write("")
                st.write("")
                if st.button("Create", use_container_width=True):
                    try:
                        new_conv = client.create_conversation(active_ws_id, title=conv_title_input)
                        conv_id = str(new_conv.get("conversation_id"))
                        st.session_state["active_conversation_id"] = conv_id
                        st.success(f"Created {conv_id[:8]}...")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Conv create failed: {exc}")

            # Refresh & Select conversation
            try:
                conv_data = client.list_conversations(active_ws_id, status_filter="active", limit=50)
                conversations = conv_data.get("conversations", [])
                st.session_state["conversations"] = conversations

                if conversations:
                    conv_ids = [str(c["conversation_id"]) for c in conversations]
                    c_idx = (
                        conv_ids.index(st.session_state["active_conversation_id"])
                        if st.session_state.get("active_conversation_id") in conv_ids
                        else 0
                    )
                    selected_c = st.selectbox(
                        "Active Conversation",
                        options=conv_ids,
                        index=c_idx,
                        format_func=lambda cid: next(
                            (f"{c.get('title', 'Untitled')[:20]} ({cid[:6]}...)" for c in conversations if str(c.get("conversation_id")) == cid),
                            cid[:8]
                        ),
                    )
                    if selected_c != st.session_state.get("active_conversation_id"):
                        st.session_state["active_conversation_id"] = selected_c
                        st.rerun()

                    # Auto-detect latest turn and active/running state for this conversation
                    try:
                        t_data = client.list_turns(active_ws_id, selected_c, limit=3)
                        t_list = t_data.get("turns", [])
                        if t_list:
                            latest_t = t_list[0]
                            st.session_state["active_turn_id"] = str(latest_t.get("turn_id"))
                            st.session_state["active_turn_status"] = latest_t.get("status")
                            # Hydrate assistant answer and event stream if state is currently empty
                            if not st.session_state.get("accumulated_answer") and latest_t.get("assistant_message"):
                                st.session_state["accumulated_answer"] = latest_t.get("assistant_message")
                            if not st.session_state.get("live_events") and latest_t.get("turn_id"):
                                try:
                                    ev_data = client.get_turn_events_sync(active_ws_id, selected_c, str(latest_t["turn_id"]))
                                    raw_evs = ev_data.get("events", [])
                                    if raw_evs:
                                        st.session_state["live_events"] = [
                                            {"id": e.get("sequence"), "event": e.get("event_type"), "data": e.get("payload")}
                                            for e in raw_evs
                                        ]
                                        st.session_state["last_event_sequence"] = max(e.get("sequence", 0) for e in raw_evs)
                                except Exception:
                                    pass
                            if latest_t.get("status") in ("pending", "running"):
                                st.warning(f"⚠️ Turn `{str(latest_t.get('turn_id'))[:8]}` is in progress ({latest_t.get('status')}).")
                                if st.button("🛑 Force Unlock Conversation", key="sidebar_force_cancel_btn", use_container_width=True):
                                    try:
                                        client.cancel_turn(active_ws_id, selected_c, str(latest_t.get("turn_id")))
                                        st.session_state["active_turn_status"] = "cancelled"
                                        st.success("Turn cancelled! Conversation unlocked.")
                                        st.rerun()
                                    except Exception as c_err:
                                        st.error(f"Cancel failed: {c_err}")
                        else:
                            st.session_state["active_turn_id"] = None
                            st.session_state["active_turn_status"] = None
                    except Exception:
                        pass
                else:
                    st.info("No conversations in this workspace yet.")
            except Exception as exc:
                st.warning(f"Failed listing conversations: {exc}")
        else:
            st.info("Select or create a workspace first.")

        st.divider()

        # 4. Stage Timers & Raw Execution Logs (Option A - Dynamic)
        st.markdown("#### 4. Stage Timers & Raw Logs")
        sidebar_timers_ph = st.empty()
        sidebar_logs_ph = st.empty()
        sidebar_trace_ph = st.empty()

        def update_sidebar_views():
            stage_timings = st.session_state.get("stage_timings", [])
            with sidebar_timers_ph.container():
                with st.expander("⏱️ Stage Timers Breakdown", expanded=True):
                    if stage_timings:
                        total_t = stage_timings[-1].get("elapsed", 0.0)
                        st.caption(f"Total Turn Time: **{total_t:.1f}s** ({len(stage_timings)} stages observed)")
                        for item in stage_timings:
                            ev_name = item.get("stage", "stage")
                            duration = item.get("duration", 0.0)
                            elapsed = item.get("elapsed", 0.0)
                            st.markdown(
                                f"""<div style="font-size:0.83rem; margin-bottom:4px; padding:3px 6px; background:#f1f5f9; border-radius:4px; border-left:3px solid #0284c7;">
                                    <b>{ev_name}</b><br/>
                                    <span style="color:#059669; font-weight:600;">+{duration:.1f}s</span> &nbsp;·&nbsp; <span style="color:#64748b;">(T+{elapsed:.1f}s)</span>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No turn executed yet. Timers will populate incrementally as events arrive.")

            with sidebar_logs_ph.container():
                with st.expander("📜 Live Raw SSE Logs", expanded=True):
                    raw_events = st.session_state.get("live_events", [])
                    if raw_events:
                        st.caption(f"Total Events Observed: {len(raw_events)}")
                        st.code(json.dumps(raw_events[-15:], indent=2, default=str), language="json")
                    else:
                        st.caption("No SSE events observed yet.")

            with sidebar_trace_ph.container():
                with st.expander("🔍 Last API Request Trace", expanded=False):
                    dbg = st.session_state.get("last_request_debug")
                    if dbg:
                        st.json(dbg)
                    else:
                        st.caption("No request debug trace captured yet.")

        # Initial render
        update_sidebar_views()

    # -------------------------------------------------------------------------
    # MAIN AREA: Integration Test Panels
    # -------------------------------------------------------------------------
    st.markdown('<div class="testbed-header">NeosisLM Chapter 4 Integration Testbed</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="testbed-subtitle">Full-stack HTTP Integration Console · Zero Engine Bypass · Canonical SSE · Real ARQ & Database Verification</div>',
        unsafe_allow_html=True,
    )

    active_ws_id = st.session_state.get("active_workspace_id")
    active_conv_id = st.session_state.get("active_conversation_id")

    if not active_ws_id or not active_conv_id:
        st.warning(
            "Please create or select both an **Active Workspace** and an **Active Conversation** in the sidebar to begin testing."
        )
        return

    # Tabs for the 6 primary developer test sections
    tab_chat, tab_sources, tab_replay, tab_promotions, tab_rollback, tab_debug = st.tabs([
        "Chat & Execution",
        "Storage / Ingestion Integration",
        "Turn Replay & Inspection",
        "Promotion Testing",
        "Rollback & Timeline Fencing",
        "Debug / Raw API Inspector",
    ])

    # =========================================================================
    # TAB 1: Chat & Execution (Ground Mode & Research Mode)
    # =========================================================================
    with tab_chat:
        st.markdown("### Conversation Turn Execution")

        col_mode, col_stream = st.columns([3, 1])
        with col_mode:
            exec_mode = st.radio(
                "Execution Mode",
                options=["ground", "research"],
                format_func=lambda m: "Ground Mode (Workspace Sources + Open Notebook Projection)" if m == "ground" else "Research Mode (Autonomous Deep Research + ARQ Worker)",
                horizontal=True,
            )
        with col_stream:
            stream_toggle = st.checkbox("Stream SSE Events", value=True, help="Stream live event frames incrementally via text/event-stream")

        # Ground Mode controls: Source Scope selection
        selected_source_ids: List[str] = []
        if exec_mode == "ground":
            ws_sources = st.session_state.get("workspace_sources", {}).get(active_ws_id, [])
            source_options = {
                str(s["source_id"]): f"{s.get('filename', 'Source')} ({str(s['source_id'])[:8]}...)"
                for s in ws_sources
            }

            st.caption("Source Isolation (Test B): Leave empty to search all workspace sources, or select specific sources to verify backend-enforced source isolation.")
            if source_options:
                selected_source_ids = st.multiselect(
                    "Selected Source Scope (Optional)",
                    options=list(source_options.keys()),
                    format_func=lambda sid: source_options.get(sid, sid),
                    help="Populates TurnCreate.source_scope. Backend strictly enforces isolation.",
                )
            else:
                st.caption("No sources uploaded in this session yet. Upload files in the 'Source Ingestion' tab, or input manual UUIDs below.")
                custom_source = st.text_input("Manual Source UUID Scope (optional comma-separated)")
                if custom_source:
                    selected_source_ids = [s.strip() for s in custom_source.split(",") if s.strip()]

        # Research Mode controls: Options
        AUTO_ROUTE = "Auto (recommended)"
        research_engine = AUTO_ROUTE
        engine_choices = [AUTO_ROUTE, "open_deep_research", "storm", "gpt_researcher"]
        token_budget = 8000
        if exec_mode == "research":
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                research_engine = st.selectbox(
                    "Research Engine", engine_choices, index=0,
                    help=(
                        "Auto: simple/normal questions use Open Deep Research (low/balanced budget); clearly deep "
                        "investigations go to STORM and broad source discovery to GPT-Researcher when eligible; a weak ODR "
                        "answer escalates once to the specialist that fits the diagnosed gap. Engines never run in parallel. "
                        "Gates: ROUTER_AUTO_STORM / ROUTER_AUTO_GPT_RESEARCHER (auto|off). Explicit engines are for testing."
                    ),
                )
            with col_r2:
                token_budget = st.number_input(
                    "Context budget (tokens)", min_value=1000, max_value=64000, value=8000, step=1000,
                    help=(
                        "Sizes the workspace/conversation context handed to the engine. It is not an execution cap: only "
                        "Open Deep Research enforces call/token caps mid-run (its budget profile); STORM and GPT-Researcher "
                        "only record usage afterwards."
                    ),
                )
            if research_engine in ("storm", "gpt_researcher"):
                st.caption(f"{research_engine} runs its own full upstream pipeline, takes only the question (no workspace "
                           "context), has no mid-run budget control and can run several minutes.")
            st.caption("To get a cited paper of the whole session, type e.g. *Compile everything we've discussed into a "
                       "research paper*, or use **Compile study report** below.")

        # Message Input
        default_prompt = (
            "What do the workspace sources say about this topic?"
            if exec_mode == "ground"
            else "Investigate the primary architectural advantages of event-driven knowledge architectures."
        )
        user_message = st.text_area("Message / Objective", value=default_prompt, height=90)

        # Submit & Cancellation Controls
        col_sub, col_cancel, col_reconn = st.columns([2, 2, 2])
        active_turn_id = st.session_state.get("active_turn_id")

        with col_sub:
            submit_btn = st.button("Submit Turn", use_container_width=True, type="primary")

        with col_cancel:
            cancel_btn = st.button("Cancel Turn", use_container_width=True, disabled=not active_turn_id)

        with col_reconn:
            reconn_btn = st.button("Reconnect Stream", use_container_width=True, disabled=not active_turn_id)

        # ---------------------------------------------------------------------
        # Turn Cancellation Handler
        # ---------------------------------------------------------------------
        if cancel_btn and active_turn_id:
            try:
                with st.spinner("Cancelling active turn..."):
                    canc_resp = client.cancel_turn(active_ws_id, active_conv_id, active_turn_id)
                    st.session_state["active_turn_status"] = "cancelled"
                    st.warning(f"Turn {active_turn_id[:8]} cancelled! Terminal status: {canc_resp.get('status')}")
            except Exception as exc:
                st.error(f"Cancellation error: {exc}")

        # ---------------------------------------------------------------------
        # Stream Reconnect Handler (Test D)
        # ---------------------------------------------------------------------
        if reconn_btn and active_turn_id:
            cursor = st.session_state.get("last_event_sequence", 0)
            st.info(f"Reconnecting to stream for Turn `{active_turn_id}` from sequence `{cursor}`...")

            event_display = st.empty()
            reconnected_events = list(st.session_state.get("live_events", []))

            try:
                stream_gen = client.stream_turn_events(
                    workspace_id=active_ws_id,
                    conversation_id=active_conv_id,
                    turn_id=active_turn_id,
                    after_sequence=cursor,
                    last_event_id=str(cursor),
                )

                for ev in stream_gen:
                    ev_type = ev.get("event")
                    seq = ev.get("id")
                    if seq is not None and isinstance(seq, int):
                        st.session_state["last_event_sequence"] = max(st.session_state["last_event_sequence"], seq)

                    reconnected_events.append(ev)
                    st.session_state["live_events"] = reconnected_events

                    event_display.markdown(f"**Latest Replayed Event:** `{ev_type}` (Sequence: `{seq}`)")

                    if ev_type in TERMINAL_EVENT_TYPES:
                        st.success(f"Stream completed terminal state: `{ev_type}`")
                        break

            except Exception as exc:
                st.error(f"Reconnect error: {exc}")

        # ---------------------------------------------------------------------
        # Turn Execution Handler (Submit)
        # ---------------------------------------------------------------------
        if submit_btn and user_message.strip():
            # Reset UI state for new turn
            st.session_state["accumulated_answer"] = ""
            st.session_state["provenance_status"] = None
            st.session_state["evidence_refs"] = []
            st.session_state["research_evidence"] = []
            st.session_state["routing"] = None
            st.session_state["answer_details"] = None
            st.session_state["turn_timings"] = None
            st.session_state["study_report"] = None
            st.session_state["live_events"] = []
            st.session_state["last_event_sequence"] = 0

            turn_create_body: Dict[str, Any] = {
                "mode": exec_mode,
                "message": user_message.strip(),
            }
            if exec_mode == "ground" and selected_source_ids:
                turn_create_body["source_scope"] = selected_source_ids
            if exec_mode == "research":
                if research_engine == AUTO_ROUTE:
                    turn_create_body["research_options"] = {"routing_mode": "auto", "token_budget": token_budget}
                else:
                    turn_create_body["research_options"] = {
                        "routing_mode": "explicit",
                        "engine": research_engine,
                        "token_budget": token_budget,
                    }

            if stream_toggle:
                # STREAMING SSE PATH (POST /turns?stream=true)
                status_box = st.status("Executing turn via SSE stream...", expanded=True)
                answer_placeholder = st.empty()
                stream_events_list: List[Dict[str, Any]] = []

                t_start = time.time()
                st.session_state["turn_start_time"] = t_start
                st.session_state["stage_timings"] = []
                last_stage_time = t_start

                try:
                    event_generator = client.stream_turn_submit(
                        workspace_id=active_ws_id,
                        conversation_id=active_conv_id,
                        turn_create=turn_create_body,
                    )

                    for ev in event_generator:
                        now_t = time.time()
                        elapsed_total = now_t - t_start
                        duration_stage = now_t - last_stage_time
                        last_stage_time = now_t

                        ev_type = ev.get("event")
                        seq = ev.get("id")
                        payload = ev.get("data")

                        if seq is not None and isinstance(seq, int):
                            st.session_state["last_event_sequence"] = max(st.session_state["last_event_sequence"], seq)

                        stream_events_list.append(ev)
                        st.session_state["live_events"] = stream_events_list

                        # Stage label for timing breakdown
                        stage_label = ev_type or "event"
                        if ev_type == "scratchpad_entry" and isinstance(payload, dict):
                            c = payload.get("content", "")
                            stage_label = f"scratchpad: {c[:35]}..." if len(c) > 35 else f"scratchpad: {c}"
                        elif ev_type in ("turn.research_planning", "turn.researching") and isinstance(payload, dict):
                            m = payload.get("message", "")
                            if m:
                                stage_label = f"{ev_type} ({m[:30]}...)"

                        st.session_state["stage_timings"].append({
                            "stage": stage_label,
                            "duration": round(duration_stage, 2),
                            "elapsed": round(elapsed_total, 2),
                        })

                        # Status update with live duration
                        status_box.write(f"Event `[{seq or '-'}]` **{ev_type}** · *+{duration_stage:.1f}s* &nbsp;`(T+{elapsed_total:.1f}s)`")

                        # Dynamically update sidebar stage timers and raw logs in real time
                        try:
                            update_sidebar_views()
                        except Exception:
                            pass

                        # Token incremental streaming
                        if ev_type == "token" and isinstance(payload, dict):
                            token_txt = payload.get("token", "")
                            st.session_state["accumulated_answer"] += token_txt
                            answer_placeholder.markdown(st.session_state["accumulated_answer"])

                        # Ground answer complete event
                        elif ev_type == "ground_answer" and isinstance(payload, dict):
                            ans = payload.get("answer", "")
                            if ans:
                                st.session_state["accumulated_answer"] = ans
                                answer_placeholder.markdown(ans)
                            st.session_state["provenance_status"] = payload.get("provenance_status")
                            st.session_state["evidence_refs"] = payload.get("evidence", [])

                        # Research status & lifecycle events
                        elif ev_type == "turn.research_started" and isinstance(payload, dict):
                            if payload.get("turn_id"):
                                st.session_state["active_turn_id"] = str(payload.get("turn_id"))
                            if payload.get("run_id"):
                                status_box.write(f"Research Run admitted: `{payload.get('run_id')}`")
                        elif ev_type in ("turn.completed", "done"):
                            if isinstance(payload, dict) and payload.get("assistant_message"):
                                st.session_state["accumulated_answer"] = payload.get("assistant_message")
                                answer_placeholder.markdown(st.session_state["accumulated_answer"])
                            if isinstance(payload, dict) and payload.get("evidence_details") is not None:
                                st.session_state["evidence_refs"] = payload.get("evidence_details") or []
                                st.session_state["ground_unresolved"] = payload.get("unresolved_citations") or []
                                st.session_state["provenance_status"] = payload.get("provenance_status")
                            if isinstance(payload, dict):
                                st.session_state["research_evidence"] = payload.get("evidence") or st.session_state.get("research_evidence") or []
                                st.session_state["routing"] = payload.get("routing") or st.session_state.get("routing")
                                st.session_state["study_report"] = payload.get("study_report") or st.session_state.get("study_report")
                                st.session_state["answer_details"] = payload.get("answer_details") or st.session_state.get("answer_details")
                                st.session_state["turn_timings"] = payload.get("timings") or st.session_state.get("turn_timings")
                            status_box.update(label="Turn Completed Successfully!", state="complete", expanded=False)
                            break
                        elif ev_type in ("turn.cancelled", "cancelled"):
                            status_box.update(label="Turn Cancelled.", state="error", expanded=False)
                            break
                        elif ev_type in ("turn.failed", "error"):
                            err_msg = ""
                            if isinstance(payload, dict):
                                err_msg = payload.get("assistant_message") or payload.get("error") or payload.get("message") or payload.get("reason") or ""
                            if err_msg:
                                st.session_state["accumulated_answer"] = f"**Execution Failed:** {err_msg}"
                                answer_placeholder.markdown(st.session_state["accumulated_answer"])
                            status_box.update(label=f"Turn Failed: {err_msg}" if err_msg else "Turn Failed.", state="error", expanded=True)
                            break

                    try:
                        update_sidebar_views()
                    except Exception:
                        pass

                except Exception as exc:
                    err_str = str(exc)
                    status_box.update(label=f"Stream error: {err_str}", state="error")
                    if "409" in err_str or "conversation_turn_in_progress" in err_str:
                        st.error("⚠️ **Conflict [409]: A turn is already in progress (or was interrupted) for this conversation.**")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            if st.button("🛑 Force Unlock Conversation", key="btn_unlock_stream_409"):
                                try:
                                    t_data = client.list_turns(active_ws_id, active_conv_id, limit=5)
                                    for t in t_data.get("turns", []):
                                        if t.get("status") in ("pending", "running"):
                                            client.cancel_turn(active_ws_id, active_conv_id, str(t["turn_id"]))
                                    st.success("Unlocked! You can now resubmit your turn.")
                                    st.rerun()
                                except Exception as c_err:
                                    st.error(f"Unlock failed: {c_err}")
                        with col_c2:
                            if st.button("➕ Start Fresh Conversation", key="btn_new_stream_409"):
                                try:
                                    new_c = client.create_conversation(active_ws_id, title="New Conversation")
                                    st.session_state["active_conversation_id"] = str(new_c["conversation_id"])
                                    st.session_state["active_turn_id"] = None
                                    st.rerun()
                                except Exception as n_err:
                                    st.error(f"New conversation failed: {n_err}")
                    else:
                        st.error(f"Streaming execution error: {exc}")

            else:
                # SYNCHRONOUS / 202 ACCEPTED PATH (POST /turns?stream=false)
                with st.spinner("Submitting turn to canonical API..."):
                    try:
                        turn_resp = client.submit_turn_sync(
                            workspace_id=active_ws_id,
                            conversation_id=active_conv_id,
                            turn_create=turn_create_body,
                        )
                        t_id = str(turn_resp.get("turn_id"))
                        st.session_state["active_turn_id"] = t_id
                        st.session_state["active_turn_status"] = turn_resp.get("status")
                        st.session_state["accumulated_answer"] = turn_resp.get("assistant_message") or ""
                        st.session_state["evidence_refs"] = turn_resp.get("ground_evidence_refs") or []

                        st.success(f"Turn submitted (Status: {turn_resp.get('status')}, ID: {t_id[:8]}...)")

                        # If status is running or pending, poll or fetch events
                        ev_data = client.get_turn_events_sync(active_ws_id, active_conv_id, t_id)
                        st.session_state["live_events"] = [
                            {"id": e.get("sequence"), "event": e.get("event_type"), "data": e.get("payload")}
                            for e in ev_data.get("events", [])
                        ]

                    except Exception as exc:
                        err_str = str(exc)
                        if "409" in err_str or "conversation_turn_in_progress" in err_str:
                            st.error("⚠️ **Conflict [409]: A turn is already in progress for this conversation.**")
                            if st.button("🛑 Force Unlock Conversation", key="btn_unlock_sync_409"):
                                try:
                                    t_data = client.list_turns(active_ws_id, active_conv_id, limit=5)
                                    for t in t_data.get("turns", []):
                                        if t.get("status") in ("pending", "running"):
                                            client.cancel_turn(active_ws_id, active_conv_id, str(t["turn_id"]))
                                    st.success("Unlocked! You can now resubmit your turn.")
                                    st.rerun()
                                except Exception as c_err:
                                    st.error(f"Unlock failed: {c_err}")
                        else:
                            st.error(f"Submission failed: {exc}")

        # Display Assistant Output
        st.markdown("#### Assistant Response")
        ans_text = st.session_state.get("accumulated_answer")
        if ans_text:
            st.markdown(ans_text)
        else:
            st.caption("No answer output yet.")

        # Research evidence + routing come with the completion event (also recovered from replayed events).
        for _ev in st.session_state.get("live_events", []) or []:
            _p = _ev.get("data")
            if _ev.get("event") in ("turn.completed", "done") and isinstance(_p, dict):
                if _p.get("evidence") and not st.session_state.get("research_evidence"):
                    st.session_state["research_evidence"] = _p["evidence"]
                if _p.get("routing") and not st.session_state.get("routing"):
                    st.session_state["routing"] = _p["routing"]
                if _p.get("study_report") and not st.session_state.get("study_report"):
                    st.session_state["study_report"] = _p["study_report"]
                if _p.get("answer_details") and not st.session_state.get("answer_details"):
                    st.session_state["answer_details"] = _p["answer_details"]
                if _p.get("timings") and not st.session_state.get("turn_timings"):
                    st.session_state["turn_timings"] = _p["timings"]

        routing = st.session_state.get("routing")
        if routing:
            # One concise status line; the full routing record stays in a collapsed expander.
            _esc = routing.get("escalation") or {}
            _esc_txt = (f"escalated {_esc.get('from')} → {_esc.get('to')} ({_esc.get('reason')})" if routing.get("escalated")
                        else (f"escalation to {_esc.get('to')} blocked" if _esc.get("blocked") else "no escalation"))
            _total = (routing.get("timings") or {}).get("total_ms")
            _pref = routing.get("preferred_engine")
            st.caption(
                f"Answered by **{routing.get('answered_by')}** ({routing.get('answer_budget_profile') or 'default'} profile)"
                + (f" · preferred {_pref}" if _pref and _pref != routing.get("answered_by") else "")
                + f" · {_esc_txt}"
                + (f" · {_total / 1000:.0f}s" if _total else "")
                + (" · budget enforced" if routing.get("budget_enforced") else " · wall-clock/config bounded only")
            )
            _first = (routing.get("attempts") or [{}])[0].get("assessment") or {}
            _unretrieved = (_first.get("metrics") or {}).get("cited_urls_not_retrieved") or []
            if _unretrieved and routing.get("answered_by") == "open_deep_research":
                st.caption(f"⚠ {len(_unretrieved)} cited link(s) were not retrieved during this turn (written from the model's "
                           "memory) and are not part of the evidence below.")
            if st.session_state.get("answer_details"):
                with st.expander("Full upstream output (STORM article)", expanded=False):
                    st.markdown(st.session_state["answer_details"])
            with st.expander("Engine routing details", expanded=False):
                esc = routing.get("escalation") or {}
                st.markdown(
                    f"**Preferred:** `{routing.get('preferred_engine')}` · **Answered by:** `{routing.get('answered_by')}` · mode `{routing.get('mode')}`"
                    + (f" · intent `{routing.get('intent')}`" if routing.get("intent") else "")
                    + (f" · format `{routing.get('answer_format')}`" if routing.get("answer_format") else "")
                )
                if esc:
                    if esc.get("blocked"):
                        st.warning(f"Escalation {esc.get('from')} → {esc.get('to')} for `{esc.get('reason')}` was blocked: {esc['blocked']}")
                    elif esc.get("specialist_failed"):
                        st.warning(f"Escalated to {esc.get('to')} for `{esc.get('reason')}`, which failed ({esc['specialist_failed']}); kept the ODR answer.")
                    else:
                        st.info(f"Escalated {esc.get('from')} → {esc.get('to')}: {esc.get('reason')}"
                                + (f" (diagnosis: {', '.join(esc.get('diagnosis') or [])})" if esc.get("diagnosis") else ""))
                else:
                    st.caption("No escalation: the first engine's answer was used.")
                badge = "enforced" if routing.get("budget_enforced") else "NOT enforced"
                st.markdown(f"**Budget:** {badge} — {routing.get('budget_note', '')}")
                attempts = routing.get("attempts") or []
                if attempts:
                    st.table([{
                        "#": a.get("sequence"), "engine": a.get("engine"), "profile": a.get("budget_profile") or "-",
                        "trigger": a.get("trigger"), "status": a.get("status"),
                        "latency_s": round((a.get("latency_ms") or 0) / 1000, 1),
                        "tokens": (a.get("input_tokens") or 0) + (a.get("output_tokens") or 0),
                        "evidence": a.get("evidence_count"),
                        "verdict": ((a.get("assessment") or {}).get("failure") or "sufficient") if a.get("assessment") else "-",
                        "tokens/cost": "/".join((a.get("usage_quality") or {}).values()) or "-",
                        "reason": a.get("reason"),
                    } for a in attempts])
                tt = st.session_state.get("turn_timings") or {}
                if tt or routing.get("timings"):
                    st.caption("Timings: " + ", ".join(f"{k}={v}" for k, v in {**(routing.get("timings") or {}), **tt}.items() if v is not None))
                for a in attempts:
                    em = a.get("engine_metrics") or {}
                    if em:
                        st.caption(f"#{a.get('sequence')} {a.get('engine')} engine metrics: "
                                   + ", ".join(f"{k}={v}" for k, v in em.items() if k not in ("limits",)))

        research_evidence = st.session_state.get("research_evidence") or []
        if research_evidence:
            with st.expander(f"Research evidence ({len(research_evidence)})", expanded=False):
                for i, e in enumerate(research_evidence, start=1):
                    title = e.get("title") or e.get("url") or "source"
                    st.markdown(f"**{i}. [{title}]({e.get('url')})** · `{e.get('retriever')}` · evidence `{e.get('evidence_id')}`")
                    if e.get("excerpt"):
                        st.caption(e["excerpt"][:300])

        study = st.session_state.get("study_report")
        if study:
            st.success(f"Study-session paper saved (report `{study.get('report_id')}`"
                       + (f", version {study.get('version')}" if study.get("version") else "")
                       + f"); review candidate `{study.get('candidate_id')}` is pending review.")
            for w in study.get("warnings") or []:
                st.warning(w)

        if st.button("📄 Compile study report", key="btn_compile_study_report",
                     help="Explicitly compile this whole conversation into a cited paper. Runs no new research."):
            with st.spinner("Compiling the study session (one LLM call over this conversation's material)..."):
                try:
                    rep = client.compile_study_report(active_ws_id, active_conv_id)
                    st.session_state["accumulated_answer"] = rep.get("content", "")
                    st.session_state["study_report"] = rep
                    st.rerun()
                except Exception as rep_err:
                    st.error(f"Study report failed: {rep_err}")
        if st.button("📚 Show saved study reports", key="btn_list_study_reports"):
            try:
                items = client.list_study_reports(active_ws_id, active_conv_id).get("items", [])
                if not items:
                    st.caption("No study-session papers saved for this conversation yet.")
                for item in items:
                    with st.expander(f"Version {item.get('version')} · {item.get('created_at', '')[:19]} · {item.get('report_id')}"):
                        if item.get("warnings"):
                            st.warning(item["warnings"])
                        st.markdown(item.get("content", ""))
            except Exception as list_err:
                st.error(f"Could not list study reports: {list_err}")

        # Ground Provenance & Evidence Details
        prov = st.session_state.get("provenance_status")
        ev_refs = st.session_state.get("evidence_refs")
        if prov or ev_refs:
            with st.expander("Ground Provenance & Evidence", expanded=True):
                if prov:
                    prov_badge = "badge-ok" if prov == "fully_grounded" else "badge-warn"
                    st.markdown(f"Provenance Status: <span class='badge-status {prov_badge}'>{prov}</span>", unsafe_allow_html=True)
                if ev_refs and all(isinstance(e, dict) and e.get("source_id") for e in ev_refs):
                    for e in ev_refs:
                        st.markdown(f"**{e.get('title') or e['source_id']}** · canonical source `{e['source_id']}`"
                                    + (" · cited inline" if e.get("cited_inline") else "")
                                    + (f" · [document]({client.base_url.rstrip('/')}{e['document_ref']})"
                                       if e.get("document_ref") else ""))
                        if e.get("excerpt"):
                            st.caption(e["excerpt"][:300])
                elif ev_refs:
                    st.markdown("Evidence References:")
                    st.json(ev_refs)
                if prov == "none":
                    st.warning("This answer cited none of your workspace sources, so it is not verified against them.")
                for u in st.session_state.get("ground_unresolved") or []:
                    st.warning(f"Unresolved citation `{u.get('upstream_id')}`: {u.get('reason')} (not shown as evidence)")

        # ---------------------------------------------------------------------
        # SECTION 7: SSE Event Viewer
        # ---------------------------------------------------------------------
        st.markdown("#### Real-Time SSE Event Stream")
        events = st.session_state.get("live_events", [])
        last_seq = st.session_state.get("last_event_sequence", 0)

        st.caption(f"Total events observed: **{len(events)}** | Cursor (`Last-Event-ID`): **{last_seq}**")

        if events:
            with st.expander("Inspect Event Stream Log", expanded=True):
                for idx, ev in enumerate(reversed(events)):
                    seq_str = f"Seq #{ev.get('id')}" if ev.get("id") is not None else "Pulse"
                    ev_type = ev.get("event")
                    with st.container():
                        st.markdown(f"**{seq_str}** · `{ev_type}`")
                        safe_display_json(ev.get("data"))
                        st.divider()

    # =========================================================================
    # TAB 2: Storage / Ingestion Integration (S3/MinIO -> Postgres -> ARQ -> Open Notebook)
    # =========================================================================
    with tab_sources:
        st.markdown("### Storage / Ingestion Integration")
        st.caption(
            "End-to-end pipeline verification: **S3 / MinIO Object Store** $\\rightarrow$ "
            "**PostgreSQL Source/Snapshot** $\\rightarrow$ **ARQ / Redis Parsing & Chunking** $\\rightarrow$ "
            "**Open Notebook Projection**."
        )

        st.markdown(
            """
            <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
                <div class="card-box" style="flex: 1; min-width: 160px; text-align: center;">
                    <b>1. S3 / MinIO</b><br/><span style="font-size: 0.8rem; color: #475569;">Raw Object Storage</span>
                </div>
                <div class="card-box" style="flex: 1; min-width: 160px; text-align: center;">
                    <b>2. PostgreSQL</b><br/><span style="font-size: 0.8rem; color: #475569;">Source & Snapshot</span>
                </div>
                <div class="card-box" style="flex: 1; min-width: 160px; text-align: center;">
                    <b>3. ARQ / Redis</b><br/><span style="font-size: 0.8rem; color: #475569;">parse_and_chunk_job</span>
                </div>
                <div class="card-box" style="flex: 1; min-width: 160px; text-align: center;">
                    <b>4. Open Notebook</b><br/><span style="font-size: 0.8rem; color: #475569;">Knowledge Projection</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Upload Source Document",
            type=["txt", "pdf", "md", "json", "csv"],
            help="Direct multipart upload to FastAPI endpoint POST /api/v1/workspaces/{id}/files",
        )

        if uploaded_file is not None:
            if st.button("Upload Document to S3 & Enqueue Pipeline", key="upload_file_btn", type="primary"):
                try:
                    with st.spinner("Uploading to S3 / MinIO via FastAPI..."):
                        content = uploaded_file.getvalue()
                        res = client.upload_file(
                            workspace_id=active_ws_id,
                            filename=uploaded_file.name,
                            content=content,
                            mime_type=uploaded_file.type or "application/octet-stream",
                        )
                        s_id = str(res.get("source_id"))
                        snapshots = res.get("snapshots", [])
                        snap = snapshots[0] if snapshots else {}
                        file_uri = snap.get("file_uri", f"s3://neosislm-dev/{active_ws_id}/...")
                        sha256 = snap.get("checksum_sha256", "n/a")

                        st.success(f"Source Uploaded! ID: `{s_id}`")
                        st.info(f"S3 Object URI: `{file_uri}`")

                        # Track in session state
                        if active_ws_id not in st.session_state["workspace_sources"]:
                            st.session_state["workspace_sources"][active_ws_id] = []
                        st.session_state["workspace_sources"][active_ws_id].append({
                            "source_id": s_id,
                            "filename": uploaded_file.name,
                            "size": len(content),
                            "file_uri": file_uri,
                            "checksum_sha256": sha256,
                            "status": res.get("processing_status", "pending"),
                            "verified_s3": False,
                        })
                        st.json(res)
                except Exception as exc:
                    st.error(f"Upload error: {exc}")

        st.divider()
        st.markdown("#### Known Workspace Sources & Pipeline Status")

        ws_sources = st.session_state.get("workspace_sources", {}).get(active_ws_id, [])
        if ws_sources:
            for s in ws_sources:
                sid = s["source_id"]
                file_uri = s.get("file_uri", "s3://neosislm-dev/...")
                status_str = s.get("status", "unknown")
                status_badge = "badge-ok" if status_str == "completed" else ("badge-warn" if status_str in ("pending", "processing") else "badge-err")

                with st.expander(f"{s['filename']} ({sid[:8]}...) - Status: {status_str}", expanded=True):
                    st.markdown(
                        f"""
                        <div class="card-box">
                            <b>Source ID:</b> <code>{sid}</code><br/>
                            <b>S3 Object URI:</b> <code>{file_uri}</code><br/>
                            <b>Size:</b> <code>{s.get('size', 0)} bytes</code> | <b>SHA256:</b> <code>{s.get('checksum_sha256', 'n/a')}</code><br/>
                            <b>Processing Status:</b> <span class="badge-status {status_badge}">{status_str}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if st.button("Verify Object in MinIO", key=f"verify_{sid}", use_container_width=True):
                            try:
                                with st.spinner("Downloading raw object from MinIO through FastAPI..."):
                                    file_bytes, headers = client.download_source_file(active_ws_id, sid)
                                    import hashlib
                                    actual_sha256 = hashlib.sha256(file_bytes).hexdigest()
                                    expected_sha256 = headers.get("x-checksum-sha256") or s.get("checksum_sha256")

                                    checksum_match = (actual_sha256 == expected_sha256)
                                    s["verified_s3"] = True

                                    st.success(f"Verified in MinIO! ({len(file_bytes)} bytes downloaded)")
                                    st.markdown(f"**Object URI:** `{headers.get('x-file-uri', file_uri)}`")
                                    st.markdown(f"**Checksum SHA256 Match:** `{checksum_match}` (`{actual_sha256[:16]}...`)")

                                    # Preview snippet
                                    try:
                                        preview_txt = file_bytes.decode("utf-8", errors="replace")[:400]
                                        st.text_area("Object Preview (from MinIO)", value=preview_txt, height=100, key=f"prev_{sid}")
                                    except Exception:
                                        pass
                            except Exception as exc:
                                st.error(f"S3/MinIO verification failed: {exc}")

                    with col_v2:
                        if st.button("Poll Worker Status", key=f"poll_{sid}", use_container_width=True):
                            try:
                                st_res = client.get_source_status(active_ws_id, sid)
                                s["status"] = st_res.get("status")
                                st.info(f"Current Worker Status: `{st_res.get('status')}`")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Poll failed: {exc}")
        else:
            st.info("No sources recorded for this workspace in this session yet.")

        st.divider()

        # Open Notebook Projection Status Check
        st.markdown("#### Open Notebook Projection Breakdown")
        col_proj1, col_proj2 = st.columns([2, 1])
        with col_proj1:
            st.caption("Checks the projection status count of all workspace sources mapped to Open Notebook.")
        with col_proj2:
            if st.button("Check Projection Status", use_container_width=True):
                try:
                    proj = client.get_projection_status(active_ws_id)
                    st.json(proj)
                except Exception as exc:
                    st.error(f"Projection check error: {exc}")

    # =========================================================================
    # TAB 3: Turn Replay & Inspection
    # =========================================================================
    with tab_replay:
        st.markdown("### Turn Replay & Historical Inspection")
        st.caption("Inspect persisted turns, query monotonic ChatEvents, and test replay from an arbitrary sequence cursor.")

        try:
            turns_data = client.list_turns(active_ws_id, active_conv_id, limit=50)
            turns = turns_data.get("turns", [])
        except Exception as exc:
            st.error(f"Failed to list turns: {exc}")
            turns = []

        if turns:
            turn_options = {
                str(t["turn_id"]): f"Turn #{t.get('sequence')} ({t.get('mode')}) - Status: {t.get('status')} [{str(t['turn_id'])[:8]}...]"
                for t in turns
            }
            selected_turn_id = st.selectbox(
                "Select Turn to Inspect",
                options=list(turn_options.keys()),
                format_func=lambda tid: turn_options[tid],
            )

            if selected_turn_id:
                try:
                    t_detail = client.get_turn(active_ws_id, active_conv_id, selected_turn_id)
                    st.markdown(
                        f"""
                        <div class="card-box">
                            <b>Turn ID:</b> <code>{t_detail.get('turn_id')}</code><br/>
                            <b>Sequence:</b> <code>{t_detail.get('sequence')}</code><br/>
                            <b>Mode:</b> <code>{t_detail.get('mode')}</code><br/>
                            <b>Status:</b> <code>{t_detail.get('status')}</code><br/>
                            <b>Research Run ID:</b> <code>{t_detail.get('research_run_id')}</code><br/>
                            <b>Error Code:</b> <code>{t_detail.get('error_code')}</code>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.expander("Inspect Turn Context Version Snapshot"):
                        st.json(t_detail.get("context_version", {}))

                    # Replay Events
                    st.markdown("#### Historical Event Replay")
                    col_cur, col_rep_sync, col_rep_stream = st.columns([2, 2, 2])
                    with col_cur:
                        after_seq = st.number_input("after_sequence (exclusive cursor)", min_value=0, value=0, step=1)
                    with col_rep_sync:
                        st.write("")
                        st.write("")
                        replay_sync_btn = st.button("Replay (JSON)", use_container_width=True)
                    with col_rep_stream:
                        st.write("")
                        st.write("")
                        replay_stream_btn = st.button("Replay (SSE Stream)", use_container_width=True)

                    if replay_sync_btn:
                        ev_list_resp = client.get_turn_events_sync(
                            active_ws_id, active_conv_id, selected_turn_id, after_sequence=int(after_seq)
                        )
                        events = ev_list_resp.get("events", [])
                        st.success(f"Loaded {len(events)} historical events.")
                        st.json(events)

                    if replay_stream_btn:
                        st.info(f"Streaming replayed events from cursor `{after_seq}`...")
                        stream_gen = client.stream_turn_events(
                            active_ws_id, active_conv_id, selected_turn_id, after_sequence=int(after_seq)
                        )
                        replayed = []
                        for ev in stream_gen:
                            replayed.append(ev)
                        st.success(f"Streamed {len(replayed)} replayed events.")
                        st.json(replayed)

                except Exception as exc:
                    st.error(f"Failed loading turn details: {exc}")
        else:
            st.info("No turns found in this conversation.")

    # =========================================================================
    # TAB 4: Promotion Testing
    # =========================================================================
    with tab_promotions:
        st.markdown("### Promotion Testing (Research Artifacts)")
        st.caption(
            "Inspect candidate artifacts produced by Autonomous Research runs. "
            "Verify acceptance, rejection, and timeline fencing post-commit projection."
        )

        col_pf, col_pr = st.columns([3, 1])
        with col_pf:
            status_filter = st.selectbox(
                "Filter Candidate Status",
                options=["all", "pending_review", "accepted", "rejected"],
                index=1,
            )
        with col_pr:
            st.write("")
            st.write("")
            refresh_prom_btn = st.button("Refresh Candidates", use_container_width=True)

        filt = None if status_filter == "all" else status_filter
        try:
            candidates = client.list_promotions(active_ws_id, status_filter=filt)
            st.caption(f"Found **{len(candidates)}** candidate artifacts.")

            if candidates:
                for c in candidates:
                    art_id = str(c.get("artifact_id"))
                    art_type = c.get("artifact_type")
                    p_status = c.get("promotion_status")

                    with st.expander(f"Artifact {art_id[:8]}... · Type: {art_type} · Status: {p_status}", expanded=(p_status == "pending_review")):
                        st.markdown(f"**ID:** `{art_id}` | **Run ID:** `{c.get('run_id')}` | **Target Type:** `{c.get('promoted_target_type')}`")
                        st.markdown("**Payload:**")
                        st.json(c.get("payload", {}))

                        if p_status == "pending_review":
                            col_acc, col_rej = st.columns(2)
                            with col_acc:
                                if st.button(f"Accept Candidate", key=f"acc_{art_id}", use_container_width=True):
                                    try:
                                        res = client.accept_promotion(active_ws_id, art_id)
                                        st.success(f"Accepted! Target ID: `{res.get('promoted_target_id')}`")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Acceptance rejected: {exc}")
                            with col_rej:
                                reason = st.text_input("Rejection Reason", key=f"reason_{art_id}", placeholder="Optional reason")
                                if st.button(f"Reject Candidate", key=f"rej_{art_id}", use_container_width=True):
                                    try:
                                        res = client.reject_promotion(active_ws_id, art_id, reason=reason)
                                        st.warning("Candidate rejected.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Rejection failed: {exc}")
            else:
                st.info("No candidates matching filter.")
        except Exception as exc:
            st.error(f"Failed listing promotions: {exc}")

    # =========================================================================
    # TAB 5: Rollback & Timeline Fencing
    # =========================================================================
    with tab_rollback:
        st.markdown("### Rollback & Timeline Fencing")
        st.caption(
            "Test Chapter 4 atomic rollback and timeline fencing. "
            "Create commits, rollback to prior snapshots, and verify stale background work is fenced."
        )

        ws_details = st.session_state.get("workspace_details", {})
        curr_commit = ws_details.get("active_commit_id")
        curr_epoch = ws_details.get("timeline_epoch", 1)

        st.markdown(
            f"""
            <div class="card-box">
                <b>Current Active Commit:</b> <code>{curr_commit or 'None'}</code><br/>
                <b>Current Timeline Epoch:</b> <code>{curr_epoch}</code><br/>
                <b>Ground Version:</b> <code>{ws_details.get('ground_version', 1)}</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 1. Create Commit
        st.markdown("#### 1. Create Commit Snapshot")
        if st.button("Create Workspace Commit", type="primary"):
            try:
                commit_resp = client.create_commit(active_ws_id)
                cid = str(commit_resp.get("commit_id"))
                st.success(f"Commit created: `{cid}`")

                # Track in session state
                if active_ws_id not in st.session_state["workspace_commits"]:
                    st.session_state["workspace_commits"][active_ws_id] = []
                st.session_state["workspace_commits"][active_ws_id].append(commit_resp)

                # Refresh workspace details
                st.session_state["workspace_details"] = client.get_workspace(active_ws_id)
                st.rerun()
            except Exception as exc:
                st.error(f"Commit creation failed: {exc}")

        st.divider()

        # 2. Rollback to Commit
        st.markdown("#### 2. Rollback Workspace")
        known_commits = st.session_state.get("workspace_commits", {}).get(active_ws_id, [])
        commit_options = [str(c.get("commit_id")) for c in known_commits]

        rollback_target = st.selectbox(
            "Select Target Commit ID",
            options=commit_options if commit_options else ["None available"],
            disabled=not bool(commit_options),
        )

        manual_commit = st.text_input("Or Enter Manual Target Commit UUID")
        target_commit_id = manual_commit.strip() if manual_commit.strip() else rollback_target

        if st.button("Rollback Workspace", disabled=(target_commit_id == "None available")):
            try:
                with st.spinner("Executing atomic rollback..."):
                    updated_ws = client.rollback_workspace(active_ws_id, target_commit_id)
                    st.session_state["workspace_details"] = updated_ws
                    st.warning(f"Rollback successful! New Timeline Epoch: `{updated_ws.get('timeline_epoch')}`")
                    st.rerun()
            except Exception as exc:
                st.error(f"Rollback failed: {exc}")

        st.divider()

        # 3. Output Knowledge Graph Inspection
        st.markdown("#### 3. Output Knowledge Graph")
        if st.button("Fetch Current Output Graph"):
            try:
                graph = client.get_workspace_graph(active_ws_id)
                nodes = graph.get("nodes", [])
                edges = graph.get("edges", [])
                st.success(f"Graph loaded: {len(nodes)} nodes, {len(edges)} edges.")
                st.json(graph)
            except Exception as exc:
                st.error(f"Graph fetch failed: {exc}")

    # =========================================================================
    # TAB 6: Debug / Raw API Inspector
    # =========================================================================
    with tab_debug:
        st.markdown("### Developer Debug & Raw API Inspector")
        st.caption("Inspect the exact HTTP method, URL, masked headers, request payload, response status, and duration of the latest API call.")

        dbg = st.session_state.get("last_request_debug")
        if dbg:
            status_code = dbg.get("status_code")
            status_class = "badge-ok" if status_code and status_code < 400 else "badge-err"
            st.markdown(
                f"""
                <div class="card-box">
                    <b>Method:</b> <code>{dbg.get('method')}</code><br/>
                    <b>URL:</b> <code>{dbg.get('url')}</code><br/>
                    <b>Status Code:</b> <span class="badge-status {status_class}">{status_code or 'ERROR'}</span><br/>
                    <b>Latency:</b> <code>{dbg.get('duration_ms')} ms</code><br/>
                    <b>Timestamp:</b> <code>{dbg.get('timestamp')}</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_dbg1, col_dbg2 = st.columns(2)
            with col_dbg1:
                st.markdown("**Request Headers:**")
                st.json(dbg.get("request_headers", {}))
                st.markdown("**Request Payload:**")
                st.json(dbg.get("request_body") or {})

            with col_dbg2:
                st.markdown("**Response Headers:**")
                st.json(dbg.get("response_headers", {}))
                st.markdown("**Response Body:**")
                safe_display_json(dbg.get("response_body") or {})

            if dbg.get("error"):
                st.error(f"Underlying Exception: {dbg.get('error')}")
        else:
            st.info("No API requests executed yet.")

        # Raw SSE Frames Log
        st.markdown("#### Raw SSE Frames Buffer (Last 50 lines)")
        raw_sse = st.session_state.get("raw_sse_log", [])
        if raw_sse:
            st.text_area("SSE Stream Wire Trace", value="\n".join(raw_sse), height=250)
            if st.button("Clear SSE Trace"):
                st.session_state["raw_sse_log"] = []
                st.rerun()
        else:
            st.caption("No SSE frames received yet.")


if __name__ == "__main__":
    main()
