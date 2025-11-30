from flask import Flask, session, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from dotenv import load_dotenv
import os
from uuid import uuid4
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

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
app = Flask(__name__, static_folder='static', static_url_path='/static')

# ============================================================
# 🔥 CORREÇÃO CRÍTICA: CONFIGURAÇÃO DE SESSÃO PARA O RENDER
# ============================================================

app.secret_key = os.getenv("SECRET_KEY", "sua_chave_secreta_super_segura")

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Isso diz ao Flask para confiar nos cabeçalhos HTTPS do Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ... (resto do código de configuração de sessão) ...

# 🔥 DETECTAR SE ESTÁ EM PRODUÇÃO (RENDER)
IS_PRODUCTION = os.getenv('RENDER') is not None or os.getenv('RENDER_SERVICE_NAME') is not None


if IS_PRODUCTION:
    print("🚀 MODO PRODUÇÃO (RENDER) - Configuração de cookies ajustada")
    
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "sua_chave_secreta_super_segura")
    
    # Configurações para garantir que o cookie persista no mobile
    app.config['SESSION_COOKIE_SAMESITE'] = 'None' 
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_DOMAIN'] = None # Deixe None no Render
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['SESSION_PROXY'] = True # Importante
    
else:
    print("💻 MODO DESENVOLVIMENTO (LOCAL)")
    
    # Para desenvolvimento local
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False     
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_PATH'] = '/'

# Configurações comuns
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_TYPE'] = 'filesystem'

# ============================================================
# 🔥 CONFIGURAÇÃO DE CORS PARA O RENDER
# ============================================================

if IS_PRODUCTION:
    ALLOWED_ORIGINS = [
        "https://repensei.onrender.com",
    ]
else:
    ALLOWED_ORIGINS = [
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
     expose_headers=["Content-Type", "Authorization", "Set-Cookie"],
     max_age=3600
)

# ============================================================
# SOCKETIO
# ============================================================

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

# ============================================================
# 🔥 ROTA PRINCIPAL - CORRIGIDA PARA SERVIR login.html
# ============================================================

@app.route('/')
def index():
    """Redireciona para a página de login"""
    return app.send_static_file('login.html')

# ============================================================
# 🔥 ROTA EXPLÍCITA PARA /login.html
# ============================================================

@app.route('/login.html')
def login_page():
    """Serve explicitamente o login.html"""
    return app.send_static_file('login.html')

# ============================================================
# ROTAS DE SAÚDE
# ============================================================

@app.route('/health')
def health_check():
    """Health check para monitoramento"""
    return jsonify({
        'status': 'healthy',
        'environment': 'production' if IS_PRODUCTION else 'development',
        'database': 'connected' if conn else 'disconnected',
        'keys_configured': len(key_manager.keys_data.get('keys', [])),
        'session_config': {
            'samesite': app.config['SESSION_COOKIE_SAMESITE'],
            'secure': app.config['SESSION_COOKIE_SECURE'],
            'httponly': app.config['SESSION_COOKIE_HTTPONLY']
        }
    }), 200

@app.route('/api/session-test')
def session_test():
    """Testa se a sessão está funcionando"""
    if 'test_count' not in session:
        session['test_count'] = 0
    session['test_count'] += 1
    
    return jsonify({
        'session_working': True,
        'test_count': session['test_count'],
        'session_id': request.cookies.get('session'),
        'cookies': list(request.cookies.keys())
    }), 200

# ============================================================
# ROTAS DE ADMIN (Chaves API)
# ============================================================

@app.route('/api/keys/status', methods=['GET'])
def api_keys_status():
    key_manager.get_status()
    status_data = {
        "total_keys": len(key_manager.keys_data['keys']),
        "current_key": key_manager.keys_data['keys'][key_manager.current_key_index]['name'],
        "keys": [{"name": k['name'], "active": k['active'], "error_count": k['error_count']} for k in key_manager.keys_data['keys']]
    }
    return jsonify(status_data), 200

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

instrucoes = """*** IDENTIDADE E PROTOCOLOS: TUTOR SOCRÁTICO DE HUMANIDADES ***

VOCÊ É: Um mentor de Filosofia e Sociologia que utiliza o Método Socrático (Maiêutica).
SEU OBJETIVO: Não entregar respostas, mas "parir" ideias. Você deve desafiar as premissas do usuário, apontar contradições lógicas e expandir o horizonte do debate.

---

### REGRAS RIGÍDAS DE ESCOPO (SEGURANÇA):

1. **VETO TEMÁTICO (Fique na sua raia):**
   - Você SÓ debate temas sob a ótica da Filosofia ou Sociologia.
   - Se o usuário trouxer um tema de Ciências Exatas ou Biológicas (ex: "Como calcular a hipotenusa?" ou "Como funciona a mitose?"), você deve **RECUSAR** a explicação técnica e tentar (se possível) puxar para a ética ou epistemologia.
   - *Exemplo de Recusa:* "Não sou um professor de Matemática, mas podemos discutir a lógica por trás desse conceito ou como a verdade matemática difere da verdade moral. O que você acha?"
   - Se não houver gancho filosófico claro, diga: "Esse tema foge do meu campo de estudo (Humanidades). Vamos focar em algo social ou filosófico?"

2. **ANTI-ALUCINAÇÃO E "PSEUDO-FILOSOFIA":**
   - Não aceite debates sobre "Filosofia de [Coisa Aleatória]" (ex: "Filosofia da Geometria Plana" ou "Sociologia do Motor V8") a menos que seja um campo acadêmico real.
   - Se o usuário tentar inventar uma disciplina, corte gentilmente: "Isso parece mais uma questão técnica do que filosófica. Vamos reformular?"

3. **FILTRO DE LINGUAGEM E DECÊNCIA:**
   - Se o usuário usar temas vulgares, obscenos ou de baixo calão (mesmo que tente disfarçar de "Sociologia do..."), encerre o tópico imediatamente. Diga: "Não acredito que esse tema seja produtivo para um debate acadêmico sério."

---

### ESTILO DE INTERAÇÃO (O "COMO"):

1. **Postura de Debate:** Aja como um parceiro intelectual, não como uma enciclopédia. Use linguagem natural, acessível, mas instigante.
2. **A Técnica da Pergunta:** Para cada afirmação do usuário, devolva uma pergunta que o faça questionar a origem daquela ideia.
   - *Usuário:* "O ser humano é mau por natureza."
   - *Você:* "Interessante. Mas se isso fosse uma verdade absoluta, como você explicaria o altruísmo ou o sacrifício? Hobbes estaria certo, ou Rousseau deixou passar algo?"
3. **Desafio Construtivo:** Se o argumento do usuário for fraco ou falacioso, aponte a falha gentilmente e peça para ele defender melhor o ponto.

---

RESUMO OPERACIONAL: Mantenha o usuário pensando. Mantenha o foco em Humanidades. Bloqueie desvios técnicos ou inapropriados."""

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