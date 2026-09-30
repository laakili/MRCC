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


class RescueAsset(db.Model):
    __tablename__ = 'rescue_assets'
    __table_args__ = {'schema': 'mrcc'}

    asset_id      = db.Column(db.Integer, primary_key=True)
    geom          = db.Column(Geometry(geometry_type='POINT', srid=4326))
    latitude      = db.Column(db.Float, nullable=False)
    longitude     = db.Column(db.Float, nullable=False)
    asset_type    = db.Column(db.String(50))
    asset_name    = db.Column(db.String(100))
    asset_code    = db.Column(db.String(50), unique=True)
    base_location = db.Column(db.String(100))
    status        = db.Column(db.String(20), default='available')
    capacity      = db.Column(db.Integer)
    speed         = db.Column(db.Float)
    range_km      = db.Column(db.Float)
    crew_count    = db.Column(db.Integer, default=0)
    is_active     = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'asset_id':     self.asset_id,
            'asset_type':   self.asset_type,
            'asset_name':   self.asset_name,
            'asset_code':   self.asset_code,
            'base_location':self.base_location,
            'latitude':     self.latitude,
            'longitude':    self.longitude,
            'status':       self.status,
            'capacity':     self.capacity,
            'speed':        self.speed,
            'range_km':     self.range_km,
            'crew_count':   self.crew_count,
        }


class Ship(db.Model):
    __tablename__ = 'ships'

    ship_id     = db.Column(db.Text, primary_key=True)
    shipname    = db.Column(db.Text)
    lat         = db.Column(db.Float)
    lon         = db.Column(db.Float)
    speed       = db.Column(db.Float)
    course      = db.Column(db.Float)
    heading     = db.Column(db.Float)
    destination = db.Column(db.Text)
    flag        = db.Column(db.Text)
    shiptype    = db.Column(db.Text)
    type_name   = db.Column(db.Text)
    last_update = db.Column(db.DateTime)