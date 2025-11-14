from flask import Blueprint, request, jsonify, session
from config import conn, cursor
from mysql.connector import IntegrityError 
import sqlite3 
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
        
    search = request.args.get('search', None)
    plano_filter = request.args.get('plano', None)

    # Adicionado COUNT(qr.id_resultado) as total_quizzes
    base_query = """
        SELECT 
            a.id_aluno, a.nome, a.email, a.plano, a.url_foto,
            COUNT(qr.id_resultado) as total_quizzes, 
            AVG(CASE WHEN qr.total_perguntas > 0 THEN qr.acertos * 1.0 / qr.total_perguntas ELSE NULL END) as media_geral,
            AVG(CASE WHEN qr.total_perguntas > 0 AND qr.tema = 'Filosofia' THEN qr.acertos * 1.0 / qr.total_perguntas ELSE NULL END) as media_filosofia,
            AVG(CASE WHEN qr.total_perguntas > 0 AND qr.tema = 'Sociologia' THEN qr.acertos * 1.0 / qr.total_perguntas ELSE NULL END) as media_sociologia
        FROM 
            aluno a
        LEFT JOIN 
            quiz_resultado qr ON a.id_aluno = qr.id_aluno
    """
    
    where_clauses = []
    params = []

    if search:
        where_clauses.append("(a.nome LIKE ? OR a.email LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if plano_filter:
        where_clauses.append("a.plano = ?")
        params.append(plano_filter)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += """
        GROUP BY 
            a.id_aluno, a.nome, a.email, a.plano, a.url_foto
        ORDER BY 
            a.nome
    """
    
    cursor.execute(base_query, tuple(params))
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
    plano = data.get('plano', 'freemium') 

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
    senha = data.get('senha') 

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
        alunos_por_plano = [dict(r) for r in cursor.fetchall()]

        # Stat 3: Médias de Acertos (dos cards)
        cursor.execute('SELECT AVG(acertos * 1.0 / total_perguntas) as media FROM quiz_resultado WHERE total_perguntas > 0')
        media_geral_result = cursor.fetchone()
        media_geral = media_geral_result['media'] if media_geral_result and media_geral_result['media'] is not None else 0

        cursor.execute("SELECT AVG(acertos * 1.0 / total_perguntas) as media FROM quiz_resultado WHERE total_perguntas > 0 AND tema = 'Filosofia'")
        media_filo_result = cursor.fetchone()
        media_filosofia = media_filo_result['media'] if media_filo_result and media_filo_result['media'] is not None else 0

        cursor.execute("SELECT AVG(acertos * 1.0 / total_perguntas) as media FROM quiz_resultado WHERE total_perguntas > 0 AND tema = 'Sociologia'")
        media_socio_result = cursor.fetchone()
        media_sociologia = media_socio_result['media'] if media_socio_result and media_socio_result['media'] is not None else 0
        
        # =================================================================
        # --- INÍCIO DA CORREÇÃO (Stat 4: Gráfico Agrupado) ---
        # =================================================================
        
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=6) # Inclui hoje (total 7 dias)
        
        # ATUALIZADO: Query agora busca 'Filosofia e Sociologia' também
        cursor.execute("""
            SELECT 
                a.plano, 
                qr.tema,
                COUNT(qr.id_resultado) as total_quizzes
            FROM 
                quiz_resultado qr
            JOIN 
                aluno a ON a.id_aluno = qr.id_aluno
            WHERE 
                qr.data_criacao >= ? 
                AND (qr.tema = 'Filosofia' OR qr.tema = 'Sociologia' OR qr.tema = 'Filosofia e Sociologia')
            GROUP BY 
                a.plano, qr.tema
        """, (seven_days_ago,))
        
        query_results = [dict(r) for r in cursor.fetchall()]
        
        # ATUALIZADO: Lógica de processamento
        data_map = {
            'freemium': {'Filosofia': 0, 'Sociologia': 0},
            'premium': {'Filosofia': 0, 'Sociologia': 0}
        }

        for item in query_results:
            plano = item['plano']
            tema = item['tema']
            count = item['total_quizzes']
            
            if plano in data_map:
                if tema == 'Filosofia':
                    data_map[plano]['Filosofia'] += count
                elif tema == 'Sociologia':
                    data_map[plano]['Sociologia'] += count
                elif tema == 'Filosofia e Sociologia':
                    # Adiciona a contagem para AMBOS os datasets
                    data_map[plano]['Filosofia'] += count
                    data_map[plano]['Sociologia'] += count
        
        # (Premium quizzes com temas customizados ainda não são contados aqui,
        # mas isso resolve o problema principal dos quizzes 'Ambos' do freemium)

        labels = ['freemium', 'premium']
        data_filosofia = [data_map['freemium']['Filosofia'], data_map['premium']['Filosofia']]
        data_sociologia = [data_map['freemium']['Sociologia'], data_map['premium']['Sociologia']]

        # =================================================================
        # --- FIM DA CORREÇÃO ---
        # =================================================================

        stats = {
            'total_alunos': total_alunos,
            'alunos_por_plano': alunos_por_plano,
            'media_geral_acertos': f"{media_geral * 100:.2f}%",
            'media_filosofia': f"{media_filosofia * 100:.2f}%",
            'media_sociologia': f"{media_sociologia * 100:.2f}%",
            'quizzes_por_plano_e_tema': { 
                'labels': labels,
                'data_filosofia': data_filosofia,
                'data_sociologia': data_sociologia
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
        FROM quiz_resultado
        WHERE id_aluno = ?
        ORDER BY data_criacao DESC
    """, (id_aluno,))
    resultados = cursor.fetchall()
    
    return jsonify([dict(r) for r in resultados]), 200