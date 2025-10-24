from flask import Blueprint, request, jsonify
from utils import carregar_dados_json, get_user_plan
import random

# Cria um Blueprint para rotas freemium
# O front-end chamará, por exemplo, /freemium/quiz
freemium_bp = Blueprint('freemium_bp', __name__, url_prefix='/freemium')

@freemium_bp.route('/quiz', methods=['POST'])
def quiz_freemium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')
    
    if not id_aluno:
        return jsonify({'error': 'ID do aluno é obrigatório.'}), 400

    # Verificamos o plano. Embora o front-end deva direcionar,
    # esta é uma verificação de segurança.
    plano_usuario = get_user_plan(id_aluno)
    if plano_usuario != 'freemium':
        return jsonify({'error': 'Rota inválida para seu plano.'}), 403

    # Lógica específica do Freemium (usando JSON)
    categoria = data.get('category', 'ambos')
    
    # Carrega do 'questions.json'
    todas_as_perguntas = carregar_dados_json('questions.json')
    
    if not todas_as_perguntas:
         return jsonify({'error': 'Não foi possível carregar as perguntas.'}), 500

    perguntas_filtradas = []
    if categoria == 'ambos':
        perguntas_filosofia = [p for p in todas_as_perguntas if p.get('category') == 'filosofia']
        perguntas_sociologia = [p for p in todas_as_perguntas if p.get('category') == 'sociologia']
        random.shuffle(perguntas_filosofia)
        random.shuffle(perguntas_sociologia)
        perguntas_filtradas.extend(perguntas_filosofia[:5])
        perguntas_filtradas.extend(perguntas_sociologia[:5])
    else:
        perguntas_filtradas = [p for p in todas_as_perguntas if p.get('category') == categoria]

    random.shuffle(perguntas_filtradas)
    return jsonify(perguntas_filtradas[:10])


@freemium_bp.route('/flashcard', methods=['POST'])
def flashcard_freemium():
    data = request.get_json()
    id_aluno = data.get('id_aluno')

    if not id_aluno:
        return jsonify({'error': 'ID do aluno é obrigatório.'}), 400
        
    plano_usuario = get_user_plan(id_aluno)
    if plano_usuario != 'freemium':
        return jsonify({'error': 'Rota inválida para seu plano.'}), 403

    # Lógica específica do Freemium (usando JSON)
    categoria = data.get('category', 'ambos')
    
    # Carrega do 'flashcards.json'
    todos_flashcards = carregar_dados_json('flashcards.json')
    
    if not todos_flashcards:
        return jsonify({'error': 'Não foi possível carregar os flashcards.'}), 500
    
    flashcards_filtrados = []
    if categoria == 'ambos':
        flashcards_filosofia = [f for f in todos_flashcards if f.get('category') == 'filosofia']
        flashcards_sociologia = [f for f in todos_flashcards if f.get('category') == 'sociologia']
        random.shuffle(flashcards_filosofia)
        random.shuffle(flashcards_sociologia)
        flashcards_filtrados.extend(flashcards_filosofia[:4])
        flashcards_filtrados.extend(flashcards_sociologia[:4])
    else:
        flashcards_filtrados = [f for f in todos_flashcards if f.get('category') == categoria]
    
    random.shuffle(flashcards_filtrados)
    return jsonify(flashcards_filtrados[:8])