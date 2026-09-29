package com.agentic.execution_service.service.email;

import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import jakarta.mail.Message;
import jakarta.mail.Session;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeBodyPart;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.internet.MimeMultipart;
import org.junit.jupiter.api.Test;

import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

class MimeMessageParserTest {

    @Test
    void testParseSimpleMessageWithReplyTo() throws Exception {
        Session session = Session.getDefaultInstance(new Properties());
        MimeMessage message = new MimeMessage(session);

        message.setHeader("Message-ID", "<test-uuid-1234@domain.com>");
        message.setSubject("Entrega de Práctica 1 - Algoritmos", "UTF-8");
        message.setFrom(new InternetAddress("profesor.noreply@universidad.es", "Prof. Carlos"));
        message.setReplyTo(new InternetAddress[]{new InternetAddress("dudas.profesor@universidad.es", "Buzón de Dudas")});
        message.setRecipient(Message.RecipientType.TO, new InternetAddress("alumno@universidad.es"));
        message.setText("Recuerden entregar la práctica antes de las 23:59.");

        EmailMessageDTO dto = MimeMessageParser.parse(message, EmailAccountType.OUTLOOK, "alumno@universidad.es");

        assertEquals("<test-uuid-1234@domain.com>", dto.id());
        assertEquals(EmailAccountType.OUTLOOK, dto.account());
        assertEquals("alumno@universidad.es", dto.accountAddress());
        assertEquals("Entrega de Práctica 1 - Algoritmos", dto.subject());
        assertEquals("Prof. Carlos", dto.fromName());
        assertEquals("profesor.noreply@universidad.es", dto.fromAddress());
        // CRITICAL CHECK: Reply-To takes precedence over From
        assertEquals("dudas.profesor@universidad.es", dto.replyToAddress());
        assertTrue(dto.bodyText().contains("Recuerden entregar la práctica"));
        assertFalse(dto.hasAttachments());
    }

    @Test
    void testParseMultipartWithHtmlAndAttachments() throws Exception {
        Session session = Session.getDefaultInstance(new Properties());
        MimeMessage message = new MimeMessage(session);

        message.setSubject("Aviso de examen");
        message.setFrom(new InternetAddress("secretaria@universidad.es"));
        message.setRecipient(Message.RecipientType.TO, new InternetAddress("estudiante@universidad.es"));

        MimeMultipart multipart = new MimeMultipart();

        MimeBodyPart htmlPart = new MimeBodyPart();
        htmlPart.setContent("<html><body><p>El examen tendrá lugar en el <b>Aula Magna</b>.</p></body></html>", "text/html");
        multipart.addBodyPart(htmlPart);

        MimeBodyPart attachPart = new MimeBodyPart();
        attachPart.setFileName("guia_docente.pdf");
        attachPart.setText("fake pdf content");
        multipart.addBodyPart(attachPart);

        message.setContent(multipart);
        message.saveChanges();

        EmailMessageDTO dto = MimeMessageParser.parse(message, EmailAccountType.GMAIL, "estudiante@gmail.com");

        assertEquals(EmailAccountType.GMAIL, dto.account());
        assertEquals("secretaria@universidad.es", dto.replyToAddress());
        assertTrue(dto.bodyText().contains("El examen tendrá lugar en el Aula Magna."));
        assertTrue(dto.hasAttachments());
        assertTrue(dto.attachmentNames().contains("guia_docente.pdf"));
    }
}
