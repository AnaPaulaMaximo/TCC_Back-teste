from flask import Blueprint, request, jsonify
from utils import get_user_plan
import google.generativeai as genai
import os

# Cria um Blueprint para rotas premium
# O front-end chamará, por exemplo, /premium/quiz
premium_bp = Blueprint('premium_bp', __name__, url_prefix='/premium')

# O modelo é configurado no app.py principal, aqui apenas usamos
MODEL_NAME = "gemini-2.5-flash" 

# Função de verificação de segurança
def check_premium_access(id_aluno):
    if not id_aluno:
        return jsonify({'error': 'ID do aluno é obrigatório.'}), 400
    if get_user_plan(id_aluno) != 'premium':
        return jsonify({'error': 'Esta funcionalidade é exclusiva para usuários Premium.'}), 403
    return None

@premium_bp.route('/quiz', methods=['POST'])
def quiz_premium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')
    
    # Verifica se o usuário é premium
    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error

    # Lógica específica do Premium (usando IA)
    if 'tema' not in data:
        return jsonify({'error': 'O campo "tema" é obrigatório para usuários Premium.'}), 400
    
    tema = data['tema']
    prompt = f"""Dado o tema '{tema}', primeiro avalie se ele é estritamente relacionado a filosofia ou sociologia e se não contém conteúdo preconceituoso, sexual, violento ou inadequado de qualquer tipo.

Se o tema for válido, gere um quiz com 10 questões sobre ele. Retorne as questões **APENAS** em formato JSON, sem qualquer texto adicional, formatação Markdown de blocos de código ou outros caracteres fora do JSON. Cada questão deve ser um objeto com as seguintes chaves:
- "pergunta": (string) O texto da pergunta.
- "opcoes": (array de strings) Um array com 4 opções de resposta.
- "resposta_correta": (string) O texto exato de uma das opções.
- "explicacao": (string) Uma breve explicação (1-2 frases) do porquê a resposta correta está certa.
**as quetões devem ser variadas de um quiz para outro, evite repetir as mesmas perguntas.

Se o tema for inválido, retorne **APENAS** a mensagem: NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.
"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        texto = response.text.strip()
        # Retorna o texto bruto para o front-end processar
        return jsonify({"assunto": tema, "contedo": texto})
    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar quiz com IA: {str(e)}"}), 500


@premium_bp.route('/flashcard', methods=['POST'])
def flashcard_premium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')

    auth_error = check_premium_access(id_aluno)
    if auth_error:
        return auth_error

    # Lógica específica do Premium (usando IA)
    if 'tema' not in data:
        return jsonify({'error': 'O campo "tema" é obrigatório para usuários Premium.'}), 400
    
    tema = data['tema']
    prompt = f"""
Dado o tema '{tema}', primeiro avalie se ele é estritamente relacionado a filosofia ou sociologia e se não contém conteúdo inadequado.

Se o tema for válido, Gere 12 perguntas para flashcards sobre o tema '{tema}'. Retorne a pergunta e a resposta correta, a resposta deve ser breve e acertiva. Estrutura: Pergunta: [pergunta] Resposta: [resposta]

Se o tema for inválido, retorne **APENAS** a mensagem: NÃO É POSSIVEL FORMAR UMA RESPOSTA DEVIDO A INADEQUAÇÃO DO ASSUNTO.
"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        texto = response.text.strip()
        return jsonify({"assunto": tema, "contedo": texto})
    except Exception as e:
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
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        texto = response.text.strip()
        return jsonify({"assunto": tema, "conteudo": texto})
    except Exception as e:
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
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        texto_corrigido = response.text.strip()
        return jsonify({"texto_original": texto, "correcao": texto_corrigido})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500