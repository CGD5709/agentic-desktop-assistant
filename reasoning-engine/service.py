import asyncio
import json
import uuid
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from agent import builder, AgentState, mq_client, JARVIS_SYSTEM_PROMPT, profile_store, vector_store, memory_manager
from models import EventEnvelope, ToolExecutionResponsePayload

# Variables globales para el servicio
app_graph = None
# Usamos un único hilo persistente para todo el ciclo de vida del servicio
config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}

def convert_java_tools_to_openai_format(raw_tools: list) -> list:
    """
    Convierte el manifiesto de herramientas de Java al formato OpenAI
    que ChatOllama.bind_tools() espera.
    
    Java envía:   {"name": "...", "description": "...", "parameters": {...}}
    OpenAI espera: {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    converted = []
    for tool in raw_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
            }
        }
        converted.append(openai_tool)
    return converted

async def handle_rabbitmq_message(raw_body: str, routing_key: str):
    """El CALLBACK que escucha todos los eventos de la red."""
    
    # === 1. INTERCEPTAMOS EL SYSTEM DISCOVERY ===
    if routing_key == "system.discovery.java":
        try:
            data = json.loads(raw_body)
            tools_list = data.get("payload", {}).get("tools", [])
            
            # Importamos nuestra lista global y la actualizamos
            from agent import dynamic_tools
            dynamic_tools.clear()
            
            # Convertimos al formato OpenAI antes de almacenar
            converted_tools = convert_java_tools_to_openai_format(tools_list)
            dynamic_tools.extend(converted_tools)
            
            nombres = [t["function"]["name"] for t in converted_tools]
            print(f"\n📡 [System Discovery] Manifiesto recibido de Java.")
            print(f"   -> 🛠️ {len(converted_tools)} herramienta(s) asimilada(s): {nombres}")
            print("\nUsuario: ", end="", flush=True)
        except Exception as e:
            print(f"\n❌ Error procesando el manifiesto de herramientas: {e}")
        return

    # === 2. REGISTRO DE RESPUESTAS DE HERRAMIENTAS ===
    if "tool.response" in routing_key:
        print(f"\n[RabbitMQ] 📥 Respuesta recibida de Java (Router: {routing_key})")

async def main():
    global app_graph

    print("🔌 Iniciando Arquitectura Orientada a Eventos...")
    await mq_client.connect()
    
    print("🧠 Inicializando Almacén de Perfil y Memoria Vectorial...")
    await profile_store.initialize()
    await vector_store.initialize()

    # Levantamos el consumidor en segundo plano SIN bloquear la consola
    asyncio.create_task(mq_client.start_consuming(handle_rabbitmq_message))
    
    try:
        async with AsyncSqliteSaver.from_conn_string("agent_memory.db") as memory_saver:
            app_graph = builder.compile(checkpointer=memory_saver)
            
            print("✅ Motor de Razonamiento listo con Memoria 4-Niveles (Jarvis / Qwen 2.5 7B).")
            print("------------------------------------------------------------------")
            
            # Bucle infinito interactivo
            while True:
                try:
                    # Ejecutamos input() en otro hilo para no bloquear eventos
                    user_input = await asyncio.get_event_loop().run_in_executor(None, input, "\nUsuario: ")
                except (KeyboardInterrupt, EOFError, asyncio.CancelledError):
                    break
                    
                # Ignoramos si el usuario solo pulsó Enter o espacios
                if not user_input or not user_input.strip():
                    continue
                    
                if user_input.strip().lower() in ['salir', 'exit', 'quit']:
                    print("👋 Cerrando asistente...")
                    break
                    
                state_update: AgentState = {
                    "messages": [HumanMessage(content=user_input.strip())],
                    "correlation_id": "req-" + str(uuid.uuid4())[:8],
                }
                
                # Disparamos el grafo de LangGraph
                result = await app_graph.ainvoke(state_update, config=config)
                
                # Obtenemos la última respuesta del asistente
                last_msg = result["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    print(f"🤖 Asistente: {last_msg.content}")

    except asyncio.CancelledError:
        pass
    finally:
        print("💾 Guardando memorias y cerrando servicios limpiamente...")
        await memory_manager.flush_and_close()
        await profile_store.close()
        await mq_client.close()
        print("✅ Apagado completado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass