package com.agentic.execution_service.models.email;

/**
 * Supported authentication mechanisms for email accounts.
 */
public enum EmailAuthType {
    /**
     * Standard username and password (or App Password) via IMAP / SMTP.
     */
    BASIC_AUTH,

    /**
     * OAuth2 Device Authorization Code Flow (e.g. for Microsoft 365 / Graph API).
     */
    OAUTH2_DEVICE_CODE
}
