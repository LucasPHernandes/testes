from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///refeitorio.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ORDEM DAS REFEIÇÕES
ORDEM_REFEICOES = {
    'Lanche da Manhã': 1,
    'Lanche da manhã': 1,
    'Almoço': 2,
    'Almoco': 2,
    'Lanche da Tarde': 3,
    'Lanche da tarde': 3,
    'Jantar': 4,
    'Ceia': 5
}

def get_ordem_refeicao(refeicao):
    return ORDEM_REFEICOES.get(refeicao, 999)

# MODELOS
class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(100))
    email = db.Column(db.String(100))
    total_faltas = db.Column(db.Integer, default=0)
    debito = db.Column(db.Float, default=0.0)
    ultima_falta_data = db.Column(db.Date, nullable=True)
    ultima_falta_refeicao = db.Column(db.String(50), nullable=True)
    ultima_falta_valor = db.Column(db.Float, default=0.0)
    bloqueado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    historico = db.relationship('Historico', backref='aluno', lazy=True, cascade='all, delete-orphan')
    pagamentos = db.relationship('Pagamento', backref='aluno', lazy=True, cascade='all, delete-orphan')

class Historico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    refeicao = db.Column(db.String(50))
    tipo = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, default=0.0)
    registro_data = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(200))
    faltas_quitadas = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    tipo = db.Column(db.String(20), default='geral')

class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(50), default='sistema')
    acao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), default='info')
    detalhes = db.Column(db.Text)

with app.app_context():
    db.create_all()
    
    configuracoes_padrao = [
        {'chave': 'max_faltas', 'valor': '3', 'descricao': 'Máximo de faltas para bloqueio', 'tipo': 'geral'},
        {'chave': 'valor_lanche_manha', 'valor': '3.50', 'descricao': 'Valor do Lanche da Manhã', 'tipo': 'refeicao'},
        {'chave': 'valor_almoco', 'valor': '8.00', 'descricao': 'Valor do Almoço', 'tipo': 'refeicao'},
        {'chave': 'valor_lanche_tarde', 'valor': '3.50', 'descricao': 'Valor do Lanche da Tarde', 'tipo': 'refeicao'},
        {'chave': 'valor_janta', 'valor': '8.00', 'descricao': 'Valor do Jantar', 'tipo': 'refeicao'},
        {'chave': 'valor_ceia', 'valor': '4.00', 'descricao': 'Valor da Ceia', 'tipo': 'refeicao'},
    ]
    
    for conf in configuracoes_padrao:
        if not Configuracao.query.filter_by(chave=conf['chave']).first():
            nova_conf = Configuracao(
                chave=conf['chave'], 
                valor=conf['valor'], 
                descricao=conf['descricao'],
                tipo=conf['tipo']
            )
            db.session.add(nova_conf)
    
    db.session.commit()

# FUNÇÕES AUXILIARES
def get_config(chave):
    conf = Configuracao.query.filter_by(chave=chave).first()
    return conf.valor if conf else None

def get_valor_refeicao(tipo_refeicao):
    mapa = {
        'Lanche da Manhã': 'valor_lanche_manha',
        'Lanche da manhã': 'valor_lanche_manha',
        'Almoço': 'valor_almoco',
        'Almoco': 'valor_almoco',
        'Lanche da Tarde': 'valor_lanche_tarde',
        'Lanche da tarde': 'valor_lanche_tarde',
        'Jantar': 'valor_janta',
        'Ceia': 'valor_ceia'
    }
    chave = mapa.get(tipo_refeicao, 'valor_almoco')
    valor = get_config(chave)
    return float(valor) if valor else 5.0

def log_auditoria(acao, tipo='info', detalhes=None):
    auditoria = Auditoria(acao=acao, tipo=tipo, detalhes=detalhes)
    db.session.add(auditoria)
    db.session.commit()

def verificar_bloqueio(aluno):
    max_faltas = int(get_config('max_faltas') or 3)
    if aluno.total_faltas >= max_faltas and not aluno.bloqueado:
        aluno.bloqueado = True
        log_auditoria(f'Aluno {aluno.nome} BLOQUEADO com {aluno.total_faltas} faltas', 'alerta')
        return True
    return False

