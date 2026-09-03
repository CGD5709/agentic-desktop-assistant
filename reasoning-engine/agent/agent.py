"""
Agent Orchestrator module for the Jarvis Desktop Assistant.
Assembles the multi-tier memory system, messaging clients, and LangGraph workflow nodes.
"""
from typing import Any, Dict, List
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END

from rabbitmq import RabbitMQClient
from .models import AgentState
from .prompts import (
    JARVIS_SYSTEM_PROMPT,
    ROUTER_PROMPT,
    COMMAND_PROMPT,
    SUMMARIZE_PROMPT,
)
from .memory.profile_store import ProfileStore
from .memory.vector_store import VectorMemoryStore
from .memory.async_manager import AsyncMemoryManager
from .memory.short_term import SessionSummarizer

from .nodes import (
    RouterNode,
    ChatNode,
    CommandNode,
    ActionNode,
    SummarizeNode,
    route_intent,
    should_use_tools,
)

# === GLOBAL CLIENTS AND PERSISTENCE STORES ===
mq_client = RabbitMQClient()
profile_store = ProfileStore(db_path="./data/assistant_profile.db")
vector_store = VectorMemoryStore(persist_directory="./data/chroma_db")
memory_manager = AsyncMemoryManager(
    vector_store=vector_store,
    profile_store=profile_store,
    debounce_seconds=45.0,
)
session_summarizer = SessionSummarizer()

# Dynamic tools registered from external services (OpenAI function calling schema)
dynamic_tools: List[Dict[str, Any]] = []

# Base local model optimized for function calling and instruction following
llm = ChatOllama(model="qwen2.5:7b", temperature=0.2)

# === NODE INSTANTIATION (DEPENDENCY INJECTION) ===
router_node = RouterNode(
    llm=llm,
    vector_store=vector_store,
    prompt=ROUTER_PROMPT,
)

chat_node = ChatNode(
    llm=llm,
    profile_store=profile_store,
    session_summarizer=session_summarizer,
    vector_store=vector_store,
    memory_manager=memory_manager,
    system_prompt=JARVIS_SYSTEM_PROMPT,
    max_dialogue_tokens=3000,
)

command_node = CommandNode(
    llm=llm,
    profile_store=profile_store,
    session_summarizer=session_summarizer,
    vector_store=vector_store,
    memory_manager=memory_manager,
    tools=dynamic_tools,
    system_prompt=COMMAND_PROMPT,
    max_dialogue_tokens=3000,
)

action_node = ActionNode(mq_client=mq_client)

summarize_node = SummarizeNode(
    llm=llm,
    profile_store=profile_store,
    session_summarizer=session_summarizer,
    vector_store=vector_store,
    memory_manager=memory_manager,
    system_prompt=SUMMARIZE_PROMPT,
    max_dialogue_tokens=3000,
)

# === GRAPH WORKFLOW CONSTRUCTION ===
builder = StateGraph(AgentState)  # type: ignore[type-var]

builder.add_node("router_node", router_node)
builder.add_node("chat_node", chat_node)
builder.add_node("command_node", command_node)
builder.add_node("action_node", action_node)
builder.add_node("summarize_node", summarize_node)

# Flow Topology:
# START -> router_node (classifies intent and conditionally queries vector store)
#           ├─ (CHAT) ────> chat_node ───────────────────────────────> END
#           └─ (COMMAND) ─> command_node ─┬─ (requires tool calls) ──> action_node ─> summarize_node ─> END
#                                         └─ (no tool calls) ────────> END

builder.add_edge(START, "router_node")
builder.add_conditional_edges(
    "router_node",
    route_intent,
    {
        "chat_node": "chat_node",
        "command_node": "command_node",
    },
)
builder.add_edge("chat_node", END)
builder.add_conditional_edges(
    "command_node",
    should_use_tools,
    {
        "action_node": "action_node",
        "end": END,
    },
)
builder.add_edge("action_node", "summarize_node")
builder.add_edge("summarize_node", END)
