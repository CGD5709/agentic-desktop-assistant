package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import com.agentic.execution_service.service.email.EmailAccountManager;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Agent tool for querying unread emails across Gmail and Outlook accounts.
 */
@Component
public class FetchUnreadEmailsTool implements AgentTool {

    private static final Logger logger = LoggerFactory.getLogger(FetchUnreadEmailsTool.class);

    private final EmailAccountManager emailAccountManager;
    private final ObjectMapper objectMapper;

    public FetchUnreadEmailsTool(EmailAccountManager emailAccountManager, ObjectMapper objectMapper) {
        this.emailAccountManager = emailAccountManager;
        this.objectMapper = objectMapper;
    }

    @Override
    public String getName() {
        return "consultar_correos_no_leidos";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> accountProperty = Map.of(
                "type", "string",
                "enum", List.of("GMAIL"),
                "description", "La cuenta de correo a consultar ('GMAIL'). Por defecto 'GMAIL'."
        );

        Map<String, Object> limitProperty = Map.of(
                "type", "integer",
                "description", "Número máximo de correos no leídos más recientes a recuperar (por defecto 5, máximo 10)."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of(
                        "cuenta", accountProperty,
                        "limite", limitProperty
                )
        );

        return new ToolDefinition(
                getName(),
                "Consulta la bandeja de entrada de Gmail y devuelve la lista de correos no leídos más recientes con sus metadatos detallados (asunto, remitente, fecha, resumen del contenido).",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        String account = "GMAIL";
        int limit = 5;

        if (arguments != null) {
            if (arguments.containsKey("cuenta") && arguments.get("cuenta") != null) {
                account = String.valueOf(arguments.get("cuenta")).trim();
            }
            if (arguments.containsKey("limite") && arguments.get("limite") != null) {
                Object limObj = arguments.get("limite");
                if (limObj instanceof Number num) {
                    limit = num.intValue();
                } else {
                    try {
                        limit = Integer.parseInt(String.valueOf(limObj).trim());
                    } catch (NumberFormatException ignored) {}
                }
            }
        }

        limit = Math.max(1, Math.min(limit, 10));

        logger.info("Executing FetchUnreadEmailsTool: account={}, limit={}", account, limit);
        List<EmailMessageDTO> emails = emailAccountManager.fetchUnreadEmails(account, limit);

        if (emails.isEmpty()) {
            return "{\"total\": 0, \"mensajes\": [], \"aviso\": \"No se encontraron correos no leídos o las cuentas no están configuradas.\"}";
        }

        return objectMapper.writeValueAsString(Map.of(
                "total", emails.size(),
                "mensajes", emails
        ));
    }
}