# ROTAS PRINCIPAIS
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/alunos')
def alunos():
    return render_template('alunos.html')

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

@app.route('/auditoria')
def auditoria():
    return render_template('auditoria.html')

@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

# ==================== API - ALUNOS ====================
@app.route('/api/alunos', methods=['GET'])
def api_alunos():
    alunos = Aluno.query.all()
    result = []
    for aluno in alunos:
        result.append({
            'id': aluno.id,
            'matricula': aluno.matricula,
            'nome': aluno.nome,
            'curso': aluno.curso,
            'total_faltas': aluno.total_faltas,
            'debito': aluno.debito,
            'ultima_falta': aluno.ultima_falta_data.strftime('%d/%m/%Y') if aluno.ultima_falta_data else None,
            'ultima_refeicao': aluno.ultima_falta_refeicao,
            'bloqueado': aluno.bloqueado,
            'status': 'BLOQUEADO' if aluno.bloqueado else 'Ativo'
        })
    return jsonify(result)

@app.route('/api/alunos/<int:id>', methods=['GET'])
def api_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    
    def normalizar_refeicao(refeicao):
        ref = refeicao.lower().strip()
        if 'manhã' in ref or 'manha' in ref:
            return 'Lanche da Manhã'
        elif 'almoço' in ref or 'almoco' in ref:
            return 'Almoço'
        elif 'tarde' in ref:
            return 'Lanche da Tarde'
        elif 'jantar' in ref:
            return 'Jantar'
        elif 'ceia' in ref:
            return 'Ceia'
        return refeicao
    
    def get_ordem_segura(refeicao):
        ref = refeicao.lower()
        if 'manhã' in ref or 'manha' in ref:
            return 1
        elif 'almoço' in ref or 'almoco' in ref:
            return 2
        elif 'tarde' in ref:
            return 3
        elif 'jantar' in ref:
            return 4
        elif 'ceia' in ref:
            return 5
        return 999
    
    faltas = Historico.query.filter_by(
        aluno_id=aluno.id,
        tipo='falta',
        status='pendente'
    ).all()
    
    faltas_com_info = []
    for falta in faltas:
        ordem = get_ordem_segura(falta.refeicao)
        ref_normalizada = normalizar_refeicao(falta.refeicao)
        
        faltas_com_info.append({
            'data_obj': falta.data,
            'data_str': falta.data.strftime('%d/%m/%Y'),
            'refeicao_original': falta.refeicao,
            'refeicao': ref_normalizada,
            'ordem': ordem,
            'valor': falta.valor
        })
    
    faltas_com_info.sort(key=lambda x: (x['data_obj'], x['ordem']), reverse=True)
    
    ultima_falta = None
    if faltas_com_info:
        ultima_falta = {
            'data': faltas_com_info[0]['data_str'],
            'refeicao': faltas_com_info[0]['refeicao'],
            'valor': faltas_com_info[0]['valor']
        }
    
    faltas_pendentes = []
    for f in faltas_com_info:
        faltas_pendentes.append({
            'data': f['data_str'],
            'refeicao': f['refeicao'],
            'valor': f['valor']
        })
    
    historico = []
    for h in aluno.historico:
        historico.append({
            'data': h.data.strftime('%d/%m/%Y'),
            'refeicao': h.refeicao,
            'tipo': h.tipo,
            'status': h.status,
            'valor': h.valor
        })
    
    max_faltas = int(get_config('max_faltas') or 3)
    
    return jsonify({
        'id': aluno.id,
        'matricula': aluno.matricula,
        'nome': aluno.nome,
        'curso': aluno.curso,
        'total_faltas': len(faltas_pendentes),
        'debito': aluno.debito,
        'ultima_falta': ultima_falta,
        'faltas_pendentes': faltas_pendentes,
        'bloqueado': aluno.bloqueado,
        'max_faltas': max_faltas,
        'faltas_restantes': max(0, max_faltas - len(faltas_pendentes)),
        'historico': historico,
        'pagamentos': [{
            'data': p.data.strftime('%d/%m/%Y'),
            'valor': p.valor,
            'motivo': p.motivo,
            'faltas_quitadas': p.faltas_quitadas
        } for p in aluno.pagamentos]
    })

