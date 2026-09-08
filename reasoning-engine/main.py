"""
Main application entry point for the JARVIS Reasoning Engine.
Configures FastAPI, lifespan lifecycle, CORS middleware, and API routers.
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from agent import AgentRuntime, create_agent_runtime
from api.websockets import router as websockets_router
from services.connection_manager import WebSocketConnectionManager
from services.rabbitmq_listener import create_rabbitmq_message_handler

# Asegurar codificación UTF-8 en consolas Windows (evita errores con emojis como 🔌)
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"
CHECKPOINT_DB_PATH = DATA_DIR / "agent_memory.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida asíncrono para inicializar servicios, bases de datos y consumidores."""
    print("🔌 [Server] Iniciando Motor de Razonamiento y Servicios...")

    runtime = create_agent_runtime()
    ws_manager = WebSocketConnectionManager()
    config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}

    # Inyección de dependencias en app.state
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
        print(f"⚠️ [Server] Error inicializando conexiones de runtime (RabbitMQ): {e}")
        print("ℹ️ [Server] Continuando con la compilación del grafo y checkpointer...")
        try:
            await runtime.profile_store.initialize()
            await runtime.vector_store.initialize()
        except Exception as store_err:
            print(f"⚠️ [Server] Error inicializando almacenes de perfil/vector: {store_err}")

    # Inicialización del Checkpointer de SQLite
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        memory_saver_ctx = AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
        memory_saver = await memory_saver_ctx.__aenter__()
        app.state.app_graph = runtime.graph.compile(checkpointer=memory_saver)
        print("✅ [Server] LangGraph Engine & WebSockets Listos en http://0.0.0.0:8000")
    except Exception as graph_err:
        print(f"❌ [Server] Error al compilar el grafo LangGraph: {graph_err}")

    try:
        yield
    finally:
        print("💾 [Server] Cerrando servicios de memoria y conexiones...")
        try:
            await runtime.close()
        except Exception as e:
            print(f"⚠️ [Server] Error al cerrar runtime: {e}")
        if memory_saver_ctx:
            try:
                await memory_saver_ctx.__aexit__(None, None, None)
            except Exception as e:
                print(f"⚠️ [Server] Error al cerrar checkpointer SQLite: {e}")
        print("👋 [Server] Servidor detenido limpiamente.")


app = FastAPI(title="JARVIS Reasoning Engine WebSocket Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión del router modular de WebSockets
app.include_router(websockets_router)


@app.get("/health")
async def health_check(request: Request):
    """Endpoint de estado del servicio y herramientas registradas."""
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
