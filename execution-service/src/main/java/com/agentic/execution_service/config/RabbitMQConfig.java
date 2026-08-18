package com.agentic.execution_service.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import com.fasterxml.jackson.databind.ObjectMapper;

@Configuration
public class RabbitMQConfig {

    public static final String EXCHANGE_NAME = "agent_events";
    public static final String QUEUE_NAME = "java_execution_queue";
    public static final String ROUTING_KEY = "tool.request.*";

    // 1. Declaramos el Exchange (por si Java arranca antes que Python)
    @Bean
    public TopicExchange agentEventsExchange() {
        return new TopicExchange(EXCHANGE_NAME);
    }

    // 2. Declaramos la cola donde Java recibirá las peticiones
    @Bean
    public Queue executionQueue() {
        return new Queue(QUEUE_NAME, true); // true = durable
    }

    // 3. Vinculamos la cola al Exchange con el routing key
    @Bean
    public Binding binding(Queue executionQueue, TopicExchange agentEventsExchange) {
        return BindingBuilder.bind(executionQueue).to(agentEventsExchange).with(ROUTING_KEY);
    }

    // 4. Inyectamos Jackson para convertir automáticamente JSON <-> Objetos Java
   @Bean
    public MessageConverter jsonMessageConverter() {
        ObjectMapper mapper = new ObjectMapper();
        return new Jackson2JsonMessageConverter(mapper);
    }
}
