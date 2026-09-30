from app import db
from flask_login import UserMixin
from datetime import datetime
from enum import Enum as PyEnum  # ← CETTE LIGNE manquait !
from sqlalchemy.dialects.postgresql import JSON
# ─── Imports SQLAlchemy ──────────────────────────────────────────────────────
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time, Boolean, Float, Numeric,
    BigInteger, SmallInteger, Index, create_engine, func, text
)
from shapely.geometry import Point

from shapely import wkt
from shapely.geometry import Point
from shapely.wkt import loads

import psycopg2
from psycopg2.extras import RealDictCursor  # ← CETTE LIGNE !
import psycopg2.extras
from geoalchemy2 import Geometry  # ← Geometry ici !
from sqlalchemy import func, DateTime
from flask_sqlalchemy import SQLAlchemy


class StatutOrganisme(str, PyEnum):
    ACTIF = "actif"
    SUSPENDU = "suspendu"
    ARCHIVE = "archivé"

class TypeOrganisme(str, PyEnum):
    MRCC = "MRCC"
    MRSC = "MRSC"
    CROSS = "CROSS"
    DGMM = "DGMM"
    ARMADA = "ARMADA"
    HEMS = "HEMS"
    H24 = "H24"
    SOCIETE = "Société"
    ONG = "ONG"
    AUTORITE_LOCALE = "Autorité locale"
    AUTRE = "Autre"

class Organisme(db.Model):
    __tablename__ = 'organisme'
    __table_args__ = {'schema': 'mrcc'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code_organisme = Column(String(10), unique=True, nullable=False, index=True)
    nom = Column(String(100), nullable=False)
    nom_court = Column(String(20))
    
    # ✅ SOLUTION 1: db.Enum() (Flask-SQLAlchemy)
    type_organisme = db.Column(db.Enum(TypeOrganisme), nullable=False, index=True)
    
    telephone = Column(String(20))
    email = Column(String(100))
    site_web = Column(String(200))
    
    point_contact = Column(Geometry('POINT', srid=4326), index=True)
    adresse = Column(Text)
    
    zone_responsabilite = Column(Geometry('POLYGON', srid=4326), index=True)
    competences = Column(JSON)
    
    # ✅ SOLUTION 1: db.Enum()
    statut = db.Column(db.Enum(StatutOrganisme), default=StatutOrganisme.ACTIF, index=True)
    
    date_creation = Column(DateTime, server_default=func.now())
    date_modif = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    responsable_nom = Column(String(100))
    notes = Column(Text)
    
    def __repr__(self):
        return f"<Organisme(code='{self.code_organisme}', nom='{self.nom}')>"
    
    @property
    def coordonnees(self):
        if self.point_contact:
            return {'lat': self.point_contact.y, 'lon': self.point_contact.x}
        return None
    
    def to_dict(self):
        return {
            'id': self.id, 'code': self.code_organisme, 'nom': self.nom,
            'type': getattr(self.type_organisme, 'value', self.type_organisme),
            'coordonnees': self.coordonnees,
            'statut': getattr(self.statut, 'value', self.statut)
        }
