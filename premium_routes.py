from flask import Blueprint, request, jsonify, session, current_app
from utils import get_user_plan
from api_key_manager import generate_with_retry
import google.generativeai as genai
import os
import datetime
from config import conn, cursor
import json

premium_bp = Blueprint('premium_bp', __name__, url_prefix='/premium')

MODEL_NAME = "gemini-2.5-flash"

def check_premium_access(id_aluno):
    if not id_aluno:
        return jsonify({'error': 'ID do aluno é obrigatório.'}), 400
    if get_user_plan(id_aluno) != 'premium':
        return jsonify({'error': 'Esta funcionalidade é exclusiva para usuários Premium.'}), 403
    return None

def check_premium_session():
    if 'id_aluno' not in session:
        return jsonify({'error': 'Usuário não logado.'}), 401
    if session.get('plano') != 'premium':
        return jsonify({'error': 'Acesso negado. Funcionalidade Premium.'}), 403
    return None

@premium_bp.route('/quiz', methods=['POST'])
def quiz_premium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')
    
    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error

    if 'tema' not in data:
        return jsonify({'error': 'O campo "tema" é obrigatório para usuários Premium.'}), 400
    
    tema = data['tema']
    
    # MUDANÇA AQUI: O prompt agora pede classificação explicita
    prompt = f"""Dado o tema '{tema}', atue como um professor especialista.
    
    1. Classifique este tema estritamente em uma destas duas categorias: "Filosofia" ou "Sociologia". Escolha a que melhor se encaixa.
    2. Gere um quiz com 10 questões sobre o tema.

    Retorne APENAS um JSON válido com a seguinte estrutura exata, sem crases ou markdown:
    {{
        "categoria": "Filosofia" ou "Sociologia - oque o usuário escreveu no tema (ex:aristoteles)",
        "questoes": [
            {{
                "pergunta": "texto da pergunta",
                "opcoes": ["opcao1", "opcao2", "opcao3", "opcao4"],
                "resposta_correta": "texto da opcao correta",
                "explicacao": "breve explicacao"
            }}
        ]
    }}

    Se o tema for inválido/inadequado, retorne APENAS: {{"erro": "Tema inadequado"}}
    """
    
    try:
        key_manager = current_app.config['KEY_MANAGER']
        texto = generate_with_retry(key_manager, prompt, MODEL_NAME)
        
        if texto is None:
            return jsonify({"erro": "Não foi possível gerar o quiz após várias tentativas."}), 500
        
        # Limpeza básica caso a IA mande markdown
        texto = texto.replace("```json", "").replace("```", "").strip()
        
        return jsonify({"assunto": tema, "contedo": texto})
    
    except Exception as e:
        print(f"Erro ao gerar quiz: {e}")
        return jsonify({"erro": f"Erro ao gerar quiz com IA: {str(e)}"}), 500


@premium_bp.route('/flashcard', methods=['POST'])
def flashcard_premium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')

    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error

    if 'tema' not in data:
        return jsonify({'error': 'O campo "tema" é obrigatório para usuários Premium.'}), 400
    
    tema = data['tema']
    prompt = f"""
Dado o tema '{tema}', primeiro avalie se ele é estritamente relacionado a filosofia ou sociologia e se não contém conteúdo inadequado.

Se o tema for válido, Gere 12 perguntas para flashcards sobre o tema '{tema}'. Retorne a pergunta e a resposta correta, a resposta deve ser breve e acertiva. Estrutura: Pergunta: [pergunta] Resposta: [resposta]

Se o tema for inválido, retorne **APENAS** a mensagem: NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.
"""
    try:
        # --- USA O GERENCIADOR DE CHAVES ---
        key_manager = current_app.config['KEY_MANAGER']
        texto = generate_with_retry(key_manager, prompt, MODEL_NAME)
        
        if texto is None:
            return jsonify({"erro": "Não foi possível gerar os flashcards após várias tentativas."}), 500
        
        # Salva no histórico
        try:
            cursor.execute(
                'INSERT INTO historico_premium (id_aluno, tipo_atividade, tema, conteudo_gerado, data_criacao) VALUES (?, ?, ?, ?, ?)',
                (id_aluno, 'flashcard', tema, texto, datetime.datetime.now())
            )
            conn.commit()
        except Exception as e:
            print(f"Erro ao salvar historico (flashcard): {e}")
            conn.rollback()

        return jsonify({"assunto": tema, "contedo": texto})
    
    except Exception as e:
        print(f"Erro ao gerar flashcards: {e}")
        return jsonify({"erro": f"Erro ao gerar flashcards com IA: {str(e)}"}), 500


@premium_bp.route('/resumo', methods=['POST'])
def resumo():
    data = request.get_json()
    id_aluno = data.get('id_aluno')

    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error
        
    if 'tema' not in data:
        return jsonify({'error': 'O campo "tema" é obrigatório.'}), 400
    
    tema = data['tema']
    prompt = f"""
        Dado o tema '{tema}', avalie se ele é estritamente relacionado a filosofia ou sociologia e não contém conteúdo inadequado.
        O resumo deve ser focado nos principais tópicos do tema.
        Se o tema for inválido, retorne **APENAS** a mensagem: NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.
    """
    try:
        # --- USA O GERENCIADOR DE CHAVES ---
        key_manager = current_app.config['KEY_MANAGER']
        texto = generate_with_retry(key_manager, prompt, MODEL_NAME)
        
        if texto is None:
            return jsonify({"erro": "Não foi possível gerar o resumo após várias tentativas."}), 500
        
        # Salva no histórico
        try:
            cursor.execute(
                'INSERT INTO historico_premium (id_aluno, tipo_atividade, tema, conteudo_gerado, data_criacao) VALUES (?, ?, ?, ?, ?)',
                (id_aluno, 'resumo', tema, texto, datetime.datetime.now())
            )
            conn.commit()
        except Exception as e:
            print(f"Erro ao salvar historico (resumo): {e}")
            conn.rollback()
        
        return jsonify({"assunto": tema, "conteudo": texto})
    
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return jsonify({"erro": str(e)}), 500

