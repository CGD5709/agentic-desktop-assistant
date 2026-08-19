import asyncio
import json
import aio_pika
import aio_pika.abc
from typing import Callable, Awaitable, Dict, Any, Optional
from models import EventEnvelope

class RabbitMQClient:
    def __init__(self, amqp_url: str = "amqp://guest:guest@localhost/"):
        """
        Por defecto, intentará conectarse al RabbitMQ local.
        Cuando usemos Docker, cambiaremos esta URL.
        """
        self.amqp_url = amqp_url
        
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.exchange: aio_pika.abc.AbstractExchange | None = None
        # Mapa de futuros pendientes: correlation_id -> Future
        self.pending_futures: Dict[str, asyncio.Future] = {}

    async def connect(self):
        """Establece la conexión y declara el router (Exchange)"""
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        
        # Declaramos el Topic Exchange (ADR-006)
        self.exchange = await self.channel.declare_exchange(
            name="agent_events", 
            type=aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        print("[RabbitMQ] Conectado y Exchange 'agent_events' declarado.")

    async def publish(self, routing_key: str, envelope: EventEnvelope):
        """Serializa el modelo Pydantic a JSON y lo envía a la cola"""
        if not self.exchange:
            raise RuntimeError("Debes llamar a connect() antes de publicar.")

        # by_alias=True es crucial para que Pydantic convierta 'event_id' a 'eventId'
        json_payload = envelope.model_dump_json(by_alias=True)
        
        message = aio_pika.Message(
            body=json_payload.encode("utf-8"),
            content_type="application/json"
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
        print(f"[RabbitMQ] Mensaje publicado (Router: {routing_key})")

    async def send_and_wait(self, routing_key: str, envelope: EventEnvelope) -> Dict[str, Any]:
        """
        Publica una petición y espera asíncronamente la respuesta de Java.
        No tiene timeout artificial: puede esperar horas si requiere confirmación humana.
        """
        correlation_id = envelope.metadata.correlation_id
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self.pending_futures[correlation_id] = future

        try:
            await self.publish(routing_key, envelope)
            result = await future
            return result
        finally:
            self.pending_futures.pop(correlation_id, None)

    async def start_consuming(self, message_handler: Callable[[str, str], Awaitable[None]]):
        """
        Crea una cola exclusiva para Python, se suscribe a los eventos
        necesarios y los pasa a una función manejadora (callback).
        """
        if not self.channel or not self.exchange:
            raise RuntimeError("Debes llamar a connect() antes de consumir.")

        # Declaramos la cola donde Python recibirá sus mensajes
        queue = await self.channel.declare_queue("python_reasoning_queue", durable=True)
        
        # Nos suscribimos al registro de herramientas de Java
        await queue.bind(self.exchange, routing_key="system.discovery.java")
        # Nos suscribimos a las respuestas de las herramientas (cualquiera)
        await queue.bind(self.exchange, routing_key="tool.response.*")

        print("[RabbitMQ] Escuchando eventos en 'python_reasoning_queue'...")

        # Bucle asíncrono infinito para procesar mensajes
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(): 
                    raw_body = message.body.decode("utf-8")
                    safe_routing_key = message.routing_key or ""
                    try:
                        # Si es una respuesta de herramienta, completamos el Future pendiente si existe
                        if "tool.response" in safe_routing_key:
                            try:
                                data = json.loads(raw_body)
                                correlation_id = data.get("metadata", {}).get("correlationId")
                                if correlation_id and correlation_id in self.pending_futures:
                                    fut = self.pending_futures[correlation_id]
                                    if not fut.done():
                                        fut.set_result(data)
                            except Exception as parse_err:
                                print(f"[RabbitMQ] Error parseando payload de respuesta: {parse_err}")

                        await message_handler(raw_body, safe_routing_key)
                    except Exception as e:
                        print(f" [RabbitMQ] Error en el manejador: {e}")

    async def close(self):
        """Cierra la conexión limpiamente"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            print("[RabbitMQ] Conexión cerrada.")