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
    
    prompt = f"""
Você é um Validador Acadêmico Rígido e Professor de Filosofia/Sociologia.
Sua tarefa é analisar o tema: '{tema}'

ETAPA 1: VERIFICAÇÃO DE SEGURANÇA E ESCOPO (CRITÉRIO ELIMINATÓRIO)
Analise o tema e responda "NÃO" se ele se encaixar em qualquer um destes casos:
1. É um tema puramente de Exatas (Matemática, Física, Química, Geometria, Lógica Matemática Pura) ou Biológicas (Anatomia, Fisiologia), sem foco central em Ética ou Epistemologia.
2. É um tema de cultura pop, entretenimento, esportes ou cotidiano sem ligação acadêmica clássica.
3. É uma "falsa conexão" (ex: "Filosofia do Triângulo", "Sociologia do Futebol", "Filosofia da Fórmula 1"). Não tente inventar uma conexão filosófica se o tema central não for filosofia.
4. Contém palavrões, gírias vulgares ou conteúdo ofensivo.

Se a resposta for "NÃO" (tema inválido), pare tudo e retorne EXATAMENTE este JSON:
{{ "erro": "Tema inadequado" }}

ETAPA 2: GERAÇÃO (Apenas se passou na Etapa 1)
Se o tema for VALIDAMENTE de Filosofia ou Sociologia, gere um JSON com 10 questões.

Estrutura obrigatória do JSON de sucesso:
{{
    "categoria": "Filosofia" ou "Sociologia",
    "questoes": [
        {{
            "pergunta": "Enunciado claro",
            "opcoes": ["A", "B", "C", "D"],
            "resposta_correta": "texto da opção correta",
            "explicacao": "Explicação breve"
        }}
    ]
}}

Retorne APENAS o JSON (de erro ou de sucesso). Sem markdown, sem ```.
"""
    
    try:
        key_manager = current_app.config['KEY_MANAGER']
        texto = generate_with_retry(key_manager, prompt, MODEL_NAME)
        
        if texto is None:
            return jsonify({"erro": "Não foi possível gerar o quiz após várias tentativas."}), 500
        
        # Limpeza básica caso a IA mande markdown
        texto = texto.replace("```json", "").replace("```", "").strip()
        
        # --- CORREÇÃO IMPORTANTE AQUI ---
        # Tenta ler o JSON para ver se a IA retornou o erro de inadequação
        try:
            json_response = json.loads(texto)
            if "erro" in json_response:
                return jsonify({"erro": "Tema inadequado. Por favor, insira um tema estritamente de Filosofia ou Sociologia."}), 400
        except json.JSONDecodeError:
            # Se não for JSON válido, segue o fluxo (pode ser erro da IA, mas não bloqueamos aqui)
            pass
        except Exception:
            pass
            
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
Analise o tema: '{tema}'.

REGRA ABSOLUTA DE BLOQUEIO:
Se este tema for sobre Matemática, Física, Química, Biologia, Esportes, Entretenimento, ou se contiver linguagem vulgar/obscena, PARE IMEDIATAMENTE.
Não tente encontrar "o lado filosófico" de um tema que não é filosofia (ex: não aceite "Filosofia da Geometria" ou "Sociologia do Neymar").

Se o tema for inválido, escreva APENAS: 
NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.

Se o tema for VÁLIDO (Filosofia ou Sociologia acadêmica), gere 12 flashcards seguindo o formato:
Pergunta: [pergunta] Resposta: [resposta curta]
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
Atue como um filtro acadêmico rigoroso. Tema solicitado: '{tema}'.

1. O tema é claramente parte do currículo de Filosofia ou Sociologia do Ensino Médio ou Superior?
2. O tema NÃO é de Exatas, Biológicas, Tecnológicas ou Cultura Pop?
3. O tema está livre de termos ofensivos ou obscenos?

Se a resposta para qualquer pergunta for "NÃO", retorne APENAS:
NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.

Se todas as respostas forem "SIM", gere um resumo acadêmico de 4 a 6 parágrafos sobre '{tema}'.
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
    prompt = f"""
Você é um corretor de provas de Filosofia e Sociologia.
Analise o tema: '{tema}' e o texto '{texto} do aluno.

CRITÉRIO DE REJEIÇÃO IMEDIATA:
1. Se o tema ou o texto tratarem de Matemática, Física, Biologia, Química ou assuntos do cotidiano sem base filosófica teórica, REJEITE.
2. Se houver linguagem obscena, REJEITE.

Em caso de rejeição, responda APENAS:
NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.

Caso contrário, forneça um feedback de até 3 parágrafos corrigindo conceitos filosóficos/sociológicos.
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