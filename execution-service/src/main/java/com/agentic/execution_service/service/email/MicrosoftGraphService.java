package com.agentic.execution_service.service.email;

import com.agentic.execution_service.models.email.EmailAccountConfig;
import com.agentic.execution_service.models.email.EmailAccountType;
import com.agentic.execution_service.models.email.EmailMessageDTO;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.jsoup.Jsoup;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service handling Microsoft Graph API operations for Outlook / Office 365 accounts,
 * specifically tailored for institutional accounts (e.g. Universidad de Sevilla @alum.us.es)
 * using OAuth2 Device Code Flow.
 */
@Service
public class MicrosoftGraphService {

    private static final Logger logger = LoggerFactory.getLogger(MicrosoftGraphService.class);

    private static final String GRAPH_API_BASE = "https://graph.microsoft.com/v1.0";
    private static final String DEFAULT_SCOPES = "offline_access https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/User.Read";

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final Map<String, TokenData> tokenCache = new ConcurrentHashMap<>();

    public MicrosoftGraphService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    private static class TokenData {
        String accessToken;
        String refreshToken;
        long expiresAtEpochMs;

        TokenData(String accessToken, String refreshToken, long expiresAtEpochMs) {
            this.accessToken = accessToken;
            this.refreshToken = refreshToken;
            this.expiresAtEpochMs = expiresAtEpochMs;
        }

        boolean isValid() {
            // Valid if expires more than 120 seconds in the future
            return accessToken != null && !accessToken.isBlank() && expiresAtEpochMs > (System.currentTimeMillis() + 120_000);
        }
    }

    /**
     * Obtains a valid OAuth2 Access Token for Microsoft Graph, either from memory cache,
     * token file, token refresh, or by initiating Device Code Flow.
     */
    public synchronized String getAccessToken(EmailAccountConfig config) throws Exception {
        String cacheKey = config.getUser() != null ? config.getUser() : "default_outlook";

        TokenData tokenData = tokenCache.get(cacheKey);
        if (tokenData != null && tokenData.isValid()) {
            return tokenData.accessToken;
        }

        // Try reading from file
        Path tokenPath = Path.of(config.getTokenFilePath());
        if (Files.exists(tokenPath)) {
            try {
                String json = Files.readString(tokenPath, StandardCharsets.UTF_8);
                JsonNode root = objectMapper.readTree(json);
                String accessToken = root.path("access_token").asText(null);
                String refreshToken = root.path("refresh_token").asText(null);
                long expiresAt = root.path("expires_at").asLong(0);

                if (accessToken != null && expiresAt > (System.currentTimeMillis() + 120_000)) {
                    tokenData = new TokenData(accessToken, refreshToken, expiresAt);
                    tokenCache.put(cacheKey, tokenData);
                    return accessToken;
                }

                // If expired but has refresh token, attempt refresh
                if (refreshToken != null && !refreshToken.isBlank()) {
                    logger.info("Access token expired for {}. Refreshing using refresh_token...", config.getUser());
                    try {
                        TokenData refreshed = refreshAccessToken(config, refreshToken);
                        tokenCache.put(cacheKey, refreshed);
                        saveTokenToFile(tokenPath, refreshed);
                        return refreshed.accessToken;
                    } catch (Exception e) {
                        logger.warn("Failed to refresh token: {}. Initiating new Device Code Flow...", e.getMessage());
                    }
                }
            } catch (Exception e) {
                logger.warn("Failed reading cached token from {}: {}", tokenPath, e.getMessage());
            }
        }

        // Must initiate Device Code Flow
        TokenData newTokens = performDeviceCodeFlow(config);
        tokenCache.put(cacheKey, newTokens);
        saveTokenToFile(tokenPath, newTokens);
        return newTokens.accessToken;
    }

