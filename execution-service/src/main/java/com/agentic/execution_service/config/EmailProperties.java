package com.agentic.execution_service.config;

import com.agentic.execution_service.models.email.EmailAccountConfig;
import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailAuthType;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

/**
 * Multi-account configuration properties for email providers.
 */
@Configuration
@ConfigurationProperties(prefix = "mail")
public class EmailProperties {

    private Map<String, EmailAccountConfig> accounts = new HashMap<>();

    public EmailProperties() {
        // Default template for Gmail
        EmailAccountConfig gmail = new EmailAccountConfig();
        gmail.setType(EmailAccountType.GMAIL);
        gmail.setAuthType(EmailAuthType.BASIC_AUTH);
        gmail.setImapHost("imap.gmail.com");
        gmail.setImapPort(993);
        gmail.setSmtpHost("smtp.gmail.com");
        gmail.setSmtpPort(587);
        accounts.put("gmail", gmail);

        // Default template for Outlook (disabled)
        EmailAccountConfig outlook = new EmailAccountConfig();
        outlook.setType(EmailAccountType.OUTLOOK);
        outlook.setEnabled(false);
        outlook.setAuthType(EmailAuthType.OAUTH2_DEVICE_CODE);
        outlook.setImapHost("outlook.office365.com");
        outlook.setImapPort(993);
        outlook.setSmtpHost("smtp.office365.com");
        outlook.setSmtpPort(587);
        accounts.put("outlook", outlook);
    }

    public Map<String, EmailAccountConfig> getAccounts() {
        return accounts;
    }

    public void setAccounts(Map<String, EmailAccountConfig> accounts) {
        if (accounts != null) {
            this.accounts.putAll(accounts);
        }
    }

    public EmailAccountConfig getGmailConfig() {
        EmailAccountConfig cfg = accounts.get("gmail");
        if (cfg != null) {
            cfg.setType(EmailAccountType.GMAIL);
            if (cfg.getImapHost() == null || cfg.getImapHost().isBlank()) {
                cfg.setImapHost("imap.gmail.com");
            }
            if (cfg.getSmtpHost() == null || cfg.getSmtpHost().isBlank()) {
                cfg.setSmtpHost("smtp.gmail.com");
            }
        }
        return cfg;
    }

    public EmailAccountConfig getOutlookConfig() {
        EmailAccountConfig cfg = accounts.get("outlook");
        if (cfg != null) {
            cfg.setType(EmailAccountType.OUTLOOK);
            if (cfg.getImapHost() == null || cfg.getImapHost().isBlank()) {
                cfg.setImapHost("outlook.office365.com");
            }
            if (cfg.getSmtpHost() == null || cfg.getSmtpHost().isBlank()) {
                cfg.setSmtpHost("smtp.office365.com");
            }
            if (cfg.getClientId() == null || cfg.getClientId().isBlank() || "14d82eec-204b-4a2f-b3e8-2947c07cfdd7".equals(cfg.getClientId())) {
                cfg.setClientId("d3590ed6-52b3-4102-aeff-aad2292ab01c");
            }
            if (cfg.getTenantId() == null || cfg.getTenantId().isBlank() || "common".equals(cfg.getTenantId())) {
                cfg.setTenantId("organizations");
            }
        }
        return cfg;
    }
}