@premium_bp.route('/correcao', methods=['POST'])
def correcao():
    data = request.get_json()
    id_aluno = data.get('id_aluno')

    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error

    if 'tema' not in data or 'texto' not in data:
        return jsonify({'error': 'Os campos "tema" e "texto" são obrigatórios.'}), 400

    tema = data['tema']
    texto = data['texto']
    prompt = f""""
        Você é um professor especializado em Filosofia e Sociologia. Corrija o texto do aluno sobre o tema '{tema}'.
        Texto do aluno: '{texto}'.
        Seu feedback deve ser resumido e focado no conteúdo, não na gramática.
        Avalie se o tema é apropriado. Se não for, retorne **APENAS** a mensagem: NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.
    """
    try:
        # --- USA O GERENCIADOR DE CHAVES ---
        key_manager = current_app.config['KEY_MANAGER']
        texto_corrigido = generate_with_retry(key_manager, prompt, MODEL_NAME)
        
        if texto_corrigido is None:
            return jsonify({"erro": "Não foi possível gerar a correção após várias tentativas."}), 500
        
        # Salva no histórico
        try:
            cursor.execute(
                'INSERT INTO historico_premium (id_aluno, tipo_atividade, tema, conteudo_gerado, texto_original, data_criacao) VALUES (?, ?, ?, ?, ?, ?)',
                (id_aluno, 'correcao', tema, texto_corrigido, texto, datetime.datetime.now())
            )
            conn.commit()
        except Exception as e:
            print(f"Erro ao salvar historico (correcao): {e}")
            conn.rollback()
        
        return jsonify({"texto_original": texto, "correcao": texto_corrigido})
    
    except Exception as e:
        print(f"Erro ao corrigir texto: {e}")
        return jsonify({"erro": str(e)}), 500

@premium_bp.route('/quiz/salvar_completo', methods=['POST'])
def salvar_quiz_premium_completo():
    data = request.get_json()
    id_aluno = data.get('id_aluno')
    
    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error
        
    try:
        tema = data.get('tema')
        acertos = data.get('acertos')
        total_perguntas = data.get('total_perguntas')
        conteudo_gerado = data.get('conteudo_gerado')
        respostas_usuario = json.dumps(data.get('respostas_usuario'))
        
        if not all([tema, acertos is not None, total_perguntas, conteudo_gerado, respostas_usuario]):
             return jsonify({'error': 'Dados incompletos para salvar o quiz.'}), 400

        cursor.execute(
            """
            INSERT INTO historico_premium 
            (id_aluno, tipo_atividade, tema, conteudo_gerado, acertos, total_perguntas, respostas_usuario, data_criacao) 
            VALUES (?, 'quiz', ?, ?, ?, ?, ?, ?)
            """,
            (id_aluno, tema, conteudo_gerado, acertos, total_perguntas, respostas_usuario, datetime.datetime.now())
        )
        conn.commit()
        return jsonify({'message': 'Resultado do quiz salvo no histórico premium.'}), 201

    except Exception as e:
        print(f"Erro ao salvar quiz completo: {e}")
        conn.rollback()
        return jsonify({"error": f"Erro interno ao salvar quiz: {e}"}), 500

@premium_bp.route('/historico/<int:id_aluno>', methods=['GET'])
def get_historico(id_aluno):
    auth_error = check_premium_session()
    if auth_error:
        return auth_error
    
    if session['id_aluno'] != id_aluno:
        return jsonify({'error': 'Acesso não autorizado ao histórico de outro usuário.'}), 403

    try:
        cursor.execute(
            """
            SELECT 
                id_historico as id, 
                tipo_atividade, 
                tema, 
                data_criacao, 
                acertos, 
                total_perguntas
            FROM historico_premium 
            WHERE id_aluno = ?
            ORDER BY data_criacao DESC
            """, (id_aluno,)
        )
        full_history = [dict(r) for r in cursor.fetchall()]
        
        return jsonify(full_history)

    except Exception as e:
        print(f"Erro ao buscar historico: {e}")
        conn.rollback()
        return jsonify({"error": f"Erro interno ao buscar historico: {e}"}), 500

@premium_bp.route('/historico/item/<int:item_id>', methods=['GET'])
def get_historico_item(item_id):
    auth_error = check_premium_session()
    if auth_error:
        return auth_error
    
    id_aluno_sessao = session['id_aluno']
    
    try:
        cursor.execute(
            "SELECT * FROM historico_premium WHERE id_historico = ? AND id_aluno = ?",
            (item_id, id_aluno_sessao)
        )
        item = cursor.fetchone()
        
        if not item:
            return jsonify({'error': 'Item de histórico não encontrado ou não pertence a você.'}), 404
        
        item_dict = dict(item)
        
        try:
            item_dict['respostas_usuario'] = json.loads(item_dict['respostas_usuario'])
        except:
            item_dict['respostas_usuario'] = {}

        return jsonify(item_dict)

    except Exception as e:
        print(f"Erro ao buscar item do historico: {e}")
        conn.rollback()
        return jsonify({"error": f"Erro interno ao buscar item: {e}"}), 500