from flask import Blueprint, request, jsonify, session
from config import conn, cursor
import sqlite3
import re

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

# ===================================================================
# FUNÇÕES DE VALIDAÇÃO (mantidas)
# ===================================================================

def validar_email(email):
    if not email or len(email.strip()) == 0:
        return False, "E-mail é obrigatório"
    
    email = email.strip().lower()
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(regex, email):
        return False, "Formato de e-mail inválido"
    
    if len(email) > 100:
        return False, "E-mail muito longo (máximo 100 caracteres)"
    
    return True, None

def email_ja_existe(email):
    try:
        cursor.execute('SELECT id_aluno FROM Aluno WHERE email = ?', (email.lower(),))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Erro ao verificar e-mail: {e}")
        return False

def validar_senha(senha):
    erros = []
    
    if not senha:
        return False, ["Senha é obrigatória"]
    
    if len(senha) < 8:
        erros.append("A senha deve ter no mínimo 8 caracteres")
    
    if len(senha) > 128:
        erros.append("A senha deve ter no máximo 128 caracteres")
    
    if not re.search(r'[A-Z]', senha):
        erros.append("Deve conter pelo menos uma letra maiúscula")
    
    if not re.search(r'[a-z]', senha):
        erros.append("Deve conter pelo menos uma letra minúscula")
    
    if not re.search(r'[0-9]', senha):
        erros.append("Deve conter pelo menos um número")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', senha):
        erros.append("Deve conter pelo menos um caractere especial (!@#$%&*)")
    
    senhas_comuns = [
        '123456', '123456789', 'qwerty', 'password', '12345678',
        '111111', '123123', '1234567890', '1234567', 'senha',
        'senha123', 'admin', 'admin123', 'root', '12345',
        'password123', 'abc123', '1q2w3e4r', 'qwerty123', 'letmein'
    ]
    
    if senha.lower() in senhas_comuns:
        erros.append("Esta senha é muito comum. Escolha uma senha mais segura")
    
    if re.search(r'(.)\1{2,}', senha):
        erros.append("Evite repetir o mesmo caractere mais de 2 vezes seguidas")
    
    return len(erros) == 0, erros

def validar_nome(nome):
    if not nome or len(nome.strip()) == 0:
        return False, None, "Nome é obrigatório"
    
    nome = nome.strip()
    
    if len(nome) < 3:
        return False, None, "O nome deve ter no mínimo 3 caracteres"
    
    if len(nome) > 100:
        return False, None, "O nome deve ter no máximo 100 caracteres"
    
    partes = [p for p in nome.split(' ') if len(p) > 0]
    if len(partes) < 2:
        return False, None, "Por favor, digite nome e sobrenome completos"
    
    if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', nome):
        return False, None, "O nome deve conter apenas letras"
    
    nome_formatado = ' '.join([p.capitalize() for p in partes])
    
    return True, nome_formatado, None

# ===================================================================
# ROTA DE LOGIN - CORRIGIDA
# ===================================================================

@auth_bp.route('/login', methods=['POST'])
def login():
    # 🔥 CORREÇÃO 1: Limpar sessão ANTES de processar
    session.clear()
    
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios.'}), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    email = email.strip().lower()

    # 🔥 CORREÇÃO 2: Tentar login como ALUNO primeiro (mais comum)
    cursor.execute('SELECT id_aluno, nome, email, plano, url_foto FROM Aluno WHERE email = ? AND senha = ?', (email, senha))
    aluno = cursor.fetchone()

    if aluno:
        # Login de aluno bem-sucedido
        session['id_aluno'] = aluno['id_aluno']
        session['plano'] = aluno['plano']
        session.permanent = True  # 🔥 CORREÇÃO 3: Tornar sessão permanente
        
        return jsonify({
            'message': 'Login realizado com sucesso!', 
            'role': 'aluno', 
            'user': dict(aluno)
        }), 200

    # Se não for aluno, tenta admin
    cursor.execute('SELECT id_admin, nome, email FROM Admin WHERE email = ? AND senha = ?', (email, senha))
    admin = cursor.fetchone()
    
    if admin:
        session['admin_id'] = admin['id_admin']
        session['admin_nome'] = admin['nome']
        session.permanent = True  # 🔥 CORREÇÃO 3: Tornar sessão permanente
        
        return jsonify({
            'message': 'Login de admin realizado com sucesso!', 
            'role': 'admin', 
            'user': dict(admin)
        }), 200

    # Credenciais inválidas
    return jsonify({'error': 'Email ou senha inválidos.'}), 401


