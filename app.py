from flask import Flask, session, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from dotenv import load_dotenv
import os
from uuid import uuid4
from datetime import timedelta

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

# 1. Configuração DE SESSÃO para funcionar na Nuvem
app.secret_key = os.getenv("SECRET_KEY", "sua_chave_secreta_super_segura")

# ===== CONFIGURAÇÕES IMPORTANTES DE SESSÃO =====
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Permite cookies cross-site
app.config['SESSION_COOKIE_SECURE'] = True       # HTTPS obrigatório
app.config['SESSION_COOKIE_HTTPONLY'] = True     # Proteção contra XSS
app.config['SESSION_COOKIE_PATH'] = '/'          # Disponível em toda a aplicação
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessão dura 7 dias
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Renova a sessão a cada request

# 2. Configuração do CORS (Atualizada com suas URLs)
ALLOWED_ORIGINS = [
    "https://tcc-frontend-nine.vercel.app",
    "https://tcc-frontend-repensei.vercel.app",
    "https://tcc-frontend-git-main-anas-projects-d45e7b2d.vercel.app",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501"
]

CORS(app, 
     supports_credentials=True,
     origins=ALLOWED_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     expose_headers=["Content-Type", "Authorization"],
     max_age=3600  # Cache preflight por 1 hora
)

# 3. Inicialização do SocketIO
socketio = SocketIO(app, 
                    cors_allowed_origins=ALLOWED_ORIGINS,
                    ping_timeout=60,
                    ping_interval=25,
                    async_mode='eventlet')

# --- INICIALIZA O GERENCIADOR DE CHAVES ---
print("\n🔐 Inicializando Gerenciador de Chaves API...")
key_manager = APIKeyManager()

if not key_manager.keys_data.get('keys'):
    print("\n⚠️ Nenhuma chave configurada!")
else:
    key_manager.get_status()

# --- Configuração Google GenAI ---
MODEL_NAME = "gemini-2.5-flash"
app.config['KEY_MANAGER'] = key_manager

# --- Registrar Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(freemium_bp)
app.register_blueprint(premium_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(quiz_bp)

# --- Middleware para debug de sessão (remover em produção) ---
@app.before_request
def log_session():
    """Log da sessão para debug"""
    if request.endpoint and not request.endpoint.startswith('static'):
        print(f"🔍 Request: {request.method} {request.path}")
        print(f"   Sessão ativa: {bool(session)}")
        if session:
            print(f"   Conteúdo: {dict(session)}")

# --- Rota Principal ---
@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'message': 'API TCC Backend Rodando com SocketIO',
        'version': '2.0',
        'endpoints': {
            'auth': '/auth/*',
            'freemium': '/freemium/*',
            'premium': '/premium/*',
            'admin': '/admin/*',
            'quiz': '/quiz/*'
        }
    }), 200

# --- Rota de Health Check ---
@app.route('/health')
def health_check():
    """Health check para monitoramento"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if conn else 'disconnected',
        'keys_configured': len(key_manager.keys_data.get('keys', []))
    }), 200

# --- Rota para verificar status das chaves (Admin) ---
@app.route('/api/keys/status', methods=['GET'])
def api_keys_status():
    key_manager.get_status()
    status_data = {
        "total_keys": len(key_manager.keys_data['keys']),
        "current_key": key_manager.keys_data['keys'][key_manager.current_key_index]['name'],
        "keys": [{"name": k['name'], "active": k['active'], "error_count": k['error_count']} for k in key_manager.keys_data['keys']]
    }
    return jsonify(status_data), 200

# --- Rota para rotacionar manualmente (Admin) ---
@app.route('/api/keys/rotate', methods=['POST'])
def rotate_key_manual():
    success = key_manager.rotate_key(reason="Rotação manual via API")
    if success:
        return jsonify({"message": "Chave rotacionada com sucesso"}), 200
    else:
        return jsonify({"error": "Falha ao rotacionar chave"}), 500

# ===================================
# Chatbot com SocketIO
# ===================================

instrucoes = """Você é um tutor de Filosofia e Sociologia. Seu objetivo não é dar respostas prontas, mas sim gerar uma conversa real que faça o usuário pensar. Aja como um parceiro de debate. 
Em vez de simplesmente responder, faça perguntas de volta, desafie as premissas do usuário e incentive-o a explorar diferentes ângulos de um mesmo tema.
Use uma linguagem natural e acessível."""

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
            print(f"✅ Novo chat iniciado para sessão: {session_id}")
        except Exception as e:
            print(f"❌ Erro ao iniciar chat da IA para sessão {session_id}: {e}")
            return None

    return active_chats.get(session_id)

@socketio.on('connect')
def handle_connect():
    print(f"🔌 Cliente conectado: {request.sid}")
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
    
    user_chat = get_user_chat()
    if user_chat:
        welcome_message = "Olá! Vamos debater filosofia ou sociologia?"
        # Tenta pegar a última mensagem do modelo se existir
        if user_chat.history and len(user_chat.history) > 0:
             last_msg = user_chat.history[-1]
             if last_msg.role == 'model':
                 welcome_message = last_msg.parts[0].text

        emit('nova_mensagem', {"remetente": "bot", "texto": welcome_message})
        emit('status_conexao', {'data': 'Conectado com sucesso!'})
    else:
        emit('erro', {'erro': 'Não foi possível iniciar o assistente de IA.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    mensagem_usuario = data.get("mensagem")
    print(f"📨 Mensagem recebida: {mensagem_usuario}")
    
    if not mensagem_usuario:
        return

    user_chat = get_user_chat()
    if not user_chat:
        emit('erro', {'erro': 'Sessão perdida. Recarregue a página.'})
        return

    try:
        resposta = user_chat.send_message(mensagem_usuario)
        emit('nova_mensagem', {"remetente": "bot", "texto": resposta.text})
    except Exception as e:
        print(f"❌ Erro GenAI: {e}")
        if key_manager.handle_api_error(e):
             emit('erro', {'erro': 'Limite atingido, trocando chave... Tente novamente em alguns segundos.'})
        else:
             emit('erro', {'erro': 'Erro ao processar mensagem.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"🔌 Cliente desconectado: {request.sid}")

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Erro interno do servidor', 'details': str(e)}), 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True, allow_unsafe_werkzeug=True)