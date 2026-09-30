from app import db
from flask_login import UserMixin
from datetime import datetime
from enum import Enum as PyEnum  # ← CETTE LIGNE manquait !

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
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy


class Event(db.Model):
    __tablename__ = 'event'
    __table_args__ = {'schema': 'evenements'}

    id    = Column(Integer, primary_key=True)
    point = Column(Geometry(geometry_type='POINT', srid=4326))

    name      = Column(String)
    libelle   = Column(Text)
    denom_fr  = Column(String)

    date_debut    = Column(Date)
    date_fin      = Column(Date)
    heure_debut   = Column(Time)
    heure_fin     = Column(Time)
    heure_control = Column(Time)
    heure_depat   = Column(Time)
    heure_entree  = Column(Time)

    id_type       = Column(Integer, nullable=False)
    id_propr      = Column(Integer, default=1)
    id_competence = Column(Integer, default=1)
    id_importance = Column(Integer, default=1)
    id_theme      = Column(Integer, default=1)

    pays      = Column(String)
    region    = Column(String)
    province  = Column(String)
    region_adm= Column(String)
    commune   = Column(String)
    caidat    = Column(String)
    cercle    = Column(String)
    douar     = Column(String)

    active     = Column(Boolean, default=True)
    reference  = Column(Text)
    web        = Column(String(300))
    photo      = Column(String(300))
    utilisateur= Column(Text)

    date_sys   = Column(Date)
    heure_sys  = Column(Time(timezone=True))
    date_creat = Column(Date)

    nbre_pers  = Column(Integer)
    nbre_mort  = Column(Integer)
    nbre_bl    = Column(Integer)

    situation  = Column(String(50))
    resume     = Column(Text)
    detail     = Column(Text)
    observation= Column(Text)
    lieu       = Column(Text)

    buffer     = Column(Float)
    magnitude  = Column(Float)

    id_event_parent     = Column(BigInteger, default=1)
    statut              = Column(String)
    ordre               = Column(Integer)
    pourcentage_maitrise= Column(Float)
    superficie_ha       = Column(Numeric)
    simulation          = Column(Boolean, default=False)
    rayon_buffer        = Column(Integer, default=50000)
    date_explorer       = Column(Date)


class VueTypeCategorieSectEvent(db.Model):
    __tablename__ = 'vue_type_categrie_sect_event'
    __table_args__ = {'schema': 'parameters'}

    id_type      = Column(Integer, primary_key=True)
    id_secteur   = Column(Integer)
    secteur      = Column(String)
    id_categorie = Column(Integer)
    categorie    = Column(String)
    type         = Column(String)
    mviewer      = Column(Boolean)


class RescueEvent(db.Model):
    __tablename__ = 'rescue_events'
    __table_args__ = {'schema': 'mrcc'}

    event_id     = db.Column(db.Integer, primary_key=True)
    event_number = db.Column(db.String(20), unique=True, nullable=False)
    event_type   = db.Column(db.String(50), nullable=False)
    status       = db.Column(db.String(20), default='active')
    priority     = db.Column(db.String(10), default='normal')

    geom              = db.Column(Geometry(geometry_type='POINT', srid=4326))
    latitude          = db.Column(db.Float, nullable=False)
    longitude         = db.Column(db.Float, nullable=False)
    location_name     = db.Column(db.String(200))
    distance_coast_km = db.Column(db.Float)

    description   = db.Column(db.Text)
    reported_by   = db.Column(db.String(100))
    report_time   = db.Column(db.DateTime, default=datetime.utcnow)
    incident_time = db.Column(db.DateTime)

    persons_involved = db.Column(db.Integer, default=1)
    persons_rescued  = db.Column(db.Integer, default=0)
    persons_deceased = db.Column(db.Integer, default=0)
    persons_missing  = db.Column(db.Integer, default=0)

    assets_deployed  = db.Column(db.JSON, default=list)
    assets_available = db.Column(db.JSON, default=list)

    wind_speed        = db.Column(db.Float)
    wind_direction    = db.Column(db.Float)
    current_speed     = db.Column(db.Float)
    current_direction = db.Column(db.Float)
    sea_state         = db.Column(db.Integer)
    visibility_km     = db.Column(db.Float)
    water_temperature = db.Column(db.Float)

    vessel_name = db.Column(db.String(100))
    vessel_type = db.Column(db.String(50))
    vessel_flag = db.Column(db.String(50))
    vessel_imo  = db.Column(db.String(20))
    vessel_mmsi = db.Column(db.String(20))

    created_by  = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    attachments = db.Column(db.JSON, default=list)
    notes       = db.Column(db.Text)
    action_log  = db.Column(db.JSON, default=list)

    def __repr__(self):
        return f'<RescueEvent {self.event_number}>'

    def to_dict(self):
        return {
            'event_id':          self.event_id,
            'event_number':      self.event_number,
            'event_type':        self.event_type,
            #'id_event_type':     self.id_event_type,  # Redondant pour faciliter les requêtes
            'status':            self.status,
            'priority':          self.priority,
            'latitude':          self.latitude,
            'longitude':         self.longitude,
            'location_name':     self.location_name,
            'distance_coast_km': self.distance_coast_km,
            'description':       self.description,
            'reported_by':       self.reported_by,
            'report_time':       self.report_time.isoformat() if self.report_time else None,
            'incident_time':     self.incident_time.isoformat() if self.incident_time else None,
            'persons_involved':  self.persons_involved,
            'persons_rescued':   self.persons_rescued,
            'persons_deceased':  self.persons_deceased,
            'persons_missing':   self.persons_missing,
            'assets_deployed':   self.assets_deployed,
            'wind_speed':        self.wind_speed,
            'wind_direction':    self.wind_direction,
            'current_speed':     self.current_speed,
            'current_direction': self.current_direction,
            'sea_state':         self.sea_state,
            'visibility_km':     self.visibility_km,
            'water_temperature': self.water_temperature,
            'vessel_name':       self.vessel_name,
            'vessel_type':       self.vessel_type,
            'vessel_flag':       self.vessel_flag,
            'vessel_imo':        self.vessel_imo,
            'vessel_mmsi':       self.vessel_mmsi,
            'created_by':        self.created_by,
            'assigned_to':       self.assigned_to,
            'created_at':        self.created_at.isoformat() if self.created_at else None,
            'updated_at':        self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at':       self.resolved_at.isoformat() if self.resolved_at else None,
            'notes':             self.notes,
        }


class RescueUpdate(db.Model):
    __tablename__ = 'rescue_updates'
    __table_args__ = {'schema': 'mrcc'}

    update_id      = db.Column(db.Integer, primary_key=True)
    event_id       = db.Column(db.Integer, db.ForeignKey('mrcc.rescue_events.event_id'))
    user_id        = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    update_type    = db.Column(db.String(50))
    content        = db.Column(db.Text)
    previous_value = db.Column(db.Text)
    new_value      = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'update_id':  self.update_id,
            'event_id':   self.event_id,
            'user_id':    self.user_id,
            'update_type':self.update_type,
            'content':    self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

