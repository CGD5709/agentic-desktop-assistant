import ast
import json
import re
from typing import Any, Dict, Final, List, Optional, Set
import uuid
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..memory.async_manager import AsyncMemoryManager
from ..memory.profile_store import ProfileStore
from ..memory.short_term import SessionSummarizer
from ..memory.vector_store import VectorMemoryStore
from ..models import AgentState
from ..prompts import COMMAND_PROMPT
from .base import BaseAgentNode, DEFAULT_MAX_DIALOGUE_TOKENS


# Dynamic cross-language semantic token synonyms for tool discovery matching
KEYWORD_SYNONYMS: Final[Dict[str, str]] = {
    "email": "correo",
    "emails": "correos",
    "mail": "correo",
    "mails": "correos",
    "unread": "no_leidos",
    "read": "leer",
    "fetch": "consultar",
    "get": "consultar",
    "kill": "matar",
    "close": "cerrar",
    "stop": "terminar",
    "process": "proceso",
    "processes": "procesos",
    "web": "web",
    "website": "sitio_web",
    "url": "sitio_web",
    "open": "abrir",
    "browser": "sitio_web",
    "port": "puerto",
    "ports": "puertos",
    "scan": "escanear",
    "audio": "audio",
    "volume": "volumen",
    "sound": "audio",
    "memory": "rendimiento",
    "cpu": "rendimiento",
    "ram": "rendimiento",
    "stats": "rendimiento",
}

ARG_SYNONYMS: Final[Dict[str, List[str]]] = {
    "account": ["cuenta", "account"],
    "limit": ["limite", "limite_procesos", "limit"],
    "name": ["nombre_proceso", "nombre", "name"],
    "process_name": ["nombre_proceso", "process_name"],
    "pid": ["pid", "process_id"],
    "url": ["url", "link", "direccion"],
    "port": ["puerto", "port"],
    "to": ["destinatario", "recipient", "to"],
    "recipient": ["destinatario", "recipient"],
    "subject": ["asunto", "subject"],
    "body": ["cuerpo", "body", "message", "mensaje", "content"],
    "action": ["accion", "action"],
}


