from flask import Blueprint, request, jsonify, session
from config import conn, cursor
from datetime import datetime, timedelta
import sqlite3

# ✅ CORRIGIDO: Nome correto do Blueprint
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# ===================================================================
# ROTA PARA VERIFICAR SESSÃO DE ADMIN
# ===================================================================

@admin_bp.route('/check_session', methods=['GET'])
def check_session():
    """Verifica se há uma sessão de admin ativa"""
    
    if 'admin_id' not in session:
        return jsonify({
            'logged_in': False,
            'message': 'Nenhuma sessão de admin ativa'
        }), 401
    
    return jsonify({
        'logged_in': True,
        'admin': {
            'id': session['admin_id'],
            'nome': session.get('admin_nome', 'Admin')
        }
    }), 200


# ===================================================================
# ROTA DE LOGOUT DO ADMIN
# ===================================================================

@admin_bp.route('/logout', methods=['POST'])
def logout():
    """Logout de admin"""
    try:
        session.clear()
        return jsonify({'message': 'Logout realizado com sucesso.'}), 200
    except Exception as e:
        print(f"Erro no logout: {e}")
        return jsonify({'error': 'Erro ao fazer logout'}), 500


# ===================================================================
# DASHBOARD: ESTATÍSTICAS GERAIS
# ===================================================================

