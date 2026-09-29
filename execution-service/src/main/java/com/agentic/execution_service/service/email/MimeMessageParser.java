package com.agentic.execution_service.service.email;

import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import jakarta.mail.Address;
import jakarta.mail.BodyPart;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.Multipart;
import jakarta.mail.Part;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.internet.MimeUtility;
import org.jsoup.Jsoup;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.UUID;

/**
 * Deterministic RFC-822 / MIME message parser.
 * Guarantees zero-hallucination extraction of recipient, sender, subject, and body fields.
 */
public class MimeMessageParser {

    private static final Logger logger = LoggerFactory.getLogger(MimeMessageParser.class);
    private static final int SNIPPET_MAX_LENGTH = 250;

    public static EmailMessageDTO parse(Message message, EmailAccountType accountType, String accountAddress) throws MessagingException, IOException {
        String messageId = extractMessageId(message);
        String subject = decodeSubject(message.getSubject());

        // Deterministic sender extraction
        String fromName = "";
        String fromAddress = "";
        Address[] fromAddresses = message.getFrom();
        if (fromAddresses != null && fromAddresses.length > 0 && fromAddresses[0] instanceof InternetAddress internetAddress) {
            fromAddress = sanitizeEmail(internetAddress.getAddress());
            fromName = internetAddress.getPersonal() != null ? decodeSubject(internetAddress.getPersonal()) : "";
        }

        // Deterministic Reply-To extraction (Critical safety rule: reply-to takes precedence over from)
        String replyToAddress = fromAddress;
        Address[] replyToList = message.getReplyTo();
        if (replyToList != null && replyToList.length > 0 && replyToList[0] instanceof InternetAddress replyToInternet) {
            String candidateReplyTo = sanitizeEmail(replyToInternet.getAddress());
            if (candidateReplyTo != null && !candidateReplyTo.isBlank()) {
                replyToAddress = candidateReplyTo;
            }
        }

        // Recipient lists
        List<String> toAddresses = extractAddresses(message.getRecipients(Message.RecipientType.TO));
        List<String> ccAddresses = extractAddresses(message.getRecipients(Message.RecipientType.CC));

        // Received timestamp
        Date date = message.getReceivedDate() != null ? message.getReceivedDate() : message.getSentDate();
        String receivedAt = date != null
                ? DateTimeFormatter.ISO_INSTANT.format(date.toInstant())
                : DateTimeFormatter.ISO_INSTANT.format(Instant.now());

        // Body content and attachments
        List<String> attachmentNames = new ArrayList<>();
        StringBuilder plainTextBuffer = new StringBuilder();
        StringBuilder htmlBuffer = new StringBuilder();

        extractContentRecursively(message, plainTextBuffer, htmlBuffer, attachmentNames);

        String fullBodyText = plainTextBuffer.toString().trim();
        if (fullBodyText.isBlank() && !htmlBuffer.isEmpty()) {
            fullBodyText = Jsoup.parse(htmlBuffer.toString()).text().trim();
        }

        String snippet = fullBodyText.length() > SNIPPET_MAX_LENGTH
                ? fullBodyText.substring(0, SNIPPET_MAX_LENGTH) + "..."
                : fullBodyText;

        if (fullBodyText.length() > 2000) {
            fullBodyText = fullBodyText.substring(0, 2000) + "... [Contenido truncado]";
        }

        return new EmailMessageDTO(
                messageId,
                accountType,
                accountAddress,
                subject,
                fromName,
                fromAddress,
                replyToAddress,
                toAddresses,
                ccAddresses,
                receivedAt,
                snippet,
                fullBodyText,
                !attachmentNames.isEmpty(),
                attachmentNames
        );
    }

    private static String extractMessageId(Message message) throws MessagingException {
        if (message instanceof MimeMessage mimeMessage) {
            String mid = mimeMessage.getMessageID();
            if (mid != null && !mid.isBlank()) {
                return mid.trim();
            }
        }
        String[] headers = message.getHeader("Message-ID");
        if (headers != null && headers.length > 0 && headers[0] != null && !headers[0].isBlank()) {
            return headers[0].trim();
        }
        return "msg-" + UUID.randomUUID().toString().substring(0, 12);
    }

    private static String decodeSubject(String text) {
        if (text == null) {
            return "(Sin asunto)";
        }
        try {
            return MimeUtility.decodeText(text).trim();
        } catch (Exception e) {
            return text.trim();
        }
    }

    private static String sanitizeEmail(String email) {
        if (email == null) {
            return "";
        }
        return email.trim().toLowerCase();
    }

    private static List<String> extractAddresses(Address[] addresses) {
        if (addresses == null) {
            return List.of();
        }
        return Arrays.stream(addresses)
                .filter(InternetAddress.class::isInstance)
                .map(InternetAddress.class::cast)
                .map(InternetAddress::getAddress)
                .filter(addr -> addr != null && !addr.isBlank())
                .map(String::toLowerCase)
                .toList();
    }

    private static void extractContentRecursively(Part part, StringBuilder plainText, StringBuilder htmlText, List<String> attachments)
            throws MessagingException, IOException {
        
        if (part.isMimeType("multipart/*")) {
            Object content = part.getContent();
            if (content instanceof Multipart multipart) {
                for (int i = 0; i < multipart.getCount(); i++) {
                    BodyPart bodyPart = multipart.getBodyPart(i);
                    extractContentRecursively(bodyPart, plainText, htmlText, attachments);
                }
            }
            return;
        }

        String disposition = part.getDisposition();
        String fileName = part.getFileName();

        if (Part.ATTACHMENT.equalsIgnoreCase(disposition) || (fileName != null && !fileName.isBlank())) {
            try {
                String decodedName = fileName != null ? MimeUtility.decodeText(fileName) : "adjunto_sin_nombre";
                attachments.add(decodedName);
            } catch (Exception e) {
                attachments.add(fileName != null ? fileName : "adjunto");
            }
            return;
        }

        if (part.isMimeType("text/plain")) {
            Object content = part.getContent();
            if (content instanceof String str) {
                plainText.append(str).append("\n");
            }
        } else if (part.isMimeType("text/html")) {
            Object content = part.getContent();
            if (content instanceof String str) {
                htmlText.append(str).append("\n");
            }
        }
    }
}
