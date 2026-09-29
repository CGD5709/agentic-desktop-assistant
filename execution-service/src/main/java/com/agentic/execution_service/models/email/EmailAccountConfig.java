package com.agentic.execution_service.models.email;

/**
 * Configuration holder for a specific email account provider.
 */
public class EmailAccountConfig {

    private EmailAccountType type;
    private EmailAuthType authType = EmailAuthType.BASIC_AUTH;
    private String user = "";
    private String password = "";
    private String imapHost = "";
    private int imapPort = 993;
    private String smtpHost = "";
    private int smtpPort = 587;
    private boolean enabled = false;

    // OAuth2 / Graph API settings
    private String clientId = "d3590ed6-52b3-4102-aeff-aad2292ab01c"; // Microsoft Office public client ID
    private String tenantId = "organizations";
    private String tokenFilePath = "tokens/outlook_token.json";

    public EmailAccountConfig() {
    }

    public EmailAccountConfig(EmailAccountType type, String user, String password, String imapHost, int imapPort, String smtpHost, int smtpPort, boolean enabled) {
        this.type = type;
        this.user = user;
        this.password = password;
        this.imapHost = imapHost;
        this.imapPort = imapPort;
        this.smtpHost = smtpHost;
        this.smtpPort = smtpPort;
        this.enabled = enabled;
        this.authType = EmailAuthType.BASIC_AUTH;
    }

    public EmailAccountType getType() {
        return type;
    }

    public void setType(EmailAccountType type) {
        this.type = type;
    }

    public EmailAuthType getAuthType() {
        return authType;
    }

    public void setAuthType(EmailAuthType authType) {
        this.authType = authType;
    }

    public String getUser() {
        return user;
    }

    public void setUser(String user) {
        this.user = user;
    }

    public String getPassword() {
        if (password != null) {
            return password.replace(" ", "").replace("-", "").trim();
        }
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public String getImapHost() {
        return imapHost;
    }

    public void setImapHost(String imapHost) {
        this.imapHost = imapHost;
    }

    public int getImapPort() {
        return imapPort;
    }

    public void setImapPort(int imapPort) {
        this.imapPort = imapPort;
    }

    public String getSmtpHost() {
        return smtpHost;
    }

    public void setSmtpHost(String smtpHost) {
        this.smtpHost = smtpHost;
    }

    public int getSmtpPort() {
        return smtpPort;
    }

    public void setSmtpPort(int smtpPort) {
        this.smtpPort = smtpPort;
    }

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
    }

    public String getTenantId() {
        return tenantId;
    }

    public void setTenantId(String tenantId) {
        this.tenantId = tenantId;
    }

    public String getTokenFilePath() {
        return tokenFilePath;
    }

    public void setTokenFilePath(String tokenFilePath) {
        this.tokenFilePath = tokenFilePath;
    }

    public boolean isEnabled() {
        if (!enabled || user == null || user.isBlank()) {
            return false;
        }
        if (authType == EmailAuthType.OAUTH2_DEVICE_CODE) {
            return true;
        }
        return password != null && !password.isBlank();
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }
}
