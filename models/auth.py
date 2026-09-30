from app import db
from flask_login import UserMixin
from datetime import datetime

class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'
    __table_args__ = {'schema': 'auth'}
    
    id = db.Column(db.Integer, primary_key=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    est_actif = db.Column(db.Boolean, default=True)
    derniere_connexion = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    personnel = db.relationship('Personnel', foreign_keys=[personnel_id])
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active(self):
        return self.est_actif
    
    def __repr__(self):
        return f'<Utilisateur {self.email}>'


class DroitAcces(db.Model):
    __tablename__ = 'droits_acces'
    __table_args__ = {'schema': 'auth'}
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    peut_lire = db.Column(db.Boolean, default=True)
    peut_creer = db.Column(db.Boolean, default=False)
    peut_modifier = db.Column(db.Boolean, default=False)
    peut_supprimer = db.Column(db.Boolean, default=False)
    peut_exporter = db.Column(db.Boolean, default=False)
    peut_imprimer = db.Column(db.Boolean, default=False)
    
    __table_args__ = (db.UniqueConstraint('role', 'module', name='unique_role_module'), {'schema': 'auth'})


class JournalAction(db.Model):
    __tablename__ = 'journal_actions'
    __table_args__ = {'schema': 'auth'}
    
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('auth.utilisateurs.id'))
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    utilisateur = db.relationship('Utilisateur', foreign_keys=[utilisateur_id])


class JournalConnexion(db.Model):
    __tablename__ = 'journal_connexions'
    __table_args__ = {'schema': 'auth'}
    
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('auth.utilisateurs.id'))
    email = db.Column(db.String(255))
    action = db.Column(db.String(50))  # CONNEXION, DECONNEXION, ECHEC
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    utilisateur = db.relationship('Utilisateur', foreign_keys=[utilisateur_id])
    
    def __repr__(self):
        return f'<JournalConnexion {self.email} - {self.action} - {self.created_at}>'