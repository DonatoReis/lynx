# cache.py

import sqlite3
import time

CACHE_DB = 'cache.db'
CACHE_EXPIRATION = 24 * 3600  # 24 horas

def init_db():
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            data TEXT,
            timestamp REAL
        )
    ''')
    conn.commit()
    conn.close()

def carregar_cache():
    init_db()
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    current_time = time.time()
    cursor.execute('SELECT key, data, timestamp FROM cache WHERE timestamp > ?', (current_time - CACHE_EXPIRATION,))
    rows = cursor.fetchall()
    cache = {key: {'data': data, 'timestamp': timestamp} for key, data, timestamp in rows}
    conn.close()
    return cache

def salvar_cache(key, data):
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    timestamp = time.time()
    cursor.execute('REPLACE INTO cache (key, data, timestamp) VALUES (?, ?, ?)', (key, data, timestamp))
    conn.commit()
    conn.close()
