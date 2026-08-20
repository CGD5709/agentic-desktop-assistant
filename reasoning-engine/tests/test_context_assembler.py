from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from memory.context_assembler import ContextAssembler
from memory.models import MemoryItem, MemoryCategory


def test_context_assembler_full_pipeline():
    base_prompt = "Eres Jarvis, el asistente de escritorio."
    profile_ctx = "<user_profile>\n- usuario: Josevi\n</user_profile>"
    session_summary = "<session_summary>\nSesión iniciada a las 10:00\n</session_summary>"
    
    memories = [
        MemoryItem(
            text="El proyecto principal se llama desktop-assistant",
            category=MemoryCategory.PROJECT
        )
    ]
    
    dialogue = [
        HumanMessage(content="Hola Jarvis"),
        AIMessage(content="Hola Josevi, ¿en qué puedo ayudarte?"),
        HumanMessage(content="¿Cómo se llama mi proyecto?")
    ]

    assembled = ContextAssembler.assemble(
        base_system_prompt=base_prompt,
        messages=dialogue,
        profile_context=profile_ctx,
        retrieved_memories=memories,
        session_summary_context=session_summary,
        max_dialogue_tokens=3000
    )

    # El primer mensaje debe ser el SystemMessage consolidado
    assert isinstance(assembled[0], SystemMessage)
    system_content = assembled[0].content
    
    assert base_prompt in system_content
    assert "Josevi" in system_content
    assert "<user_profile>" in system_content
    assert "<auxiliary_context>" in system_content
    assert "desktop-assistant" in system_content
    assert "<session_summary>" in system_content

    # Los siguientes deben ser los mensajes del diálogo recortado
    assert len(assembled) == 4
    assert isinstance(assembled[-1], HumanMessage)
    assert assembled[-1].content == "¿Cómo se llama mi proyecto?"
