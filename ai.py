# ai.py

import openai
import logging
import asyncio
from openai import RateLimitError, OpenAIError

async def consultar_openai(produtos, respostas, config, callback=None):
    produtos_joined = "\n".join(produtos)

    # Get the prompt template from the config
    prompt_template = config.get('prompts', {}).get('prompt_template', '')
    if not prompt_template:
        # Default prompt template
        prompt_template = """
Você é um especialista em produtos químicos e tratamento de superfícies metálicas. Utilize as informações fornecidas pelo cliente para recomendar os melhores produtos disponíveis.

{informacoes_cliente}

# Produtos Disponíveis:
{produtos}

# Formato de Saída:
- Resumo das necessidades do cliente.
- Produto(s) recomendado(s).
- Justificativa para cada recomendação.
- Conselho ou métrica adicional relevante para a consulta do cliente.

# Notes:
- Utilize linguagem técnica adequada ao nível de conhecimento do cliente.
- Apresente a resposta de forma clara, coesa e fluida, evitando o uso de formatação com asteriscos ou marcadores.
"""
    # Prepare variables for formatting
    variables = respostas.copy()
    variables['produtos'] = produtos_joined

    # Construir informações do cliente
    informacoes_cliente = "\n".join(f"- {key.replace('_', ' ').title()}: {value}" for key, value in respostas.items())
    variables['informacoes_cliente'] = informacoes_cliente

    # Format the prompt
    prompt = prompt_template.format(**variables)

    # Get the system message from config
    system_message = config.get('prompts', {}).get('system_message', '')
    if not system_message:
        system_message = "Você é um especialista em produtos químicos e tratamento de superfícies metálicas."

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    logging.info("Prompt enviado para OpenAI:")
    logging.info(prompt)

    openai.api_key = config.get('api_key')
    attempts = 5
    backoff = 1

    for attempt in range(attempts):
        try:
            response = await openai.chat.completions.acreate(
                model="gpt-4o-mini-2024-07-18",
                messages=messages,
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True
            )

            resultado = ""
            async for chunk in response:
                chunk_message = chunk['choices'][0]['delta'].get('content', '')
                resultado += chunk_message
                if callback:
                    callback(chunk_message)
            logging.info("Consulta à OpenAI realizada com sucesso.")
            return resultado
        except RateLimitError:
            logging.warning(f"Limite de taxa atingido. Tentativa {attempt + 1}/{attempts}.")
            await asyncio.sleep(backoff)
            backoff *= 2
        except OpenAIError as e:
            logging.error(f"Erro ao consultar a API da OpenAI: {e}")
            return "Desculpe, não foi possível processar sua solicitação no momento."
    return "Desculpe, estou enfrentando problemas para processar sua solicitação no momento."
