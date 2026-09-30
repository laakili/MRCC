from app import db
from flask_login import UserMixin
from datetime import datetime
from enum import Enum as PyEnum  # ← CETTE LIGNE manquait !

# ─── Imports SQLAlchemy ──────────────────────────────────────────────────────
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, Boolean, Float, Numeric,
    BigInteger, SmallInteger, Index, create_engine, func, text
)
# ─── Imports SQLAlchemy ──────────────────────────────────────────────────────
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, Boolean, Float, Numeric,
    BigInteger, SmallInteger, Index, create_engine, func, text
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON


#=============================================================================
#  CLASS ALERTES
#=============================================================================

class StatutAlerte(str, PyEnum):
    NOUVELLE = "nouvelle"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    ANNULEE = "annulee"

class NiveauUrgence(str, PyEnum):
    NORMAL = "normal"
    URGENT = "urgent"
    CRITIQUE = "critique"

class AlerteSauvetage(db.Model):
    __tablename__ = 'alertes_sauvetage'
    __table_args__ = {'schema': 'mrcc'}
    
    # Colonnes principales
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titre = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    date_creation = db.Column(db.DateTime, server_default=func.now())
    date_urgence = db.Column(db.DateTime)
    
    # Statut avec enum
    statut = db.Column(db.String(50), default='nouvelle')
    niveau_urgence = db.Column(db.String(50))
    
    # Position (numérique → POINT GeoAlchemy)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    precision_position = db.Column(db.String(100))
    
    # Incident
    type_incident = db.Column(db.String(100), nullable=False)
    nombre_personnes = db.Column(db.Integer)
    conditions_meteo = db.Column(db.Text)
    
    # Moyen alerte/navire
    moyen_alerte = db.Column(db.String(100))
    navire_implique = db.Column(db.String(255))
    immatriculation_navire = db.Column(db.String(50))
    
    # Métadonnées
    createur_id = db.Column(db.Integer)
    fichier_joint = db.Column(db.String(255))
    notes_complementaires = db.Column(db.Text)
    organisme_id = db.Column(db.Integer)
    
    # Propriétés calculées
    @property
    def position(self):
        """Retourne POINT geometry ou None"""
        if self.latitude and self.longitude:
            from geoalchemy2.shape import to_shape
            return f"POINT({self.longitude} {self.latitude})"
        return None
    
    @property
    def is_urgente(self):
        """True si urgente/critique"""
        return self.niveau_urgence in ['urgent', 'critique']
    
    @property
    def age_alerte(self):
        """Âge en heures"""
        if self.date_creation:
            return (datetime.now() - self.date_creation).total_seconds() / 3600
        return 0
    
    def to_dict(self):
        """JSON pour API/GeoJSON"""
        return {
            'id': self.id,
            'titre': self.titre,
            'description': self.description,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'date_urgence': self.date_urgence.isoformat() if self.date_urgence else None,
            'statut': self.statut,
            'niveau_urgence': self.niveau_urgence,
            'position': {
                'lat': float(self.latitude) if self.latitude else None,
                'lon': float(self.longitude) if self.longitude else None
            },
            'type_incident': self.type_incident,
            'nombre_personnes': self.nombre_personnes,
            'age_heure': round(self.age_alerte, 1),
            'is_urgente': self.is_urgente
        }
    
    def to_geojson(self):
        """GeoJSON Feature complète"""
        if not self.latitude or not self.longitude:
            return None
            
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(self.longitude), float(self.latitude)]
            },
            'properties': self.to_dict()
        }
    
    def __repr__(self):
        return f"<Alerte(id={self.id}, titre='{self.titre}', statut='{self.statut}')>"


class MiseAJourAlerte(db.Model):
    __tablename__ = 'mises_a_jour_alertes'
    __table_args__ = {'schema': 'mrcc'}
    
    # Colonnes
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alerte_id = db.Column(db.Integer, db.ForeignKey('mrcc.alertes_sauvetage.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('mrcc.users.id', ondelete='CASCADE'), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    statut_precedent = db.Column(db.String(50))
    nouveau_statut = db.Column(db.String(50))
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relations
    alerte = db.relationship('AlerteSauvetage', backref='mises_a_jour', lazy=True)
    # utilisateur = db.relationship('User', backref='mises_a_jour_alertes', lazy=True)
    
    def __init__(self, alerte_id, user_id, contenu, statut_precedent=None, nouveau_statut=None):
        self.alerte_id = alerte_id
        self.user_id = user_id
        self.contenu = contenu
        self.statut_precedent = statut_precedent
        self.nouveau_statut = nouveau_statut
        self.date_mise_a_jour = datetime.now()
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'alerte_id': self.alerte_id,
            'user_id': self.user_id,
            'contenu': self.contenu,
            'statut_precedent': self.statut_precedent,
            'nouveau_statut': self.nouveau_statut,
            'date_mise_a_jour': self.date_mise_a_jour.isoformat() if self.date_mise_a_jour else None,
            'utilisateur': {
                'id': self.utilisateur.id,
                'nom': self.utilisateur.nom,
                'prenom': self.utilisateur.prenom
            } if self.utilisateur else None
        }
    
    def __repr__(self):
        return f"<MiseAJourAlerte(id={self.id}, alerte_id={self.alerte_id}, date={self.date_mise_a_jour})>"
