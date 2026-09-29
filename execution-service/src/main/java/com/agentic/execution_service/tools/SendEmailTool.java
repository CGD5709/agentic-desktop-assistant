package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.service.email.EmailAccountManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Agent tool for sending email messages via SMTP with mandatory Human-in-the-Loop authorization.
 */
@Component
public class SendEmailTool implements AgentTool {

    private static final Logger logger = LoggerFactory.getLogger(SendEmailTool.class);

    private final EmailAccountManager emailAccountManager;

    public SendEmailTool(EmailAccountManager emailAccountManager) {
        this.emailAccountManager = emailAccountManager;
    }

    @Override
    public String getName() {
        return "enviar_correo_electronico";
    }

    @Override
    public boolean isCritical() {
        return true;
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> accountProperty = Map.of(
                "type", "string",
                "enum", List.of("GMAIL"),
                "description", "La cuenta de origen ('GMAIL'). Por defecto 'GMAIL'."
        );

        Map<String, Object> toProperty = Map.of(
                "type", "string",
                "description", "Dirección de correo electrónico del destinatario (ejemplo: 'persona@dominio.com'). OBLIGATORIO."
        );

        Map<String, Object> subjectProperty = Map.of(
                "type", "string",
                "description", "El asunto del correo electrónico. OBLIGATORIO."
        );

        Map<String, Object> bodyProperty = Map.of(
                "type", "string",
                "description", "El contenido o cuerpo del mensaje en texto plano. OBLIGATORIO."
        );

        Map<String, Object> inReplyToProperty = Map.of(
                "type", "string",
                "description", "Identificador Message-ID del correo original si este mensaje es una respuesta en un hilo de conversación. Opcional."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "required", List.of("destinatario", "asunto", "cuerpo"),
                "properties", Map.of(
                        "cuenta", accountProperty,
                        "destinatario", toProperty,
                        "asunto", subjectProperty,
                        "cuerpo", bodyProperty,
                        "in_reply_to", inReplyToProperty
                )
        );

        return new ToolDefinition(
                getName(),
                "Envía un correo electrónico a través del servidor SMTP de Gmail. Requiere confirmación humana previa.",
                parametersSchema,
                true,
                "¿Autoriza enviar el correo electrónico desde Gmail hacia '{destinatario}' con el asunto '{asunto}'?"
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        if (arguments == null || !arguments.containsKey("destinatario") || !arguments.containsKey("asunto") || !arguments.containsKey("cuerpo")) {
            throw new IllegalArgumentException("Debes proporcionar obligatoriamente 'destinatario', 'asunto' y 'cuerpo'.");
        }

        String accountStr = arguments.containsKey("cuenta") && arguments.get("cuenta") != null
                ? String.valueOf(arguments.get("cuenta")).trim().toUpperCase()
                : "GMAIL";
        EmailAccountType accountType;
        try {
            accountType = EmailAccountType.valueOf(accountStr);
        } catch (IllegalArgumentException e) {
            accountType = EmailAccountType.GMAIL;
        }

        String toAddress = String.valueOf(arguments.get("destinatario")).trim();
        String subject = String.valueOf(arguments.get("asunto")).trim();
        String body = String.valueOf(arguments.get("cuerpo"));
        String inReplyTo = arguments.containsKey("in_reply_to") && arguments.get("in_reply_to") != null
                ? String.valueOf(arguments.get("in_reply_to")).trim()
                : null;

        logger.info("Executing SendEmailTool: account={}, to={}, subject={}", accountType, toAddress, subject);

        return emailAccountManager.sendEmail(accountType, toAddress, subject, body, inReplyTo);
    }
}