    private TokenData refreshAccessToken(EmailAccountConfig config, String refreshToken) throws Exception {
        String tenant = config.getTenantId() != null && !config.getTenantId().isBlank() ? config.getTenantId() : "common";
        String tokenUrl = "https://login.microsoftonline.com/" + tenant + "/oauth2/v2.0/token";

        String requestBody = "client_id=" + URLEncoder.encode(config.getClientId(), StandardCharsets.UTF_8)
                + "&grant_type=refresh_token"
                + "&refresh_token=" + URLEncoder.encode(refreshToken, StandardCharsets.UTF_8)
                + "&scope=" + URLEncoder.encode(DEFAULT_SCOPES, StandardCharsets.UTF_8);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(tokenUrl))
                .header("Content-Type", "application/x-www-form-urlencoded")
                .timeout(Duration.ofSeconds(15))
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() != 200) {
            throw new RuntimeException("Token refresh error (HTTP " + response.statusCode() + "): " + response.body());
        }

        JsonNode json = objectMapper.readTree(response.body());
        String newAccessToken = json.path("access_token").asText();
        String newRefreshToken = json.path("refresh_token").asText(refreshToken);
        long expiresInSec = json.path("expires_in").asLong(3600);
        long expiresAtEpochMs = System.currentTimeMillis() + (expiresInSec * 1000);

        return new TokenData(newAccessToken, newRefreshToken, expiresAtEpochMs);
    }

    private TokenData performDeviceCodeFlow(EmailAccountConfig config) throws Exception {
        String tenant = config.getTenantId() != null && !config.getTenantId().isBlank() ? config.getTenantId() : "common";
        String deviceCodeUrl = "https://login.microsoftonline.com/" + tenant + "/oauth2/v2.0/devicecode";

        String requestBody = "client_id=" + URLEncoder.encode(config.getClientId(), StandardCharsets.UTF_8)
                + "&scope=" + URLEncoder.encode(DEFAULT_SCOPES, StandardCharsets.UTF_8);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(deviceCodeUrl))
                .header("Content-Type", "application/x-www-form-urlencoded")
                .timeout(Duration.ofSeconds(15))
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() != 200) {
            throw new RuntimeException("Device code initiation error (HTTP " + response.statusCode() + "): " + response.body());
        }

        JsonNode json = objectMapper.readTree(response.body());
        String deviceCode = json.path("device_code").asText();
        String userCode = json.path("user_code").asText();
        String verificationUri = json.path("verification_uri").asText("https://microsoft.com/devicelogin");
        int expiresInSec = json.path("expires_in").asInt(900);
        int intervalSec = Math.max(json.path("interval").asInt(5), 3);

        String banner = """
                
                ================================================================================
                AUTENTICACIÓN REQUERIDA PARA OUTLOOK / OFFICE 365 (%s)
                1. Abre en tu navegador: %s
                2. Introduce el siguiente código: %s
                3. Inicia sesión con tu cuenta institucional de la Universidad de Sevilla.
                ================================================================================
                """.formatted(config.getUser(), verificationUri, userCode);

        logger.warn(banner);
        System.out.println(banner);

        // Polling loop
        String tokenUrl = "https://login.microsoftonline.com/" + tenant + "/oauth2/v2.0/token";
        long startTime = System.currentTimeMillis();
        long deadline = startTime + (expiresInSec * 1000L);

        while (System.currentTimeMillis() < deadline) {
            Thread.sleep(intervalSec * 1000L);

            String pollBody = "client_id=" + URLEncoder.encode(config.getClientId(), StandardCharsets.UTF_8)
                    + "&grant_type=urn:ietf:params:oauth:grant-type:device_code"
                    + "&device_code=" + URLEncoder.encode(deviceCode, StandardCharsets.UTF_8);

            HttpRequest pollRequest = HttpRequest.newBuilder()
                    .uri(URI.create(tokenUrl))
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .timeout(Duration.ofSeconds(15))
                    .POST(HttpRequest.BodyPublishers.ofString(pollBody))
                    .build();

            HttpResponse<String> pollResponse = httpClient.send(pollRequest, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

            if (pollResponse.statusCode() == 200) {
                JsonNode tokenJson = objectMapper.readTree(pollResponse.body());
                String accessToken = tokenJson.path("access_token").asText();
                String refreshToken = tokenJson.path("refresh_token").asText();
                long tokenExpiresIn = tokenJson.path("expires_in").asLong(3600);
                long expiresAt = System.currentTimeMillis() + (tokenExpiresIn * 1000);

                logger.info("Successfully authenticated Outlook account {} via OAuth2 Device Code Flow!", config.getUser());
                System.out.println("[OK] Autenticación completada con éxito para " + config.getUser());

                return new TokenData(accessToken, refreshToken, expiresAt);
            }

            JsonNode errJson = objectMapper.readTree(pollResponse.body());
            String error = errJson.path("error").asText();

            if ("authorization_pending".equalsIgnoreCase(error)) {
                // User has not finished entering code yet, continue polling
                continue;
            } else if ("slow_down".equalsIgnoreCase(error)) {
                intervalSec += 5;
            } else {
                String errorDesc = errJson.path("error_description").asText(error);
                throw new RuntimeException("Error during device code auth: " + error + " - " + errorDesc);
            }
        }

        throw new RuntimeException("Device code flow timed out after " + expiresInSec + " seconds.");
    }

    private void saveTokenToFile(Path tokenPath, TokenData tokens) {
        try {
            if (tokenPath.getParent() != null) {
                Files.createDirectories(tokenPath.getParent());
            }
            ObjectNode root = objectMapper.createObjectNode();
            root.put("access_token", tokens.accessToken);
            root.put("refresh_token", tokens.refreshToken);
            root.put("expires_at", tokens.expiresAtEpochMs);
            Files.writeString(tokenPath, objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(root), StandardCharsets.UTF_8);
            logger.info("Saved OAuth token cache to {}", tokenPath.toAbsolutePath());
        } catch (Exception e) {
            logger.warn("Could not save token cache to {}: {}", tokenPath, e.getMessage());
        }
    }

    /**
     * Fetches unread emails from Microsoft Graph API inbox.
     */
    public List<EmailMessageDTO> fetchUnreadEmails(EmailAccountConfig config, int limit) {
        List<EmailMessageDTO> result = new ArrayList<>();
        try {
            String accessToken = getAccessToken(config);

            String url = GRAPH_API_BASE + "/me/mailFolders/inbox/messages"
                    + "?$filter=" + URLEncoder.encode("isRead eq false", StandardCharsets.UTF_8)
                    + "&$top=" + limit
                    + "&$select=" + URLEncoder.encode("id,conversationId,subject,bodyPreview,body,from,sender,toRecipients,ccRecipients,replyTo,receivedDateTime,hasAttachments,internetMessageId", StandardCharsets.UTF_8);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Bearer " + accessToken)
                    .header("Accept", "application/json")
                    .timeout(Duration.ofSeconds(15))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() != 200) {
                logger.error("Error fetching unread messages from Graph API (HTTP {}): {}", response.statusCode(), response.body());
                return result;
            }

            JsonNode root = objectMapper.readTree(response.body());
            JsonNode valueArray = root.path("value");

            if (valueArray.isArray()) {
                for (JsonNode msgNode : valueArray) {
                    try {
                        EmailMessageDTO dto = parseGraphMessage(msgNode, config.getUser());
                        result.add(dto);
                    } catch (Exception e) {
                        logger.warn("Failed parsing Graph API message: {}", e.getMessage());
                    }
                }
            }

            logger.info("Fetched {} unread messages from Outlook ({}) via Microsoft Graph", result.size(), config.getUser());
        } catch (Exception e) {
            logger.error("Failed fetching unread emails from Outlook Graph API: {}", e.getMessage(), e);
        }
        return result;
    }

    private EmailMessageDTO parseGraphMessage(JsonNode msgNode, String accountUser) {
        String graphId = msgNode.path("id").asText();
        String internetMsgId = msgNode.path("internetMessageId").asText(graphId);
        String subject = msgNode.path("subject").asText("(Sin asunto)");

        // From
        JsonNode fromNode = msgNode.path("from").path("emailAddress");
        String fromName = fromNode.path("name").asText("");
        String fromAddress = fromNode.path("address").asText("");

        // Reply-To with fallback
        String replyToAddress = fromAddress;
        JsonNode replyToArray = msgNode.path("replyTo");
        if (replyToArray.isArray() && !replyToArray.isEmpty()) {
            String candidate = replyToArray.get(0).path("emailAddress").path("address").asText("");
            if (!candidate.isBlank()) {
                replyToAddress = candidate;
            }
        }

        // To recipients
        List<String> toAddresses = new ArrayList<>();
        JsonNode toArray = msgNode.path("toRecipients");
        if (toArray.isArray()) {
            for (JsonNode item : toArray) {
                String addr = item.path("emailAddress").path("address").asText("");
                if (!addr.isBlank()) {
                    toAddresses.add(addr);
                }
            }
        }

        // Cc recipients
        List<String> ccAddresses = new ArrayList<>();
        JsonNode ccArray = msgNode.path("ccRecipients");
        if (ccArray.isArray()) {
            for (JsonNode item : ccArray) {
                String addr = item.path("emailAddress").path("address").asText("");
                if (!addr.isBlank()) {
                    ccAddresses.add(addr);
                }
            }
        }

        String receivedAt = msgNode.path("receivedDateTime").asText("");
        String bodyPreview = msgNode.path("bodyPreview").asText("");

        JsonNode bodyNode = msgNode.path("body");
        String contentType = bodyNode.path("contentType").asText("text");
        String content = bodyNode.path("content").asText("");

        String bodyText = content;
        if ("html".equalsIgnoreCase(contentType)) {
            bodyText = Jsoup.parse(content).text();
        }

        String bodySnippet = !bodyPreview.isBlank() ? bodyPreview :
                (bodyText.length() > 150 ? bodyText.substring(0, 150) + "..." : bodyText);

        boolean hasAttachments = msgNode.path("hasAttachments").asBoolean(false);

        return new EmailMessageDTO(
                internetMsgId,
                EmailAccountType.OUTLOOK,
                accountUser != null ? accountUser : "",
                subject,
                fromName,
                fromAddress,
                replyToAddress,
                toAddresses,
                ccAddresses,
                receivedAt,
                bodySnippet,
                bodyText,
                hasAttachments,
                List.of()
        );
    }

    /**
     * Sends an email via Microsoft Graph API.
     */
    public String sendEmail(EmailAccountConfig config, String toAddress, String subject, String body, String inReplyToMessageId) throws Exception {
        String accessToken = getAccessToken(config);

        ObjectNode payload = objectMapper.createObjectNode();
        ObjectNode message = payload.putObject("message");

        message.put("subject", subject != null ? subject : "");

        ObjectNode bodyNode = message.putObject("body");
        bodyNode.put("contentType", "Text");
        bodyNode.put("content", body != null ? body : "");

        ArrayNode toRecipients = message.putArray("toRecipients");
        ObjectNode recipient = toRecipients.addObject();
        ObjectNode emailAddr = recipient.putObject("emailAddress");
        emailAddr.put("address", toAddress.trim());

        if (inReplyToMessageId != null && !inReplyToMessageId.isBlank()) {
            ArrayNode headers = message.putArray("internetMessageHeaders");
            ObjectNode header = headers.addObject();
            header.put("name", "In-Reply-To");
            header.put("value", inReplyToMessageId.trim());
        }

        payload.put("saveToSentItems", true);

        String jsonPayload = objectMapper.writeValueAsString(payload);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(GRAPH_API_BASE + "/me/sendMail"))
                .header("Authorization", "Bearer " + accessToken)
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(20))
                .POST(HttpRequest.BodyPublishers.ofString(jsonPayload, StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() != 202 && response.statusCode() != 200) {
            throw new RuntimeException("Error sending email via Microsoft Graph (HTTP " + response.statusCode() + "): " + response.body());
        }

        logger.info("Successfully sent email via Microsoft Graph to {}", toAddress);
        return "Correo enviado satisfactoriamente mediante Microsoft Graph desde " + config.getUser() + " (OUTLOOK) hacia " + toAddress + " con asunto: '" + subject + "'";
    }
}
