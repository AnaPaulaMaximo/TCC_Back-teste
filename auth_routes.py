from flask import Blueprint, request, jsonify, session
from config import conn, cursor
import sqlite3
import re

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

# ===================================================================
# FUNÇÕES DE VALIDAÇÃO
# ===================================================================

def validar_email(email):
    """
    Valida formato do e-mail
    Retorna: (bool, str) - (valido, mensagem_erro)
    """
    if not email or len(email.strip()) == 0:
        return False, "E-mail é obrigatório"
    
    email = email.strip().lower()
    
    # Regex para validar formato básico do e-mail
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(regex, email):
        return False, "Formato de e-mail inválido"
    
    if len(email) > 100:
        return False, "E-mail muito longo (máximo 100 caracteres)"
    
    return True, None


def email_ja_existe(email):
    """
    Verifica se o e-mail já está cadastrado
    """
    try:
        cursor.execute('SELECT id_aluno FROM Aluno WHERE email = ?', (email.lower(),))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Erro ao verificar e-mail: {e}")
        return False


def validar_senha(senha):
    """
    Valida complexidade da senha
    Retorna: (bool, list) - (valida, lista_de_erros)
    """
    erros = []
    
    if not senha:
        return False, ["Senha é obrigatória"]
    
    # Comprimento
    if len(senha) < 8:
        erros.append("A senha deve ter no mínimo 8 caracteres")
    
    if len(senha) > 128:
        erros.append("A senha deve ter no máximo 128 caracteres")
    
    # Complexidade
    if not re.search(r'[A-Z]', senha):
        erros.append("Deve conter pelo menos uma letra maiúscula")
    
    if not re.search(r'[a-z]', senha):
        erros.append("Deve conter pelo menos uma letra minúscula")
    
    if not re.search(r'[0-9]', senha):
        erros.append("Deve conter pelo menos um número")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', senha):
        erros.append("Deve conter pelo menos um caractere especial (!@#$%&*)")
    
    # Senhas comuns bloqueadas
    senhas_comuns = [
        '123456', '123456789', 'qwerty', 'password', '12345678',
        '111111', '123123', '1234567890', '1234567', 'senha',
        'senha123', 'admin', 'admin123', 'root', '12345',
        'password123', 'abc123', '1q2w3e4r', 'qwerty123', 'letmein'
    ]
    
    if senha.lower() in senhas_comuns:
        erros.append("Esta senha é muito comum. Escolha uma senha mais segura")
    
    # Verificar repetição excessiva
    if re.search(r'(.)\1{2,}', senha):
        erros.append("Evite repetir o mesmo caractere mais de 2 vezes seguidas")
    
    return len(erros) == 0, erros


def validar_nome(nome):
    """
    Valida nome completo
    Retorna: (bool, str, str) - (valido, nome_formatado, mensagem_erro)
    """
    if not nome or len(nome.strip()) == 0:
        return False, None, "Nome é obrigatório"
    
    nome = nome.strip()
    
    # Comprimento
    if len(nome) < 3:
        return False, None, "O nome deve ter no mínimo 3 caracteres"
    
    if len(nome) > 100:
        return False, None, "O nome deve ter no máximo 100 caracteres"
    
    # Verificar se tem pelo menos nome e sobrenome
    partes = [p for p in nome.split(' ') if len(p) > 0]
    if len(partes) < 2:
        return False, None, "Por favor, digite nome e sobrenome completos"
    
    # Verificar caracteres válidos (letras, espaços e acentos)
    if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', nome):
        return False, None, "O nome deve conter apenas letras"
    
    # Formatar nome (primeira letra maiúscula em cada palavra)
    nome_formatado = ' '.join([p.capitalize() for p in partes])
    
    return True, nome_formatado, None


# ===================================================================
# ROTA DE VALIDAÇÃO PRÉVIA
# ===================================================================

