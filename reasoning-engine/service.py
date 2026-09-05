"""
Interactive console service for the Jarvis desktop assistant reasoning engine.
"""
import asyncio
import json
import uuid
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent import AgentState, create_agent_runtime

# Initialize runtime container
runtime = create_agent_runtime()

app_graph = None
config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}


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
    """Callback que escucha todos los eventos de la red de mensajería."""
    if routing_key == "system.discovery.execution_service":
        try:
            data = json.loads(raw_body)
            tools_list = data.get("payload", {}).get("tools", [])

            runtime.dynamic_tools.clear()
            converted_tools = convert_execution_tools_to_openai_format(tools_list)
            runtime.dynamic_tools.extend(converted_tools)

            nombres = [t["function"]["name"] for t in converted_tools]
            print("\n📡 [System Discovery] Manifiesto recibido de execution-service.")
            print(f"   -> 🛠️ {len(converted_tools)} herramienta(s) asimilada(s): {nombres}")
            print("\nUsuario: ", end="", flush=True)
        except Exception as e:
            print(f"\n❌ Error procesando el manifiesto de herramientas: {e}")
        return

    if "tool.response" in routing_key:
        print(f"\n[RabbitMQ] 📥 Respuesta recibida de execution-service (Router: {routing_key})")


async def main() -> None:
    global app_graph

    print("🔌 Iniciando Arquitectura Orientada a Eventos...")
    await runtime.initialize()

    # Levantamos el consumidor en segundo plano SIN bloquear la consola
    asyncio.create_task(runtime.mq_client.start_consuming(handle_rabbitmq_message))

    try:
        async with AsyncSqliteSaver.from_conn_string("agent_memory.db") as memory_saver:
            app_graph = runtime.graph.compile(checkpointer=memory_saver)

            print("✅ Motor de Razonamiento listo con Memoria 4-Niveles (Jarvis / Qwen 2.5 7B).")
            print("------------------------------------------------------------------")

            while True:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(None, input, "\nUsuario: ")
                except (KeyboardInterrupt, EOFError, asyncio.CancelledError):
                    break

                if not user_input or not user_input.strip():
                    continue

                if user_input.strip().lower() in ["salir", "exit", "quit"]:
                    print("👋 Cerrando asistente...")
                    break

                state_update: AgentState = {
                    "messages": [HumanMessage(content=user_input.strip())],
                    "correlation_id": "req-" + str(uuid.uuid4())[:8],
                }

                result = await app_graph.ainvoke(state_update, config=config)

                last_msg = result["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    print(f"🤖 Asistente: {last_msg.content}")

    except asyncio.CancelledError:
        pass
    finally:
        print("💾 Guardando memorias y cerrando servicios limpiamente...")
        await runtime.close()
        print("✅ Apagado completado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass