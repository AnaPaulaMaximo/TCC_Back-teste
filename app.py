from flask import Flask, session, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from dotenv import load_dotenv
import os
from uuid import uuid4
from flask import request


# --- Importar Config e Blueprints ---
from config import conn, cursor 
from auth_routes import auth_bp
from freemium_routes import freemium_bp
from premium_routes import premium_bp

# --- Configurações Iniciais ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "uma-chave-secreta-padrao-muito-forte")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuração Google GenAI ---
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("ERRO: A variável de ambiente GOOGLE_API_KEY não está definida.")
else:
    try:
        genai.configure(api_key=API_KEY)
        print(">>> Google GenAI configurado com sucesso.")
    except Exception as e:
        print(f">>> ERRO ao configurar Google GenAI: {e}")

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
instrucoes = """Você é um assistente de IA focado em ajudar estudantes com temas de filosofia e sociologia, de maneira didática e interativa."""
active_chats = {}

def get_user_chat():
    # Usa a sessão do Flask (criada no login) para identificar o usuário
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
    print(f"Cliente desconectado: {request.sid}")
    # Opcional: limpar o chat da memória se a sessão expirar
    session_id = session.pop('session_id', None)
    if session_id and session_id in active_chats:
        del active_chats[session_id]
        print(f"Chat da sessão {session_id} limpo.")


# --- Inicialização ---
if __name__ == "__main__":
    # Use a porta 5002, como no seu arquivo original
    socketio.run(app, host="0.0.0.0", port=5002, debug=True, allow_unsafe_werkzeug=True)