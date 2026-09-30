import os
import sys
import json
import time
import uuid
import asyncio
import contextlib
import requests
import streamlit as st

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Suppress LangChain tracing network errors in UI
import langchain_core.tracers.context
@contextlib.contextmanager
def _no_op_tracing(**kwargs):
    yield
langchain_core.tracers.context.tracing_v2_enabled = _no_op_tracing

# Import NeosisLM Core & Orchestration Components (Chapters 1 - 4)
from sqlalchemy import select, text
from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.models.source import Source, SourceSnapshot
from app.models.block import DocumentBlock
from app.services.hybrid_retrieval import HybridRetrievalService, RetrievedChunk
from app.services.memory_router import MemoryRouterService
from app.orchestration.ground_mode import GroundModeOrchestrator
from app.orchestration.research_mode import ResearchModeOrchestrator
from app.integrations.research_engine.factory import ResearchEngineFactory
from app.schemas.graph import OutputGraph

# Load .env.ui keys if present
from dotenv import dotenv_values
_ui_env = dotenv_values(os.path.join(REPO_ROOT, ".env.ui"))

# Streamlit Page Configuration
st.set_page_config(
    page_title="NeosisLM System Testbed",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for High-Tech Dashboard Aesthetic
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .engine-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }
    .step-box {
        background-color: #FFFFFF;
        border-left: 4px solid #3B82F6;
        border-radius: 4px;
        padding: 10px 14px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-ground {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-research {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-hallucination-pass {
        background-color: #DCFCE7;
        color: #15803D;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .badge-hallucination-fail {
        background-color: #FEE2E2;
        color: #B91C1C;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Sidebar: Configuration & Engine Selection ---
with st.sidebar:
    st.markdown("### ⚙️ Engine Configuration")

    llm_provider = st.radio(
        "LLM Gateway Backend",
        ["NVIDIA NIM (Cloud API)", "Local / Fast Mock Engine"],
        index=0,
        help="NVIDIA NIM uses live cloud API with user keys. Fast Mock runs the full LangGraph and PostgreSQL RRF instantly without cloud queue latency.",
    )

    nvidia_key = st.text_input(
        "NVIDIA API Key",
        value=_ui_env.get("NVIDIA_API_KEY", os.environ.get("NVIDIA_API_KEY", "")),
        type="password",
        disabled=(llm_provider != "NVIDIA NIM (Cloud API)")
    )

    model_options = [
        "deepseek-ai/deepseek-v4.1-flash",
        "moonshotai/kimi-k3",
        "Custom...",
    ]
    env_model = _ui_env.get("NVIDIA_MODEL", "deepseek-ai/deepseek-v4.1-flash")
    default_model_idx = model_options.index(env_model) if env_model in model_options else 0
    selected_model = st.selectbox(
        "NVIDIA Model",
        model_options,
        index=default_model_idx,
        disabled=(llm_provider != "NVIDIA NIM (Cloud API)")
    )
    if selected_model == "Custom...":
        active_model = st.text_input("Enter Model ID", value="moonshotai/kimi-k3")
    else:
        active_model = selected_model

    tavily_key = st.text_input(
        "Tavily API Key (Research Mode)",
        value=_ui_env.get("TAVILY_API_KEY", os.environ.get("TAVILY_API_KEY", "")),
        type="password",
        help="Used by WebSearchTool for autonomous live web queries."
    )

    st.markdown("---")
    st.markdown("### 🗄️ PostgreSQL Workspace")

    # Helper to fetch active workspaces
    async def get_workspaces():
        try:
            async with async_session_maker() as session:
                res = await session.execute(select(Workspace).order_by(Workspace.created_at.desc()).limit(15))
                return res.scalars().all()
        except Exception as e:
            return []

    workspaces_list = asyncio.run(get_workspaces())
    ws_options = {f"Workspace {str(w.workspace_id)[:8]} ({w.status})": w.workspace_id for w in workspaces_list}
    
    if ws_options:
        selected_ws_label = st.selectbox("Active Workspace", list(ws_options.keys()))
        active_workspace_id = ws_options[selected_ws_label]
    else:
        st.info("No workspaces found in DB.")
        active_workspace_id = None

    if st.button("➕ Create New Workspace in DB", use_container_width=True):
        async def create_ws():
            async with async_session_maker() as session:
                new_ws = Workspace(owner_id=uuid.uuid4(), status="active")
                session.add(new_ws)
                await session.commit()
                return new_ws.workspace_id
        new_id = asyncio.run(create_ws())
        st.success(f"Created Workspace {str(new_id)[:8]}")
        st.rerun()

    st.markdown("---")
    if st.button("🧹 Clear Execution Traces", use_container_width=True):
        st.session_state.traces = []
        st.rerun()

# --- Initialize Session State ---
if "traces" not in st.session_state:
    st.session_state.traces = []

# --- Header & Mode Selection ---
st.markdown('<div class="main-header">NeosisLM Engine Testbed</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Directly testing Chapters 1–4: GroundModeOrchestrator (PostgreSQL RRF + Hallucination Judge) & ResearchModeOrchestrator (LangGraph Multi-Step Synthesis)</div>',
    unsafe_allow_html=True,
)

col_mode, col_badge = st.columns([1, 2])
with col_mode:
    mode_selection = st.radio(
        "Engine Under Test",
        ["🟢 Ground Mode Engine", "🔍 Research Mode Engine"],
        horizontal=True,
        label_visibility="collapsed"
    )
is_ground_mode = "Ground" in mode_selection

with col_badge:
    if is_ground_mode:
        st.markdown(
            '<span class="badge-ground">GROUND ENGINE ACTIVE</span> — Runs `GroundModeOrchestrator`: PostgreSQL RRF retrieval, `MemoryRouterService` budgeting, grounded synthesis, and hallucination judge verification.',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="badge-research">RESEARCH ENGINE ACTIVE</span> — Runs `ResearchEngineFactory` (`ResearchModeOrchestrator` / `OpenDeepResearchEngine`): Autonomous planner, live Tavily executor, OutputGraph synthesizer, and report generator.',
            unsafe_allow_html=True
        )

# --- LLM and Embed Gateway Definitions ---
def create_llm_gateway(provider: str, api_key: str, model: str):
    async def llm_gateway(prompt: str) -> str:
        if provider == "Local / Fast Mock Engine" or not api_key:
            # Deterministic fast mock for testing pipeline logic without cloud delays
            if "hallucination detection judge" in prompt:
                return "YES"
            if "research planner" in prompt:
                return json.dumps([
                    "quantum coherence mechanisms in biological systems",
                    "room temperature photosynthetic energy transfer",
                    "FMO complex experimental measurements"
                ])
            if "research synthesis agent" in prompt:
                # Return valid OutputGraph JSON
                return json.dumps({
                    "nodes": [
                        {
                            "id": "node-1",
                            "label": "Fenna-Matthews-Olson Complex",
                            "properties": {"role": "Pigment-protein antenna complex"}
                        },
                        {
                            "id": "node-2",
                            "label": "Excitonic Quantum Coherence",
                            "properties": {"duration": "300 femtoseconds", "temperature": "Room temperature (300K)"}
                        }
                    ],
                    "edges": [
                        {
                            "source_id": "node-1",
                            "target_id": "node-2",
                            "type": "EXHIBITS",
                            "properties": {"efficiency": "Near-unity energy transfer"}
                        }
                    ]
                })
            if "research reporting agent" in prompt:
                return (
                    "### Research Brief: Quantum Coherence in Photosynthesis\n\n"
                    "**Key Finding**: The Fenna-Matthews-Olson (FMO) photosynthetic complex in green sulfur bacteria "
                    "harnesses excitonic quantum coherence to facilitate near-unity energy transfer efficiency even at ambient room temperatures.\n\n"
                    "**Mechanism**: Protective vibrational modes of the surrounding protein scaffold prevent thermal dephasing, "
                    "maintaining phase coherence between bacteriochlorophyll-a pigments across 300+ femtoseconds."
                )
            # Default answer for ground mode
            return json.dumps({
                "answer": "Photosynthetic complexes sustain quantum coherence for over 300 femtoseconds at room temperature in the FMO complex.",
                "evidence": []
            })

        # NVIDIA NIM Cloud Invocation
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "stream": True,
            "temperature": 0.2
        }
        
        loop = asyncio.get_running_loop()
        def _call_nim():
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120
            )
            accumulated = []
            reasoning = []
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        d_str = decoded[6:].strip()
                        if d_str == "[DONE]":
                            break
                        try:
                            delta = json.loads(d_str)["choices"][0]["delta"]
                            content = delta.get("content")
                            if content:
                                accumulated.append(content)
                            reas = delta.get("reasoning_content")
                            if reas:
                                reasoning.append(reas)
                        except Exception:
                            pass
            return "".join(accumulated) if accumulated else "".join(reasoning)

        return await loop.run_in_executor(None, _call_nim)

    return llm_gateway

async def mock_embed_gateway(text: str) -> list[float]:
    # Returns 768-dimensional normalized embedding matching pgvector column
    import hashlib
    # Generate pseudo-deterministic 768 floats based on text hash
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = [(float(b) / 255.0) - 0.5 for b in h]
    # Tile to 768
    return (vec * (768 // len(vec) + 1))[:768]

# --- Live Tavily Search Tool for Research Engine ---
class TavilyLiveSearchTool:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str) -> str:
        if not self.api_key:
            return f"Mock search findings for '{query}': High-efficiency solid state battery architectures and electrolyte interfaces."
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": 3,
            "search_depth": "basic",
            "include_answer": True
        }
        loop = asyncio.get_running_loop()
        def _req():
            try:
                r = requests.post(url, json=payload, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    lines = []
                    if data.get("answer"):
                        lines.append(f"Direct Answer: {data['answer']}")
                    for res in data.get("results", []):
                        lines.append(f"- [{res.get('title')}]: {res.get('content')} ({res.get('url')})")
                    return "\n".join(lines)
                return f"Tavily returned HTTP {r.status_code}"
            except Exception as e:
                return f"Tavily search exception: {e}"
        return await loop.run_in_executor(None, _req)


# ==============================================================================
# GROUND MODE UI: DATABASE SOURCES & INGESTION
# ==============================================================================
if is_ground_mode:
    st.markdown("### 📚 PostgreSQL Workspace Sources")
    if not active_workspace_id:
        st.warning("Please create or select a Workspace in the left sidebar to use Ground Mode.")
    else:
        # Fetch current sources and blocks in this workspace
        async def fetch_workspace_sources(ws_id):
            async with async_session_maker() as session:
                q = (
                    select(DocumentBlock, Source, SourceSnapshot)
                    .join(Source, DocumentBlock.source_id == Source.source_id)
                    .join(SourceSnapshot, DocumentBlock.snapshot_id == SourceSnapshot.snapshot_id)
                    .where(Source.workspace_id == ws_id)
                    .order_by(DocumentBlock.created_at.desc())
                    .limit(20)
                )
                res = await session.execute(q)
                return res.all()

        current_blocks = asyncio.run(fetch_workspace_sources(active_workspace_id))

        with st.expander(f"📁 Document Blocks in Workspace ({len(current_blocks)} blocks indexed in DB)", expanded=(len(current_blocks) == 0)):
            if current_blocks:
                for block, src, snap in current_blocks:
                    st.markdown(
                        f"""
                        <div class="step-box">
                            <strong>📄 {snap.filename}</strong> (Block ID: <code>{str(block.block_id)[:8]}</code>)<br>
                            <small>{block.text_or_ref}</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No documents in this workspace yet. Ingest a document below to test PostgreSQL RRF retrieval.")

            st.markdown("#### Ingest New Document into Workspace")
            col_t, col_btn = st.columns([3, 1])
            with col_t:
                doc_title = st.text_input("Document Name", value="Quantum_Photosynthesis_Spec.txt")
            doc_body = st.text_area(
                "Document Content",
                value=(
                    "Photosynthetic complexes utilize excitonic quantum coherence to achieve near-unity quantum efficiency in energy transfer. "
                    "The Fenna-Matthews-Olson (FMO) complex found in green sulfur bacteria sustains electronic coherence between bacteriochlorophyll-a pigments "
                    "for over 300 femtoseconds at room temperature (300 K), facilitated by protective vibrational modes that suppress thermal dephasing."
                ),
                height=120
            )

            if st.button("📥 Ingest Document into PostgreSQL (Vector + Text Indexes)"):
                async def ingest_doc(ws_id, title, content):
                    async with async_session_maker() as session:
                        # 1. Source
                        ws = await session.get(Workspace, ws_id)
                        owner_id = ws.owner_id if ws else uuid.uuid4()
                        src = Source(workspace_id=ws_id, owner_id=owner_id, source_type="document", processing_status="completed")
                        session.add(src)
                        await session.flush()

                        # 2. Snapshot
                        snap = SourceSnapshot(
                            source_id=src.source_id,
                            filename=title,
                            file_uri=f"s3://neosislm-dev/{title}",
                            size=len(content),
                            checksum_sha256=str(uuid.uuid4())
                        )
                        session.add(snap)
                        await session.flush()

                        # 3. DocumentBlock with 768-dim embedding and text tsvector
                        emb = await mock_embed_gateway(content)
                        block = DocumentBlock(
                            source_id=src.source_id,
                            snapshot_id=snap.snapshot_id,
                            block_type="text",
                            sequence=1,
                            text_or_ref=content,
                            embedding=emb,
                            metadata_={"title": title}
                        )
                        session.add(block)
                        await session.commit()

                        # 4. Generate tsvector
                        await session.execute(
                            text("UPDATE document_blocks SET search_vector = to_tsvector('english', text_or_ref) WHERE block_id = :bid"),
                            {"bid": block.block_id}
                        )
                        await session.commit()
                        return block.block_id

                new_bid = asyncio.run(ingest_doc(active_workspace_id, doc_title, doc_body))
                st.success(f"Successfully ingested block `{str(new_bid)[:8]}` into PostgreSQL!")
                st.rerun()

# ==============================================================================
# EXECUTION HISTORY & CHAT INTERFACE
# ==============================================================================
st.markdown("---")
st.markdown("### 🧪 Engine Execution Traces")

for item in st.session_state.traces:
    mode = item.get("mode")
    query = item.get("query")
    if mode == "ground":
        with st.chat_message("user"):
            st.markdown(f"**Query (Ground Mode)**: {query}")
        with st.chat_message("assistant"):
            st.markdown(f'<span class="badge-ground">GROUND ENGINE RESULT</span>', unsafe_allow_html=True)
            st.markdown(item.get("answer"))
            
            with st.expander("🔬 View GroundModeOrchestrator LangGraph Stages", expanded=True):
                col_r, col_h = st.columns(2)
                with col_r:
                    st.markdown("**1. PostgreSQL Hybrid Retrieval (RRF):**")
                    retrieved = item.get("retrieved", [])
                    if retrieved:
                        for c in retrieved:
                            st.markdown(f"- `Block {c['id'][:8]}` (RRF Score: `{c['score']:.4f}`): *{c['text'][:80]}...*")
                    else:
                        st.write("No blocks matched retrieval query.")
                with col_h:
                    st.markdown("**2. Hallucination Detection Judge:**")
                    is_g = item.get("is_grounded")
                    retries = item.get("retries", 1)
                    if is_g:
                        st.markdown('<span class="badge-hallucination-pass">GROUNDED: YES</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-hallucination-fail">GROUNDED: NO (Failed Judge)</span>', unsafe_allow_html=True)
                    st.caption(f"Graph retries count: {retries}")
                    if item.get("evidence"):
                        st.caption(f"Validated Evidence UUIDs: {item.get('evidence')}")
    else:
        with st.chat_message("user"):
            st.markdown(f"**Objective (Research Mode)**: {query}")
        with st.chat_message("assistant"):
            st.markdown(f'<span class="badge-research">RESEARCH ENGINE RESULT</span>', unsafe_allow_html=True)
            st.markdown(item.get("summary", "No summary generated"))

            with st.expander("🗺️ View Synthesized OutputGraph (Knowledge Graph)", expanded=True):
                graph = item.get("final_graph") or {}
                nodes = graph.get("nodes", [])
                edges = graph.get("edges", [])
                st.markdown(f"**Synthesized Graph Entities**: `{len(nodes)}` Nodes, `{len(edges)}` Edges")
                
                if nodes:
                    st.dataframe([{"Node ID": n.get("id"), "Label": n.get("label"), "Properties": str(n.get("properties"))} for n in nodes], use_container_width=True)
                if edges:
                    st.dataframe([{"Source": e.get("source_id"), "Target": e.get("target_id"), "Type": e.get("type")} for e in edges], use_container_width=True)

            with st.expander("🔍 View Research Execution Steps"):
                for s in item.get("steps", []):
                    st.markdown(f"- **{s.get('status').upper()}**: {s.get('message')}")
                    if s.get("plan"):
                        st.code(json.dumps(s.get("plan"), indent=2))

# ==============================================================================
# USER INPUT & LIVE ENGINE DISPATCH
# ==============================================================================
user_input = st.chat_input(
    placeholder="Enter query for Ground Engine or research objective for Research Engine..."
)

if user_input:
    llm_gateway = create_llm_gateway(llm_provider, nvidia_key, active_model)

    if is_ground_mode:
        if not active_workspace_id:
            st.error("Please select or create a Workspace in PostgreSQL first.")
        else:
            with st.spinner("⚡ Running GroundModeOrchestrator LangGraph: retrieve -> answer -> check_hallucination..."):
                async def run_ground(ws_id, query):
                    retriever = HybridRetrievalService()
                    # Step 1: Hybrid Retrieval
                    q_emb = await mock_embed_gateway(query)
                    chunks = await retriever.retrieve(workspace_id=ws_id, query_text=query, query_embedding=q_emb)
                    
                    # Step 2 & 3: Run Orchestrator
                    orchestrator = GroundModeOrchestrator(
                        hybrid_retriever=retriever,
                        llm_gateway=llm_gateway,
                        embed_gateway=mock_embed_gateway
                    )
                    state = await orchestrator.run(workspace_id=ws_id, query=query)
                    return state, chunks

                state, chunks = asyncio.run(run_ground(active_workspace_id, user_input))

                st.session_state.traces.append({
                    "mode": "ground",
                    "query": user_input,
                    "answer": state.get("answer"),
                    "is_grounded": state.get("is_grounded"),
                    "retries": state.get("retries"),
                    "evidence": [str(e) for e in state.get("evidence", [])],
                    "retrieved": [{"id": str(c.block_id), "score": c.score, "text": c.text} for c in chunks]
                })
                st.rerun()

    else:
        # Research Mode Execution
        with st.spinner("🔍 Running ResearchModeOrchestrator: planner -> executor -> synthesizer -> reporter..."):
            async def run_research(query):
                search_tool = TavilyLiveSearchTool(tavily_key)
                orchestrator = ResearchModeOrchestrator(llm_gateway=llm_gateway, search_tool=search_tool)
                
                events = []
                final_summary = ""
                final_graph = {}
                async for ev in orchestrator.astream_events(workspace_id=uuid.uuid4(), objective=query):
                    events.append(ev)
                    if ev.get("status") == "synthesizing":
                        final_graph = ev.get("final_graph") or {}
                    elif ev.get("status") == "reporting":
                        final_summary = ev.get("summary") or ""
                
                # If summary wasn't in events, invoke reporter
                if not final_summary:
                    res_state = await orchestrator.run(workspace_id=uuid.uuid4(), objective=query)
                    final_summary = res_state.get("summary", "")
                    final_graph = res_state.get("final_graph", {})

                return final_summary, final_graph, events

            summary, graph, steps = asyncio.run(run_research(user_input))

            st.session_state.traces.append({
                "mode": "research",
                "query": user_input,
                "summary": summary,
                "final_graph": graph,
                "steps": steps
            })
            st.rerun()