@app.route('/api/alunos/<int:id>/pagamento', methods=['POST'])
def api_pagamento(id):
    aluno = Aluno.query.get_or_404(id)
    data = request.json
    valor = float(data.get('valor', 0))
    motivo = data.get('motivo', 'Pagamento de débito')
    
    if valor <= 0:
        return jsonify({'success': False, 'message': 'Valor inválido!'}), 400
    
    if aluno.debito <= 0:
        return jsonify({'success': False, 'message': 'Aluno não possui débito!'}), 400
    
    if abs(valor - aluno.debito) > 0.01:
        return jsonify({
            'success': False, 
            'message': f'O valor a pagar é R$ {aluno.debito:.2f}'
        }), 400
    
    faltas_pendentes = Historico.query.filter_by(
        aluno_id=aluno.id,
        tipo='falta',
        status='pendente'
    ).all()
    
    total_faltas = len(faltas_pendentes)
    
    pagamento = Pagamento(
        aluno_id=aluno.id,
        data=date.today(),
        valor=valor,
        motivo=motivo,
        faltas_quitadas=total_faltas
    )
    db.session.add(pagamento)
    
    for falta in faltas_pendentes:
        falta.status = 'paga'
    
    aluno.bloqueado = False
    aluno.debito = 0
    aluno.ultima_falta_data = None
    aluno.ultima_falta_refeicao = None
    aluno.ultima_falta_valor = 0
    aluno.total_faltas = 0
    
    log_auditoria(
        f'Aluno {aluno.nome} pagou R$ {valor:.2f} e quitou {total_faltas} faltas',
        'pagamento',
        motivo
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Pagamento registrado! {total_faltas} falta(s) quitada(s).',
        'novo_debito': 0,
        'total_faltas': 0,
        'bloqueado': False
    })

# ==================== API - IMPORTAÇÃO ====================
@app.route('/api/importar/agendamentos', methods=['POST'])
def api_importar_agendamentos():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo!'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Selecione um arquivo!'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        df = pd.read_excel(filepath)
        
        colunas = ['Dia', 'Identificação', 'Usuário', 'Curso/Departamento', 'Refeição', 'Comparecimento']
        for col in colunas:
            if col not in df.columns:
                return jsonify({'success': False, 'message': f'Coluna "{col}" não encontrada!'}), 400
        
        def normalizar_refeicao(refeicao):
            ref = refeicao.lower().strip()
            if 'manhã' in ref or 'manha' in ref:
                return 'Lanche da Manhã'
            elif 'almoço' in ref or 'almoco' in ref:
                return 'Almoço'
            elif 'tarde' in ref:
                return 'Lanche da Tarde'
            elif 'jantar' in ref:
                return 'Jantar'
            elif 'ceia' in ref:
                return 'Ceia'
            return refeicao
        
        def get_ordem_segura(refeicao):
            ref = refeicao.lower()
            if 'manhã' in ref or 'manha' in ref:
                return 1
            elif 'almoço' in ref or 'almoco' in ref:
                return 2
            elif 'tarde' in ref:
                return 3
            elif 'jantar' in ref:
                return 4
            elif 'ceia' in ref:
                return 5
            return 999
        
        registros = []
        for _, row in df.iterrows():
            try:
                matricula = str(row['Identificação']).strip()
                nome = str(row['Usuário']).strip()
                curso = str(row['Curso/Departamento']).strip()
                refeicao_original = str(row['Refeição']).strip()
                comparecimento = str(row['Comparecimento']).strip()
                
                refeicao_normalizada = normalizar_refeicao(refeicao_original)
                ordem = get_ordem_segura(refeicao_original)
                
                data_str = str(row['Dia']).strip()
                if '/' in data_str:
                    data_registro = datetime.strptime(data_str, '%d/%m/%Y').date()
                else:
                    data_registro = date.today()
                
                registros.append({
                    'matricula': matricula,
                    'nome': nome,
                    'curso': curso,
                    'refeicao_original': refeicao_original,
                    'refeicao': refeicao_normalizada,
                    'comparecimento': comparecimento,
                    'data': data_registro,
                    'ordem': ordem
                })
            except Exception as e:
                print(f"Erro na linha: {e}")
                continue
        
        registros.sort(key=lambda x: (x['data'], x['ordem']))
        
        novos = 0
        faltas = 0
        bloqueados = []
        
        for reg in registros:
            aluno = Aluno.query.filter_by(matricula=reg['matricula']).first()
            
            if not aluno:
                aluno = Aluno(
                    matricula=reg['matricula'],
                    nome=reg['nome'],
                    curso=reg['curso']
                )
                db.session.add(aluno)
                db.session.flush()
                novos += 1
            
            if aluno.bloqueado:
                continue
            
            existe = Historico.query.filter_by(
                aluno_id=aluno.id,
                data=reg['data'],
                refeicao=reg['refeicao_original']
            ).first()
            
            if existe:
                continue
            
            if reg['comparecimento'].lower() == 'sim':
                historico = Historico(
                    aluno_id=aluno.id,
                    data=reg['data'],
                    refeicao=reg['refeicao_original'],
                    tipo='presenca',
                    status='presente',
                    valor=0
                )
                db.session.add(historico)
            else:
                valor = get_valor_refeicao(reg['refeicao_original'])
                
                historico = Historico(
                    aluno_id=aluno.id,
                    data=reg['data'],
                    refeicao=reg['refeicao_original'],
                    tipo='falta',
                    status='pendente',
                    valor=valor
                )
                db.session.add(historico)
                
                aluno.total_faltas += 1
                aluno.ultima_falta_data = reg['data']
                aluno.ultima_falta_refeicao = reg['refeicao']
                aluno.ultima_falta_valor = valor
                aluno.debito = valor
                
                faltas += 1
                
                if verificar_bloqueio(aluno):
                    bloqueados.append(aluno.nome)
        
        db.session.commit()
        
        msg = f'Importação OK! {novos} novos alunos, {faltas} faltas.'
        if bloqueados:
            msg += f' {len(bloqueados)} bloqueados.'
        
        return jsonify({'success': True, 'message': msg})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ==================== API - RELATÓRIOS ====================
