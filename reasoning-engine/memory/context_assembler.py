from typing import List, Sequence, Optional, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from memory.short_term import trim_messages_token_budget
from memory.models import MemoryItem


class ContextAssembler:
    """
    Ensamblador Unificado de Contexto.
    Combina de forma limpia y estructurada los 4 niveles de memoria:
    1. System Prompt base
    2. Perfil estructurado (Nivel 0)
    3. Memorias a largo plazo semánticas (Nivel 2)
    4. Resumen de sesión (Nivel 1)
    5. Historial reciente podado dentro del presupuesto de tokens (Nivel 1)
    """

    @staticmethod
    def assemble(
        base_system_prompt: str,
        messages: Sequence[BaseMessage],
        profile_context: Optional[str] = None,
        retrieved_memories: Optional[Sequence[Any]] = None,
        session_summary_context: Optional[str] = None,
        max_dialogue_tokens: int = 3000,
        memory_store_formatter = None
    ) -> List[BaseMessage]:
        """
        Construye la lista final de mensajes ordenada y delimitada para el LLM.
        """
        system_sections: List[str] = [base_system_prompt.strip()]

        # 1. Perfil de Usuario (Nivel 0)
        if profile_context and profile_context.strip():
            system_sections.append(profile_context.strip())

        # 2. Recuerdos a Largo Plazo (Nivel 2)
        if retrieved_memories:
            if memory_store_formatter:
                mem_str = memory_store_formatter(retrieved_memories)
            else:
                lines = ["<auxiliary_context>", "Información relevante recuperada de sesiones anteriores:"]
                for mem in retrieved_memories:
                    text = mem.get("text", "") if isinstance(mem, dict) else getattr(mem, "text", "")
                    lines.append(f"- {text}")
                lines.append("</auxiliary_context>")
                mem_str = "\n".join(lines)

            if mem_str.strip():
                system_sections.append(mem_str.strip())

        # 3. Resumen de Sesión (Nivel 1)
        if session_summary_context and session_summary_context.strip():
            system_sections.append(session_summary_context.strip())

        # Consolidamos las secciones del sistema en un único SystemMessage inicial
        full_system_message = SystemMessage(content="\n\n".join(system_sections))

        # 4. Historial reciente podado respetando límites de tokens y atomicidad de tool calls (Nivel 1)
        trimmed_dialogue = trim_messages_token_budget(
            messages=messages,
            max_tokens=max_dialogue_tokens,
            keep_system_messages=False
        )

        return [full_system_message] + list(trimmed_dialogue)
