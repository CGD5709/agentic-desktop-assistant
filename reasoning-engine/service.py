import asyncio
import json
import uuid
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from agent import builder, AgentState, mq_client
from models import EventEnvelope, ToolExecutionResponsePayload

# Variables globales para el servicio
app_graph = None
# Usamos un único hilo persistente para todo el ciclo de vida del servicio
config: RunnableConfig = {"configurable": {"thread_id": "sesion-produccion"}}

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
            dynamic_tools.extend(tools_list)
            
            nombres = [t.get("name") for t in tools_list]
            print(f"\n📡 [System Discovery] Manifiesto recibido de Java.")
            print(f"   -> 🛠️ {len(tools_list)} herramienta(s) asimilada(s) por Llama 3.1: {nombres}")
            print("\nUsuario: ", end="", flush=True) # Restauramos el prompt visual
        except Exception as e:
            print(f"\n❌ Error procesando el manifiesto de herramientas: {e}")
        return

    # === 2. PROCESAMOS LAS RESPUESTAS DE LAS HERRAMIENTAS ===
    if "tool.response" not in routing_key:
        return

    print(f"\n[RabbitMQ] 📥 Respuesta recibida de Java (Router: {routing_key})")
    try:
        data = json.loads(raw_body)
        envelope = EventEnvelope(**data)
        payload = ToolExecutionResponsePayload(**envelope.payload)
        
        tool_call_id = envelope.metadata.correlation_id
        resultado_texto = f"Estado: {payload.status}. Salida de consola: {payload.output}"
        
        tool_message = ToolMessage(
            content=resultado_texto,
            tool_call_id=tool_call_id
        )
        
        print("   -> 🧠 Despertando a Llama 3.1 con el resultado...")
        assert app_graph is not None, "El grafo no se ha inicializado correctamente."
        await app_graph.aupdate_state(config, {"messages": [tool_message]})
        
        result = await app_graph.ainvoke(None, config=config)
        
        final_message = result["messages"][-1].content
        print(f"\n🤖 Asistente: {final_message}")
        print("\nUsuario: ", end="", flush=True) 
        
    except Exception as e:
        print(f"\n❌ Error procesando respuesta de Java: {e}")

async def main():
    global app_graph

    print("🔌 Iniciando Arquitectura Orientada a Eventos...")
    await mq_client.connect()
    
    # Levantamos el consumidor en segundo plano SIN bloquear la consola
    asyncio.create_task(mq_client.start_consuming(handle_rabbitmq_message))
    
    async with AsyncSqliteSaver.from_conn_string("agent_memory.db") as memory_saver:
        app_graph = builder.compile(checkpointer=memory_saver)
        
        print("✅ Motor de Razonamiento listo y en escucha.")
        print("--------------------------------------------------")
        
        # Inyectamos las reglas base si la memoria está limpia
        current_state = await app_graph.aget_state(config)
        if not current_state.values.get("messages"):
            await app_graph.aupdate_state(config, {"messages": [SystemMessage(content="Eres el cerebro de un asistente de escritorio. NUNCA uses herramientas a menos que te pidan una acción explícita.")]})
        
        # Bucle infinito interactivo
        while True:
            # Ejecutamos input() en otro hilo para no bloquear los eventos de RabbitMQ
            user_input = await asyncio.get_event_loop().run_in_executor(None, input, "\nUsuario: ")
            
            if user_input.lower() in ['salir', 'exit']:
                break
                
            state_update: AgentState = {
                "messages": [HumanMessage(content=user_input)],
                "correlation_id": "req-" + str(uuid.uuid4())[:8]
            }
            
            # Disparamos el grafo
            result = await app_graph.ainvoke(state_update, config=config)
            
            # Verificamos dónde se detuvo el grafo
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                # Si resolvió todo sin herramientas (ej. saludo)
                print(f"🤖 Asistente: {last_msg.content}")
            elif isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                # Si decidió usar una herramienta y se pausó
                print("⏳ Delegando a Execution Service... (Esperando respuesta de Java por RabbitMQ)")

    await mq_client.close()

if __name__ == "__main__":
    asyncio.run(main())