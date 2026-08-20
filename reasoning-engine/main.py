import asyncio
from agent import builder, AgentState, mq_client, profile_store, vector_store, memory_manager
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def main():
    print("🔌 Conectando a RabbitMQ...")
    await mq_client.connect()

    print("🧠 Inicializando Almacenes de Memoria...")
    await profile_store.initialize()
    await vector_store.initialize()

    # Configuramos una preferencia de prueba en el perfil (Nivel 0)
    await profile_store.set("usuario", "Josevi", category="general")
    await profile_store.set("lenguaje_favorito", "Python", category="technical")

    try:
        async with AsyncSqliteSaver.from_conn_string("agent_memory.db") as memory_saver:
            agent_graph = builder.compile(checkpointer=memory_saver)
            config: RunnableConfig = {"configurable": {"thread_id": "sesion-josevi-004"}}

            print("\n=== TURNO 1: El usuario saluda y se presenta ===")
            state_1: AgentState = {
                "messages": [HumanMessage(content="Hola Jarvis, soy Josevi y estoy trabajando en el proyecto desktop assistant.")],
                "correlation_id": "id-corr-001",
            }
            result_1 = await agent_graph.ainvoke(state_1, config=config)
            print(f"\n🤖 Asistente: {result_1['messages'][-1].content}")

            print("\n\n=== TURNO 2: El usuario pide una orden técnica ===")
            state_2: AgentState = {
                "messages": [HumanMessage(content="Por favor, haz un commit en git.")],
                "correlation_id": "id-corr-002",
            }
            result_2 = await agent_graph.ainvoke(state_2, config=config)
            print(f"\n🤖 Asistente: {result_2['messages'][-1].content}")

    finally:
        print("\n💾 Guardando memorias y cerrando...")
        await memory_manager.flush_and_close()
        await profile_store.close()
        await mq_client.close()
        print("✅ Finalizado con éxito.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass