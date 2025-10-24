# Em app.py

from flask import Flask, session, jsonify, request # Garanta que request está importado
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from dotenv import load_dotenv
import os
from uuid import uuid4

# --- Importar Config e Blueprints ---
from config import conn, cursor
from auth_routes import auth_bp
from freemium_routes import freemium_bp
from premium_routes import premium_bp

# --- Configurações Iniciais ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "uma-chave-secreta-padrao-muito-forte")

# --- CORREÇÃO CORS ---
# Substitua a linha antiga por esta:
CORS(app,
     # Lista as origens permitidas (seu front-end)
     origins=["http://127.0.0.1:5501", "http://localhost:5501"],
     supports_credentials=True) # Mantém o suporte a credenciais

socketio = SocketIO(app, cors_allowed_origins=["http://127.0.0.1:5501", "http://localhost:5501"]) # Ajuste aqui também para o SocketIO

# --- Configuração Google GenAI ---
# ... (resto do código GenAI) ...
API_KEY = os.getenv("GOOGLE_API_KEY")
# ... (código restante GenAI) ...
MODEL_NAME = "gemini-1.5-flash"

# --- Registrar Blueprints (Rotas Separadas) ---
app.register_blueprint(auth_bp)
app.register_blueprint(freemium_bp)
app.register_blueprint(premium_bp)

# --- Rota Principal (Teste) ---
@app.route('/')
def index():
    return 'API ON - Estrutura Refatorada', 200

# ===================================
# Chatbot com SocketIO (Acesso para todos os planos)
# ===================================
# ... (código do chatbot) ...
instrucoes = """Você é um assistente de IA focado em ajudar estudantes com temas de filosofia e sociologia, de maneira didática e interativa."""
active_chats = {}

def get_user_chat():
    # ... (código get_user_chat) ...
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
    session_id = session['session_id']
    if session_id not in active_chats:
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            chat_session = model.start_chat(history=[
                {"role": "user", "parts": [{"text": instrucoes}]},
                {"role": "model", "parts": [{"text": "Olá! Sou seu assistente de estudos em Filosofia e Sociologia. Como posso ajudar você hoje?"}]}
            ])
            active_chats[session_id] = chat_session
        except Exception as e:
            print(f"Erro ao iniciar chat da IA: {e}")
            return None
    return active_chats[session_id]


@socketio.on('connect')
def handle_connect():
    # ... (código handle_connect) ...
     print(f"Cliente conectado: {request.sid}")
     user_chat = get_user_chat()
     if user_chat:
        welcome_message = user_chat.history[-1].parts[0].text
        emit('nova_mensagem', {"remetente": "bot", "texto": welcome_message})
     else:
        emit('erro', {'erro': 'Não foi possível iniciar o assistente de IA.'})
     emit('status_conexao', {'data': 'Conectado com sucesso!'})


@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    # ... (código handle_enviar_mensagem) ...
     mensagem_usuario = data.get("mensagem")
     if not mensagem_usuario:
        emit('erro', {"erro": "Mensagem não pode ser vazia."})
        return
     try:
        user_chat = get_user_chat()
        if not user_chat:
            emit('erro', {'erro': 'Chat não iniciado. Tente reconectar.'})
            return
        resposta = user_chat.send_message(mensagem_usuario)
        emit('nova_mensagem', {"remetente": "bot", "texto": resposta.text})
     except Exception as e:
        print(f"Erro na IA: {e}")
        emit('erro', {'erro': f'Ocorreu um erro na IA. Tente novamente.'})

@socketio.on('disconnect')
def handle_disconnect():
    # ... (código handle_disconnect) ...
    print(f"Cliente desconectado: {request.sid}")
    session_id = session.pop('session_id', None)
    if session_id and session_id in active_chats:
        del active_chats[session_id]
        print(f"Chat da sessão {session_id} limpo.")

# --- Inicialização ---
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5002, debug=True, allow_unsafe_werkzeug=True)