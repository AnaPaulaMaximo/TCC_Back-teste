from flask import Blueprint, request, jsonify, session
from config import conn 
import sqlite3 
import datetime

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# --- CTE: UNIFICAÇÃO DAS TABELAS ---
# Padronizamos as colunas para que o Python trate tudo igual
UNION_QUIZZES_QUERY = """
    (
        SELECT id_aluno, tema, acertos, total_perguntas, data_criacao, 'freemium' as origem
        FROM quiz_resultado
        UNION ALL
        SELECT id_aluno, tema, acertos, total_perguntas, data_criacao, 'premium' as origem
        FROM historico_premium 
        WHERE tipo_atividade = 'quiz' AND acertos IS NOT NULL
    )
"""

def check_admin_session():
    if 'admin_id' not in session:
        return jsonify({'error': 'Acesso negado. Admin não logado.'}), 403
    return None

# --- ROTAS DE AUTENTICAÇÃO ---
@admin_bp.route('/login', methods=['POST'])
def admin_login():
    cursor = conn.cursor()
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        cursor.execute('SELECT id_admin, nome FROM Admin WHERE email = ? AND senha = ?', (email, senha))
        admin = cursor.fetchone()
        
        if admin:
            session['admin_id'] = admin['id_admin']
            session['admin_nome'] = admin['nome']
            return jsonify({'message': 'Login admin sucesso', 'admin': dict(admin)}), 200
        else:
            return jsonify({'error': 'Credenciais inválidas.'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_nome', None)
    return jsonify({'message': 'Logout realizado.'}), 200

@admin_bp.route('/check_session', methods=['GET'])
def check_admin():
    error = check_admin_session()
    if error: return error
    return jsonify({'admin': {'nome': session['admin_nome']}}), 200

# --- ROTAS DE ALUNOS ---
@admin_bp.route('/alunos', methods=['GET'])
def get_alunos():
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    
    search = request.args.get('search', '')
    plano = request.args.get('plano', '')

    # Query otimizada: Agrupa primeiro na subquery para evitar duplicação no Join
    try:
        query = f"""
            SELECT 
                a.id_aluno, a.nome, a.email, a.plano, a.url_foto,
                COUNT(qr.data_criacao) as total_quizzes,
                AVG(CAST(qr.acertos AS FLOAT) / CAST(qr.total_perguntas AS FLOAT)) as media_geral,
                
                /* Médias Condicionais (Case Insensitive para pegar variações) */
                AVG(CASE WHEN UPPER(qr.tema) LIKE '%FILOSOFIA%' THEN CAST(qr.acertos AS FLOAT)/qr.total_perguntas ELSE NULL END) as media_filosofia,
                AVG(CASE WHEN UPPER(qr.tema) LIKE '%SOCIOLOGIA%' THEN CAST(qr.acertos AS FLOAT)/qr.total_perguntas ELSE NULL END) as media_sociologia
            
            FROM aluno a
            LEFT JOIN {UNION_QUIZZES_QUERY} qr ON a.id_aluno = qr.id_aluno
            WHERE (a.nome LIKE ? OR a.email LIKE ?)
        """
        params = [f"%{search}%", f"%{search}%"]

        if plano:
            query += " AND a.plano = ?"
            params.append(plano)

        query += " GROUP BY a.id_aluno, a.nome, a.email, a.plano, a.url_foto ORDER BY a.nome"

        cursor.execute(query, tuple(params))
        alunos = [dict(row) for row in cursor.fetchall()]
        return jsonify(alunos), 200
    except Exception as e:
        print(f"Erro get_alunos: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@admin_bp.route('/alunos', methods=['POST'])
def create_aluno():
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    try:
        d = request.get_json()
        cursor.execute('INSERT INTO Aluno (nome, email, senha, plano) VALUES (?, ?, ?, ?)', 
                       (d.get('nome'), d.get('email'), d.get('senha'), d.get('plano', 'freemium')))
        conn.commit()
        return jsonify({'message': 'Criado com sucesso'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()

@admin_bp.route('/alunos/<int:id_aluno>', methods=['PUT'])
def update_aluno(id_aluno):
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    try:
        d = request.get_json()
        sets = []
        vals = []
        if 'nome' in d: sets.append("nome=?"); vals.append(d['nome'])
        if 'email' in d: sets.append("email=?"); vals.append(d['email'])
        if 'plano' in d: sets.append("plano=?"); vals.append(d['plano'])
        if 'senha' in d and d['senha']: sets.append("senha=?"); vals.append(d['senha'])
        
        if not sets: return jsonify({'error': 'Nada a alterar'}), 400
        
        vals.append(id_aluno)
        cursor.execute(f"UPDATE Aluno SET {', '.join(sets)} WHERE id_aluno=?", tuple(vals))
        conn.commit()
        return jsonify({'message': 'Atualizado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@admin_bp.route('/alunos/<int:id_aluno>', methods=['DELETE'])
def delete_aluno(id_aluno):
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Aluno WHERE id_aluno=?", (id_aluno,))
        conn.commit()
        return jsonify({'message': 'Deletado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

# --- ROTAS DE STATS (DASHBOARD) ---
@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    try:
        # 1. Totais básicos
        cursor.execute("SELECT COUNT(*) as t FROM Aluno")
        result_total = cursor.fetchone()
        total_alunos = result_total['t'] if result_total else 0
        
        # CORREÇÃO AQUI: Mudado de 'as c' para 'as count' para o gráfico funcionar
        cursor.execute("SELECT plano, COUNT(*) as count FROM Aluno GROUP BY plano")
        alunos_por_plano = [dict(r) for r in cursor.fetchall()]

        # 2. Médias (usando a tabela unificada)
        cursor.execute(f"SELECT AVG(CAST(acertos AS FLOAT)/total_perguntas) as m FROM {UNION_QUIZZES_QUERY} WHERE total_perguntas > 0")
        res = cursor.fetchone()
        media_geral = res['m'] if res and res['m'] else 0

        cursor.execute(f"SELECT AVG(CAST(acertos AS FLOAT)/total_perguntas) as m FROM {UNION_QUIZZES_QUERY} WHERE total_perguntas > 0 AND tema LIKE '%Filosofia%'")
        res = cursor.fetchone()
        media_filo = res['m'] if res and res['m'] else 0

        cursor.execute(f"SELECT AVG(CAST(acertos AS FLOAT)/total_perguntas) as m FROM {UNION_QUIZZES_QUERY} WHERE total_perguntas > 0 AND tema LIKE '%Sociologia%'")
        res = cursor.fetchone()
        media_socio = res['m'] if res and res['m'] else 0

        # 3. Gráfico de Barras (Categorias da IA)
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=6)
        
        cursor.execute(f"""
            SELECT qr.tema, a.plano
            FROM {UNION_QUIZZES_QUERY} qr
            JOIN aluno a ON a.id_aluno = qr.id_aluno
            WHERE qr.data_criacao >= ?
        """, (seven_days_ago,))
        
        rows = cursor.fetchall()
        
        # Estrutura para contar
        data_map = {
            'freemium': {'Filosofia': 0, 'Sociologia': 0, 'Diversos': 0},
            'premium':  {'Filosofia': 0, 'Sociologia': 0, 'Diversos': 0}
        }

        for row in rows:
            tema = row['tema'] if row['tema'] else 'Desconhecido'
            plano = row['plano']
            
            tema_upper = tema.upper()
            
            # Lógica de Classificação:
            # Se a IA já salvou como "Filosofia - Platão", vai cair no primeiro IF.
            # Se for antigo ou sem categoria, cai em Diversos.
            categoria = 'Diversos' 
            if 'FILOSOFIA' in tema_upper:
                categoria = 'Filosofia'
            elif 'SOCIOLOGIA' in tema_upper:
                categoria = 'Sociologia'
            
            if plano in data_map:
                data_map[plano][categoria] += 1

        stats = {
            'total_alunos': total_alunos,
            'alunos_por_plano': alunos_por_plano,
            'media_geral_acertos': f"{media_geral*100:.1f}%",
            'media_filosofia': f"{media_filo*100:.1f}%",
            'media_sociologia': f"{media_socio*100:.1f}%",
            'quizzes_por_plano_e_tema': {
                'labels': ['Freemium', 'Premium'],
                'data_filosofia': [data_map['freemium']['Filosofia'], data_map['premium']['Filosofia']],
                'data_sociologia': [data_map['freemium']['Sociologia'], data_map['premium']['Sociologia']],
                'data_diversos': [data_map['freemium']['Diversos'], data_map['premium']['Diversos']]
            }
        }
        return jsonify(stats), 200

    except Exception as e:
        print(f"Erro stats: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@admin_bp.route('/alunos/<int:id_aluno>/resultados', methods=['GET'])
def get_resultados_aluno(id_aluno):
    if check_admin_session(): return check_admin_session()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT tema, acertos, total_perguntas, data_criacao, origem 
            FROM {UNION_QUIZZES_QUERY}
            WHERE id_aluno = ?
            ORDER BY data_criacao DESC
        """, (id_aluno,))
        return jsonify([dict(r) for r in cursor.fetchall()]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()