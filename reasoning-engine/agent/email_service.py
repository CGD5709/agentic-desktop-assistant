import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from logger import get_logger

from .email_models import ClassifiedEmail, EmailCategory, EmailDraftPayload, RawEmailDTO
from .prompts import EMAIL_CLASSIFICATION_PROMPT, EMAIL_DRAFTING_PROMPT

logger = get_logger("reasoning_engine.email_service")


def _clean_json_markdown(raw_text: str) -> str:
    """Strips markdown code block wrappers from a raw JSON string."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    cleaned = cleaned.removesuffix("```")
    return cleaned.strip()


class EmailAssistantService:
    """
    Coordinates semantic classification, actionability detection, and response drafting
    for emails retrieved from the Java execution-service.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm
        self._active_drafts: dict[str, EmailDraftPayload] = {}

    def parse_emails_from_tool_output(self, raw_tool_output: str) -> list[RawEmailDTO]:
        """Deserializes JSON output returned by Java's FetchUnreadEmailsTool into RawEmailDTO objects."""
        if not raw_tool_output or not raw_tool_output.strip():
            return []

        try:
            data = json.loads(raw_tool_output)
            messages_list = data.get("mensajes", []) if isinstance(data, dict) else []
            emails: list[RawEmailDTO] = []
            for item in messages_list:
                if isinstance(item, dict):
                    emails.append(RawEmailDTO.model_validate(item))
            return emails
        except Exception as e:
            logger.warning("Failed to parse emails from tool output: %s", e)
            return []

    async def classify_email(self, email: RawEmailDTO) -> ClassifiedEmail:
        """
        Classifies an email into one of the 5 official categories (URGENT, UNIVERSITY, NOTIFICATION, NOT IMPORTANT, SPAM)
        and evaluates if it requires a response.
        """
        email_content_summary = (
            f"Cuenta: {email.account} ({email.account_address})\n"
            f"De: {email.from_name} <{email.from_address}>\n"
            f"Responder A: {email.reply_to_address}\n"
            f"Asunto: {email.subject}\n"
            f"Fecha: {email.received_at}\n"
            f"Tiene adjuntos: {'Sí' if email.has_attachments else 'No'}\n\n"
            f"Contenido:\n{email.body_text[:2000]}"
        )

        messages = [
            SystemMessage(content=EMAIL_CLASSIFICATION_PROMPT),
            HumanMessage(
                content=f"Analiza y clasifica este correo electrónico:\n\n{email_content_summary}"
            ),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            raw_json = response.content if isinstance(response.content, str) else ""
            cleaned = _clean_json_markdown(raw_json)
            data = json.loads(cleaned)

            cat_str = str(data.get("category", "NOT IMPORTANT")).strip().upper()
            try:
                category = EmailCategory(cat_str)
            except Exception:
                # Handle space vs underscore or variations defensively
                if "URGENT" in cat_str:
                    category = EmailCategory.URGENT
                elif "UNIV" in cat_str:
                    category = EmailCategory.UNIVERSITY
                elif "NOTIF" in cat_str:
                    category = EmailCategory.NOTIFICATION
                elif "SPAM" in cat_str:
                    category = EmailCategory.SPAM
                else:
                    category = EmailCategory.NOT_IMPORTANT

            urgency = int(data.get("urgency_score", 1))
            summary = str(data.get("summary", email.subject))
            requires_reply = bool(data.get("requires_reply", False))
            suggested_action = data.get("suggested_action")

            return ClassifiedEmail(
                email=email,
                category=category,
                urgency_score=max(1, min(5, urgency)),
                summary=summary,
                requires_reply=requires_reply,
                suggested_action=suggested_action,
            )
        except Exception as e:
            logger.warning(
                "Error classifying email %s with LLM: %s. Using fallback classification.",
                email.id,
                e,
            )
            # Fallback heuristic classification
            category = EmailCategory.NOT_IMPORTANT
            if any(
                term in email.subject.lower() or term in email.from_address.lower()
                for term in ["urgente", "urgent", "asap", "inmediato"]
            ):
                category = EmailCategory.URGENT
            elif any(
                term in email.from_address.lower() or term in email.subject.lower()
                for term in [
                    "universidad",
                    "profesor",
                    "campus",
                    ".edu",
                    ".es",
                    "examen",
                    "práctica",
                    "practica",
                ]
            ):
                category = EmailCategory.UNIVERSITY
            elif any(
                term in email.from_address.lower()
                for term in [
                    "noreply",
                    "no-reply",
                    "notification",
                    "github",
                    "gitlab",
                    "alert",
                ]
            ):
                category = EmailCategory.NOTIFICATION

            return ClassifiedEmail(
                email=email,
                category=category,
                urgency_score=3
                if category in [EmailCategory.URGENT, EmailCategory.UNIVERSITY]
                else 1,
                summary=email.subject,
                requires_reply=(
                    category in [EmailCategory.URGENT, EmailCategory.UNIVERSITY]
                ),
            )

    async def create_draft(
        self,
        email: RawEmailDTO,
        category: EmailCategory = EmailCategory.NOT_IMPORTANT,
        urgency_score: int = 1,
        user_instructions: str | None = None,
        user_profile_context: str | None = None,
    ) -> EmailDraftPayload:
        """
        Drafts a response body using the LLM and creates a draft payload.
        CRITICAL: The recipient (name and email) is hardcoded from reply_to_address / from_address and NOT by LLM.
        """
        # Deterministic recipient resolution
        recipient_email = (
            email.reply_to_address if email.reply_to_address else email.from_address
        )
        recipient_name = (
            email.from_name if email.from_name else recipient_email.split("@")[0]
        )

        subject_reply = (
            email.subject
            if email.subject.lower().startswith("re:")
            else f"Re: {email.subject}"
        )

        context_prompt = (
            f"Estás redactando una respuesta para el siguiente correo recibido:\n"
            f"De: {email.from_name} <{email.from_address}>\n"
            f"Asunto: {email.subject}\n"
            f"Categoría: {category.value}\n"
            f"Contenido original:\n{email.body_text[:1500]}\n"
        )
        if user_profile_context:
            context_prompt += f"\nPreferencias del usuario:\n{user_profile_context}\n"
        if user_instructions:
            context_prompt += f"\nInstrucciones adicionales del usuario para la respuesta:\n{user_instructions}\n"

        messages = [
            SystemMessage(content=EMAIL_DRAFTING_PROMPT),
            HumanMessage(content=context_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            draft_body = response.content if isinstance(response.content, str) else ""
        except Exception as e:
            logger.error("Error generating draft with LLM: %s", e)
            draft_body = f"Estimado/a {recipient_name},\n\nHe recibido su correo sobre '{email.subject}' y le responderé a la brevedad.\n\nAtentamente,\nJose"

        draft = EmailDraftPayload(
            original_message_id=email.id,
            account=email.account,
            account_address=email.account_address,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject=subject_reply,
            original_snippet=email.body_snippet or email.body_text[:200],
            draft_body=draft_body.strip(),
            category=category,
            urgency_score=urgency_score,
        )

        self._active_drafts[draft.draft_id] = draft
        logger.info(
            "Created draft %s for recipient %s <%s>",
            draft.draft_id,
            recipient_name,
            recipient_email,
        )
        return draft

    def get_draft(self, draft_id: str) -> EmailDraftPayload | None:
        """Retrieves an active draft by ID."""
        return self._active_drafts.get(draft_id)

    def remove_draft(self, draft_id: str) -> EmailDraftPayload | None:
        """Removes a draft once sent or discarded."""
        return self._active_drafts.pop(draft_id, None)
