import asyncio
import json
import aio_pika
import aio_pika.abc
from typing import Callable, Awaitable, Dict, Any, Optional
from models import EventEnvelope
class RabbitMQClient:
    """
    Asynchronous RabbitMQ client implementing event broadcasting and the Async RPC pattern.
    Handles robust connections and multiplexed channels for non-blocking message passing.
    """
    def __init__(self, amqp_url: str = "amqp://guest:guest@localhost/"):
        """
        Initializes the client state. Network connection is deferred until connect() is called.
        """
        self.amqp_url = amqp_url
        
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.exchange: aio_pika.abc.AbstractExchange | None = None

        # Maps correlation_id to pending asyncio Futures for the RPC implementation 
        self.pending_futures: Dict[str, asyncio.Future] = {}

    async def connect(self):
        """
        Establishes a robust TCP connection, opens a channel, and declares the main topology.
        """
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        
        # Declares the Topic Exchange as defined in rabbitmq-spec.md
        self.exchange = await self.channel.declare_exchange(
            name="agent_events", 
            type=aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        # TODO: Replace print with logger.info
        print("[RabbitMQ] Conectado y Exchange 'agent_events' declarado.")

    async def publish(self, routing_key: str, envelope: EventEnvelope):
        """
        Serializes a Pydantic envelope to JSON and publishes it to the exchange.
        """
        if not self.exchange:
            raise ConnectionError("RabbitMQ client is not initialized. Call connect() before publishing.")

        # by_alias=True ensures Python snake_case variables are exported as camelCase (e.g., eventId)
        json_payload = envelope.model_dump_json(by_alias=True)
        
        message = aio_pika.Message(
            body=json_payload.encode("utf-8"),
            content_type="application/json"
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
        # TODO: Replace print with logger.debug
        print(f"[RabbitMQ] Mensaje publicado (Router: {routing_key})")

    async def send_and_wait(self, routing_key: str, envelope: EventEnvelope) -> Dict[str, Any]:
        """
        Publishes a request and suspends execution until a correlated response is received.
        Intentionally lacks a timeout to support long-running human-in-the-loop tasks.
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
            # Ensures memory is freed even if the future is cancelled
            self.pending_futures.pop(correlation_id, None)

    async def start_consuming(self, message_handler: Callable[[str, str], Awaitable[None]]):
        """
        Sets up an exclusive queue, binds routing keys, and starts the asynchronous consumption loop.
        Delegates business logic processing to the injected message_handler.
        """
        if not self.channel or not self.exchange:
            raise ConnectionError("RabbitMQ client is not initialized. Call connect() before consuming.")

        # Declare the exclusive queue for this Python agent instance
        queue = await self.channel.declare_queue("python_reasoning_queue", durable=True)
        
        # Bind the queue to the exchange for tool discovery and RPC responses
        await queue.bind(self.exchange, routing_key="system.discovery.java")
        await queue.bind(self.exchange, routing_key="tool.response.*")
        
        # TODO: Replace print with logger.info
        print("[RabbitMQ] Listening for events on 'python_reasoning_queue'...")

        # TODO: Refactor consumer error handling to prevent Poison Pills and false ACKs.
        # 1. Use async with message.process(ignore_processed=True) for manual control.
        # 2. Acknowledge manually: await message.ack() on success.
        # 3. Handle failures via logger.error() and await message.reject(requeue=False).
        # 4. Consider declaring a Dead Letter Queue (DLQ) to store rejected messages safely.    
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(): 
                    raw_body = message.body.decode("utf-8")
                    routing_key = message.routing_key or ""
                    
                    # Intercept and process response messages to resolve pending futures
                    if "tool.response" in routing_key:
                        try:
                            data = json.loads(raw_body)
                            correlation_id = data.get("metadata", {}).get("correlationId")
                            
                            # Resolve pending future if correlation ID matches
                            if correlation_id and correlation_id in self.pending_futures:
                                fut = self.pending_futures[correlation_id]
                                if not fut.done():
                                    fut.set_result(data)
                                    
                        except json.JSONDecodeError as parse_err:
                            # TODO: Replace print with logger.error
                            print(f"[RabbitMQ] Failed to parse response payload: {parse_err}")
                            # Discard malformed messages immediately to protect the business layer
                            continue            
                                
                    # Delegate the validated event to the external handler
                    try:
                        await message_handler(raw_body, routing_key)
                    except Exception as e:
                        # TODO: Replace print with logger.error and handle message requeueing/DLQ
                        print(f"[RabbitMQ] Handler execution failed: {e}")

    async def close(self):
        """
        Gracefully closes the network connection.
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            # TODO: Replace print with logger.info
            print("[RabbitMQ] Connection closed.")