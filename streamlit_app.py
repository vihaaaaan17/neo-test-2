import asyncio
import streamlit as st
from uuid import UUID, uuid4
import os
import litellm

# Mock context so absolute imports work if run from project root
import sys
sys.path.append(os.getcwd())

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import Core Components
from app.core.config import settings
from app.repositories.workspace import WorkspaceRepository
from app.repositories.graph import GraphRepository
from app.orchestration.research_mode import ResearchModeOrchestrator
from app.services.web_search import WebSearchTool

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Create a fresh engine with NullPool so connections aren't reused across closed event loops
engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
local_async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

st.set_page_config(page_title="NeosisLM Testing UI", layout="wide")
st.title("NeosisLM - End-to-End Test UI")

# --- SIDEBAR: API Keys ---
with st.sidebar:
    st.header("🔑 API Keys (BYOK)")
    gemini_key = st.text_input("Gemini API Key", type="password")
    tavily_key = st.text_input("Tavily API Key", type="password")
    st.markdown("---")
    st.info("These keys are used dynamically inside this Streamlit session. They are NOT saved to the backend.")
    
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key

# --- SESSION STATE ---
if "workspace_id" not in st.session_state:
    st.session_state.workspace_id = None
if "owner_id" not in st.session_state:
    st.session_state.owner_id = uuid4() # Dummy user ID for testing

# --- DB HELPERS ---
async def create_db_workspace():
    async with local_async_session_maker() as session:
        repo = WorkspaceRepository(session)
        workspace = await repo.create_workspace(owner_id=st.session_state.owner_id)
        st.session_state.workspace_id = str(workspace.workspace_id)
        return workspace

async def project_graph_to_neo4j(graph):
    from neo4j import AsyncGraphDatabase
    from app.repositories.graph import Neo4jAdapter
    
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
    
    temp_store = Neo4jAdapter(
        settings.NEO4J_URI, 
        settings.NEO4J_USER, 
        settings.NEO4J_PASSWORD, 
        driver=driver
    )
    repo = GraphRepository(temp_store)
    
    try:
        await repo.project_output_graph(UUID(st.session_state.workspace_id), graph)
    finally:
        await driver.close()

# --- LLM GATEWAY (Dynamic BYOK) ---
def get_litellm_gateway(api_key: str):
    async def llm_call(prompt: str) -> str:
        if not api_key:
            return '{"error": "No API key provided!"}'
        
        # LiteLLM routing
        response = await litellm.acompletion(
            model="gemini/gemini-3.6-flash",
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key
        )
        return response.choices[0].message.content
    return llm_call

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🏗️ Workspace Setup", "🧠 Ground Mode (QA)", "🔍 Autonomous Research"])

# TAB 1: WORKSPACE
with tab1:
    st.header("1. Initialize Workspace")
    if st.button("Create New Workspace"):
        with st.spinner("Creating Postgres workspace..."):
            ws = asyncio.run(create_db_workspace())
            st.success(f"Workspace created! ID: `{ws.workspace_id}`")
            
    if st.session_state.workspace_id:
        st.info(f"**Active Workspace**: `{st.session_state.workspace_id}`")
        st.warning("File Uploading & Parsing is omitted from this UI test to avoid running background Arq workers for Docling. We will jump straight to the Autonomous Research agent which relies on Tavily web search!")

