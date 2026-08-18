# Reasoning Engine (Capa Python)

Este microservicio asíncrono actúa como el motor de razonamiento (cerebro) del asistente de escritorio. Está diseñado siguiendo un patrón de arquitectura orientada a eventos (Event-Driven) acoplado a un motor de grafos de estado.

## Arquitectura Interna de Capas

El servicio no opera de manera lineal, sino que se divide en capas que funcionan de manera concurrente:

1. **Capa de Mensajería (`rabbitmq.py` & `models.py`)**
   - Actúa como el sistema nervioso. Mantiene una conexión asíncrona (`aio-pika`) con el *Topic Exchange* de RabbitMQ.
   - Todo el tráfico de entrada y salida es validado estrictamente mediante modelos de Pydantic, garantizando el cumplimiento de los contratos JSON definidos en el ADR-006.

2. **Capa del Agente (`agent.py`)**
   - Implementa un patrón ReAct (Reasoning + Acting) utilizando `LangGraph`.
   - Mantiene un grafo estático compuesto por un nodo de razonamiento (`reasoning_node`), un nodo ejecutor (`action_node`) y enrutadores condicionales. 
   - El agente es agnóstico a la implementación de las herramientas externas; delega la ejecución al cliente de mensajería.

3. **Capa de Estado (Pendiente)**
   - Gestionará la persistencia de los hilos de ejecución utilizando SQLite. Permitirá suspender el grafo de LangGraph mientras se esperan las respuestas asíncronas de las herramientas externas (ej. aprobación manual de comandos en Java) y reanudarlo posteriormente inyectando el `correlation_id`.

## Ejecución Local
Para aislar las dependencias, este servicio requiere el uso de su propio entorno virtual (`.venv`):
1. Activar el entorno: `.\.venv\Scripts\Activate.ps1` (Windows)
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar: `python main.py`