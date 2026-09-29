package com.agentic.execution_service.service.email;

import com.agentic.execution_service.config.EmailProperties;
import com.agentic.execution_service.models.email.EmailAccountConfig;
import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailAuthType;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import jakarta.mail.Authenticator;
import jakarta.mail.Flags;
import jakarta.mail.Folder;
import jakarta.mail.Message;
import jakarta.mail.PasswordAuthentication;
import jakarta.mail.Session;
import jakarta.mail.Store;
import jakarta.mail.Transport;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.search.FlagTerm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.CompletableFuture;

/**
 * Service managing concurrent email reading and sending across multiple email providers
 * (Gmail via IMAP/SMTP and Outlook via IMAP/SMTP or Microsoft Graph OAuth2).
 */
@Service
public class EmailAccountManager {

    private static final Logger logger = LoggerFactory.getLogger(EmailAccountManager.class);

    private final EmailProperties emailProperties;
    private final MicrosoftGraphService microsoftGraphService;

    public EmailAccountManager(EmailProperties emailProperties, MicrosoftGraphService microsoftGraphService) {
        this.emailProperties = emailProperties;
        this.microsoftGraphService = microsoftGraphService;
    }

    /**
     * Fetches unread messages across configured accounts concurrently.
     */
    public List<EmailMessageDTO> fetchUnreadEmails(String targetAccount, int limit) {
        List<CompletableFuture<List<EmailMessageDTO>>> futures = new ArrayList<>();

        boolean checkGmail = targetAccount == null || targetAccount.equalsIgnoreCase("TODAS") || targetAccount.equalsIgnoreCase("ALL") || targetAccount.equalsIgnoreCase("GMAIL");
        boolean checkOutlook = targetAccount != null && (targetAccount.equalsIgnoreCase("OUTLOOK") || (targetAccount.equalsIgnoreCase("TODAS") && emailProperties.getOutlookConfig() != null && emailProperties.getOutlookConfig().isEnabled()));

        EmailAccountConfig gmailConfig = emailProperties.getGmailConfig();
        if (checkGmail && gmailConfig != null && gmailConfig.isEnabled()) {
            futures.add(CompletableFuture.supplyAsync(() -> fetchFromAccount(gmailConfig, limit)));
        }

        EmailAccountConfig outlookConfig = emailProperties.getOutlookConfig();
        if (checkOutlook && outlookConfig != null && outlookConfig.isEnabled()) {
            futures.add(CompletableFuture.supplyAsync(() -> fetchFromAccount(outlookConfig, limit)));
        }

        if (futures.isEmpty()) {
            logger.info("No email accounts are enabled or configured for query target: {}", targetAccount);
            return List.of();
        }

        List<EmailMessageDTO> combined = new ArrayList<>();
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

        for (CompletableFuture<List<EmailMessageDTO>> future : futures) {
            try {
                combined.addAll(future.get());
            } catch (Exception e) {
                logger.warn("Error resolving account query future: {}", e.getMessage());
            }
        }

        // Sort descending by receivedAt
        combined.sort(Comparator.comparing(EmailMessageDTO::receivedAt).reversed());

        if (combined.size() > limit) {
            return combined.subList(0, limit);
        }
        return combined;
    }

