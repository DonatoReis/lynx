# config.py

import json
import os

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {
            "questions": [],
            "prompts": {},
            "api_key": "",
            "site_link": "",
            "urls_file": ""
        }

    # Ensure required keys exist
    config.setdefault('prompts', {})
    config.setdefault('api_key', "")
    config.setdefault('site_link', "")
    config.setdefault('urls_file', "")

    return config

def save_config(config):
    # Converter objetos não serializáveis em tipos suportados
    for question in config.get('questions', []):
        if 'options' in question and isinstance(question['options'], list):
            # Já é uma lista, nada a fazer
            pass
        else:
            question['options'] = []  # Ou outra ação apropriada

        if 'branching' in question and isinstance(question['branching'], dict):
            # Já é um dicionário, nada a fazer
            pass
        else:
            question['branching'] = {}

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
