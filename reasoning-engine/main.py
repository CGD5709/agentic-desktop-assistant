from agent import agent_graph, AgentState 
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

def main():
    # Cambiamos el ID para empezar una conversación limpia (sin la simulación anterior)
    config: RunnableConfig = {"configurable": {"thread_id": "sesion-josevi-002"}}
    
    print("\n=== TURNO 1: El usuario saluda ===")
    state_1: AgentState = {
        "messages": [HumanMessage(content="Hola, me llamo Josevi.")],
        "correlation_id": "id-001"
    }
    # Guardamos el resultado del grafo en una variable
    result_1 = agent_graph.invoke(state_1, config=config)
    
    # Extraemos y mostramos SOLO el último mensaje (la respuesta de la IA)
    respuesta_ia_1 = result_1["messages"][-1].content
    print(f"\n🤖 Asistente: {respuesta_ia_1}")
    
    
    print("\n\n=== TURNO 2: El usuario pide una acción ===")
    state_2: AgentState = {
        "messages": [HumanMessage(content="Por favor, haz un commit en git.")],
        "correlation_id": "id-002"
    }
    # Guardamos el resultado del grafo tras la acción
    result_2 = agent_graph.invoke(state_2, config=config)
    
    # Volvemos a extraer el último mensaje tras volver del action_node
    respuesta_ia_2 = result_2["messages"][-1].content
    print(f"\n🤖 Asistente: {respuesta_ia_2}")
    
    
    print("\n\n=== VERIFICACIÓN DE MEMORIA ===")
    print("Historial completo recuperado de SQLite:")
    for msg in result_2["messages"]:
        # Evitamos imprimir mensajes vacíos de las peticiones de herramientas
        if msg.content: 
            print(f"- {msg.type.capitalize()}: {msg.content}")

if __name__ == "__main__":
    main()