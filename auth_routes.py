from flask import Blueprint, request, jsonify, session
from mysql.connector import IntegrityError # Pode manter, mas o erro do SQLite é sqlite3.IntegrityError
from config import conn, cursor
import sqlite3 # Importe para capturar o erro específico

# Cria um Blueprint para rotas de autenticação
# O front-end chamará, por exemplo, /auth/login
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios.'}), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    # --- INÍCIO DA LÓGICA DE LOGIN UNIFICADO ---
    
    # 1. Tenta fazer login como Administrador primeiro
    cursor.execute('SELECT id_admin, nome, email FROM Admin WHERE email = ? AND senha = ?', (email, senha))
    admin = cursor.fetchone()
    
    if admin:
        # É um admin! Limpa qualquer sessão de aluno antiga
        session.pop('id_aluno', None)
        session.pop('plano', None)
        
        # Cria a sessão de admin
        session['admin_id'] = admin['id_admin']
        session['admin_nome'] = admin['nome']
        
        return jsonify({
            'message': 'Login de admin realizado com sucesso!', 
            'role': 'admin', 
            'user': dict(admin)
        }), 200

    # 2. Se não for admin, tenta fazer login como Aluno
    cursor.execute('SELECT id_aluno, nome, email, plano, url_foto FROM Aluno WHERE email = ? AND senha = ?', (email, senha))
    aluno = cursor.fetchone()

    if aluno:
        # É um aluno! Limpa qualquer sessão de admin antiga
        session.pop('admin_id', None)
        session.pop('admin_nome', None)

        # Cria a sessão de aluno
        session['id_aluno'] = aluno['id_aluno']
        session['plano'] = aluno['plano']
        
        return jsonify({
            'message': 'Login realizado com sucesso!', 
            'role': 'aluno', 
            'user': dict(aluno)
        }), 200

    # 3. Se não for nenhum dos dois, retorna erro
    return jsonify({'error': 'Email ou senha inválidos.'}), 401


@auth_bp.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    if not nome or not email or not senha:
        return jsonify({'error': 'Todos os campos são obrigatórios.'}), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    try:
        # Novos usuários começam como 'freemium' por padrão
        cursor.execute('INSERT INTO Aluno (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha))
        conn.commit()
        return jsonify({'message': 'Usuário cadastrado com sucesso.'}), 201
    except (IntegrityError, sqlite3.IntegrityError):
        return jsonify({'error': 'Email já cadastrado.'}), 400

@auth_bp.route('/editar_usuario/<int:id_aluno>', methods=['PUT'])
def editar_usuario(id_aluno):
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    url_foto = data.get('url_foto')
    
    # ===> MUDANÇA 1: Capturar o campo 'plano' <===
    plano = data.get('plano')

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    campos = []
    valores = []

    if nome:
        campos.append("nome=?")
        valores.append(nome)
    if email:
        campos.append("email=?")
        valores.append(email)
    if senha:
        campos.append("senha=?")
        valores.append(senha)
    if url_foto is not None:
        campos.append("url_foto=?")
        valores.append(url_foto)
    
    # ===> MUDANÇA 2: Adicionar 'plano' na query SQL se ele existir <===
    if plano:
        campos.append("plano=?")
        valores.append(plano)

    if not campos:
        return jsonify({'error': 'Nenhum campo para atualizar.'}), 400

    query = f"UPDATE Aluno SET {', '.join(campos)} WHERE id_aluno=?"
    valores.append(id_aluno)

    try:
        cursor.execute(query, tuple(valores))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Usuário não encontrado.'}), 404

        # ===> MUDANÇA 3: Atualizar a sessão IMEDIATAMENTE <===
        # Isso conserta o erro de "Acesso Negado" no histórico sem precisar relogar
        if 'id_aluno' in session and session['id_aluno'] == id_aluno:
            if plano:
                session['plano'] = plano
                print(f"✅ Sessão do usuário {id_aluno} atualizada para {plano}")

        return jsonify({'message': 'Usuário atualizado com sucesso.'})
    
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar: {str(e)}'}), 500

@auth_bp.route('/excluir_usuario/<int:id_aluno>', methods=['DELETE'])
def excluir_usuario(id_aluno):
    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500
        
    cursor.execute('DELETE FROM Aluno WHERE id_aluno=?', (id_aluno,))
    conn.commit()
    if cursor.rowcount == 0:
        return jsonify({'error': 'Usuário não encontrado.'}), 404
    return jsonify({'message': 'Usuário excluído com sucesso.'})

@auth_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500
        
    cursor.execute('SELECT id_aluno, nome, email, url_foto, plano FROM Aluno')
    usuarios = cursor.fetchall()
    return jsonify([dict(u) for u in usuarios])