def resolve_tool_definition(call_name: str, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Dynamically resolves a tool invocation name to a registered tool definition
    received from the execution-service discovery manifest.

    Args:
        call_name: Name of the tool function requested by the LLM.
        available_tools: List of dynamic tool schema descriptors from Java.

    Returns:
        The matched tool dictionary if found; None otherwise.
    """
    if not call_name or not available_tools:
        return None

    call_clean = call_name.strip().lower().replace("-", "_")

    # 1. Exact or normalized name match
    for tool in available_tools:
        fn = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = fn.get("name", "") if isinstance(fn, dict) else tool.get("name", "")
        if name.lower() == call_clean:
            return tool

    # 2. Semantic token overlap matching against tool names and descriptions
    call_tokens = set(re.split(r"[_\s]+", call_clean))
    expanded_tokens = set(call_tokens)
    for tok in call_tokens:
        if tok in KEYWORD_SYNONYMS:
            expanded_tokens.add(KEYWORD_SYNONYMS[tok])

    best_tool = None
    best_score = 0

    for tool in available_tools:
        fn = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = fn.get("name", "") if isinstance(fn, dict) else tool.get("name", "")
        desc = fn.get("description", "").lower() if isinstance(fn, dict) else ""
        name_tokens = set(re.split(r"[_\s]+", name.lower()))
        desc_tokens = set(re.split(r"[_\s,.]+", desc))

        score = len(expanded_tokens & name_tokens) * 3 + len(expanded_tokens & desc_tokens)
        if score > best_score and score >= 2:
            best_score = score
            best_tool = tool

    return best_tool


def normalize_tool_args(tool_schema: Optional[Dict[str, Any]], raw_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dynamically normalizes raw arguments against the tool's JSON Schema property definitions.

    Args:
        tool_schema: The matched tool definition dictionary containing JSON Schema parameters.
        raw_args: The arguments dictionary parsed from the LLM invocation.

    Returns:
        Normalized dictionary with argument keys aligned to schema property names.
    """
    if not isinstance(raw_args, dict):
        return {}

    fn = tool_schema.get("function", {}) if isinstance(tool_schema, dict) else {}
    params = fn.get("parameters", {}) if isinstance(fn, dict) else {}
    props = params.get("properties", {}) if isinstance(params, dict) else {}

    normalized: Dict[str, Any] = {}

    for raw_k, raw_v in raw_args.items():
        k_lower = str(raw_k).lower()
        matched_prop = None

        # 1. Exact match in tool properties
        if props and k_lower in props:
            matched_prop = k_lower
        else:
            # 2. Check cross-language synonyms
            for _, syn_list in ARG_SYNONYMS.items():
                if k_lower in syn_list:
                    if props:
                        for target_prop in syn_list:
                            if target_prop in props:
                                matched_prop = target_prop
                                break
                    else:
                        matched_prop = syn_list[0]
                        break
                if matched_prop:
                    break

        final_key = matched_prop if matched_prop else raw_k
        normalized[final_key] = raw_v

    return normalized


def _extract_python_call_ast(expr_str: str, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Safely parse a Python expression like tool_call(func, arg='value') or func(arg='value')
    using Python's AST parser and resolve it dynamically against registered tools.
    """
    try:
        parsed = ast.parse(expr_str.strip(), mode="eval")
        if not isinstance(parsed.body, ast.Call):
            return None
        call = parsed.body
        func_name = ""
        args_dict: Dict[str, Any] = {}

        if isinstance(call.func, ast.Name):
            if call.func.id == "tool_call":
                if call.args:
                    first_arg = call.args[0]
                    if isinstance(first_arg, ast.Name):
                        func_name = first_arg.id
                    elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        func_name = first_arg.value
                if len(call.args) > 1 and isinstance(call.args[1], ast.Dict):
                    for k, v in zip(call.args[1].keys, call.args[1].values):
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            try:
                                args_dict[k.value] = ast.literal_eval(v)
                            except Exception:
                                pass
            else:
                func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            func_name = call.func.attr

        matched_tool = resolve_tool_definition(func_name, available_tools)
        if not matched_tool:
            return None

        fn_meta = matched_tool.get("function", {}) if isinstance(matched_tool, dict) else {}
        canonical_name = fn_meta.get("name", func_name) if isinstance(fn_meta, dict) else matched_tool.get("name", func_name)

        # Extract keyword arguments
        for kw in call.keywords:
            if kw.arg:
                try:
                    args_dict[kw.arg] = ast.literal_eval(kw.value)
                except Exception:
                    if isinstance(kw.value, ast.Name):
                        args_dict[kw.arg] = kw.value.id

        return {
            "name": canonical_name,
            "args": normalize_tool_args(matched_tool, args_dict),
            "id": f"call_{uuid.uuid4()}",
            "type": "tool_call",
        }
    except Exception:
        return None


def extract_fallback_tool_calls(
    response: AIMessage,
    available_tools: List[Dict[str, Any]],
) -> Optional[List[Dict[str, Any]]]:
    """
    Inspect an AIMessage that lacks structured tool_calls.
    Extract simulated tool calls from XML tags (<tool_call>), Markdown JSON, Python code blocks,
    or inline function calls, mapping them into standard OpenAI-compatible tool_call dictionaries.

    Args:
        response: Generated AIMessage from the language model.
        available_tools: List of dynamic tool schema descriptors.

    Returns:
        List of structured tool call dictionaries if found; None otherwise.
    """
    if not isinstance(response.content, str) or not response.content.strip():
        return None

    if not available_tools:
        return None

    content = response.content.strip()
    found_tool_calls: List[Dict[str, Any]] = []

    # Strategy 1: XML tags <tool_call> ... </tool_call>
    xml_matches = re.findall(r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", content, re.IGNORECASE)
    for xml_cand in xml_matches:
        try:
            parsed = json.loads(xml_cand)
            if isinstance(parsed, dict):
                raw_name = parsed.get("name") or parsed.get("tool_name") or ""
                matched_tool = resolve_tool_definition(raw_name, available_tools)
                if matched_tool:
                    fn_meta = matched_tool.get("function", {})
                    c_name = fn_meta.get("name", raw_name) if isinstance(fn_meta, dict) else raw_name
                    raw_args = parsed.get("arguments") or parsed.get("args") or {}
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except Exception:
                            raw_args = {}
                    found_tool_calls.append({
                        "name": c_name,
                        "args": normalize_tool_args(matched_tool, raw_args),
                        "id": f"call_{uuid.uuid4()}",
                        "type": "tool_call",
                    })
        except Exception:
            ast_res = _extract_python_call_ast(xml_cand, available_tools)
            if ast_res:
                found_tool_calls.append(ast_res)

    if found_tool_calls:
        return found_tool_calls

    # Strategy 2: Markdown JSON code blocks ```json ... ``` or standalone JSON objects
    json_candidates = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content, re.IGNORECASE)
    if not json_candidates:
        json_candidates = re.findall(r"(\{\s*\"(?:name|tool_name|action|function)\"\s*:\s*\"[^\"]+\"[\s\S]*?\})", content)

    for candidate in json_candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                raw_name = parsed.get("name") or parsed.get("tool_name") or parsed.get("action") or ""
                matched_tool = resolve_tool_definition(raw_name, available_tools)
                if matched_tool:
                    fn_meta = matched_tool.get("function", {})
                    c_name = fn_meta.get("name", raw_name) if isinstance(fn_meta, dict) else raw_name
                    raw_args = parsed.get("arguments") or parsed.get("args") or parsed.get("action_input") or {}
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except Exception:
                            raw_args = {}
                    found_tool_calls.append({
                        "name": c_name,
                        "args": normalize_tool_args(matched_tool, raw_args),
                        "id": f"call_{uuid.uuid4()}",
                        "type": "tool_call",
                    })
        except Exception:
            continue

    if found_tool_calls:
        return found_tool_calls

    # Strategy 3: Python code blocks (```python ... ``` or ''' python ... ''')
    py_blocks = re.findall(r"(?:```|''')(?:python)?\s*([\s\S]*?)\s*(?:```|''')", content, re.IGNORECASE)
    for block in py_blocks:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line:
                ast_res = _extract_python_call_ast(line, available_tools)
                if ast_res:
                    found_tool_calls.append(ast_res)

    if found_tool_calls:
        return found_tool_calls

    # Strategy 4: Inline standalone function calls
    inline_calls = re.findall(r"([a-zA-Z_0-9]+\s*\([^)\n]*\))", content)
    for inline_str in inline_calls:
        ast_res = _extract_python_call_ast(inline_str, available_tools)
        if ast_res:
            found_tool_calls.append(ast_res)

    return found_tool_calls if found_tool_calls else None


class CommandNode(BaseAgentNode):
    """
    Manages technical commands, system queries, and dynamic tool binding.
    Inherits multi-tier memory assembly and turn recording from BaseAgentNode.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = COMMAND_PROMPT,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        """
        Initialize the command node with tool registry and memory dependencies.
        """
        super().__init__(
            llm=llm,
            profile_store=profile_store,
            session_summarizer=session_summarizer,
            vector_store=vector_store,
            memory_manager=memory_manager,
            system_prompt=system_prompt,
            max_dialogue_tokens=max_dialogue_tokens,
        )
        self._tools = tools if tools is not None else []

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute technical command reasoning and bind available tools.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary containing the generated AIMessage response.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        assembled_messages = await self._assemble_context(messages, retrieved_memories)

        if self._tools:
            llm_with_tools = self._llm.bind_tools(self._tools)
            response = await llm_with_tools.ainvoke(assembled_messages)
        else:
            response = await self._llm.ainvoke(assembled_messages)

        # Normalize native structured tool_calls if emitted by the LLM
        if isinstance(response, AIMessage) and response.tool_calls and self._tools:
            normalized_calls = []
            for tc in response.tool_calls:
                raw_name = tc.get("name", "")
                matched_tool = resolve_tool_definition(raw_name, self._tools)
                fn_meta = matched_tool.get("function", {}) if isinstance(matched_tool, dict) else {}
                canonical_name = fn_meta.get("name", raw_name) if isinstance(fn_meta, dict) else raw_name
                raw_args = tc.get("args") or {}
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except Exception:
                        raw_args = {}
                normalized_args = normalize_tool_args(matched_tool, raw_args)
                normalized_calls.append({
                    "name": canonical_name,
                    "args": normalized_args,
                    "id": tc.get("id") or f"call_{uuid.uuid4()}",
                    "type": "tool_call",
                })
            response = AIMessage(
                content="",
                tool_calls=normalized_calls,
                id=getattr(response, "id", str(uuid.uuid4())),
            )

        # Fallback recovery: If no structured tool_calls were emitted, but the model generated
        # simulated tool calling syntax (XML, JSON, Python code blocks, inline calls), recover it.
        if isinstance(response, AIMessage) and not response.tool_calls and self._tools:
            fallback_calls = extract_fallback_tool_calls(response, self._tools)
            if fallback_calls:
                response = AIMessage(
                    content="",
                    tool_calls=fallback_calls,
                    id=getattr(response, "id", str(uuid.uuid4())),
                )

        # If no tool calls were requested, record conversational turn immediately.
        # Otherwise, the turn will be consolidated following tool execution in SummarizeNode.
        has_tool_calls = isinstance(response, AIMessage) and bool(response.tool_calls)
        if not has_tool_calls:
            self._record_turn(messages, response)

        return {"messages": [response]}


__all__ = [
    "CommandNode",
    "extract_fallback_tool_calls",
    "resolve_tool_definition",
    "normalize_tool_args",
]
