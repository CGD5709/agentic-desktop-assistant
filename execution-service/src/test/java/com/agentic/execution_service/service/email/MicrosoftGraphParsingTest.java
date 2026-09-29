package com.agentic.execution_service.service.email;

import com.agentic.execution_service.models.email.EmailAccountConfig;
import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailAuthType;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class MicrosoftGraphParsingTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void testEmailAccountConfigOAuth2Enabled() {
        EmailAccountConfig config = new EmailAccountConfig();
        config.setType(EmailAccountType.OUTLOOK);
        config.setAuthType(EmailAuthType.OAUTH2_DEVICE_CODE);
        config.setUser("jossanmon1@alum.us.es");
        config.setEnabled(true);
        // Notice: password is empty, but with OAUTH2_DEVICE_CODE it should be enabled!
        assertTrue(config.isEnabled());

        // Basic Auth requires password
        config.setAuthType(EmailAuthType.BASIC_AUTH);
        assertFalse(config.isEnabled());
        config.setPassword("app-password");
        assertTrue(config.isEnabled());
    }

    @Test
    void testGraphMessageJsonParsing() throws Exception {
        String json = """
        {
          "id": "AAMkAGEx...",
          "conversationId": "AAQkAG...",
          "subject": "Convocatoria Examen Extraordinario",
          "bodyPreview": "Se convoca a los alumnos el día 30...",
          "body": {
            "contentType": "html",
            "content": "<html><body><p>Estimados alumnos,<br>Se convoca a los alumnos el <b>día 30</b> en el aula A1.</p></body></html>"
          },
          "from": {
            "emailAddress": {
              "name": "Profesor García",
              "address": "pgarcia@us.es"
            }
          },
          "replyTo": [
            {
              "emailAddress": {
                "name": "Coordinación Asignatura",
                "address": "coord_asignatura@us.es"
              }
            }
          ],
          "toRecipients": [
            {
              "emailAddress": {
                "name": "Jose",
                "address": "jossanmon1@alum.us.es"
              }
            }
          ],
          "ccRecipients": [
            {
              "emailAddress": {
                "name": "Tutor",
                "address": "tutor@us.es"
              }
            }
          ],
          "receivedDateTime": "2026-09-24T14:30:00Z",
          "hasAttachments": false,
          "internetMessageId": "<us-msg-9876@us.es>"
        }
        """;

        JsonNode msgNode = objectMapper.readTree(json);
        MicrosoftGraphService graphService = new MicrosoftGraphService(objectMapper);

        // Test parsing via reflection or direct instance call
        java.lang.reflect.Method method = MicrosoftGraphService.class.getDeclaredMethod("parseGraphMessage", JsonNode.class, String.class);
        method.setAccessible(true);
        EmailMessageDTO dto = (EmailMessageDTO) method.invoke(graphService, msgNode, "jossanmon1@alum.us.es");

        assertNotNull(dto);
        assertEquals("<us-msg-9876@us.es>", dto.id());
        assertEquals(EmailAccountType.OUTLOOK, dto.account());
        assertEquals("jossanmon1@alum.us.es", dto.accountAddress());
        assertEquals("Convocatoria Examen Extraordinario", dto.subject());
        assertEquals("Profesor García", dto.fromName());
        assertEquals("pgarcia@us.es", dto.fromAddress());
        // CRITICAL CHECK: replyTo address extracted deterministically
        assertEquals("coord_asignatura@us.es", dto.replyToAddress());
        assertEquals(List.of("jossanmon1@alum.us.es"), dto.toAddresses());
        assertEquals(List.of("tutor@us.es"), dto.ccAddresses());
        assertTrue(dto.bodyText().contains("Estimados alumnos,"));
        assertTrue(dto.bodyText().contains("día 30 en el aula A1."));
        assertFalse(dto.hasAttachments());
    }
}
