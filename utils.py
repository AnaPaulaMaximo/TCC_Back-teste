import json
import os
from config import cursor

def carregar_dados_json(nome_arquivo):
    """Carrega dados de um arquivo JSON local."""
    try:
        # Garante que o caminho para o JSON seja relativo a este arquivo
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, nome_arquivo)
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"AVISO: Não foi possível carregar o arquivo {nome_arquivo}.")
        return []

def get_user_plan(id_aluno):
    """Busca o plano do usuário no banco de dados."""
    if not cursor:
        print("Erro: Sem conexão com o banco de dados.")
        return 'freemium'
        
    try:
        cursor.execute('SELECT plano FROM Aluno WHERE id_aluno = %s', (id_aluno,))
        resultado = cursor.fetchone()
        if resultado and resultado.get('plano'):
            return resultado['plano']
    except Exception as e:
        print(f"Erro ao buscar plano do usuário: {e}")
    
    # Retorna 'freemium' como padrão em caso de erro ou se o plano for nulo
    return 'freemium'