@auth_bp.route('/validar_cadastro', methods=['POST'])
def validar_cadastro():
    """
    Endpoint para validar dados antes do cadastro
    Útil para feedback em tempo real
    """
    data = request.get_json()
    
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    
    erros = {}
    
    # Validar nome
    if nome:
        valido_nome, nome_formatado, erro_nome = validar_nome(nome)
        if not valido_nome:
            erros['nome'] = [erro_nome]
    
    # Validar e-mail
    if email:
        valido_email, erro_email = validar_email(email)
        if not valido_email:
            erros['email'] = [erro_email]
        elif email_ja_existe(email):
            erros['email'] = ["Este e-mail já está cadastrado"]
    
    # Validar senha
    if senha:
        valido_senha, erros_senha = validar_senha(senha)
        if not valido_senha:
            erros['senha'] = erros_senha
    
    if erros:
        return jsonify({'valido': False, 'erros': erros}), 400
    
    return jsonify({'valido': True, 'nome_formatado': nome_formatado if nome else None}), 200


# ===================================================================
# ROTAS DE AUTENTICAÇÃO (ATUALIZADAS COM VALIDAÇÕES)
# ===================================================================

@auth_bp.route('/login', methods=['POST'])
def login():
    # 1. Limpa qualquer sessão anterior imediatamente
    session.clear() 
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios.'}), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    # Normalizar e-mail
    email = email.strip().lower()

    # Tenta fazer login como Administrador primeiro
    cursor.execute('SELECT id_admin, nome, email FROM Admin WHERE email = ? AND senha = ?', (email, senha))
    admin = cursor.fetchone()
    
    if admin:
        session.pop('id_aluno', None)
        session.pop('plano', None)
        
        session['admin_id'] = admin['id_admin']
        session['admin_nome'] = admin['nome']
        
        return jsonify({
            'message': 'Login de admin realizado com sucesso!', 
            'role': 'admin', 
            'user': dict(admin)
        }), 200

    # Tenta fazer login como Aluno
    cursor.execute('SELECT id_aluno, nome, email, plano, url_foto FROM Aluno WHERE email = ? AND senha = ?', (email, senha))
    aluno = cursor.fetchone()

    if aluno:
        session.pop('admin_id', None)
        session.pop('admin_nome', None)

        session['id_aluno'] = aluno['id_aluno']
        session['plano'] = aluno['plano']
        
        return jsonify({
            'message': 'Login realizado com sucesso!', 
            'role': 'aluno', 
            'user': dict(aluno)
        }), 200

    return jsonify({'error': 'Email ou senha inválidos.'}), 401


@auth_bp.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    # ===== VALIDAÇÃO COMPLETA =====
    
    # 1. Validar nome
    valido_nome, nome_formatado, erro_nome = validar_nome(nome)
    if not valido_nome:
        return jsonify({'error': erro_nome}), 400
    
    # 2. Validar e-mail
    valido_email, erro_email = validar_email(email)
    if not valido_email:
        return jsonify({'error': erro_email}), 400
    
    email = email.strip().lower()
    
    # 3. Verificar se e-mail já existe
    if email_ja_existe(email):
        return jsonify({'error': 'Este e-mail já está cadastrado.'}), 400
    
    # 4. Validar senha
    valido_senha, erros_senha = validar_senha(senha)
    if not valido_senha:
        return jsonify({
            'error': 'Senha não atende aos requisitos de segurança.',
            'detalhes': erros_senha
        }), 400

    if not cursor:
        return jsonify({'error': 'Erro de conexão com o banco de dados.'}), 500

    try:
        # Inserir com nome formatado e email normalizado
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

    # Validar e adicionar nome
    if nome:
        valido_nome, nome_formatado, erro_nome = validar_nome(nome)
        if not valido_nome:
            return jsonify({'error': erro_nome}), 400
        campos.append("nome=?")
        valores.append(nome_formatado)
    
    # Validar e adicionar e-mail
    if email:
        valido_email, erro_email = validar_email(email)
        if not valido_email:
            return jsonify({'error': erro_email}), 400
        
        email = email.strip().lower()
        
        # Verificar se e-mail já existe (exceto o próprio usuário)
        cursor.execute(
            'SELECT id_aluno FROM Aluno WHERE email = ? AND id_aluno != ?', 
            (email, id_aluno)
        )
        if cursor.fetchone():
            return jsonify({'error': 'Este e-mail já está em uso por outro usuário.'}), 400
        
        campos.append("email=?")
        valores.append(email)
    
    # Validar e adicionar senha
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

        # Atualizar sessão se necessário
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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Limpa todos os dados da sessão (id_aluno, plano, etc)
    return jsonify({'message': 'Logout realizado com sucesso.'}), 200