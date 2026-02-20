from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Aluno(db.Model):
    __tablename__ = 'aluno'
    
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    faltas_consecutivas = db.Column(db.Integer, default=0)
    total_faltas = db.Column(db.Integer, default=0)
    debito = db.Column(db.Float, default=0.0)
    bloqueado_ate = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    historico = db.relationship('Historico', backref='aluno', lazy=True, cascade='all, delete-orphan')
    pagamentos = db.relationship('Pagamento', backref='aluno', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'matricula': self.matricula,
            'nome': self.nome,
            'email': self.email,
            'faltas_consecutivas': self.faltas_consecutivas,
            'total_faltas': self.total_faltas,
            'debito': self.debito,
            'bloqueado_ate': self.bloqueado_ate.strftime('%Y-%m-%d') if self.bloqueado_ate else None
        }
    
    def __repr__(self):
        return f'<Aluno {self.matricula} - {self.nome}>'

class Historico(db.Model):
    __tablename__ = 'historico'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # agendamento, presenca, falta
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Historico {self.aluno_id} - {self.data} - {self.tipo}>'

class Pagamento(db.Model):
    __tablename__ = 'pagamento'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Pagamento {self.aluno_id} - R$ {self.valor}>'

class Configuracao(db.Model):
    __tablename__ = 'configuracao'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Config {self.chave} = {self.valor}>'

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(50), default='sistema')
    acao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), default='info')
    detalhes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Auditoria {self.timestamp} - {self.acao}>'