import asyncio
# Fíjate que ahora importamos 'builder' en lugar de 'agent_graph'
from agent import builder, AgentState, mq_client 
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

# IMPORTACIÓN DE LA MEMORIA ASÍNCRONA
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver 

async def main():
    # 1. Abrimos la conexión de red
    print("🔌 Conectando a RabbitMQ...")
    await mq_client.connect()
    
    # 2. Levantamos la memoria asíncrona de SQLite
    async with AsyncSqliteSaver.from_conn_string("agent_memory.db") as memory_saver:
        
        # 3. Compilamos el grafo inyectándole la memoria asíncrona
        agent_graph = builder.compile(checkpointer=memory_saver)
        config: RunnableConfig = {"configurable": {"thread_id": "sesion-josevi-004"}}
        
        print("\n=== TURNO 1: El usuario saluda ===")
        state_1: AgentState = {
            "messages": [
                SystemMessage(content="Eres el cerebro de un asistente de escritorio. NUNCA uses herramientas a menos que el usuario te lo pida explícitamente."),
                HumanMessage(content="Hola, me llamo Josevi.")
            ],
            "correlation_id": "id-corr-001"
        }
        result_1 = await agent_graph.ainvoke(state_1, config=config)
        print(f"\n🤖 Asistente: {result_1['messages'][-1].content}")
        
        
        print("\n\n=== TURNO 2: El usuario pide una acción ===")
        state_2: AgentState = {
            "messages": [HumanMessage(content="Por favor, haz un commit en git.")],
            "correlation_id": "id-corr-002"
        }
        result_2 = await agent_graph.ainvoke(state_2, config=config)
        print(f"\n🤖 Asistente: {result_2['messages'][-1].content}")
        
    # 4. Cerramos la conexión de red limpiamente
    await mq_client.close()

if __name__ == "__main__":
    asyncio.run(main())