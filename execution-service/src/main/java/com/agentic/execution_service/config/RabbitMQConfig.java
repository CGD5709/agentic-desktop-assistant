package com.agentic.execution_service.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ infrastructure configuration for inter-service communication with the reasoning engine.
 */
@Configuration
public class RabbitMQConfig {

    public static final String EXCHANGE_NAME = "agent_events";
    public static final String QUEUE_NAME = "execution_service_queue";
    public static final String ROUTING_KEY = "tool.request.*";

    @Bean
    public TopicExchange agentEventsExchange() {
        return new TopicExchange(EXCHANGE_NAME);
    }

    @Bean
    public Queue executionQueue() {
        return new Queue(QUEUE_NAME, true);
    }

    @Bean
    public Binding binding(Queue executionQueue, TopicExchange agentEventsExchange) {
        return BindingBuilder.bind(executionQueue).to(agentEventsExchange).with(ROUTING_KEY);
    }

    @Bean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }

    @Bean
    public MessageConverter jsonMessageConverter(ObjectMapper objectMapper) {
        return new Jackson2JsonMessageConverter(objectMapper);
    }
}
