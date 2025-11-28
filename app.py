from flask import Flask, session, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from dotenv import load_dotenv
import os
from uuid import uuid4

# --- IMPORTAÇÃO DO GERENCIADOR DE CHAVES ---
from api_key_manager import APIKeyManager, generate_with_retry

# --- Importar Config e Blueprints ---
from config import conn, cursor
from auth_routes import auth_bp
from freemium_routes import freemium_bp
from premium_routes import premium_bp
from admin_routes import admin_bp
from quiz_routes import quiz_bp

# --- Configurações Iniciais ---
load_dotenv()
app = Flask(__name__)
# 1. Configuração SUPER IMPORTANTE da Sessão para funcionar na Nuvem
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui')
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  
app.config['SESSION_COOKIE_SECURE'] = True      

CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": [
            "https://tcc-frontend-nine.vercel.app", # Coloque AQUI o link do seu Frontend na Vercel
            "http://localhost:5500",                  # Para funcionar nos seus testes locais
            "http://127.0.0.1:5500"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# --- INICIALIZA O GERENCIADOR DE CHAVES ---
print("\n🔐 Inicializando Gerenciador de Chaves API...")
key_manager = APIKeyManager()

# Verifica se precisa adicionar chaves (primeira execução)
if not key_manager.keys_data.get('keys'):
    print("\n⚠️ Nenhuma chave configurada!")
    print("📝 Execute o script de configuração:")
    print("   python setup_keys.py")
    print("\n   Ou adicione manualmente:")
    print("   from api_key_manager import APIKeyManager")
    print("   manager = APIKeyManager()")
    print("   manager.add_key('SUA_CHAVE_1', 'chave_principal')")
    print("   manager.add_key('SUA_CHAVE_2', 'chave_backup')\n")
else:
    key_manager.get_status()

# --- Configuração Google GenAI (agora gerenciada pelo APIKeyManager) ---
MODEL_NAME = "gemini-2.5-flash"

# --- Disponibiliza o key_manager globalmente para as rotas ---
app.config['KEY_MANAGER'] = key_manager

# --- Registrar Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(freemium_bp)
app.register_blueprint(premium_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(quiz_bp)

# --- Rota Principal ---
@app.route('/')
def index():
    return 'API ON - Estrutura Refatorada com Gerenciamento de Chaves', 200

# --- Rota para verificar status das chaves (Admin) ---
@app.route('/api/keys/status', methods=['GET'])
def api_keys_status():
    """Endpoint para verificar o status das chaves (use com cautela em produção)"""
    # Em produção, adicione autenticação aqui!
    key_manager.get_status()
    
    status_data = {
        "total_keys": len(key_manager.keys_data['keys']),
        "current_key": key_manager.keys_data['keys'][key_manager.current_key_index]['name'],
        "last_rotation": key_manager.keys_data.get('last_rotation'),
        "keys": [
            {
                "name": k['name'],
                "active": k['active'],
                "error_count": k['error_count'],
                "last_error": k['last_error']
            }
            for k in key_manager.keys_data['keys']
        ]
    }
    
    return jsonify(status_data), 200

# --- Rota para rotacionar manualmente (Admin) ---
@app.route('/api/keys/rotate', methods=['POST'])
def rotate_key_manual():
    """Endpoint para forçar rotação de chave"""
    # Em produção, adicione autenticação aqui!
    success = key_manager.rotate_key(reason="Rotação manual via API")
    
    if success:
        return jsonify({"message": "Chave rotacionada com sucesso"}), 200
    else:
        return jsonify({"error": "Falha ao rotacionar chave"}), 500

# ===================================
# Chatbot com SocketIO (MODIFICADO)
# ===================================

instrucoes = """Você é um tutor de Filosofia e Sociologia. Seu objetivo não é dar respostas prontas, mas sim gerar uma conversa real que faça o usuário pensar. Aja como um parceiro de debate. 

Em vez de simplesmente responder, faça perguntas de volta, desafie as premissas do usuário e incentive-o a explorar diferentes ângulos de um mesmo tema. Conduza a conversa para fora da zona de conforto, estimulando o pensamento crítico e a reflexão profunda. 

Use uma linguagem natural e acessível, como se fosse uma pessoa conversando. O objetivo é que o usuário sinta que está em um diálogo genuíno, não em um interrogatório.
"""

active_chats = {}

def get_user_chat():
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
    session_id = session['session_id']

    if session_id not in active_chats:
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            chat_session = model.start_chat(history=[
                {"role": "user", "parts": [{"text": instrucoes}]},
                {"role": "model", "parts": [{"text": "Olá! Estou aqui para bater um papo sobre filosofia e sociologia. Sobre o que você gostaria de conversar hoje?"}]}
            ])
            active_chats[session_id] = chat_session
            print(f"Novo chat iniciado para sessão: {session_id}")
        except Exception as e:
            print(f"Erro ao iniciar chat da IA para sessão {session_id}: {e}")
            return None

    return active_chats.get(session_id)

@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
        print(f"Nova session_id criada na conexão: {session['session_id']}")

    user_chat = get_user_chat()
    if user_chat and user_chat.history:
        welcome_message = "Olá! Estou aqui para bater um papo sobre filosofia e sociologia. Sobre o que você gostaria de conversar hoje?"
        if user_chat.history and len(user_chat.history) > 1 and user_chat.history[-1].role == 'model':
            welcome_message = user_chat.history[-1].parts[0].text
        elif user_chat.history and user_chat.history[1].role == 'model':
            welcome_message = user_chat.history[1].parts[0].text

        emit('nova_mensagem', {"remetente": "bot", "texto": welcome_message})
        emit('status_conexao', {'data': 'Conectado com sucesso!'})
    else:
        emit('erro', {'erro': 'Não foi possível iniciar o assistente de IA.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    mensagem_usuario = data.get("mensagem")
    print(f"Mensagem recebida de {request.sid}: {mensagem_usuario}")
    
    if not mensagem_usuario:
        emit('erro', {"erro": "Mensagem não pode ser vazia."})
        return

    user_chat = get_user_chat()
    if not user_chat:
        print(f"Erro: Chat não encontrado para session_id: {session.get('session_id')}")
        emit('erro', {'erro': 'Chat não iniciado ou sessão perdida. Tente reconectar.'})
        return

    try:
        print(f"Enviando para IA (sessão {session.get('session_id')}): {mensagem_usuario}")
        resposta = user_chat.send_message(mensagem_usuario)
        print(f"Resposta da IA (sessão {session.get('session_id')}): {resposta.text[:50]}...")
        emit('nova_mensagem', {"remetente": "bot", "texto": resposta.text})
    
    except Exception as e:
        print(f"Erro na chamada da API GenAI (sessão {session.get('session_id')}): {e}")
        
        # --- TENTA ROTACIONAR A CHAVE ---
        if key_manager.handle_api_error(e):
            emit('erro', {'erro': 'Limite de API atingido. Tentando com outra chave... Por favor, envie sua mensagem novamente.'})
        else:
            emit('erro', {'erro': 'Ocorreu um erro ao processar sua mensagem com a IA. Tente novamente.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}")
    session_id = session.get('session_id')
    if session_id and session_id in active_chats:
        del active_chats[session_id]
        print(f"Chat da sessão {session_id} limpo.")

# --- Inicialização ---
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Iniciando servidor Flask com SocketIO...")
    print("="*60)
    key_manager.get_status()
    print("="*60 + "\n")
    
    socketio.run(app, host="0.0.0.0", debug=True, allow_unsafe_werkzeug=True)