@app.route('/api/relatorios/diario', methods=['GET'])
def api_relatorio_diario():
    try:
        # Verificar se foi passada uma data específica
        data_param = request.args.get('data')
        
        if data_param:
            # Formato esperado: YYYY-MM-DD
            data_atual = datetime.strptime(data_param, '%Y-%m-%d').date()
        else:
            data_atual = date.today()
        
        registros = Historico.query.filter_by(data=data_atual).all()
        
        presentes = sum(1 for r in registros if r.tipo == 'presenca')
        faltas = sum(1 for r in registros if r.tipo == 'falta')
        
        # Estatísticas por refeição
        refeicoes = {}
        valor_total_faltas = 0
        
        for r in registros:
            if r.tipo == 'falta':
                valor_total_faltas += r.valor
                if r.refeicao not in refeicoes:
                    refeicoes[r.refeicao] = {'presentes': 0, 'faltas': 0, 'valor': 0}
                refeicoes[r.refeicao]['faltas'] += 1
                refeicoes[r.refeicao]['valor'] += r.valor
            elif r.tipo == 'presenca':
                if r.refeicao not in refeicoes:
                    refeicoes[r.refeicao] = {'presentes': 0, 'faltas': 0, 'valor': 0}
                refeicoes[r.refeicao]['presentes'] += 1
        
        total_alunos = Aluno.query.count()
        bloqueados = Aluno.query.filter_by(bloqueado=True).count()
        total_debitos = db.session.query(db.func.sum(Aluno.debito)).scalar() or 0
        
        return jsonify({
            'data': data_atual.strftime('%d/%m/%Y'),
            'presentes': presentes,
            'faltas': faltas,
            'valor_total_faltas': valor_total_faltas,
            'refeicoes': refeicoes,
            'total_alunos': total_alunos,
            'bloqueados': bloqueados,
            'total_debitos': total_debitos
        })
    except Exception as e:
        print(f"Erro no relatório diário: {e}")
        return jsonify({
            'data': date.today().strftime('%d/%m/%Y'),
            'presentes': 0,
            'faltas': 0,
            'valor_total_faltas': 0,
            'refeicoes': {},
            'total_alunos': 0,
            'bloqueados': 0,
            'total_debitos': 0
        })
    