# ===================================================================
# ROTA DE LOGOUT - CORRIGIDA
# ===================================================================

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    # 🔥 CORREÇÃO 4: Retornar status explícito de sucesso
    return jsonify({
        'message': 'Logout realizado com sucesso.',
        'redirect': '/login.html'  # Frontend deve usar isso
    }), 200


# ===================================================================
# CADASTRO E OUTRAS ROTAS (mantidas como estavam)
# ===================================================================

@auth_bp.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    valido_nome, nome_formatado, erro_nome = validar_nome(nome)
    if not valido_nome:
        return jsonify({'error': erro_nome}), 400
    
    valido_email, erro_email = validar_email(email)
    if not valido_email:
        return jsonify({'error': erro_email}), 400
    
    email = email.strip().lower()
    
    if email_ja_existe(email):
        return jsonify({'error': 'Este e-mail já está cadastrado.'}), 400
    
    valido_senha, erros_senha = validar_senha(senha)
    if not valido_senha:
        return jsonify({
            'error': 'Senha não atende aos requisitos de segurança.',
            'detalhes': erros_senha
        }), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    try:
        cursor.execute(
            'INSERT INTO Aluno (nome, email, senha) VALUES (?, ?, ?)', 
            (nome_formatado, email, senha)
        )
        conn.commit()
        return jsonify({
            'message': 'Usuário cadastrado com sucesso.',
            'nome': nome_formatado
        }), 201
        
    except (IntegrityError, sqlite3.IntegrityError):
        return jsonify({'error': 'Email já cadastrado (erro no banco de dados).'}), 400
    except Exception as e:
        print(f"Erro ao cadastrar usuário: {e}")
        return jsonify({'error': 'Erro ao processar cadastro. Tente novamente.'}), 500


@auth_bp.route('/editar_usuario/<int:id_aluno>', methods=['PUT'])
def editar_usuario(id_aluno):
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    url_foto = data.get('url_foto')
    plano = data.get('plano')

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    campos = []
    valores = []

    if nome:
        valido_nome, nome_formatado, erro_nome = validar_nome(nome)
        if not valido_nome:
            return jsonify({'error': erro_nome}), 400
        campos.append("nome=?")
        valores.append(nome_formatado)
    
    if email:
        valido_email, erro_email = validar_email(email)
        if not valido_email:
            return jsonify({'error': erro_email}), 400
        
        email = email.strip().lower()
        
        cursor.execute(
            'SELECT id_aluno FROM Aluno WHERE email = ? AND id_aluno != ?', 
            (email, id_aluno)
        )
        if cursor.fetchone():
            return jsonify({'error': 'Este e-mail já está em uso por outro usuário.'}), 400
        
        campos.append("email=?")
        valores.append(email)
    
    if senha:
        valido_senha, erros_senha = validar_senha(senha)
        if not valido_senha:
            return jsonify({
                'error': 'Nova senha não atende aos requisitos de segurança.',
                'detalhes': erros_senha
            }), 400
        campos.append("senha=?")
        valores.append(senha)
    
    if url_foto is not None:
        campos.append("url_foto=?")
        valores.append(url_foto)
    
    if plano:
        if plano not in ['freemium', 'premium']:
            return jsonify({'error': 'Plano inválido. Use "freemium" ou "premium".'}), 400
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

        # 🔥 CORREÇÃO 5: Atualizar sessão se for o próprio usuário
        if 'id_aluno' in session and session['id_aluno'] == id_aluno:
            if plano:
                session['plano'] = plano

        return jsonify({'message': 'Usuário atualizado com sucesso.'})
    
    except Exception as e:
        print(f"Erro ao atualizar usuário: {e}")
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