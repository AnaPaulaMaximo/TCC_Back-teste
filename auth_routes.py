from flask import Blueprint, request, jsonify, session
from mysql.connector import IntegrityError
from config import conn, cursor

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

    cursor.execute('SELECT id_aluno, nome, email, plano, url_foto FROM Aluno WHERE email = %s AND senha = %s', (email, senha))
    usuario = cursor.fetchone()

    if usuario:
        # Armazena dados na sessão para uso futuro (ex: chatbot)
        session['id_aluno'] = usuario['id_aluno']
        session['plano'] = usuario['plano']
        # Retorna o usuário completo, incluindo o 'plano'
        # O front-end deve ler 'user.plano' para decidir quais rotas chamar
        return jsonify({'message': 'Login realizado com sucesso!', 'user': usuario}), 200
    else:
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
        # Novos usuários começam como 'freemium' por padrão (conforme seu DB)
        cursor.execute('INSERT INTO Aluno (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, senha))
        conn.commit()
        return jsonify({'message': 'Usuário cadastrado com sucesso.'}), 201
    except IntegrityError:
        return jsonify({'error': 'Email já cadastrado.'}), 400

@auth_bp.route('/editar_usuario/<int:id_aluno>', methods=['PUT'])
def editar_usuario(id_aluno):
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    url_foto = data.get('url_foto')

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    campos = []
    valores = []

    if nome:
        campos.append("nome=%s")
        valores.append(nome)
    if email:
        campos.append("email=%s")
        valores.append(email)
    if senha:
        campos.append("senha=%s")
        valores.append(senha)
    if url_foto is not None:
        campos.append("url_foto=%s")
        valores.append(url_foto)

    if not campos:
        return jsonify({'error': 'Nenhum campo para atualizar.'}), 400

    query = f"UPDATE Aluno SET {', '.join(campos)} WHERE id_aluno=%s"
    valores.append(id_aluno)

    cursor.execute(query, tuple(valores))
    conn.commit()

    if cursor.rowcount == 0:
        return jsonify({'error': 'Usuário não encontrado.'}), 404

    return jsonify({'message': 'Usuário atualizado com sucesso.'})

@auth_bp.route('/excluir_usuario/<int:id_aluno>', methods=['DELETE'])
def excluir_usuario(id_aluno):
    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500
        
    cursor.execute('DELETE FROM Aluno WHERE id_aluno=%s', (id_aluno,))
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
    return jsonify(usuarios)