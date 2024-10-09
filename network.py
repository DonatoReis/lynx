# network.py

import aiohttp
import asyncio
import logging
import time
from bs4 import BeautifulSoup
from cache import salvar_cache
import hashlib

async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logging.error(f"Erro ao acessar a página {url}: {e}")
        return None

async def extrair_conteudo(url, cache):
    cache_key = hashlib.md5(url.encode()).hexdigest()

    if cache_key in cache:
        logging.info(f"Produtos carregados do cache para a URL: {url}")
        return cache[cache_key]['data']

    async with aiohttp.ClientSession() as session:
        content = await fetch(session, url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            produtos_html = soup.find_all('h1', class_='c-dark title-big mb-0')
            descricoes_html = soup.find_all('article', class_='product-text')

            produtos = []
            for titulo, descricao in zip(produtos_html, descricoes_html):
                titulo_texto = titulo.get_text(strip=True)
                descricao_texto = descricao.get_text(strip=True)
                produtos.append(f"{titulo_texto}: {descricao_texto}")
            
            # Salva no cache
            salvar_cache(cache_key, produtos)
            logging.info(f"{len(produtos)} produtos extraídos e salvos no cache para a URL: {url}")
            return produtos
        else:
            return []

async def ler_urls_arquivo(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            urls = [linha.strip() for linha in arquivo.readlines() if linha.strip()]
        logging.info(f"{len(urls)} URLs lidas do arquivo {caminho_arquivo}.")
        return urls
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo {caminho_arquivo}: {e}")
        return []