@app.route('/api/relatorios/geral', methods=['GET'])
def api_relatorio_geral():
    try:
        total_alunos = Aluno.query.count()
        total_faltas = db.session.query(db.func.sum(Aluno.total_faltas)).scalar() or 0
        total_debitos = db.session.query(db.func.sum(Aluno.debito)).scalar() or 0
        
        alunos_com_falta = Aluno.query.filter(Aluno.total_faltas > 0).count()
        alunos_com_debito = Aluno.query.filter(Aluno.debito > 0).count()
        bloqueados = Aluno.query.filter_by(bloqueado=True).count()
        
        # Top 10 com mais faltas
        top_faltas_query = Aluno.query.order_by(Aluno.total_faltas.desc()).limit(10).all()
        top_faltas = []
        for a in top_faltas_query:
            top_faltas.append({
                'nome': a.nome,
                'matricula': a.matricula,
                'faltas': a.total_faltas,
                'debito': a.debito,
                'curso': a.curso
            })
        
        # Totais por tipo de refeição
        refeicoes_stats = db.session.query(
            Historico.refeicao,
            db.func.count(Historico.id).label('total'),
            db.func.sum(Historico.valor).label('total_valor')
        ).filter(Historico.tipo == 'falta').group_by(Historico.refeicao).all()
        
        refeicoes = {}
        for r in refeicoes_stats:
            refeicoes[r.refeicao] = {
                'total': r.total,
                'valor_total': r.total_valor or 0
            }
        
        max_faltas = int(get_config('max_faltas') or 3)
        
        # Alunos em risco (próximos do bloqueio)
        em_risco = Aluno.query.filter(
            Aluno.total_faltas >= (max_faltas - 1),
            Aluno.total_faltas < max_faltas,
            Aluno.bloqueado == False
        ).count()
        
        return jsonify({
            'total_alunos': total_alunos,
            'total_faltas': total_faltas,
            'media_faltas': total_faltas / total_alunos if total_alunos > 0 else 0,
            'total_debitos': total_debitos,
            'alunos_com_falta': alunos_com_falta,
            'alunos_com_debito': alunos_com_debito,
            'bloqueados': bloqueados,
            'max_faltas': max_faltas,
            'em_risco': em_risco,
            'top_faltas': top_faltas,
            'refeicoes': refeicoes
        })
    except Exception as e:
        print(f"Erro no relatório geral: {e}")
        return jsonify({
            'total_alunos': 0,
            'total_faltas': 0,
            'media_faltas': 0,
            'total_debitos': 0,
            'alunos_com_falta': 0,
            'alunos_com_debito': 0,
            'bloqueados': 0,
            'max_faltas': 3,
            'em_risco': 0,
            'top_faltas': [],
            'refeicoes': {}
        })

@app.route('/api/relatorios/bloqueados', methods=['GET'])
def api_relatorio_bloqueados():
    try:
        bloqueados = Aluno.query.filter_by(bloqueado=True).all()
        result = []
        for a in bloqueados:
            result.append({
                'id': a.id,
                'nome': a.nome,
                'matricula': a.matricula,
                'curso': a.curso,
                'total_faltas': a.total_faltas,
                'debito': a.debito,
                'ultima_falta': a.ultima_falta_data.strftime('%d/%m/%Y') if a.ultima_falta_data else None
            })
        return jsonify(result)
    except Exception as e:
        print(f"Erro ao carregar bloqueados: {e}")
        return jsonify([])

@app.route('/api/relatorios/valores', methods=['GET'])
def api_relatorio_valores():
    try:
        # Valores configurados
        configuracoes = Configuracao.query.filter_by(tipo='refeicao').all()
        valores = {}
        for conf in configuracoes:
            nome = conf.descricao.replace('Valor do ', '')
            valores[nome] = float(conf.valor)
        
        # Estatísticas de uso
        stats = db.session.query(
            Historico.refeicao,
            db.func.count(Historico.id).label('total_faltas'),
            db.func.sum(Historico.valor).label('total_arrecadado')
        ).filter(Historico.tipo == 'falta').group_by(Historico.refeicao).all()
        
        uso = {}
        for s in stats:
            uso[s.refeicao] = {
                'faltas': s.total_faltas,
                'total': s.total_arrecadado or 0
            }
        
        return jsonify({
            'valores': valores,
            'uso': uso
        })
    except Exception as e:
        print(f"Erro no relatório de valores: {e}")
        return jsonify({'valores': {}, 'uso': {}})

