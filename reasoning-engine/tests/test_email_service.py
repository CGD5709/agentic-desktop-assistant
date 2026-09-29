import pytest
from unittest.mock import AsyncMock
from langchain_core.messages import AIMessage

from agent.email_models import EmailCategory, RawEmailDTO
from agent.email_service import EmailAssistantService


def test_parse_emails_from_tool_output():
    mock_llm = AsyncMock()
    service = EmailAssistantService(llm=mock_llm)

    json_tool_output = """
    {
      "total": 2,
      "mensajes": [
        {
          "id": "<msg-001@gmail.com>",
          "account": "GMAIL",
          "accountAddress": "personal@gmail.com",
          "subject": "Práctica 2 IA",
          "fromName": "Profesor Juan",
          "fromAddress": "profesor@universidad.es",
          "replyToAddress": "dudas.profesor@universidad.es",
          "toAddresses": ["personal@gmail.com"],
          "receivedAt": "2026-09-24T14:30:00Z",
          "bodySnippet": "Recuerden entregar antes del viernes...",
          "bodyText": "Recuerden entregar antes del viernes en el campus virtual.",
          "hasAttachments": true,
          "attachmentNames": ["enunciado.pdf"]
        },
        {
          "id": "<msg-002@outlook.com>",
          "account": "OUTLOOK",
          "accountAddress": "trabajo@empresa.com",
          "subject": "Alerta de servidor caído en producción",
          "fromName": "DevOps Bot",
          "fromAddress": "alertas@empresa.com",
          "replyToAddress": "alertas@empresa.com",
          "toAddresses": ["trabajo@empresa.com"],
          "receivedAt": "2026-09-24T14:35:00Z",
          "bodySnippet": "El contenedor de la API no responde...",
          "bodyText": "El contenedor de la API no responde en el puerto 8080.",
          "hasAttachments": false,
          "attachmentNames": []
        }
      ]
    }
    """

    emails = service.parse_emails_from_tool_output(json_tool_output)
    assert len(emails) == 2
    assert emails[0].account == "GMAIL"
    assert emails[0].reply_to_address == "dudas.profesor@universidad.es"
    assert emails[0].has_attachments is True
    assert emails[1].account == "OUTLOOK"
    assert emails[1].subject == "Alerta de servidor caído en producción"


@pytest.mark.asyncio
async def test_classify_email_five_categories():
    mock_llm = AsyncMock()
    service = EmailAssistantService(llm=mock_llm)

    email = RawEmailDTO(
        id="<msg-test-1>",
        account="GMAIL",
        accountAddress="alumno@universidad.es",
        subject="Revisión de examen final",
        fromName="Dra. Martínez",
        fromAddress="martinez@universidad.es",
        replyToAddress="martinez@universidad.es",
        bodyText="La revisión será este jueves a las 11:00 en el despacho 302."
    )

    # Simular respuesta LLM para categoría UNIVERSITY
    mock_llm.ainvoke.return_value = AIMessage(content="""
    {
      "category": "UNIVERSITY",
      "urgency_score": 4,
      "summary": "Aviso de fecha y lugar para la revisión del examen final",
      "requires_reply": false,
      "suggested_action": "Anotar fecha en el calendario"
    }
    """)

    classified = await service.classify_email(email)
    assert classified.category == EmailCategory.UNIVERSITY
    assert classified.urgency_score == 4
    assert classified.requires_reply is False

    # Simular respuesta LLM para categoría URGENT
    mock_llm.ainvoke.return_value = AIMessage(content="""
    {
      "category": "URGENT",
      "urgency_score": 5,
      "summary": "Fallo crítico en el servidor de producción",
      "requires_reply": true,
      "suggested_action": "Reiniciar servicio"
    }
    """)
    classified_urgent = await service.classify_email(email)
    assert classified_urgent.category == EmailCategory.URGENT
    assert classified_urgent.requires_reply is True


@pytest.mark.asyncio
async def test_create_draft_deterministic_recipient():
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="Estimada Dra. Martínez,\n\nMuchas gracias por la información. Asistiré a la revisión.\n\nUn cordial saludo,\nJose")

    service = EmailAssistantService(llm=mock_llm)

    email = RawEmailDTO(
        id="<msg-univ-99>",
        account="OUTLOOK",
        accountAddress="alumno@outlook.com",
        subject="Dudas sobre el proyecto de fin de grado",
        fromName="Dra. Martínez",
        fromAddress="martinez.noreply@universidad.es",
        replyToAddress="profesora.martinez@universidad.es",
        bodyText="Hola Jose, ¿a qué hora puedes reunirte para ver los avances?"
    )

    draft = await service.create_draft(
        email=email,
        category=EmailCategory.UNIVERSITY,
        urgency_score=4,
        user_instructions="Dile que puedo a las 12:00"
    )

    # VERIFICACIÓN CRÍTICA: Destinatario se obtiene de reply_to_address por código
    assert draft.recipient_email == "profesora.martinez@universidad.es"
    assert draft.recipient_name == "Dra. Martínez"
    assert draft.account == "OUTLOOK"
    assert draft.account_address == "alumno@outlook.com"
    assert draft.subject == "Re: Dudas sobre el proyecto de fin de grado"
    assert "Estimada Dra. Martínez" in draft.draft_body
    assert service.get_draft(draft.draft_id) is not None