    private List<EmailMessageDTO> fetchFromAccount(EmailAccountConfig config, int limit) {
        logger.info("Fetching unread emails from account {} ({})", config.getType(), config.getUser());

        // Delegate to Microsoft Graph if Outlook with OAuth2 or if basic password is empty
        if (config.getType() == EmailAccountType.OUTLOOK &&
                (config.getAuthType() == EmailAuthType.OAUTH2_DEVICE_CODE || config.getPassword() == null || config.getPassword().isBlank())) {
            return microsoftGraphService.fetchUnreadEmails(config, limit);
        }

        List<EmailMessageDTO> messagesList = new ArrayList<>();
        Store store = null;
        Folder inbox = null;

        try {
            Properties props = new Properties();
            props.put("mail.store.protocol", "imaps");
            props.put("mail.imaps.host", config.getImapHost());
            props.put("mail.imaps.port", String.valueOf(config.getImapPort()));
            props.put("mail.imaps.ssl.enable", "true");
            props.put("mail.imaps.ssl.trust", "*");
            props.put("mail.imaps.timeout", "10000");
            props.put("mail.imaps.connectiontimeout", "10000");

            Session session = Session.getInstance(props);
            store = session.getStore("imaps");
            store.connect(config.getImapHost(), config.getUser(), config.getPassword());

            inbox = store.getFolder("INBOX");
            inbox.open(Folder.READ_ONLY);

            // Search for unread messages (SEEN flag is false)
            FlagTerm unseenFlagTerm = new FlagTerm(new Flags(Flags.Flag.SEEN), false);
            Message[] unreadMessages = inbox.search(unseenFlagTerm);

            int totalUnread = unreadMessages.length;
            logger.info("Found {} unread messages in {}", totalUnread, config.getType());

            int countToRead = Math.min(totalUnread, limit);
            if (countToRead > 0) {
                Message[] toProcess = new Message[countToRead];
                for (int j = 0; j < countToRead; j++) {
                    toProcess[j] = unreadMessages[totalUnread - 1 - j];
                }

                jakarta.mail.FetchProfile fp = new jakarta.mail.FetchProfile();
                fp.add(jakarta.mail.FetchProfile.Item.ENVELOPE);
                fp.add(jakarta.mail.FetchProfile.Item.FLAGS);
                fp.add(jakarta.mail.FetchProfile.Item.CONTENT_INFO);
                inbox.fetch(toProcess, fp);

                for (Message msg : toProcess) {
                    try {
                        EmailMessageDTO dto = MimeMessageParser.parse(msg, config.getType(), config.getUser());
                        messagesList.add(dto);
                    } catch (Exception e) {
                        logger.warn("Failed to parse message from {}: {}", config.getType(), e.getMessage());
                    }
                }
            }

        } catch (Exception e) {
            logger.error("Error connecting to IMAP server for account {}: {}", config.getType(), e.getMessage(), e);
        } finally {
            if (inbox != null && inbox.isOpen()) {
                try {
                    inbox.close(false);
                } catch (Exception ignored) {}
            }
            if (store != null) {
                try {
                    store.close();
                } catch (Exception ignored) {}
            }
        }

        return messagesList;
    }

    /**
     * Dispatches an email message strictly using the credentials/token and endpoint of the specified account type.
     */
    public String sendEmail(EmailAccountType accountType, String toAddress, String subject, String body, String inReplyToMessageId) throws Exception {
        EmailAccountConfig config = (accountType == EmailAccountType.GMAIL)
                ? emailProperties.getGmailConfig()
                : emailProperties.getOutlookConfig();

        if (config == null || !config.isEnabled()) {
            throw new IllegalStateException("La cuenta de correo " + accountType + " no está configurada o habilitada.");
        }

        if (toAddress == null || toAddress.isBlank()) {
            throw new IllegalArgumentException("La dirección del destinatario ('toAddress') no puede estar vacía.");
        }

        logger.info("Sending email from {} ({}) to {}", accountType, config.getUser(), toAddress);

        // Delegate to Microsoft Graph if Outlook with OAuth2 or if basic password is empty
        if (config.getType() == EmailAccountType.OUTLOOK &&
                (config.getAuthType() == EmailAuthType.OAUTH2_DEVICE_CODE || config.getPassword() == null || config.getPassword().isBlank())) {
            return microsoftGraphService.sendEmail(config, toAddress, subject, body, inReplyToMessageId);
        }

        Properties props = new Properties();
        props.put("mail.smtp.auth", "true");
        props.put("mail.smtp.starttls.enable", "true");
        props.put("mail.smtp.host", config.getSmtpHost());
        props.put("mail.smtp.port", String.valueOf(config.getSmtpPort()));
        props.put("mail.smtp.ssl.trust", config.getSmtpHost());
        props.put("mail.smtp.timeout", "15000");
        props.put("mail.smtp.connectiontimeout", "15000");

        Session session = Session.getInstance(props, new Authenticator() {
            @Override
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(config.getUser(), config.getPassword());
            }
        });

        MimeMessage message = new MimeMessage(session);
        // Sender is strictly locked to the configured user address
        message.setFrom(new InternetAddress(config.getUser()));
        message.setRecipient(Message.RecipientType.TO, new InternetAddress(toAddress.trim()));
        message.setSubject(subject != null ? subject.trim() : "", "UTF-8");
        message.setText(body != null ? body : "", "UTF-8");

        if (inReplyToMessageId != null && !inReplyToMessageId.isBlank()) {
            message.setHeader("In-Reply-To", inReplyToMessageId.trim());
            message.setHeader("References", inReplyToMessageId.trim());
        }

        Transport.send(message);
        logger.info("Email sent successfully to {}", toAddress);

        return "Correo enviado satisfactoriamente desde " + config.getUser() + " (" + accountType + ") hacia " + toAddress + " con asunto: '" + subject + "'";
    }
}
