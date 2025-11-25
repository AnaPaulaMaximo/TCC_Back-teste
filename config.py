import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuração do SQLite ---
DB_NAME = "repensei.db" # O arquivo que o init_db.py criou

def get_db_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    try:
        # check_same_thread=False é necessário para o Flask
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        
        # Define o row_factory para retornar dicionários (como o mysql-connector)
        conn.row_factory = sqlite3.Row
        
        return conn
    except sqlite3.Error as e:
        print(f">>> ERRO ao conectar com o banco SQLite: {e}")
        return None

# --- Variáveis de Conexão Globais ---
conn = get_db_connection()

if conn:
    cursor = conn.cursor()
    print(">>> Conexão com o banco de dados SQLite estabelecida com sucesso!")
else:
    cursor = None
    print(">>> FALHA ao conectar com o banco de dados SQLite.")