# TAB 2: GROUND MODE
with tab2:
    st.header("2. Ground Mode (QA)")
    st.markdown("This will test the `GroundModeOrchestrator` using the existing knowledge graph.")
    
    question = st.text_input("Ask a question about the workspace")
    
    if st.button("Ask"):
        if not st.session_state.workspace_id:
            st.error("Please create a workspace first (Tab 1).")
        elif not gemini_key:
            st.error("Please provide Gemini API key in the sidebar.")
        elif not question:
            st.error("Please enter a question.")
        else:
            async def run_ground_mode():
                from app.orchestration.ground_mode import GroundModeOrchestrator
                from app.services.hybrid_retrieval import HybridRetrievalService
                
                # We also need a dummy embed gateway since we don't have embeddings setup in the UI
                async def mock_embed(text):
                    return [0.0] * 1536
                
                orchestrator = GroundModeOrchestrator(
                    hybrid_retriever=HybridRetrievalService(),
                    llm_gateway=get_litellm_gateway(gemini_key),
                    embed_gateway=mock_embed
                )
                
                with st.spinner("Searching and synthesizing..."):
                    try:
                        state = await orchestrator.run(
                            workspace_id=UUID(st.session_state.workspace_id),
                            query=question
                        )
                        st.write("**Answer:**")
                        st.write(state.get("answer"))
                        st.write("**Evidence:**")
                        st.json([str(u) for u in state.get("evidence", [])])
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")
            
            asyncio.run(run_ground_mode())

# TAB 3: RESEARCH MODE
with tab3:
    st.header("3. Run Autonomous Research (Phase 4)")
    st.markdown("This will instantiate the `ResearchModeOrchestrator` (LangGraph) locally in this Streamlit process, using your Gemini API key.")
    
    objective = st.text_input("Research Objective", placeholder="e.g. Compare the efficiency of Solid State Batteries vs LFP")
    
    if st.button("Start Research Run"):
        if not st.session_state.workspace_id:
            st.error("Please create a workspace first (Tab 1).")
        elif not gemini_key or not tavily_key:
            st.error("Please provide both Gemini and Tavily API keys in the sidebar.")
        elif not objective:
            st.error("Please enter a research objective.")
        else:
            async def run_agent():
                # Build dependencies
                llm_gw = get_litellm_gateway(gemini_key)
                search_tool = WebSearchTool()
                orchestrator = ResearchModeOrchestrator(llm_gateway=llm_gw, search_tool=search_tool)
                
                from app.orchestration.research_mode import ResearchContext
                initial_state = {
                    "workspace_id": UUID(st.session_state.workspace_id),
                    "objective": objective,
                    "context": ResearchContext(),
                    "final_graph": None,
                    "summary": None
                }
                
                status_box = st.status("Initializing LangGraph Agent...", expanded=True)
                
                final_state = None
                try:
                    async for step in orchestrator.graph.astream(initial_state):
                        node_name = list(step.keys())[0]
                        state = step[node_name]
                        final_state = state
                        
                        if node_name == "planner":
                            status_box.update(label="Planning phase complete")
                            st.write("**Generated Plan:**")
                            ctx = state.get("context", ResearchContext())
                            st.json(ctx.plan)
                        elif node_name == "executor":
                            ctx = state.get("context", ResearchContext())
                            idx = ctx.current_task_index - 1
                            plan = ctx.plan
                            if idx < len(plan):
                                status_box.update(label=f"Executed search: {plan[idx]}")
                                st.write(f"Executed search: {plan[idx]}")
                        elif node_name == "synthesizer":
                            status_box.update(label="Synthesis complete", state="running")
                            st.success("Successfully generated Output KG!")
                            st.write("**Final Synthesized Graph:**")
                            fg = state.get("final_graph")
                            if fg:
                                st.json(fg if isinstance(fg, dict) else fg.model_dump())
                        elif node_name == "reporter":
                            status_box.update(label="Research finished", state="complete")
                            st.write("**Chatbot Summary:**")
                            st.write(state.get("summary"))
                                
                    # Now Project to Neo4j
                    if final_state and final_state.get("final_graph"):
                        st.info("Projecting Graph to Neo4j...")
                        fg = final_state.get("final_graph")
                        
                        from app.schemas.graph import OutputGraph
                        if isinstance(fg, dict):
                            fg = OutputGraph(**fg)
                            
                        await project_graph_to_neo4j(fg)
                        st.success("Graph successfully stored in Neo4j!")
                                
                except Exception as e:
                    status_box.update(label="Agent failed", state="error")
                    st.error(f"Error: {str(e)}")

            # Run the async agent block
            asyncio.run(run_agent())
