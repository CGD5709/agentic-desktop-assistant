package com.agentic.execution_service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.io.BufferedReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Spring Boot entry point for the Execution Service microservice.
 */
@SpringBootApplication
public class ExecutionServiceApplication {

    private static final Logger logger = LoggerFactory.getLogger(ExecutionServiceApplication.class);

    public static void main(String[] args) {
        loadDotEnv();
        SpringApplication.run(ExecutionServiceApplication.class, args);
    }

    private static void loadDotEnv() {
        List<Path> candidatePaths = List.of(
                Path.of(".env"),
                Path.of("..", ".env"),
                Path.of(System.getProperty("user.dir", "."), ".env"),
                Path.of(System.getProperty("user.dir", "."), "..", ".env")
        );

        for (Path path : candidatePaths) {
            if (Files.exists(path) && Files.isRegularFile(path)) {
                logger.info("Loading environment configuration from {}", path.toAbsolutePath().normalize());
                try (BufferedReader reader = Files.newBufferedReader(path)) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        line = line.trim();
                        if (line.isEmpty() || line.startsWith("#")) {
                            continue;
                        }
                        int eqIdx = line.indexOf('=');
                        if (eqIdx > 0) {
                            String key = line.substring(0, eqIdx).trim();
                            String value = line.substring(eqIdx + 1).trim();
                            if ((value.startsWith("\"") && value.endsWith("\"")) ||
                                (value.startsWith("'") && value.endsWith("'"))) {
                                value = value.substring(1, value.length() - 1);
                            }
                            if (System.getenv(key) == null && System.getProperty(key) == null) {
                                System.setProperty(key, value);
                            }
                        }
                    }
                } catch (Exception e) {
                    logger.warn("Failed to parse .env file at {}: {}", path, e.getMessage());
                }
                break;
            }
        }
    }
}