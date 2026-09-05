import asyncio
import json
import uuid
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import AgentState, create_agent_runtime

# Runtime container instance
runtime = create_agent_runtime()

# Configuración del hilo persistente de LangGraph
config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}
app_graph = None
memory_saver_ctx = None


def convert_execution_tools_to_openai_format(raw_tools: list) -> list:
    """Convierte el manifiesto de herramientas de execution-service al formato OpenAI."""
    converted = []
    for tool in raw_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        converted.append(openai_tool)
    return converted


async def handle_rabbitmq_message(raw_body: str, routing_key: str) -> None:
    """Callback de RabbitMQ para capturar descubrimiento de herramientas de execution-service."""
    if routing_key == "system.discovery.execution_service":
        try:
            data = json.loads(raw_body)
            tools_list = data.get("payload", {}).get("tools", [])
            runtime.dynamic_tools.clear()
            converted_tools = convert_execution_tools_to_openai_format(tools_list)
            runtime.dynamic_tools.extend(converted_tools)
            nombres = [t["function"]["name"] for t in converted_tools]
            print(f"\n📡 [System Discovery] Herramientas recibidas de execution-service: {nombres}")
            # Notificamos a los clientes WebSocket conectados sobre las nuevas herramientas
            await ws_manager.broadcast({
                "type": "tools_updated",
                "tools": [t["function"]["name"] for t in runtime.dynamic_tools],
            })
        except Exception as e:
            print(f"\n❌ Error procesando el manifiesto de herramientas: {e}")


class WebSocketConnectionManager:
    """Administra las conexiones de clientes WebSocket activos."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 [WebSocket] Cliente conectado. Activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔌 [WebSocket] Cliente desconectado. Activos: {len(self.active_connections)}")

    async def send_personal(self, message: dict, websocket: WebSocket) -> None:
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict) -> None:
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)


ws_manager = WebSocketConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_graph, memory_saver_ctx
    print("🔌 [Server] Iniciando Motor de Razonamiento y Servicios...")
    await runtime.initialize()

    # Consumidor de RabbitMQ en segundo plano
    asyncio.create_task(runtime.mq_client.start_consuming(handle_rabbitmq_message))

    # Inicialización del Checkpointer de SQLite
    memory_saver_ctx = AsyncSqliteSaver.from_conn_string("agent_memory.db")
    memory_saver = await memory_saver_ctx.__aenter__()
    app_graph = runtime.graph.compile(checkpointer=memory_saver)
    print("✅ [Server] LangGraph Engine & WebSockets Listos en http://0.0.0.0:8000")

    yield

    print("💾 [Server] Cerrando servicios de memoria y conexiones...")
    await runtime.close()
    if memory_saver_ctx:
        await memory_saver_ctx.__aexit__(None, None, None)
    print("👋 [Server] Servidor detenido limpiamente.")


app = FastAPI(title="JARVIS Reasoning Engine WebSocket Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ONLINE",
        "engine": "JARVIS Qwen 2.5 7B",
        "tools_count": len(runtime.dynamic_tools),
        "tools": [t["function"]["name"] for t in runtime.dynamic_tools],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    # Enviamos saludo y estado inicial
    await ws_manager.send_personal({
        "type": "connected",
        "message": "Sistemas de J.A.R.V.I.S en línea y listos para interactuar.",
        "tools": [t["function"]["name"] for t in runtime.dynamic_tools],
    }, websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except Exception:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await ws_manager.send_personal({"type": "pong"}, websocket)
                continue

            if msg_type == "user_message":
                user_text = msg.get("content", "").strip()
                if not user_text:
                    continue

                print(f"📥 [WS User]: {user_text}")

                # Avisamos al frontend que Jarvis está pensando
                await ws_manager.send_personal({
                    "type": "status",
                    "state": "THINKING",
                }, websocket)

                try:
                    state: AgentState = {
                        "messages": [HumanMessage(content=user_text)],
                        "correlation_id": str(uuid.uuid4()),
                    }

                    # Ejecución en el Grafo de LangGraph
                    result = await app_graph.ainvoke(state, config=config)
                    last_msg = result["messages"][-1]
                    assistant_text = last_msg.content if isinstance(last_msg.content, str) else ""

                    print(f"🤖 [WS Jarvis]: {assistant_text[:80]}...")

                    # Enviamos la respuesta limpia al frontend
                    await ws_manager.send_personal({
                        "type": "assistant_message",
                        "content": assistant_text,
                    }, websocket)

                except Exception as err:
                    print(f"❌ Error en ejecución de grafo: {err}")
                    await ws_manager.send_personal({
                        "type": "assistant_message",
                        "content": f"He experimentado una anomalía en mi núcleo de procesamiento: {err}",
                    }, websocket)
                finally:
                    await ws_manager.send_personal({
                        "type": "status",
                        "state": "IDLE",
                    }, websocket)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ [WebSocket] Error en sesión: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
