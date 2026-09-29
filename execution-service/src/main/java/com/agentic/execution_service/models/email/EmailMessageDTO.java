package com.agentic.execution_service.models.email;

import java.util.List;

/**
 * Immutable Data Transfer Object representing a sanitized, parsed email message.
 * All recipient and sender fields are extracted deterministically via code.
 */
public record EmailMessageDTO(
    String id,
    EmailAccountType account,
    String accountAddress,
    String subject,
    String fromName,
    String fromAddress,
    String replyToAddress,
    List<String> toAddresses,
    List<String> ccAddresses,
    String receivedAt,
    String bodySnippet,
    String bodyText,
    boolean hasAttachments,
    List<String> attachmentNames
) {
    public EmailMessageDTO {
        toAddresses = toAddresses != null ? List.copyOf(toAddresses) : List.of();
        ccAddresses = ccAddresses != null ? List.copyOf(ccAddresses) : List.of();
        attachmentNames = attachmentNames != null ? List.copyOf(attachmentNames) : List.of();
    }
}
