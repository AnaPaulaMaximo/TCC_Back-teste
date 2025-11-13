from flask import Blueprint, request, jsonify, session
from config import conn, cursor
from utils import get_user_plan # Precisamos para verificar o ID do aluno
import datetime # IMPORTAR PARA CORRIGIR O BUG

quiz_bp = Blueprint('quiz_bp', __name__, url_prefix='/quiz')

@quiz_bp.route('/salvar_resultado', methods=['POST'])
def salvar_resultado():
    data = request.get_json()
    id_aluno = data.get('id_aluno')
    tema = data.get('tema')
    acertos = data.get('acertos')
    total_perguntas = data.get('total_perguntas')
    data_hoje = datetime.date.today() # Obter a data de hoje

    if not id_aluno or not tema or acertos is None or not total_perguntas:
        return jsonify({'error': 'Dados incompletos para salvar o resultado.'}), 400
    
    # Verificação simples se o aluno existe
    # (get_user_plan retorna 'freemium' como padrão, então a verificação
    # de 'is None' pode não funcionar como esperado se o aluno não existir.
    # Uma verificação de existência real seria melhor, mas mantendo a lógica original:)
    if get_user_plan(id_aluno) is None: # Esta verificação pode precisar de ajuste
        return jsonify({'error': 'Aluno não encontrado.'}), 404

    try:
        # CORREÇÃO DE BUG: Adicionado data_criacao ao INSERT
        cursor.execute(
            'INSERT INTO QuizResultado (id_aluno, tema, acertos, total_perguntas, data_criacao) VALUES (?, ?, ?, ?, ?)',
            (id_aluno, tema, acertos, total_perguntas, data_hoje) # Passa a data
        )
        conn.commit()
        return jsonify({'message': 'Resultado do quiz salvo com sucesso.'}), 201
    except Exception as e:
        print(f"Erro ao salvar resultado do quiz: {e}")
        return jsonify({'error': f'Erro interno ao salvar resultado: {e}'}), 500