@app.route('/api/relatorios/risco', methods=['GET'])
def api_relatorio_risco():
    try:
        max_faltas = int(get_config('max_faltas') or 3)
        limite_alerta = max_faltas - 1
        
        alunos_risco = Aluno.query.filter(
            Aluno.total_faltas >= limite_alerta,
            Aluno.total_faltas < max_faltas,
            Aluno.bloqueado == False
        ).all()
        
        result = []
        for aluno in alunos_risco:
            result.append({
                'id': aluno.id,
                'nome': aluno.nome,
                'matricula': aluno.matricula,
                'total_faltas': aluno.total_faltas,
                'faltas_restantes': max_faltas - aluno.total_faltas,
                'debito': aluno.debito
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Erro no relatório de risco: {e}")
        return jsonify([])

# ==================== API - CONFIGURAÇÕES ====================
@app.route('/api/configuracoes', methods=['GET'])
def api_configuracoes_get():
    configs = Configuracao.query.all()
    result = {}
    for c in configs:
        result[c.chave] = c.valor
    return jsonify(result)

@app.route('/api/configuracoes', methods=['POST'])
def api_configuracoes_post():
    data = request.json
    for chave, valor in data.items():
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = str(valor)
    db.session.commit()
    log_auditoria('Configurações atualizadas', 'sucesso')
    return jsonify({'success': True, 'message': 'Configurações salvas!'})

# ==================== API - ESTATÍSTICAS (DASHBOARD) ====================
@app.route('/api/estatisticas', methods=['GET'])
def api_estatisticas():
    try:
        total_alunos = Aluno.query.count()
        bloqueados = Aluno.query.filter_by(bloqueado=True).count()
        total_debitos = db.session.query(db.func.sum(Aluno.debito)).scalar() or 0
        total_faltas = db.session.query(db.func.sum(Aluno.total_faltas)).scalar() or 0
        
        max_faltas = int(get_config('max_faltas') or 3)
        em_risco = Aluno.query.filter(
            Aluno.total_faltas >= (max_faltas - 1),
            Aluno.total_faltas < max_faltas,
            Aluno.bloqueado == False
        ).count()
        
        data_atual = date.today()
        refeicoes_hoje = Historico.query.filter_by(data=data_atual, tipo='presenca').count()
        faltas_hoje = Historico.query.filter_by(data=data_atual, tipo='falta').count()
        
        valor_faltas_hoje = db.session.query(db.func.sum(Historico.valor)).filter(
            Historico.data == data_atual,
            Historico.tipo == 'falta'
        ).scalar() or 0
        
        return jsonify({
            'total_alunos': total_alunos,
            'bloqueados': bloqueados,
            'total_debitos': total_debitos,
            'total_faltas': total_faltas,
            'em_risco': em_risco,
            'refeicoes_hoje': refeicoes_hoje,
            'faltas_hoje': faltas_hoje,
            'valor_faltas_hoje': valor_faltas_hoje
        })
    except Exception as e:
        print(f"Erro ao carregar estatísticas: {e}")
        return jsonify({
            'total_alunos': 0,
            'bloqueados': 0,
            'total_debitos': 0,
            'total_faltas': 0,
            'em_risco': 0,
            'refeicoes_hoje': 0,
            'faltas_hoje': 0,
            'valor_faltas_hoje': 0
        })

# ==================== API - AUDITORIA ====================
@app.route('/api/auditoria', methods=['GET'])
def api_auditoria():
    logs = Auditoria.query.order_by(Auditoria.timestamp.desc()).limit(100).all()
    result = []
    for l in logs:
        result.append({
            'timestamp': l.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            'acao': l.acao,
            'tipo': l.tipo
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)