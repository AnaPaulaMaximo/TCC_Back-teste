import sqlite3
import datetime

# Nome do arquivo do banco de dados
DB_NAME = "repensei.db"

# SQL adaptado para SQLite
SQL_SCRIPT = """
DROP TABLE IF EXISTS aluno;
DROP TABLE IF EXISTS quiz_resultado;
DROP TABLE IF EXISTS Admin; /* Adicionado */

CREATE TABLE aluno (
    id_aluno INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    plano TEXT NOT NULL DEFAULT 'freemium' CHECK(plano IN ('freemium', 'premium')),
    url_foto TEXT
);

CREATE TABLE quiz_resultado (
    id_resultado INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno INTEGER NOT NULL, -- <--- ADICIONE ESTA LINHA
    tema TEXT NOT NULL,
    acertos INTEGER NOT NULL,
    total_perguntas INTEGER NOT NULL,
    data_criacao DATE NOT NULL,
    FOREIGN KEY(id_aluno) REFERENCES aluno(id_aluno) ON DELETE CASCADE 
);

/* Tabela Admin que estava faltando */
CREATE TABLE Admin (
    id_admin INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL
);


/* --- Dados iniciais --- */

/* Usuários de teste */
INSERT INTO aluno (nome, email, senha, plano) VALUES
('Aluno Teste', 'aluno@email.com', '123', 'premium'),
('Aluno Freemium', 'freemium@email.com', '123', 'freemium');

/* Administrador de teste (para a tabela Admin) */
INSERT INTO Admin (nome, email, senha) VALUES
('Admin', 'admin@email.com', 'admin123');
"""

def initialize_database():
    """
    Cria e inicializa o banco de dados SQLite.
    """
    try:
        # Conecta (ou cria o arquivo .db)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Executa os comandos SQL (permite múltiplos comandos)
        cursor.executescript(SQL_SCRIPT)
        
        conn.commit()
        conn.close()
        
        print(f"Banco de dados '{DB_NAME}' inicializado com sucesso.")
        print("Tabelas 'aluno', 'quiz_resultado' e 'Admin' criadas.")
        print("Usuários e Admin de teste inseridos.")

    except sqlite3.Error as e:
        print(f"ERRO ao inicializar o banco de dados: {e}")

if __name__ == "__main__":
    initialize_database()