"""
Agent Orchestrator module for the Jarvis Desktop Assistant.

Defines the AgentRuntime container, graph workflow assembly, and factory functions
for building isolated, testable agent runtime environments with zero import-time side effects.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Final, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from rabbitmq import RabbitMQClient
from .memory.async_manager import AsyncMemoryManager
from .memory.profile_store import ProfileStore
from .memory.short_term import SessionSummarizer
from .memory.vector_store import VectorMemoryStore
from .models import AgentState
from .nodes import (
    DEFAULT_MAX_DIALOGUE_TOKENS,
    ActionNode,
    ChatNode,
    CommandNode,
    NodeName,
    RouterNode,
    SummarizeNode,
    route_intent,
    should_use_tools,
)
from .prompts import (
    COMMAND_PROMPT,
    JARVIS_SYSTEM_PROMPT,
    ROUTER_PROMPT,
    SUMMARIZE_PROMPT,
)

# Configuration defaults for persistence, debouncing, and model execution
DEFAULT_PROFILE_DB_PATH: Final[str] = "./data/assistant_profile.db"
DEFAULT_CHROMA_DIR: Final[str] = "./data/chroma_db"
DEFAULT_DEBOUNCE_SECONDS: Final[float] = 45.0
DEFAULT_LLM_MODEL: Final[str] = "qwen2.5:7b"
DEFAULT_LLM_TEMPERATURE: Final[float] = 0.2

# Context window capacity for local Ollama execution.
# Ollama defaults to num_ctx=2048 if omitted. Bumping to 8192 accommodates
# system instructions (~500 tokens), user profile (~300 tokens), RAG memories (~500 tokens),
# dialogue history budget (3000 tokens), and ample response generation headroom without silent truncation.
DEFAULT_LLM_NUM_CTX: Final[int] = 8192


@dataclass
class AgentRuntime:
    """
    Encapsulates an isolated agent runtime environment, including the LangGraph workflow
    and all associated messaging clients, persistence stores, and background managers.
    """
    graph: StateGraph
    mq_client: RabbitMQClient
    profile_store: ProfileStore
    vector_store: VectorMemoryStore
    memory_manager: AsyncMemoryManager
    session_summarizer: SessionSummarizer
    dynamic_tools: List[Dict[str, Any]] = field(default_factory=list)
    llm: Optional[BaseChatModel] = None

    async def initialize(self) -> None:
        """Initialize messaging connections and persistent memory stores."""
        await self.mq_client.connect()
        await self.profile_store.initialize()
        await self.vector_store.initialize()

    async def close(self) -> None:
        """Flush pending background memories and cleanly close all active connections."""
        await self.memory_manager.flush_and_close()
        await self.profile_store.close()
        await self.mq_client.close()


def create_agent_graph(
    router_node: RouterNode,
    chat_node: ChatNode,
    command_node: CommandNode,
    action_node: ActionNode,
    summarize_node: SummarizeNode,
) -> StateGraph:
    """
    Assemble and configure the LangGraph workflow topology for the agent orchestrator.

    Workflow Topology:
        START -> router_node (evaluates intent and conditionally queries vector store)
                  |-- (CHAT) ----> chat_node -------------------------------> END
                  `-- (COMMAND) -> command_node --+-- (tool calls required) -> action_node -> summarize_node -> END
                                                  `-- (no tool calls) -------> END

    Args:
        router_node: Node evaluating semantic user intent.
        chat_node: Node executing standard conversational generation.
        command_node: Node handling technical instructions and tool invocation.
        action_node: Node dispatching RPC tool execution requests over RabbitMQ.
        summarize_node: Node translating raw tool responses into conversational synthesis.

    Returns:
        Configured StateGraph instance ready for checkpointing and compilation.
    """
    workflow = StateGraph(AgentState)  # type: ignore[type-var]

    workflow.add_node(NodeName.ROUTER.value, router_node)
    workflow.add_node(NodeName.CHAT.value, chat_node)
    workflow.add_node(NodeName.COMMAND.value, command_node)
    workflow.add_node(NodeName.ACTION.value, action_node)
    workflow.add_node(NodeName.SUMMARIZE.value, summarize_node)

    workflow.add_edge(START, NodeName.ROUTER.value)
    workflow.add_conditional_edges(
        NodeName.ROUTER.value,
        route_intent,
        {
            NodeName.CHAT.value: NodeName.CHAT.value,
            NodeName.COMMAND.value: NodeName.COMMAND.value,
        },
    )
    workflow.add_edge(NodeName.CHAT.value, END)
    workflow.add_conditional_edges(
        NodeName.COMMAND.value,
        should_use_tools,
        {
            NodeName.ACTION.value: NodeName.ACTION.value,
            NodeName.END.value: END,
        },
    )
    workflow.add_edge(NodeName.ACTION.value, NodeName.SUMMARIZE.value)
    workflow.add_edge(NodeName.SUMMARIZE.value, END)

    return workflow


def create_agent_runtime(
    profile_db_path: str = DEFAULT_PROFILE_DB_PATH,
    chroma_dir: str = DEFAULT_CHROMA_DIR,
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    llm_model: str = DEFAULT_LLM_MODEL,
    llm_temperature: float = DEFAULT_LLM_TEMPERATURE,
    llm_num_ctx: int = DEFAULT_LLM_NUM_CTX,
    max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    mq_client: Optional[RabbitMQClient] = None,
    llm: Optional[BaseChatModel] = None,
) -> AgentRuntime:
    """
    Construct an isolated AgentRuntime with clean dependency injection.

    Eliminates global state and import-time side effects by creating fresh client,
    store, and node instances bound to the specified configuration.

    Args:
        profile_db_path: Filesystem path to SQLite profile database.
        chroma_dir: Filesystem path to ChromaDB persistent vector storage.
        debounce_seconds: Time window for debouncing asynchronous memory consolidation.
        llm_model: Local Ollama model identifier.
        llm_temperature: Sampling temperature for model generation.
        llm_num_ctx: Context window size configured for local Ollama instances.
        max_dialogue_tokens: History token budget for conversational context assembly.
        mq_client: Optional pre-configured RabbitMQ client instance.
        llm: Optional pre-configured language model instance.

    Returns:
        Fully configured AgentRuntime container.
    """
    client = mq_client if mq_client is not None else RabbitMQClient()
    p_store = ProfileStore(db_path=profile_db_path)
    v_store = VectorMemoryStore(persist_directory=chroma_dir)
    m_manager = AsyncMemoryManager(
        vector_store=v_store,
        profile_store=p_store,
        debounce_seconds=debounce_seconds,
        num_ctx=llm_num_ctx,
    )
    s_summarizer = SessionSummarizer()
    tools: List[Dict[str, Any]] = []

    chat_llm = (
        llm
        if llm is not None
        else ChatOllama(
            model=llm_model,
            temperature=llm_temperature,
            num_ctx=llm_num_ctx,
        )
    )

    router_node = RouterNode(
        llm=chat_llm,
        vector_store=v_store,
        prompt=ROUTER_PROMPT,
    )
    chat_node = ChatNode(
        llm=chat_llm,
        profile_store=p_store,
        session_summarizer=s_summarizer,
        vector_store=v_store,
        memory_manager=m_manager,
        system_prompt=JARVIS_SYSTEM_PROMPT,
        max_dialogue_tokens=max_dialogue_tokens,
    )
    command_node = CommandNode(
        llm=chat_llm,
        profile_store=p_store,
        session_summarizer=s_summarizer,
        vector_store=v_store,
        memory_manager=m_manager,
        tools=tools,
        system_prompt=COMMAND_PROMPT,
        max_dialogue_tokens=max_dialogue_tokens,
    )
    action_node = ActionNode(mq_client=client)
    summarize_node = SummarizeNode(
        llm=chat_llm,
        profile_store=p_store,
        session_summarizer=s_summarizer,
        vector_store=v_store,
        memory_manager=m_manager,
        system_prompt=SUMMARIZE_PROMPT,
        max_dialogue_tokens=max_dialogue_tokens,
    )

    graph = create_agent_graph(
        router_node=router_node,
        chat_node=chat_node,
        command_node=command_node,
        action_node=action_node,
        summarize_node=summarize_node,
    )

    return AgentRuntime(
        graph=graph,
        mq_client=client,
        profile_store=p_store,
        vector_store=v_store,
        memory_manager=m_manager,
        session_summarizer=s_summarizer,
        dynamic_tools=tools,
        llm=chat_llm,
    )


__all__ = [
    "DEFAULT_PROFILE_DB_PATH",
    "DEFAULT_CHROMA_DIR",
    "DEFAULT_DEBOUNCE_SECONDS",
    "DEFAULT_LLM_MODEL",
    "DEFAULT_LLM_TEMPERATURE",
    "DEFAULT_LLM_NUM_CTX",
    "DEFAULT_MAX_DIALOGUE_TOKENS",
    "AgentRuntime",
    "create_agent_graph",
    "create_agent_runtime",
]
