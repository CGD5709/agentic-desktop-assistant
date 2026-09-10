"""
Main application entry point for the JARVIS Reasoning Engine.

Configures FastAPI, application lifespan lifecycle, CORS middleware,
and mounts modular API routers following Layered Architecture principles.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
import uvicorn

from agent import AgentRuntime, create_agent_runtime
from api.websockets import router as websockets_router
from config import settings
from services.connection_manager import WebSocketConnectionManager
from services.rabbitmq_listener import create_rabbitmq_message_handler


def _configure_console_encoding() -> None:
    """Enforce UTF-8 encoding on Windows standard streams to safely render emoji indicators."""
    if sys.platform == "win32":
        try:
            if sys.stdout and hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if sys.stderr and hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


_configure_console_encoding()

DATA_DIR = Path(__file__).resolve().parent / "data"
CHECKPOINT_DB_PATH = DATA_DIR / "agent_memory.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronous application lifespan manager orchestrating startup and shutdown phases.

    During startup:
    - Instantiates singleton services and injects them into app.state (Dependency Injection).
    - Initializes agent runtime connections, memory stores, and RabbitMQ consumer task.
    - Compiles the LangGraph state graph with an AsyncSqliteSaver checkpointer.

    During shutdown:
    - Gracefully terminates background tasks, network connections, and open SQLite sessions.
    """
    # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
    print("🔌 [Server] Initializing Reasoning Engine and dependent services...")

    runtime = create_agent_runtime()
    ws_manager = WebSocketConnectionManager()
    config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}

    app.state.runtime = runtime
    app.state.ws_manager = ws_manager
    app.state.config = config
    app.state.app_graph = None

    memory_saver_ctx = None

    try:
        await runtime.initialize()
        rabbitmq_handler = create_rabbitmq_message_handler(runtime, ws_manager)
        asyncio.create_task(runtime.mq_client.start_consuming(rabbitmq_handler))
    except Exception as e:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"⚠️ [Server] Runtime connection initialization error (RabbitMQ): {e}")
        print("ℹ️ [Server] Continuing graph compilation and checkpointer startup...")
        try:
            await runtime.profile_store.initialize()
            await runtime.vector_store.initialize()
        except Exception as store_err:
            # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
            print(f"⚠️ [Server] Error initializing profile or vector stores: {store_err}")

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        memory_saver_ctx = AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
        memory_saver = await memory_saver_ctx.__aenter__()
        app.state.app_graph = runtime.graph.compile(checkpointer=memory_saver)
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"✅ [Server] LangGraph Engine and WebSockets ready on http://{settings.HOST}:{settings.PORT}")
    except Exception as graph_err:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print(f"❌ [Server] Failed to compile LangGraph state graph: {graph_err}")

    try:
        yield
    finally:
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print("💾 [Server] Shutting down persistence stores and active connections...")
        try:
            await runtime.close()
        except Exception as e:
            # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
            print(f"⚠️ [Server] Error closing agent runtime: {e}")
        if memory_saver_ctx:
            try:
                await memory_saver_ctx.__aexit__(None, None, None)
            except Exception as e:
                # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
                print(f"⚠️ [Server] Error closing SQLite checkpointer: {e}")
        # TODO: Replace print with a standardized logging framework (e.g., logging/structlog).
        print("👋 [Server] Server stopped cleanly.")


app = FastAPI(title="JARVIS Reasoning Engine WebSocket Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websockets_router)


@app.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Service health check endpoint reporting engine readiness and registered external tools.

    Args:
        request: The incoming HTTP request instance.

    Returns:
        Dictionary reporting health status ('ONLINE' or 'STARTING'), engine model,
        and current dynamic tool inventory.
    """
    runtime: Optional[AgentRuntime] = getattr(request.app.state, "runtime", None)
    app_graph: Optional[CompiledStateGraph] = getattr(request.app.state, "app_graph", None)
    dynamic_tools = runtime.dynamic_tools if runtime else []
    return {
        "status": "ONLINE" if app_graph is not None else "STARTING",
        "engine": "JARVIS Qwen 2.5 7B",
        "tools_count": len(dynamic_tools),
        "tools": [t["function"]["name"] for t in dynamic_tools],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