@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """Retorna estatísticas para o dashboard do admin"""
    
    # Verifica sessão
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    try:
        # 1. Total de alunos
        cursor.execute('SELECT COUNT(*) as total FROM Aluno')
        total_alunos = cursor.fetchone()['total']
        
        # 2. Alunos por plano
        cursor.execute('''
            SELECT plano, COUNT(*) as count 
            FROM Aluno 
            GROUP BY plano
        ''')
        alunos_por_plano = [dict(row) for row in cursor.fetchall()]
        
        # 3. Média geral de acertos
        cursor.execute('''
            SELECT AVG(CAST(acertos AS FLOAT) / total_perguntas) as media 
            FROM quiz_resultado
            WHERE total_perguntas > 0
        ''')
        result = cursor.fetchone()
        media_geral = result['media'] if result['media'] else 0
        media_geral_formatada = f"{media_geral * 100:.1f}%"
        
        # 4. Média por matéria (Filosofia e Sociologia)
        # Assumindo que o tema contém "Filosofia" ou "Sociologia"
        
        # Filosofia
        cursor.execute('''
            SELECT AVG(CAST(acertos AS FLOAT) / total_perguntas) as media 
            FROM quiz_resultado
            WHERE total_perguntas > 0 
            AND LOWER(tema) LIKE '%filosofia%'
        ''')
        result = cursor.fetchone()
        media_filo = result['media'] if result['media'] else 0
        media_filosofia = f"{media_filo * 100:.1f}%"
        
        # Sociologia
        cursor.execute('''
            SELECT AVG(CAST(acertos AS FLOAT) / total_perguntas) as media 
            FROM quiz_resultado
            WHERE total_perguntas > 0 
            AND LOWER(tema) LIKE '%sociologia%'
        ''')
        result = cursor.fetchone()
        media_socio = result['media'] if result['media'] else 0
        media_sociologia = f"{media_socio * 100:.1f}%"
        
        # 5. Quizzes por plano e tema (últimos 7 dias)
        sete_dias_atras = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT 
                a.plano,
                CASE 
                    WHEN LOWER(q.tema) LIKE '%filosofia%' THEN 'Filosofia'
                    WHEN LOWER(q.tema) LIKE '%sociologia%' THEN 'Sociologia'
                    ELSE 'Outros'
                END as tema,
                COUNT(*) as count
            FROM quiz_resultado q
            JOIN Aluno a ON q.id_aluno = a.id_aluno
            WHERE q.data_criacao >= ?
            GROUP BY a.plano, tema
            ORDER BY a.plano, tema
        ''', (sete_dias_atras,))
        
        quizzes_agrupados = cursor.fetchall()
        
        # Formatar dados para o gráfico
        labels = []
        data_filosofia = []
        data_sociologia = []
        
        planos = ['freemium', 'premium']
        for plano in planos:
            labels.append(plano.capitalize())
            
            filo_count = 0
            socio_count = 0
            
            for row in quizzes_agrupados:
                if row['plano'] == plano:
                    if row['tema'] == 'Filosofia':
                        filo_count = row['count']
                    elif row['tema'] == 'Sociologia':
                        socio_count = row['count']
            
            data_filosofia.append(filo_count)
            data_sociologia.append(socio_count)
        
        return jsonify({
            'total_alunos': total_alunos,
            'alunos_por_plano': alunos_por_plano,
            'media_geral_acertos': media_geral_formatada,
            'media_filosofia': media_filosofia,
            'media_sociologia': media_sociologia,
            'quizzes_por_plano_e_tema': {
                'labels': labels,
                'data_filosofia': data_filosofia,
                'data_sociologia': data_sociologia
            }
        })
    
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return jsonify({'error': str(e)}), 500


# ===================================================================
# GERENCIAR ALUNOS: LISTAR, CRIAR, EDITAR, EXCLUIR
# ===================================================================

@admin_bp.route('/alunos', methods=['GET'])
def get_alunos():
    """Lista todos os alunos com filtros opcionais"""
    
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    search = request.args.get('search', '').strip()
    plano = request.args.get('plano', '').strip()
    
    query = '''
        SELECT 
            a.id_aluno,
            a.nome,
            a.email,
            a.plano,
            a.url_foto,
            COUNT(DISTINCT q.id_resultado) as total_quizzes,
            AVG(CASE WHEN LOWER(q.tema) LIKE '%filosofia%' THEN CAST(q.acertos AS FLOAT) / q.total_perguntas END) as media_filosofia,
            AVG(CASE WHEN LOWER(q.tema) LIKE '%sociologia%' THEN CAST(q.acertos AS FLOAT) / q.total_perguntas END) as media_sociologia,
            AVG(CAST(q.acertos AS FLOAT) / q.total_perguntas) as media_geral
        FROM Aluno a
        LEFT JOIN quiz_resultado q ON a.id_aluno = q.id_aluno
        WHERE 1=1
    '''
    
    params = []
    
    if search:
        query += ' AND (a.nome LIKE ? OR a.email LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if plano:
        query += ' AND a.plano = ?'
        params.append(plano)
    
    query += ' GROUP BY a.id_aluno ORDER BY a.nome'
    
    try:
        cursor.execute(query, params)
        alunos = [dict(row) for row in cursor.fetchall()]
        
        # Formatar médias
        for aluno in alunos:
            if aluno['media_filosofia']:
                aluno['media_filosofia'] = aluno['media_filosofia']
            if aluno['media_sociologia']:
                aluno['media_sociologia'] = aluno['media_sociologia']
            if aluno['media_geral']:
                aluno['media_geral'] = aluno['media_geral']
        
        return jsonify(alunos)
    
    except Exception as e:
        print(f"Erro ao listar alunos: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/alunos', methods=['POST'])
def create_aluno():
    """Cria um novo aluno"""
    
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    plano = data.get('plano', 'freemium')
    
    if not all([nome, email, senha]):
        return jsonify({'error': 'Nome, email e senha são obrigatórios'}), 400
    
    try:
        cursor.execute(
            'INSERT INTO Aluno (nome, email, senha, plano) VALUES (?, ?, ?, ?)',
            (nome, email.lower(), senha, plano)
        )
        conn.commit()
        return jsonify({'message': 'Aluno criado com sucesso'}), 201
    
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email já cadastrado'}), 400
    except Exception as e:
        print(f"Erro ao criar aluno: {e}")
        conn.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/alunos/<int:id_aluno>', methods=['PUT'])
def update_aluno(id_aluno):
    """Atualiza dados de um aluno"""
    
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    data = request.get_json()
    
    campos = []
    valores = []
    
    if 'nome' in data:
        campos.append('nome = ?')
        valores.append(data['nome'])
    
    if 'email' in data:
        campos.append('email = ?')
        valores.append(data['email'].lower())
    
    if 'senha' in data:
        campos.append('senha = ?')
        valores.append(data['senha'])
    
    if 'plano' in data:
        campos.append('plano = ?')
        valores.append(data['plano'])
    
    if not campos:
        return jsonify({'error': 'Nenhum campo para atualizar'}), 400
    
    valores.append(id_aluno)
    
    query = f"UPDATE Aluno SET {', '.join(campos)} WHERE id_aluno = ?"
    
    try:
        cursor.execute(query, valores)
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Aluno não encontrado'}), 404
        
        return jsonify({'message': 'Aluno atualizado com sucesso'})
    
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email já em uso'}), 400
    except Exception as e:
        print(f"Erro ao atualizar aluno: {e}")
        conn.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/alunos/<int:id_aluno>', methods=['DELETE'])
def delete_aluno(id_aluno):
    """Exclui um aluno"""
    
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    try:
        cursor.execute('DELETE FROM Aluno WHERE id_aluno = ?', (id_aluno,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Aluno não encontrado'}), 404
        
        return jsonify({'message': 'Aluno excluído com sucesso'})
    
    except Exception as e:
        print(f"Erro ao excluir aluno: {e}")
        conn.rollback()
        return jsonify({'error': str(e)}), 500


# ===================================================================
# VISUALIZAR RESULTADOS DE UM ALUNO
# ===================================================================

@admin_bp.route('/alunos/<int:id_aluno>/resultados', methods=['GET'])
def get_resultados_aluno(id_aluno):
    """Retorna os resultados de quizzes de um aluno específico"""
    
    if 'admin_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    try:
        cursor.execute('''
            SELECT 
                tema,
                acertos,
                total_perguntas,
                data_criacao
            FROM quiz_resultado
            WHERE id_aluno = ?
            ORDER BY data_criacao DESC
        ''', (id_aluno,))
        
        resultados = [dict(row) for row in cursor.fetchall()]
        return jsonify(resultados)
    
    except Exception as e:
        print(f"Erro ao buscar resultados: {e}")
        return jsonify({'error': str(e)}), 500