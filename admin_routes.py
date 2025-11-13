from flask import Blueprint, request, jsonify, session
from config import conn, cursor
from mysql.connector import IntegrityError # Pode manter, mas o erro do SQLite é sqlite3.IntegrityError
import sqlite3 # Importe para capturar o erro específico
import datetime

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# --- Função de Verificação de Admin ---
def check_admin_session():
    """Verifica se um admin está logado na sessão."""
    if 'admin_id' not in session:
        return jsonify({'error': 'Acesso negado. Você não está logado como administrador.'}), 403
    return None

# --- Rotas de Autenticação do Admin ---

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios.'}), 400

    cursor.execute('SELECT id_admin, nome FROM Admin WHERE email = ? AND senha = ?', (email, senha))
    admin = cursor.fetchone()

    if admin:
        session['admin_id'] = admin['id_admin']
        session['admin_nome'] = admin['nome']
        return jsonify({'message': 'Login de admin realizado com sucesso!', 'admin': dict(admin)}), 200
    else:
        return jsonify({'error': 'Email ou senha de admin inválidos.'}), 401

@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    return jsonify({'message': 'Logout de admin realizado com sucesso.'}), 200

@admin_bp.route('/check_session', methods=['GET'])
def check_admin():
    auth_error = check_admin_session()
    if auth_error:
        return auth_error
    
    return jsonify({
        'message': 'Admin está logado.',
        'admin': {
            'id_admin': session['admin_id'],
            'nome': session['admin_nome']
        }
    }), 200

# --- Rotas de Gerenciamento de Alunos (CRUD) ---

@admin_bp.route('/alunos', methods=['GET'])
def get_alunos():
    auth_error = check_admin_session()
    if auth_error:
        return auth_error

    cursor.execute('SELECT id_aluno, nome, email, plano, url_foto FROM Aluno ORDER BY nome')
    alunos = cursor.fetchall()
    return jsonify([dict(a) for a in alunos]), 200

@admin_bp.route('/alunos', methods=['POST'])
def create_aluno():
    auth_error = check_admin_session()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    plano = data.get('plano', 'freemium') # Default 'freemium'

    if not nome or not email or not senha:
        return jsonify({'error': 'Nome, email e senha são obrigatórios.'}), 400

    try:
        cursor.execute('INSERT INTO Aluno (nome, email, senha, plano) VALUES (?, ?, ?, ?)', 
                       (nome, email, senha, plano))
        conn.commit()
        return jsonify({'message': 'Aluno criado com sucesso.'}), 201
    except (IntegrityError, sqlite3.IntegrityError):
        return jsonify({'error': 'Email já cadastrado.'}), 400

@admin_bp.route('/alunos/<int:id_aluno>', methods=['PUT'])
def update_aluno(id_aluno):
    auth_error = check_admin_session()
    if auth_error:
        return auth_error

    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    plano = data.get('plano')
    senha = data.get('senha') # Senha é opcional na atualização

    campos = []
    valores = []

    if nome:
        campos.append("nome=?")
        valores.append(nome)
    if email:
        campos.append("email=?")
        valores.append(email)
    if plano:
        campos.append("plano=?")
        valores.append(plano)
    if senha:
        campos.append("senha=?")
        valores.append(senha)

    if not campos:
        return jsonify({'error': 'Nenhum campo para atualizar.'}), 400

    query = f"UPDATE Aluno SET {', '.join(campos)} WHERE id_aluno=?"
    valores.append(id_aluno)

    cursor.execute(query, tuple(valores))
    conn.commit()

    if cursor.rowcount == 0:
        return jsonify({'error': 'Aluno não encontrado.'}), 404
    return jsonify({'message': 'Aluno atualizado com sucesso.'}), 200

@admin_bp.route('/alunos/<int:id_aluno>', methods=['DELETE'])
def delete_aluno(id_aluno):
    auth_error = check_admin_session()
    if auth_error:
        return auth_error
        
    cursor.execute('DELETE FROM Aluno WHERE id_aluno=?', (id_aluno,))
    conn.commit()
    if cursor.rowcount == 0:
        return jsonify({'error': 'Aluno não encontrado.'}), 404
    return jsonify({'message': 'Aluno excluído com sucesso.'}), 200

# --- Rotas da Dashboard (Gráficos e Stats) ---

@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    auth_error = check_admin_session()
    if auth_error:
        return auth_error
    
    try:
        # Stat 1: Total de Alunos
        cursor.execute('SELECT COUNT(*) as total_alunos FROM Aluno')
        total_alunos = cursor.fetchone()['total_alunos']

        # Stat 2: Alunos por Plano (Gráfico de Pizza)
        cursor.execute('SELECT plano, COUNT(*) as count FROM Aluno GROUP BY plano')
        alunos_por_plano = [dict(r) for r in cursor.fetchall()] # Formato: [{'plano': 'freemium', 'count': 10}, ...]

        # Stat 3: Média de Acertos Geral (pode ser um card)
        cursor.execute('SELECT AVG(acertos / total_perguntas) as media_geral FROM QuizResultado')
        media_geral_result = cursor.fetchone()
        media_geral = media_geral_result['media_geral'] if media_geral_result else None
        
        # Stat 4: Novos Alunos nos Últimos 7 Dias (Gráfico de Linha)
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        
        cursor.execute("""
            SELECT DATE(data_criacao) as dia, COUNT(DISTINCT id_aluno) as novos_quizzes
            FROM QuizResultado
            WHERE data_criacao >= ?
            GROUP BY DATE(data_criacao)
            ORDER BY dia ASC
        """, (seven_days_ago,)) # SQLite usa ?
        
        quizzes_ultimos_dias = [dict(r) for r in cursor.fetchall()]
        
        # Formatando para o gráfico
        labels_dias = []
        data_dias = []
        
        # Converte as datas de string (SQLite) para objeto date
        quizzes_map = {datetime.date.fromisoformat(item['dia']): item['novos_quizzes'] for item in quizzes_ultimos_dias}

        # Preenche os últimos 7 dias
        for i in range(7):
            day = seven_days_ago + datetime.timedelta(days=i)
            labels_dias.append(day.strftime('%d/%m'))
            
            # Encontra o dado para esse dia, ou usa 0
            count_do_dia = quizzes_map.get(day, 0)
            data_dias.append(count_do_dia)

        
        stats = {
            'total_alunos': total_alunos,
            'alunos_por_plano': alunos_por_plano,
            'media_geral_acertos': f"{media_geral * 100:.2f}%" if media_geral else "N/A",
            'quizzes_por_dia': {
                'labels': labels_dias,
                'data': data_dias
            }
        }
        
        return jsonify(stats), 200

    except Exception as e:
        print(f"Erro ao buscar stats: {e}")
        return jsonify({'error': f'Erro interno ao buscar estatísticas: {e}'}), 500


@admin_bp.route('/alunos/<int:id_aluno>/resultados', methods=['GET'])
def get_resultados_aluno(id_aluno):
    auth_error = check_admin_session()
    if auth_error:
        return auth_error
    
    cursor.execute("""
        SELECT tema, acertos, total_perguntas, data_criacao 
        FROM QuizResultado 
        WHERE id_aluno = ?
        ORDER BY data_criacao DESC
    """, (id_aluno,))
    resultados = cursor.fetchall()
    
    return jsonify([dict(r) for r in resultados]), 200