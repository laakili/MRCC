import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from typing import Optional
from shapely.geometry import Point  # for geometry(Point, 4326)

# =============================================================================
# app.py - Application Flask MRCC Maroc
# =============================================================================
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
# ─── Imports Standard ────────────────────────────────────────────────────────
import csv
import io
import json
import logging
import math
import os
import random
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from enum import Enum as PyEnum  # ← CETTE LIGNE manquait !

# ─── Imports Tiers ───────────────────────────────────────────────────────────
import base64
import binascii
import geopandas as gpd
import jwt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pickle
import psycopg2
from psycopg2.extras import RealDictCursor  # ← CETTE LIGNE !
import psycopg2.extras
import pytz
import requests
import seaborn as sns
import statistics

from decimal import Decimal
from geopy.distance import geodesic
from jinja2 import Template
from scipy.integrate import odeint
from shapely import wkt
from shapely.geometry import Point
from shapely.wkt import loads
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# ─── Imports Flask ───────────────────────────────────────────────────────────
from flask_caching import Cache
from flask import (
    Flask, Blueprint, Response, make_response, redirect, render_template,
    request, jsonify, send_file, session, stream_with_context, url_for, flash,
    current_app
)
from flask_cors import CORS
from flask_login import (
    LoginManager, UserMixin, current_user, login_required,
    login_user, logout_user
)
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer

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
# ─── Imports Dash ────────────────────────────────────────────────────────────
from dash import Output, Input, State, ctx

# ─── Imports Plotly ──────────────────────────────────────────────────────────
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio



from datetime import datetime, timedelta
import json
import qrcode
import base64
from io import BytesIO
from weasyprint import HTML
import tempfile
import os


from sqlalchemy import func, CheckConstraint  # ← CheckConstraint ici !
from datetime import datetime                # ← Pour age_alerte
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape       # ← Pour position()


# =============================================================================
# CONFIGURATION LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mrcc_maroc.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# INITIALISATION FLASK
# =============================================================================
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

app.secret_key = os.environ.get('FLASK_APP_SECRET_KEY', 'dev-secret-key-change-in-env')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-env')

# ─── Base de données ─────────────────────────────────────────────────────────
DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_NAME     = os.environ.get('DB_NAME', 'geoportal')
DB_USER     = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
DB_PORT     = os.environ.get('DB_PORT', '5432')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── Mail ─────────────────────────────────────────────────────────────────────
app.config['MAIL_SERVER']         = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
app.config['MAIL_PORT']           = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD']       = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = ('app', os.environ.get('MAIL_DEFAULT_SENDER', ''))

# ─── Upload ───────────────────────────────────────────────────────────────────
UPLOAD_FOLDER      = 'uploads/'
UPLOAD_FOLDER_ALERTE = 'uploads/alertes'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5052/')

# ─── Extensions ───────────────────────────────────────────────────────────────
db         = SQLAlchemy(app)
mail       = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# ─── Connexion DB (psycopg2) ──────────────────────────────────────────────────
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )

engine = create_engine(
    f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

# ─── Flask-Login ──────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# =============================================================================
# CONFIGURATION GEOSERVER
# =============================================================================
GEOSERVER_URL      = os.environ.get('GEOSERVER_URL', 'http://geoai-solutions.ddns.net:8888/georisque')
GEOSERVER_USER     = os.environ.get('GEOSERVER_USER', 'admin')
GEOSERVER_PASSWORD = os.environ.get('GEOSERVER_PASSWORD', 'geoserver')
WORKSPACE          = "geodata"
DATASTORE          = "uploads"


# =============================================================================
# CONFIGURATION MRCC / MARITIMES
# =============================================================================
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"
TIMEZONE       = pytz.timezone('Africa/Casablanca')

ZONES = {
    'tanger_med':        {'lat': 35.89, 'lon': -5.48,  'name': 'Tanger-Med'},
    'gibraltar':         {'lat': 35.90, 'lon': -5.30,  'name': 'Détroit de Gibraltar'},
    'tetouan':           {'lat': 35.57, 'lon': -5.37,  'name': "Tétouan / M'diq"},
    'al_hoceima':        {'lat': 35.24, 'lon': -3.93,  'name': 'Al Hoceïma'},
    'nador':             {'lat': 35.17, 'lon': -2.93,  'name': 'Nador / Beni Ensar'},
    'saidia':            {'lat': 35.10, 'lon': -2.25,  'name': 'Saidia'},
    'tanger_atlantique': {'lat': 35.78, 'lon': -5.83,  'name': 'Tanger Atlantique'},
    'larache':           {'lat': 35.19, 'lon': -6.15,  'name': 'Larache'},
    'kenitra':           {'lat': 34.26, 'lon': -6.66,  'name': 'Kénitra'},
    'rabat':             {'lat': 34.02, 'lon': -6.84,  'name': 'Rabat'},
    'casablanca':        {'lat': 33.59, 'lon': -7.61,  'name': 'Casablanca'},
    'el_jadida':         {'lat': 33.23, 'lon': -8.50,  'name': 'El Jadida'},
    'safi':              {'lat': 32.30, 'lon': -9.23,  'name': 'Safi'},
    'essaouira':         {'lat': 31.51, 'lon': -9.76,  'name': 'Essaouira'},
    'agadir':            {'lat': 30.42, 'lon': -9.60,  'name': 'Agadir'},
    'tan_tan':           {'lat': 28.44, 'lon': -11.10, 'name': 'Tan-Tan / El Ouatia'},
    'tarfaya':           {'lat': 27.94, 'lon': -12.91, 'name': 'Tarfaya'},
    'laayoune':          {'lat': 27.15, 'lon': -13.20, 'name': 'Laâyoune'},
    'boujdour':          {'lat': 26.14, 'lon': -14.49, 'name': 'Boujdour'},
    'dakhla':            {'lat': 23.69, 'lon': -15.95, 'name': 'Dakhla'},
    'lagouira':          {'lat': 21.37, 'lon': -17.03, 'name': 'Lagouira'},
}

MRCC_MAROC = {
    'name': 'Centre de Coordination de Sauvetage Maritime - Maroc',
    'center_coords': {'lat': 33.5731, 'lon': -7.5898},
    'zones': {
        'nord':         {'lat_min': 35.5, 'lat_max': 36.0, 'lon_min': -6.0,  'lon_max': -5.0},
        'centre':       {'lat_min': 33.0, 'lat_max': 34.5, 'lon_min': -8.0,  'lon_max': -6.5},
        'sud':          {'lat_min': 30.0, 'lat_max': 32.0, 'lon_min': -10.0, 'lon_max': -8.5},
        'mediterranee': {'lat_min': 35.0, 'lat_max': 36.0, 'lon_min': -5.5,  'lon_max': -2.0},
    }
}

MARITIME_ROUTES = [
    {
        'name': 'Route Tanger - Gibraltar', 'type': 'international',
        'waypoints': [
            {'lat': 35.9017, 'lon': -5.4833},
            {'lat': 36.1100, 'lon': -5.3450},
            {'lat': 36.1439, 'lon': -5.3531},
        ],
        'traffic_density': 'TRÈS ÉLEVÉE', 'max_vessels': 300, 'risk_level': 'CRITIQUE'
    },
    {
        'name': 'Route Atlantique Nord', 'type': 'cargo',
        'waypoints': [
            {'lat': 35.7667, 'lon': -5.8000},
            {'lat': 34.0333, 'lon': -6.8333},
            {'lat': 33.6000, 'lon': -7.6167},
            {'lat': 32.2833, 'lon': -9.2333},
            {'lat': 30.4167, 'lon': -9.6000},
        ],
        'traffic_density': 'ÉLEVÉE', 'max_vessels': 150, 'risk_level': 'ÉLEVÉ'
    },
    {
        'name': 'Route Côtière Méditerranéenne', 'type': 'côtière',
        'waypoints': [
            {'lat': 35.9000, 'lon': -5.4833},
            {'lat': 35.7833, 'lon': -5.8167},
            {'lat': 35.5667, 'lon': -5.3667},
            {'lat': 35.2000, 'lon': -4.2000},
            {'lat': 35.1000, 'lon': -2.3500},
        ],
        'traffic_density': 'MODÉRÉE', 'max_vessels': 80, 'risk_level': 'MODÉRÉ'
    },
]

FISHING_ZONES = [
    {
        'name': 'Zone de pêche Nord',
        'bounds': {'lat_min': 35.0, 'lat_max': 36.0, 'lon_min': -6.5, 'lon_max': -5.0},
        'fleet_size': 150, 'season': ['été', 'automne']
    },
    {
        'name': 'Zone de pêche Centre',
        'bounds': {'lat_min': 33.0, 'lat_max': 34.5, 'lon_min': -8.5, 'lon_max': -7.0},
        'fleet_size': 200, 'season': ["toute l'année"]
    },
    {
        'name': 'Zone de pêche Sud',
        'bounds': {'lat_min': 30.0, 'lat_max': 32.0, 'lon_min': -10.5, 'lon_max': -9.0},
        'fleet_size': 120, 'season': ['printemps', 'été']
    },
]

DRIFT_COEFFICIENTS = {
    'person':           {'wind_effect': 0.03,  'current_effect': 1.0,  'leeway_angle': 2.0,  'windage': 0.5, 'description': 'Personne en mer avec gilet'},
    'life_raft':        {'wind_effect': 0.04,  'current_effect': 0.95, 'leeway_angle': 1.5,  'windage': 0.8, 'description': 'Radeau de sauvetage gonflable'},
    'lifeboat':         {'wind_effect': 0.02,  'current_effect': 0.9,  'leeway_angle': 1.0,  'windage': 0.3, 'description': 'Canot de sauvetage rigide'},
    'fishing_vessel':   {'wind_effect': 0.01,  'current_effect': 0.92, 'leeway_angle': 0.8,  'windage': 0.4, 'description': 'Bateau de pêche < 15m'},
    'cargo_container':  {'wind_effect': 0.02,  'current_effect': 0.98, 'leeway_angle': 0.5,  'windage': 0.6, 'description': 'Conteneur flottant'},
    'yacht':            {'wind_effect': 0.025, 'current_effect': 0.88, 'leeway_angle': 1.2,  'windage': 0.7, 'description': 'Voilier de plaisance'},
}

SEA_STATE_FACTORS = {
    1: {'name': 'Calme',       'wave_height': 0.1,  'leeway_multiplier': 0.5},
    2: {'name': 'Peu agitée',  'wave_height': 0.5,  'leeway_multiplier': 0.75},
    3: {'name': 'Agitée',      'wave_height': 1.25, 'leeway_multiplier': 1.0},
    4: {'name': 'Très agitée', 'wave_height': 2.5,  'leeway_multiplier': 1.25},
    5: {'name': 'Grosse mer',  'wave_height': 4.0,  'leeway_multiplier': 1.5},
}

SEARCH_PATTERNS = {
    'expanding_square': {'description': 'Carré expansif - recherche initiale',    'leg_spacing': 0.5, 'max_legs': 8},
    'sector_search':    {'description': 'Recherche sectorielle - point de référence', 'radius': 2.0, 'sectors': 8},
    'parallel_track':   {'description': 'Traces parallèles - grande zone',        'track_spacing': 0.3, 'sweep_width': 0.5},
    'shoreline_search': {'description': 'Recherche côtière',                       'distance_offshore': 1.0, 'pattern': 'zigzag'},
}

MRCC_ASSETS = {
    'vessels': [
        {'name': 'Patrouilleur Al Bachir', 'type': 'patrol',  'speed': 25, 'range': 500},
        {'name': 'Remorqueur Ibn Tofaïl',  'type': 'tug',     'speed': 15, 'range': 300},
        {'name': 'Vedette côtière',        'type': 'coastal', 'speed': 30, 'range': 150},
    ],
    'aircraft': [
        {'name': 'Hélicoptère Dauphin', 'type': 'helicopter',  'speed': 140, 'range': 400},
        {'name': 'Avion CASA CN-235',   'type': 'fixed_wing',  'speed': 250, 'range': 1000},
    ]
}

MAROD_DATA = {
    "depths": [
        {"lat": 35.7796, "lon": -5.8033, "depth": 12.5},
        {"lat": 33.5731, "lon": -7.5898, "depth": 8.2},
        {"lat": 31.5144, "lon": -9.7695, "depth": 15.7},
        {"lat": 28.4326, "lon": -11.1000, "depth": 22.3},
    ],
    "hazards": [
        {"type": "rock",  "lat": 35.7810, "lon": -5.8050, "description": "Rocher submergé"},
        {"type": "wreck", "lat": 33.5750, "lon": -7.5910, "description": "Épave à 10m de profondeur"},
    ],
    "navigation_aids": [
        {"type": "buoy",        "lat": 35.7800, "lon": -5.8000, "name": "Bouée Tanger"},
        {"type": "lighthouse",  "lat": 33.6000, "lon": -7.6000, "name": "Phare Casablanca"},
    ]
}


# =============================================================================
# MODÈLES SQLALCHEMY
# =============================================================================

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



class RescueResource:
    def __init__(
        self,
        resource_id: int,
        resource_name: str,
        type_id: int,
        base_id: int,
        identifier_code: str,
        operational_status: str = "available",
        max_capacity: Optional[int] = None,
        operational_range: Optional[int] = None,
        speed: Optional[int] = None,
        last_maintenance_date: Optional[date] = None,
        next_maintenance_date: Optional[date] = None,
        current_position: Optional[Point] = None,
        current_status: Optional[str] = None,
        is_active: bool = True,
        added_date: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
    ):
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.type_id = type_id
        self.base_id = base_id
        self.identifier_code = identifier_code
        self.operational_status = operational_status
        self.max_capacity = max_capacity
        self.operational_range = operational_range
        self.speed = speed
        self.last_maintenance_date = last_maintenance_date
        self.next_maintenance_date = next_maintenance_date
        self.current_position = current_position
        self.current_status = current_status
        self.is_active = is_active
        self.added_date = added_date or datetime.now()
        self.last_updated = last_updated or datetime.now()

    @classmethod
    def from_db_row(cls, row):
        # Example: row from a SELECT * on mrcc.rescue_resources
        # row[0] → resource_id, row[1] → resource_name, etc.
        return cls(
            resource_id=row[0],
            resource_name=row[1],
            type_id=row[2],
            base_id=row[3],
            identifier_code=row[4],
            operational_status=row[5],
            max_capacity=row[6],
            operational_range=row[7],
            speed=row[8],
            last_maintenance_date=row[9],
            next_maintenance_date=row[10],
            current_position=Point(row[11]) if row[11] else None,  # assumes WKB/Point from DB
            current_status=row[12],
            is_active=row[13],
            added_date=row[14],
            last_updated=row[15],
        )

    def __repr__(self):
        return (
            f"RescueResource(id={self.resource_id}, "
            f"name={self.resource_name}, "
            f"status={self.operational_status})"
        )



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


from flask_login import UserMixin

#=============================================================================
#  CLASS AUTENTIFICATION
#=============================================================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'mrcc'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    fonction = db.Column(db.String(255), nullable=False)
    organisme = db.Column(db.String(255), nullable=False)
    type_organisme = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'telephone': self.telephone,
            'email': self.email,
            'fonction': self.fonction,
            'organisme': self.organisme,
            'type_organisme': self.type_organisme,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

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


class AlerteHistory:
    def __init__(
        self,
        id: int,
        alerte_id: int,
        action: str,
        description: Optional[str] = None,
        details: Optional[dict] = None,
        user_id: Optional[int] = None,
        date_action: Optional[datetime] = None,
    ):
        self.id = id
        self.alerte_id = alerte_id
        self.action = action
        self.description = description
        self.details = details or {}
        self.user_id = user_id
        self.date_action = date_action or datetime.now()

    @classmethod
    def from_db_row(cls, row):
        # Exemple : row = (id, alerte_id, action, description, details, user_id, date_action)
        return cls(
            id=row[0],
            alerte_id=row[1],
            action=row[2],
            description=row[3],
            details=json.loads(row[4]) if row[4] else {},
            user_id=row[5],
            date_action=row[6],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "alerte_id": self.alerte_id,
            "action": self.action,
            "description": self.description,
            "details": self.details,
            "user_id": self.user_id,
            "date_action": self.date_action,
        }

    def __repr__(self):
        return (
            f"AlerteHistory(id={self.id}, "
            f"alerte_id={self.alerte_id}, "
            f"action={self.action}, "
            f"date_action={self.date_action})"
        )
#=============================================================================
#  CLASS ORGANISME
#=============================================================================  

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

# =============================================================================
# ROUTES API - GESTION DES BALISES PLB (CRUD)
# =============================================================================
from sqlalchemy import func, and_, or_

# Configuration du cache
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})

class BalisePLB(db.Model):
    """Modèle pour les balises PLB - Version optimisée"""
    __tablename__ = 'mrcc_temple_plb'
    __table_args__ = (
        Index('idx_balise_registration', 'registration_number'),
        Index('idx_balise_mmsi', 'mmsi'),
        Index('idx_balise_uin', 'uin'),
        Index('idx_balise_status', 'beacon_status'),
        Index('idx_balise_owner', 'owner'),
        {'schema': 'mrcc'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(100))
    unit_name = db.Column(db.String(200))
    port = db.Column(db.String(100))
    mmsi = db.Column(db.String(20))
    tac = db.Column(db.Integer)
    activity_type = db.Column(db.String(100))
    uin = db.Column(db.String(50))
    serial_number_manufacturer = db.Column(db.BigInteger)
    serial_number_sar = db.Column(db.Integer)
    registration_date = db.Column(db.String(20))
    battery_expiration_date = db.Column(db.String(20))
    manufacturer = db.Column(db.String(100))
    beacon_type = db.Column(db.String(50))
    model = db.Column(db.String(100))
    beacon_status = db.Column(db.String(50))
    owner = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone_number = db.Column(db.String(50))
    secondary_phone_number = db.Column(db.String(50))
    address = db.Column(db.Text)
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone_number = db.Column(db.String(50))
    secondary_emergency_contact_name = db.Column(db.String(200))
    secondary_emergency_contact_phone_number = db.Column(db.String(50))
    field_25 = db.Column(db.String(500))
    id_port = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Version complète pour les détails"""
        return {
            'id': self.id,
            'registration_number': self.registration_number,
            'unit_name': self.unit_name,
            'port': self.port,
            'mmsi': self.mmsi,
            'tac': self.tac,
            'activity_type': self.activity_type,
            'uin': self.uin,
            'serial_number_manufacturer': self.serial_number_manufacturer,
            'serial_number_sar': self.serial_number_sar,
            'registration_date': self.registration_date,
            'battery_expiration_date': self.battery_expiration_date,
            'manufacturer': self.manufacturer,
            'beacon_type': self.beacon_type,
            'model': self.model,
            'beacon_status': self.beacon_status,
            'owner': self.owner,
            'email': self.email,
            'phone_number': self.phone_number,
            'secondary_phone_number': self.secondary_phone_number,
            'address': self.address,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone_number': self.emergency_contact_phone_number,
            'secondary_emergency_contact_name': self.secondary_emergency_contact_name,
            'secondary_emergency_contact_phone_number': self.secondary_emergency_contact_phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict_light(self):
        """Version légère pour les listes (optimisée)"""
        return {
            'id': self.id,
            'registration_number': self.registration_number,
            'unit_name': self.unit_name,
            'mmsi': self.mmsi,
            'uin': self.uin,
            'beacon_status': self.beacon_status,
            'owner': self.owner,
            'manufacturer': self.manufacturer,
            'battery_expiration_date': self.battery_expiration_date
        }


class PLBHistory(db.Model):
    """Historique des modifications PLB - Traçabilité complète"""
    __tablename__ = 'plb_history'
    __table_args__ = (
        Index('idx_plb_history_plb_id', 'plb_id'),
        Index('idx_plb_history_action', 'action'),
        Index('idx_plb_history_created_at', 'created_at'),
        {'schema': 'mrcc'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    plb_id = db.Column(db.Integer, db.ForeignKey('mrcc.mrcc_temple_plb.id'))
    action = db.Column(db.String(50))  # CREATION, MODIFICATION, TRANSFERT, TEST, MAINTENANCE, DECOMMISSION
    field_changed = db.Column(db.String(100))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    comment = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    user_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plb_id': self.plb_id,
            'action': self.action,
            'field_changed': self.field_changed,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'comment': self.comment,
            'user_name': self.user_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PLBTransfer(db.Model):
    """Traçabilité des transferts de propriété/navire"""
    __tablename__ = 'plb_transfers'
    __table_args__ = (
        Index('idx_plb_transfer_plb_id', 'plb_id'),
        Index('idx_plb_transfer_date', 'transfer_date'),
        {'schema': 'mrcc'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    plb_id = db.Column(db.Integer, db.ForeignKey('mrcc.mrcc_temple_plb.id'))
    transfer_date = db.Column(db.DateTime, default=datetime.utcnow)
    transfer_type = db.Column(db.String(50))  # OWNER_CHANGE, VESSEL_CHANGE, BOTH
    
    # Anciennes informations
    old_owner = db.Column(db.String(200))
    old_owner_email = db.Column(db.String(200))
    old_owner_phone = db.Column(db.String(50))
    old_vessel_name = db.Column(db.String(200))
    old_vessel_mmsi = db.Column(db.String(20))
    
    # Nouvelles informations
    new_owner = db.Column(db.String(200))
    new_owner_email = db.Column(db.String(200))
    new_owner_phone = db.Column(db.String(50))
    new_vessel_name = db.Column(db.String(200))
    new_vessel_mmsi = db.Column(db.String(20))
    
    # Documents
    transfer_document = db.Column(db.String(500))  # Chemin du PDF de transfert
    old_registration_certificate = db.Column(db.String(500))
    new_registration_certificate = db.Column(db.String(500))
    
    comment = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    created_by_name = db.Column(db.String(200))
    
    def to_dict(self):
        return {
            'id': self.id,
            'plb_id': self.plb_id,
            'transfer_date': self.transfer_date.isoformat() if self.transfer_date else None,
            'transfer_type': self.transfer_type,
            'old_owner': self.old_owner,
            'old_owner_email': self.old_owner_email,
            'old_vessel_name': self.old_vessel_name,
            'old_vessel_mmsi': self.old_vessel_mmsi,
            'new_owner': self.new_owner,
            'new_owner_email': self.new_owner_email,
            'new_vessel_name': self.new_vessel_name,
            'new_vessel_mmsi': self.new_vessel_mmsi,
            'comment': self.comment,
            'created_by_name': self.created_by_name,
            'transfer_document': self.transfer_document
        }


class PLBMaintenance(db.Model):
    """Suivi des maintenances et tests PLB"""
    __tablename__ = 'plb_maintenance'
    __table_args__ = (
        Index('idx_plb_maintenance_plb_id', 'plb_id'),
        Index('idx_plb_maintenance_date', 'maintenance_date'),
        {'schema': 'mrcc'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    plb_id = db.Column(db.Integer, db.ForeignKey('mrcc.mrcc_temple_plb.id'))
    maintenance_type = db.Column(db.String(50))  # TEST_MENSUEL, BATTERY_CHANGE, INSPECTION, REPAIR
    maintenance_date = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(200))
    result = db.Column(db.String(50))  # OK, NOK, PENDING
    notes = db.Column(db.Text)
    
    # Pour batterie
    battery_type = db.Column(db.String(50))
    battery_serial = db.Column(db.String(100))
    new_expiry_date = db.Column(db.Date)
    
    # Pour test
    test_signal_received = db.Column(db.Boolean, default=False)
    gps_fix_ok = db.Column(db.Boolean, default=False)
    signal_strength = db.Column(db.Integer)  # dBm
    
    document = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('mrcc.users.id'))
    created_by_name = db.Column(db.String(200))
    
    def to_dict(self):
        return {
            'id': self.id,
            'plb_id': self.plb_id,
            'maintenance_type': self.maintenance_type,
            'maintenance_date': self.maintenance_date.isoformat() if self.maintenance_date else None,
            'performed_by': self.performed_by,
            'result': self.result,
            'notes': self.notes,
            'battery_type': self.battery_type,
            'battery_serial': self.battery_serial,
            'new_expiry_date': self.new_expiry_date.isoformat() if self.new_expiry_date else None,
            'test_signal_received': self.test_signal_received,
            'gps_fix_ok': self.gps_fix_ok,
            'signal_strength': self.signal_strength,
            'document': self.document,
            'created_by_name': self.created_by_name
        }


class PLBNotification(db.Model):
    """Notifications PLB (tests, expirations)"""
    __tablename__ = 'plb_notifications'
    __table_args__ = (
        Index('idx_plb_notification_plb_id', 'plb_id'),
        Index('idx_plb_notification_status', 'status'),
        Index('idx_plb_notification_scheduled_date', 'scheduled_date'),
        {'schema': 'mrcc'}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    plb_id = db.Column(db.Integer, db.ForeignKey('mrcc.mrcc_temple_plb.id'))
    notification_type = db.Column(db.String(50))  # TEST_DUE, BATTERY_EXPIRY, INSPECTION_DUE, TRANSFER_CONFIRM
    message = db.Column(db.Text)
    scheduled_date = db.Column(db.Date)
    sent_at = db.Column(db.DateTime)
    sent_to = db.Column(db.String(500))
    status = db.Column(db.String(20), default='PENDING')  # PENDING, SENT, FAILED, CANCELLED
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plb_id': self.plb_id,
            'notification_type': self.notification_type,
            'message': self.message,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'sent_to': self.sent_to,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }




# =============================================================================
# FLASK-LOGIN
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =============================================================================
# HELPERS
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_table_name(filename):
    table_name = filename.lower()
    table_name = re.sub(r'[^a-z0-9\s]', '', table_name)
    table_name = re.sub(r'\s+', '_', table_name)
    return table_name


def send_email(subject, recipient, body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        logger.info(f"Email envoyé à {recipient}")
    except Exception as e:
        logger.error(f"Erreur envoi email : {e}")


def convert_point(blob):
    """Convertir une colonne POINT binaire en dict latitude/longitude."""
    if blob and isinstance(blob, (bytes, bytearray)):
        hex_str = binascii.hexlify(blob).decode()
        try:
            lat = int(hex_str[16:24], 16) / 1_000_000
            lon = int(hex_str[24:32], 16) / 1_000_000
            return {'latitude': lat, 'longitude': lon}
        except Exception:
            return None
    return None


def make_serializable(obj):
    """Rendre un objet sérialisable en JSON (numpy, dict, list)."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    return obj

@app.context_processor
def inject_now():
    return {'today': datetime.now()}
# =============================================================================
# ROUTES — AUTHENTIFICATION
# =============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name     = request.form['first_name']
        last_name      = request.form['last_name']
        telephone      = request.form['telephone']
        email          = request.form['email']
        username       = request.form['username']
        password       = generate_password_hash(request.form['password'])
        fonction       = request.form['fonction']
        organisme      = request.form['organisme']
        type_organisme = request.form['type_organisme']

        try:
            conn   = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mrcc.users
                  (first_name, last_name, telephone, email, username, password,
                   fonction, organisme, type_organisme)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (first_name, last_name, telephone, email, username, password,
                  fonction, organisme, type_organisme))
            conn.commit()
            conn.close()

            token       = serializer.dumps(email, salt='email-confirmation')
            confirm_url = f"{BASE_URL}/confirm/{token}"
            send_email(
                "Confirmez votre adresse email",
                email,
                f"Bonjour {first_name},\n\nCliquez ici pour valider votre email :\n{confirm_url}"
            )
            flash("Un email de validation a été envoyé.", "info")
            return redirect(url_for('login'))
        except psycopg2.Error as e:
            flash(f"Erreur lors de l'enregistrement : {e.pgerror}", "error")

    return render_template('register.html')


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email  = serializer.loads(token, salt='email-confirmation', max_age=3600)
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE mrcc.users SET is_active = TRUE WHERE email = %s", (email,)
        )
        conn.commit()
        conn.close()
        flash("Email validé. Vous pouvez vous connecter.", "success")
        return redirect(url_for('login'))
    except Exception:
        flash("Lien de validation invalide ou expiré.", "error")
        return redirect(url_for('register'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password, first_name, last_name, telephone,
                   email, fonction, organisme, type_organisme, is_active
            FROM mrcc.users WHERE username = %s
        """, (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            if not user_data[10]:
                flash("Veuillez valider votre email avant de vous connecter.", "error")
                return redirect(url_for('login'))
            if check_password_hash(user_data[2], password):
                user = User.query.get(user_data[0])
                login_user(user)
                flash("Connexion réussie!", "success")
                return redirect(url_for('index'))
            else:
                flash("Mot de passe incorrect.", "error")
        else:
            flash("Nom d'utilisateur incorrect.", "error")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Déconnexion réussie!", "success")
    return redirect(url_for('login'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        conn  = get_db_connection()
        cursor= conn.cursor()
        cursor.execute("SELECT * FROM mrcc.users WHERE email = %s", (email,))
        user  = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            token     = serializer.dumps(email, salt='password-reset-salt')
            reset_url = f"{BASE_URL}/reset_password/{token}"
            msg = Message('Réinitialisation de mot de passe',
                          sender='soufiomario@gmail.com', recipients=[email])
            msg.body = f'Cliquez sur le lien pour réinitialiser votre mot de passe : {reset_url}'
            mail.send(msg)
            flash('Un lien de réinitialisation a été envoyé.', 'success')
        else:
            flash("Aucun utilisateur associé à cet e-mail.", 'danger')

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash("Le lien de réinitialisation a expiré ou est invalide.", 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password     = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", 'danger')
        else:
            hashed = generate_password_hash(new_password)
            conn   = get_db_connection()
            cursor = conn.cursor()
            # FIX : ajout du WHERE email = %s manquant dans le code original
            cursor.execute(
                "UPDATE mrcc.users SET password = %s WHERE email = %s",
                (hashed, email)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Mot de passe réinitialisé avec succès.', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html')


# =============================================================================
# ROUTES — TABLEAU DE BORD UTILISATEUR
# =============================================================================

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = current_user.id
    conn    = get_db_connection()
    cursor  = conn.cursor()

    cursor.execute("""
        SELECT email, first_name, last_name, telephone, fonction, organisme, type_organisme
        FROM mrcc.users WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        if 'update_info' in request.form:
            cursor.execute("""
                UPDATE mrcc.users
                SET email=%s, first_name=%s, last_name=%s, telephone=%s,
                    fonction=%s, organisme=%s, type_organisme=%s
                WHERE id=%s
            """, (
                request.form['email'], request.form['first_name'],
                request.form['last_name'], request.form['telephone'],
                request.form['fonction'], request.form['organisme'],
                request.form['type_organisme'], user_id
            ))
            conn.commit()
            flash("Informations mises à jour.", 'success')

        elif 'change_password' in request.form:
            old_pw   = request.form['old_password']
            new_pw   = request.form['new_password']
            conf_pw  = request.form['confirm_password']
            cursor.execute("SELECT password FROM mrcc.users WHERE id=%s", (user_id,))
            stored   = cursor.fetchone()[0]

            if not check_password_hash(stored, old_pw):
                flash("Ancien mot de passe incorrect.", 'danger')
            elif new_pw != conf_pw:
                flash("Les nouveaux mots de passe ne correspondent pas.", 'danger')
            else:
                cursor.execute(
                    "UPDATE mrcc.users SET password=%s WHERE id=%s",
                    (generate_password_hash(new_pw), user_id)
                )
                conn.commit()
                flash("Mot de passe modifié.", 'success')

    cursor.close()
    conn.close()
    return render_template('dashboard.html', user=user)


# =============================================================================
# ROUTES — DONNÉES PARTENAIRES
# =============================================================================

@app.route("/afficher_donnees")
@login_required
def afficher_donnees():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM donnees_partenaires")
    donnees = cur.fetchall()
    cur.close(); conn.close()
    return render_template("donnees_partenaires.html", donnees=donnees)


@app.route("/donnees")
@login_required
def donnees():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM donnees_partenaires WHERE organisme = %s", (current_user.organisme,))
    donnees = cur.fetchall()
    cur.close(); conn.close()
    return render_template("donnees.html", donnees=donnees)


@app.route("/supprimer_donnee/<int:id>")
@login_required
def supprimer_donnee(id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM donnees_partenaires WHERE id = %s", (id,))
    conn.commit()
    cur.close(); conn.close()
    flash("Donnée supprimée avec succès !", "danger")
    return redirect(url_for("afficher_donnees"))


@app.route("/ajouter_donnee", methods=["GET", "POST"])
@login_required
def ajouter_donnee():
    if request.method == "POST":
        fields = [
            'nom_donnee', 'territoire', 'descriptif', 'sommaire', 'type_donnee',
            'format_donnee', 'taille_moyenne', 'producteur', 'users_cas_usage',
            'periode_couverte', 'frequence_donnee', 'frequence_maj',
            'taille_historique', 'mode_acces', 'qualite', 'contraintes_obs'
        ]
        values = [request.form[f] for f in fields]
        reference  = request.form.get("reference", False)
        user_saisie= current_user.username
        organisme  = current_user.organisme

        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO donnees_partenaires
              (nom_donnee, territoire, descriptif, sommaire, type_donnee, format_donnee,
               taille_moyenne, producteur, users_cas_usage, periode_couverte,
               frequence_donnee, frequence_maj, taille_historique, mode_acces,
               qualite, contraintes_obs, reference, user_saisie, organisme)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (*values, reference, user_saisie, organisme))
        conn.commit()
        cur.close(); conn.close()
        flash("Donnée ajoutée avec succès !", "success")
        return redirect(url_for("afficher_donnees"))

    return render_template("ajouter_donnee.html")


@app.route("/modifier_donnees/<int:id>", methods=["GET", "POST"])
@login_required
def modifier_donnees(id):
    conn = get_db_connection()
    cur  = conn.cursor()

    if request.method == "POST":
        reference = request.form.get("reference", False)
        cur.execute("""
            UPDATE donnees_partenaires
            SET nom=%s, territoire=%s, descriptif=%s, sommaire=%s, type=%s,
                format=%s, taille=%s, producteur=%s, cas_usage=%s, periode=%s,
                frequence=%s, maj=%s, taille_historique=%s, acces=%s,
                qualite=%s, contraintes=%s, reference=%s
            WHERE id=%s
        """, (
            request.form["nom"], request.form["territoire"], request.form["descriptif"],
            request.form["sommaire"], request.form["type"], request.form["format"],
            request.form["taille"], request.form["producteur"], request.form["cas_usage"],
            request.form["periode"], request.form["frequence"], request.form["maj"],
            request.form["taille_historique"], request.form["acces"],
            request.form["qualite"], request.form["contraintes"], reference, id
        ))
        conn.commit()
        cur.close(); conn.close()
        flash("Donnée modifiée avec succès !", "success")
        return redirect(url_for("liste_donnees"))

    cur.execute("SELECT * FROM donnees_partenaires WHERE id = %s", (id,))
    donnee = cur.fetchone()
    cur.close(); conn.close()

    if not donnee:
        flash("Donnée introuvable !", "danger")
        return redirect(url_for("donnees"))

    return render_template("modifier_donnee.html", donnee=donnee)


# =============================================================================
# ROUTES — PAGES SIMPLES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/alerte')
def alerte():
    return render_template('alertes/mes_alertes.html')

@app.route('/api')
def api():
    return render_template('api.html')

@app.route('/marine')
def marine():
    return render_template('marine.html')

@app.route('/moyens')
def moyens():
    return render_template('moyens.html')

@app.route('/integrer')
def integrer():
    return render_template('integrer.html')

@app.route('/meteo')
def meteo():
    return render_template('meteo.html')

@app.route('/geoportal')
def geoportal():
    return render_template('geoportail_sar.html')

@app.route('/offshore')
def offshore():
    return render_template('offshore.html')

@app.route('/ocean')
def ocean():
    return render_template('ocean.html')

@app.route('/cartes')
def cartes():
    return render_template('cartes.html')

@app.route('/marine_traffic')
def marine_traffic():
    return render_template('marine_traffic.html')

@app.route('/derive-guide')
@login_required
def derive_guide():
    return render_template('derive_guide.html')

@app.route('/simulate_derive')
def simulate_derive():
    return render_template('simulate.html',
                           coefficients=DRIFT_COEFFICIENTS,
                           object_types=DRIFT_COEFFICIENTS.keys())

@app.route('/dashboard_derive')
def dashboard_derive():
    return render_template('dashboard.html',
                           mrcc_info=MRCC_MAROC,
                           routes=MARITIME_ROUTES)

@app.route('/rescue-events')
@login_required
def rescue_events():
    return render_template('rescue_events.html')

@app.route('/recherche-balises')
def recherche_balises():
    logger.info("=== PAGE RECHERCHE BALISES ACCEDEE ===")
    return render_template('recherche_balises.html')


# =============================================================================
# ROUTES — DROITS D'ACCÈS
# =============================================================================

@app.route('/gestion_droits', methods=['GET', 'POST'])
@login_required
def gestion_droits():
    user_s = current_user.organisme
    conn   = get_db_connection()
    cur    = conn.cursor()
    cur.execute("SELECT id, nom_donnee FROM donnees_partenaires WHERE organisme = %s", (user_s,))
    donnees = cur.fetchall()

    if request.method == 'POST':
        id_donnee              = request.form['id_donnee']
        organismes_beneficiaires = request.form.getlist('organisme_beneficiaire')
        droit_acces            = request.form['droit_acces']

        for org in organismes_beneficiaires:
            cur.execute("""
                INSERT INTO droits_acces (id_donnee, organisme_proprietaire, organisme_beneficiaire, droit_acces)
                VALUES (%s, %s, %s, %s)
            """, (id_donnee, user_s, org, droit_acces))

        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('gestion_droits'))

    cur.execute("""
        SELECT da.id, dp.nom_donnee, da.organisme_proprietaire, da.organisme_beneficiaire, da.droit_acces
        FROM droits_acces da
        JOIN donnees_partenaires dp ON da.id_donnee = dp.id
    """)
    droits = cur.fetchall()
    cur.close(); conn.close()
    return render_template('droits_acces.html', donnees=donnees, droits=droits)


# =============================================================================
# ROUTES — ALERTES SAUVETAGE
# =============================================================================


@app.route("/api/notifications")
@login_required
def get_notifications():
    """Récupère les notifications (alertes non lues)"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer les alertes non lues ou récentes (moins de 24h)
            cur.execute("""
                SELECT 
                    a.id,
                    a.titre,
                    a.description,
                    a.date_creation,
                    a.niveau_urgence,
                    a.type_incident,
                    a.statut,
                    a.latitude,
                    a.longitude,
                    a.marque_lu,
                    u.nom as createur_nom,
                    u.prenom as createur_prenom
                FROM mrcc.alertes_sauvetage a
                LEFT JOIN mrcc.users u ON a.createur_id = u.id
                WHERE (a.marque_lu = false OR a.marque_lu IS NULL)
                    AND a.statut != 'terminee'
                ORDER BY a.date_creation DESC
                LIMIT 20
            """)
            notifications = cur.fetchall()
            
            # Compter le nombre de notifications non lues
            cur.execute("""
                SELECT COUNT(*) as count
                FROM mrcc.alertes_sauvetage
                WHERE (marque_lu = false OR marque_lu IS NULL)
                    AND statut != 'terminee'
            """)
            count = cur.fetchone()['count']
            
            return jsonify({
                'notifications': notifications,
                'unread_count': count
            })
    except Exception as e:
        print(f"Erreur get_notifications: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route("/api/notifications/mark_read", methods=["POST"])
@login_required
def mark_notification_read():
    """Marque une notification comme lue"""
    data = request.get_json()
    alerte_id = data.get('alerte_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE mrcc.alertes_sauvetage
                SET marque_lu = true
                WHERE id = %s
            """, (alerte_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        print(f"Erreur mark_notification_read: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route("/api/notifications/mark_all_read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Marque toutes les notifications comme lues"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE mrcc.alertes_sauvetage
                SET marque_lu = true
                WHERE (marque_lu = false OR marque_lu IS NULL)
                    AND statut != 'terminee'
            """)
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        print(f"Erreur mark_all_notifications_read: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()





@app.route("/add_alerte_hist", methods=["GET", "POST"])
@login_required
def add_alerte_hist():
    print("=== ADD ALERTE ACCEDEE ===")
    if request.method == "POST":
        fichier_joint = None
        
        # Gestion du fichier joint
        if 'fichier_joint' in request.files:
            file = request.files['fichier_joint']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'alertes')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                fichier_joint = filename

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Récupérer l'organisme_id de l'utilisateur
                cur.execute("SELECT organisme_id FROM mrcc.users WHERE id = %s", (current_user.id,))
                user_data = cur.fetchone()
                organisme_id = user_data[0] if user_data and user_data[0] else None
                
                # Si organisme_id est une chaîne, le convertir en entier si possible
                if organisme_id and isinstance(organisme_id, str) and not organisme_id.isdigit():
                    organisme_id = None
                
                print(f"Insertion alerte - Titre: {request.form.get('titre')}")
                print(f"Organisme ID: {organisme_id}")
                
                cur.execute("""
                    INSERT INTO mrcc.alertes_sauvetage (
                        titre, description, latitude, longitude, type_incident,
                        nombre_personnes, conditions_meteo, moyen_alerte,
                        navire_implique, immatriculation_navire, niveau_urgence,
                        notes_complementaires, createur_id, organisme_id, fichier_joint,
                        statut, date_creation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    request.form.get("titre"),
                    request.form.get("description"),
                    request.form.get("latitude") or None,
                    request.form.get("longitude") or None,
                    request.form.get("type_incident"),
                    request.form.get("nombre_personnes") or None,
                    request.form.get("conditions_meteo"),
                    request.form.get("moyen_alerte"),
                    request.form.get("navire_implique"),
                    request.form.get("immatriculation_navire"),
                    request.form.get("niveau_urgence"),
                    request.form.get("notes_complementaires"),
                    current_user.id,
                    organisme_id,
                    fichier_joint,
                    'nouvelle'
                ))
                alerte_id = cur.fetchone()[0]

                # Ajouter une entrée dans l'historique
                cur.execute("""
                    INSERT INTO mrcc.mises_a_jour_alertes (alerte_id, user_id, contenu, date_mise_a_jour)
                    VALUES (%s, %s, %s, NOW())
                """, (alerte_id, current_user.id, "Création de l'alerte de sauvetage."))
                
                conn.commit()
                flash("Alerte de sauvetage créée avec succès!", "success")
                return redirect(url_for("details_alerte", alerte_id=alerte_id))
                
        except Exception as e:
            conn.rollback()
            print(f"Erreur détaillée: {str(e)}")
            flash(f"Erreur lors de la création de l'alerte: {str(e)}", "danger")
        finally:
            conn.close()

    return render_template("alertes/add_alerte.html")

@app.route("/add_alerte", methods=["GET", "POST"])
@login_required
def add_alerte():
    if request.method == "POST":
        fichier_joint = None
        
        # Gestion du fichier joint
        if 'fichier_joint' in request.files:
            file = request.files['fichier_joint']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'alertes')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                fichier_joint = filename

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Récupérer l'organisme_id de l'utilisateur
                cur.execute("SELECT organisme_id FROM mrcc.users WHERE id = %s", (current_user.id,))
                user_data = cur.fetchone()
                organisme_id = user_data[0] if user_data and user_data[0] else None
                
                # Si organisme_id est une chaîne, le convertir en entier si possible
                if organisme_id and isinstance(organisme_id, str) and not organisme_id.isdigit():
                    organisme_id = None
                
                cur.execute("""
                    INSERT INTO mrcc.alertes_sauvetage (
                        titre, description, latitude, longitude, type_incident,
                        nombre_personnes, conditions_meteo, moyen_alerte,
                        navire_implique, immatriculation_navire, niveau_urgence,
                        notes_complementaires, createur_id, organisme_id, fichier_joint,
                        statut, date_creation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    request.form.get("titre"),
                    request.form.get("description"),
                    request.form.get("latitude") or None,
                    request.form.get("longitude") or None,
                    request.form.get("type_incident"),
                    request.form.get("nombre_personnes") or None,
                    request.form.get("conditions_meteo"),
                    request.form.get("moyen_alerte"),
                    request.form.get("navire_implique"),
                    request.form.get("immatriculation_navire"),
                    request.form.get("niveau_urgence"),
                    request.form.get("notes_complementaires"),
                    current_user.id,
                    organisme_id,
                    fichier_joint,
                    'nouvelle'
                ))
                alerte_id = cur.fetchone()[0]
                
                conn.commit()
                flash("Alerte de sauvetage créée avec succès!", "success")
                return redirect(url_for("details_alerte", alerte_id=alerte_id))
                
        except Exception as e:
            conn.rollback()
            print(f"Erreur détaillée: {str(e)}")
            flash(f"Erreur lors de la création de l'alerte: {str(e)}", "danger")
        finally:
            conn.close()

    return render_template("alertes/add_alerte.html")


@app.route("/details_alerte/<int:alerte_id>")
@login_required
def details_alerte(alerte_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer l'alerte avec LEFT JOIN pour éviter les erreurs si pas d'organisme
            cur.execute("""
                SELECT a.*, u.nom, u.prenom, o.nom as organisme_nom
                FROM mrcc.alertes_sauvetage a
                LEFT JOIN mrcc.users u ON a.createur_id = u.id
                LEFT JOIN mrcc.organismes o ON a.organisme_id = o.id
                WHERE a.id = %s
            """, (alerte_id,))
            alerte = cur.fetchone()

            if not alerte:
                flash("Alerte non trouvée", "danger")
                return redirect(url_for("alerte"))

            # Convertir les types pour le template
            if alerte.get('latitude'):
                try:
                    alerte['latitude'] = float(alerte['latitude'])
                except (TypeError, ValueError):
                    alerte['latitude'] = None
            if alerte.get('longitude'):
                try:
                    alerte['longitude'] = float(alerte['longitude'])
                except (TypeError, ValueError):
                    alerte['longitude'] = None

            # Récupérer les mises à jour
            cur.execute("""
                SELECT m.*, u.nom, u.prenom
                FROM mrcc.mises_a_jour_alertes m
                LEFT JOIN mrcc.users u ON m.user_id = u.id
                WHERE m.alerte_id = %s 
                ORDER BY m.date_mise_a_jour DESC
            """, (alerte_id,))
            mises_a_jour = cur.fetchall()

            # Récupérer les moyens engagés (si la table existe)
            moyens_engages = []
            try:
                cur.execute("""
                    SELECT m.id, m.nom, m.type, m.localisation, ma.date_engagement, ma.statut
                    FROM mrcc.moyens_secours_alertes ma
                    LEFT JOIN mrcc.moyens_secours m ON ma.moyen_id = m.id
                    WHERE ma.alerte_id = %s
                """, (alerte_id,))
                moyens_engages = cur.fetchall()
            except Exception as e:
                print(f"Tablemrcc.moyens_secours_alertes non trouvée: {e}")

            return render_template("alertes/details_alerte.html",
                                   alerte=alerte, 
                                   mises_a_jour=mises_a_jour,
                                   moyens_engages=moyens_engages)
    except Exception as e:
        print(f"Erreur details_alerte: {str(e)}")
        flash(f"Erreur lors du chargement des détails: {str(e)}", "danger")
        return redirect(url_for("alerte"))
    finally:
        conn.close()


@app.route("/details_alerte_totale/<int:alerte_id>")
@login_required
def details_alerte_totale(alerte_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.*, u.nom, u.prenom, o.nom as organisme_nom
                FROM mrcc.alertes_sauvetage a
                JOIN mrcc.users u ON a.createur_id = u.id
                JOIN mrcc.organismes o ON a.organisme_id = o.id
                WHERE a.id = %s
            """, (alerte_id,))
            alerte = cur.fetchone()

            if not alerte:
                flash("Alerte non trouvée", "danger")
                return redirect(url_for("alerte"))

            # Convertir les types pour le template
            if alerte.get('latitude'):
                alerte['latitude'] = float(alerte['latitude'])
            if alerte.get('longitude'):
                alerte['longitude'] = float(alerte['longitude'])

            cur.execute("""
                SELECT m.*, u.nom, u.prenom
                FROM mrcc.mises_a_jour_alertes m
                LEFT JOIN users u ON m.user_id = u.id
                WHERE m.alerte_id = %s ORDER BY m.date_mise_a_jour DESC
            """, (alerte_id,))
            mises_a_jour = cur.fetchall()

            cur.execute("""
                SELECT m.id, m.nom, m.type, m.localisation, ma.date_engagement, ma.statut
                FROMmrcc.moyens_secours_alertes ma
                LEFT JOIN moyens_secours m ON ma.moyen_id = m.id
                WHERE ma.alerte_id = %s
            """, (alerte_id,))
            moyens_engages = cur.fetchall()

            return render_template("alertes/details_alerte.html",
                                   alerte=alerte, 
                                   mises_a_jour=mises_a_jour,
                                   moyens_engages=moyens_engages)
    except Exception as e:
        flash(f"Erreur lors du chargement des détails: {str(e)}", "danger")
        return e # redirect(url_for("alerte"))
    finally:
        conn.close()



@app.route("/alertes/<int:alerte_id>/mise-a-jour", methods=["POST"])
@login_required
def mise_a_jour_alerte(alerte_id):
    contenu       = request.form.get("contenu")
    nouveau_statut= request.form.get("statut")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT statut FROM mrcc.alertes_sauvetage WHERE id = %s", (alerte_id,))
            statut_actuel = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO mrcc.mises_a_jour_alertes (alerte_id, user_id, contenu, statut_precedent, nouveau_statut)
                VALUES (%s,%s,%s,%s,%s)
            """, (alerte_id, current_user.id, contenu, statut_actuel, nouveau_statut))

            if nouveau_statut and nouveau_statut != statut_actuel:
                cur.execute(
                    "UPDATE mrcc.alertes_sauvetage SET statut=%s WHERE id=%s",
                    (nouveau_statut, alerte_id)
                )
            conn.commit()
            flash("Mise à jour enregistrée avec succès", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur lors de la mise à jour: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("details_alerte", alerte_id=alerte_id))


@app.route("/mes_alertes", methods=["GET"])
@login_required
def mes_alertes():
    return render_template("mes_alertes.html")


@app.route("/modifier_alerte/<int:alerte_id>", methods=["GET", "POST"])
@login_required
def modifier_alerte(alerte_id):
    print(f"=== MODIFIER ALERTE {alerte_id} ACCEDEE ===")
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer l'alerte
            cur.execute("""
                SELECT * FROM mrcc.alertes_sauvetage 
                WHERE id = %s AND createur_id = %s
            """, (alerte_id, current_user.id))
            alerte = cur.fetchone()
            
            if not alerte:
                flash("Alerte introuvable ou accès non autorisé.", "warning")
                return redirect(url_for("alerte"))
            
            if request.method == "POST":
                titre = request.form.get("titre")
                description = request.form.get("description")
                type_incident = request.form.get("type_incident")
                niveau_urgence = request.form.get("niveau_urgence")
                nombre_personnes = request.form.get("nombre_personnes") or None
                conditions_meteo = request.form.get("conditions_meteo")
                notes_complementaires = request.form.get("notes_complementaires")
                latitude = request.form.get("latitude") or None
                longitude = request.form.get("longitude") or None
                precision_position = request.form.get("precision_position")
                navire_implique = request.form.get("navire_implique")
                immatriculation_navire = request.form.get("immatriculation_navire")
                moyen_alerte = request.form.get("moyen_alerte")
                
                # Gestion du fichier
                fichier_joint = alerte['fichier_joint']
                supprimer_fichier = request.form.get("supprimer_fichier") == "1"
                
                if supprimer_fichier and fichier_joint:
                    # Supprimer le fichier physique
                    upload_folder = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'alertes')
                    file_path = os.path.join(upload_folder, fichier_joint)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    fichier_joint = None
                
                if 'fichier_joint' in request.files:
                    file = request.files['fichier_joint']
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        upload_folder = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'alertes')
                        os.makedirs(upload_folder, exist_ok=True)
                        file.save(os.path.join(upload_folder, filename))
                        fichier_joint = filename
                
                # Mettre à jour l'alerte
                cur.execute("""
                    UPDATE mrcc.alertes_sauvetage 
                    SET titre=%s, description=%s, type_incident=%s, niveau_urgence=%s,
                        nombre_personnes=%s, conditions_meteo=%s, notes_complementaires=%s,
                        latitude=%s, longitude=%s, precision_position=%s,
                        navire_implique=%s, immatriculation_navire=%s, moyen_alerte=%s,
                        fichier_joint=%s
                    WHERE id=%s
                """, (titre, description, type_incident, niveau_urgence,
                      nombre_personnes, conditions_meteo, notes_complementaires,
                      latitude, longitude, precision_position,
                      navire_implique, immatriculation_navire, moyen_alerte,
                      fichier_joint, alerte_id))
                conn.commit()
                
                flash("Alerte modifiée avec succès !", "success")
                return redirect(url_for("details_alerte", alerte_id=alerte_id))
            
            return render_template("alertes/modifier_alerte.html", alerte=alerte)
    except Exception as e:
        flash(f"Erreur lors de la modification : {str(e)}", "danger")
        return redirect(url_for("alerte"))
    finally:
        conn.close()


@app.route("/supprimer_alerte/<int:alerte_id>", methods=["POST"])
@login_required
def supprimer_alerte(alerte_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Vérifier que l'utilisateur est propriétaire
            cur.execute("""
                SELECT fichier_joint FROM mrcc.alertes_sauvetage 
                WHERE id = %s AND createur_id = %s
            """, (alerte_id, current_user.id))
            alerte = cur.fetchone()
            
            if not alerte:
                flash("Alerte introuvable ou accès non autorisé.", "warning")
                return redirect(url_for("alerte"))
            
            # Supprimer le fichier s'il existe
            if alerte[0]:
                file_path = os.path.join(UPLOAD_FOLDER_ALERTE, alerte[0])
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Supprimer les mises à jour associées
            cur.execute("DELETE FROM mrcc.mises_a_jour_alertes WHERE alerte_id = %s", (alerte_id,))
            
            # Supprimer l'alerte
            cur.execute("DELETE FROM mrcc.alertes_sauvetage WHERE id = %s", (alerte_id,))
            conn.commit()
            
            flash("Alerte supprimée avec succès !", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for("alerte"))



@app.route("/api/moyens_disponibles")
@login_required
def get_moyens_disponibles():
    """Récupère la liste des moyens de secours disponibles"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer tous les moyens actifs et disponibles
            cur.execute("""
                SELECT 
                    rr.resource_id,
                    rr.resource_name,
                    rr.type_id,
                    rr.base_id,
                    rr.identifier_code,
                    rr.operational_status,
                    rr.max_capacity,
                    rr.operational_range,
                    rr.speed,
                    rrt.type_name,
                    rrt.category,
                    rrt.icon_class,
                    rb.base_name,
                    rb.location as base_location
                FROM mrcc.rescue_resources rr
                LEFT JOIN mrcc.rescue_resource_types rrt ON rr.type_id = rrt.type_id
                LEFT JOIN mrcc.rescue_bases rb ON rr.base_id = rb.base_id
                WHERE rr.operational_status = 'available' 
                    AND rr.is_active = true
                ORDER BY rrt.type_name, rr.resource_name
            """)
            moyens = cur.fetchall()
            
            # Formater les données pour l'affichage
            resultats = []
            for moyen in moyens:
                resultats.append({
                    'resource_id': moyen['resource_id'],
                    'resource_name': moyen['resource_name'],
                    'type_name': moyen['type_name'] or 'Non défini',
                    'category': moyen['category'] or 'Non défini',
                    'base_name': moyen['base_name'] or 'Base inconnue',
                    'base_location': moyen['base_location'],
                    'identifier_code': moyen['identifier_code'],
                    'operational_status': moyen['operational_status'],
                    'max_capacity': moyen['max_capacity'],
                    'operational_range': moyen['operational_range'],
                    'speed': moyen['speed']
                })
            
            return jsonify(resultats)
    except Exception as e:
        print(f"Erreur get_moyens_disponibles: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route("/api/engager_moyen/<int:alerte_id>", methods=["POST"])
@login_required
def engager_moyen(alerte_id):
    """Engage un moyen de secours sur une alerte"""
    data = request.get_json()
    moyen_id = data.get('moyen_id')
    notes = data.get('notes', '')
    
    if not moyen_id:
        return jsonify({'error': 'Moyen non spécifié'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Vérifier que l'alerte existe
            cur.execute("SELECT statut FROM mrcc.alertes_sauvetage WHERE id = %s", (alerte_id,))
            alerte = cur.fetchone()
            if not alerte:
                return jsonify({'error': 'Alerte non trouvée'}), 404
            
            # 2. Vérifier que le moyen existe et est disponible
            cur.execute("""
                SELECT resource_id, resource_name, operational_status 
                FROM mrcc.rescue_resources 
                WHERE resource_id = %s 
                    AND operational_status = 'available' 
                    AND is_active = true
            """, (moyen_id,))
            moyen = cur.fetchone()
            if not moyen:
                return jsonify({'error': 'Moyen non disponible ou inexistant'}), 400
            
            # 3. Vérifier que le moyen n'est pas déjà engagé sur cette alerte
            cur.execute("""
                SELECT id FROM mrcc.moyens_secours_alertes 
                WHERE alerte_id = %s AND moyen_id = %s
            """, (alerte_id, moyen_id))
            if cur.fetchone():
                return jsonify({'error': 'Ce moyen est déjà engagé sur cette alerte'}), 400
            
            # 4. Engager le moyen
            cur.execute("""
                INSERT INTO mrcc.moyens_secours_alertes (alerte_id, moyen_id, date_engagement, notes, engage_par)
                VALUES (%s, %s, NOW(), %s, %s)
            """, (alerte_id, moyen_id, notes, current_user.id))
            
            # 5. Mettre à jour le statut du moyen (operational_status = 'on_mission')
            cur.execute("""
                UPDATE mrcc.rescue_resources 
                SET operational_status = 'on_mission', 
                    current_status = 'Engagé sur alerte ' || %s,
                    last_updated = NOW()
                WHERE resource_id = %s
            """, (alerte_id, moyen_id))
            
            # 6. Mettre à jour le statut de l'alerte si elle est toujours 'nouvelle'
            nouveau_statut = alerte['statut']
            if alerte['statut'] == 'nouvelle':
                nouveau_statut = 'en_cours'
                cur.execute("""
                    UPDATE mrcc.alertes_sauvetage 
                    SET statut = 'en_cours'
                    WHERE id = %s
                """, (alerte_id,))
            
            # 7. Ajouter une entrée dans l'historique des alertes
            history_details = json.dumps({
                'moyen_id': moyen_id,
                'moyen_nom': moyen['resource_name'],
                'notes': notes
            })
            cur.execute("""
                INSERT INTO mrcc.alerte_history (alerte_id, action, description, details, user_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (alerte_id, 'engagement_moyen', 
                  f"Engagement du moyen {moyen['resource_name']}", 
                  history_details, current_user.id))
            
            # 8. Ajouter une mise à jour dans l'historique des alertes (mises_a_jour_alertes)
            cur.execute("""
                INSERT INTO mrcc.mises_a_jour_alertes (alerte_id, user_id, contenu, statut_precedent, nouveau_statut)
                VALUES (%s, %s, %s, %s, %s)
            """, (alerte_id, current_user.id,
                  f"Moyen engagé: {moyen['resource_name']}. {notes}",
                  alerte['statut'], nouveau_statut))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Moyen {moyen["resource_name"]} engagé avec succès',
                'alerte_statut': nouveau_statut
            })
            
    except Exception as e:
        conn.rollback()
        print(f"Erreur engager_moyen: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()



@app.route("/api/alertes/<int:alerte_id>/moyens_engages")
@login_required
def get_moyens_engages(alerte_id):
    """Récupère la liste des moyens engagés sur une alerte"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    rr.resource_id,
                    rr.resource_name,
                    rr.identifier_code,
                    rrt.type_name,
                    rrt.category,
                    rrt.icon_class,
                    rb.base_name,
                    rb.location as base_location,
                    ma.date_engagement,
                    ma.notes,
                    u.nom as engage_par_nom,
                    u.prenom as engage_par_prenom,
                    rr.operational_status,
                    rr.speed,
                    rr.max_capacity
                FROM mrcc.moyens_secours_alertes ma
                LEFT JOIN mrcc.rescue_resources rr ON ma.moyen_id = rr.resource_id
                LEFT JOIN mrcc.rescue_resource_types rrt ON rr.type_id = rrt.type_id
                LEFT JOIN mrcc.rescue_bases rb ON rr.base_id = rb.base_id
                LEFT JOIN mrcc.users u ON ma.engage_par = u.id
                WHERE ma.alerte_id = %s
                ORDER BY ma.date_engagement DESC
            """, (alerte_id,))
            moyens = cur.fetchall()
            return jsonify(moyens)
    except Exception as e:
        print(f"Erreur get_moyens_engages: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()



@app.route("/api/alertes")
@login_required
def get_alertes_api():
    """API pour récupérer toutes les alertes (pour DataTables)"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    a.id,
                    a.titre,
                    a.description,
                    a.latitude,
                    a.longitude,
                    a.type_incident,
                    a.nombre_personnes,
                    a.conditions_meteo,
                    a.moyen_alerte,
                    a.navire_implique,
                    a.immatriculation_navire,
                    a.niveau_urgence,
                    a.notes_complementaires,
                    a.statut,
                    a.date_creation,
                    a.createur_id,
                    u.nom as createur_nom,
                    u.prenom as createur_prenom,
                    o.nom as organisme_nom,
                    -- Compter le nombre de moyens engagés
                    (SELECT COUNT(*) FROM mrcc.moyens_secours_alertes WHERE alerte_id = a.id) as nb_moyens_engages
                FROM mrcc.alertes_sauvetage a
                LEFT JOIN mrcc.users u ON a.createur_id = u.id
                LEFT JOIN mrcc.organismes o ON a.organisme_id = o.id
                ORDER BY a.date_creation DESC
            """)
            alertes = cur.fetchall()
            return jsonify(alertes)
    except Exception as e:
        print(f"Erreur get_alertes_api: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route("/moyens_secours")
@login_required
def liste_moyens_secours():
    """Affiche la liste des moyens de secours"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT m.*, tm.nom as type_nom, bs.nom as base_nom
                FROM mrcc.moyens_secours m
                LEFT JOIN mrcc.types_moyens tm ON m.type = tm.id
                LEFT JOIN mrcc.bases_secours bs ON m.base_id = bs.id
                WHERE m.is_active = true
                ORDER BY m.statut, m.nom
            """)
            moyens = cur.fetchall()
            return render_template("moyens_secours/liste.html", moyens=moyens)
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
        return redirect(url_for("index"))
    finally:
        conn.close()

# =============================================================================
# ROUTES — API ALERTES
# =============================================================================
@app.route("/api/alertes")
@login_required
def api_alertes():
    """API pour récupérer les alertes de l'utilisateur"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer l'organisme_id de l'utilisateur
            cur.execute("SELECT organisme_id FROM mrcc.users WHERE id = %s", (current_user.id,))
            user_data = cur.fetchone()
            organisme_id = user_data['organisme_id'] if user_data and user_data['organisme_id'] else None
            
            # Vérifier si organisme_id est un nombre valide
            organisme_condition = ""
            params = [current_user.id]
            
            if organisme_id and str(organisme_id).isdigit():
                organisme_condition = " OR a.organisme_id = %s"
                params.append(int(organisme_id))
            
            query = f"""
                SELECT a.*, u.nom, u.prenom, 
                       CONCAT(u.prenom, ' ', u.nom) as createur_nom
                FROM mrcc.alertes_sauvetage a
                LEFT JOIN mrcc.users u ON a.createur_id = u.id
                WHERE a.createur_id = %s{organisme_condition}
                ORDER BY a.date_creation DESC
            """
            
            cur.execute(query, params)
            alertes = cur.fetchall()
            
            # Convertir les types pour JSON
            for alerte in alertes:
                if alerte.get('date_creation'):
                    alerte['date_creation'] = alerte['date_creation'].isoformat()
                if alerte.get('latitude'):
                    alerte['latitude'] = float(alerte['latitude'])
                if alerte.get('longitude'):
                    alerte['longitude'] = float(alerte['longitude'])
                if alerte.get('organisme_id'):
                    alerte['organisme_id'] = str(alerte['organisme_id'])  # Convertir en string pour JSON
            
            return jsonify(alertes)
    except Exception as e:
        print(f"Erreur API alertes: {str(e)}")
        return jsonify([])
    finally:
        conn.close()




@app.route("/api/alertes_old")
@login_required
def api_alertes_ols():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, titre, latitude, longitude, type_incident, niveau_urgence
                    FROM mrcc.alertes_sauvetage
                    WHERE statut IN ('nouvelle', 'en_cours') AND organisme_id = %s
                """, (current_user.organisme,))
                alertes = cur.fetchall()
                return jsonify([{
                    'id': a[0], 'titre': a[1],
                    'lat': float(a[2]) if a[2] else None,
                    'lng': float(a[3]) if a[3] else None,
                    'type': a[4], 'urgence': a[5]
                } for a in alertes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/stats")
@login_required
def api_stats():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT TO_CHAR(date_creation,'YYYY-MM') as mois,
                           COUNT(*) as total,
                           COUNT(CASE WHEN statut='terminee' THEN 1 END) as terminees
                    FROM mrcc.alertes_sauvetage
                    WHERE organisme_id=%s AND date_creation >= CURRENT_DATE - INTERVAL '1 year'
                    GROUP BY mois ORDER BY mois
                """, (current_user.organisme,))
                stats = cur.fetchall()
                return jsonify({
                    'labels':   [s[0] for s in stats],
                    'total':    [s[1] for s in stats],
                    'terminees':[s[2] for s in stats],
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/notifications")
@login_required
def notifications():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT alertes.id, alertes.titre, alertes.contenu, alertes.created_at
                    FROM alertes
                    JOIN user_alertes ON alertes.id = user_alertes.alerte_id
                    WHERE user_alertes.user_id=%s AND user_alertes.statut='non_vu'
                    ORDER BY alertes.created_at DESC
                """, (current_user.id,))
                notifications_list = [{
                    'id': r[0], 'titre': r[1], 'contenu': r[2],
                    'date': r[3].strftime('%d/%m/%Y %H:%M') if r[3] else ''
                } for r in cur.fetchall()]
        return jsonify(notifications_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/marquer_comme_vu/<int:alerte_id>')
@login_required
def marquer_comme_vu(alerte_id):
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE user_alertes SET statut='vu', date_vue=NOW() WHERE user_id=%s AND alerte_id=%s",
                    (current_user.id, alerte_id)
                )
                conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# ROUTES — UPLOAD / INTÉGRATION
# =============================================================================

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        flash("Aucun fichier sélectionné.")
        return redirect(url_for('api'))

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_path  = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    table_name = normalize_table_name(file.filename.rsplit('.', 1)[0])

    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(UPLOAD_FOLDER)
                shp_path = next(
                    (os.path.join(UPLOAD_FOLDER, f) for f in zf.namelist() if f.endswith('.shp')),
                    None
                )
            if not shp_path:
                flash("Aucun fichier .shp trouvé dans l'archive ZIP.")
                return redirect(url_for('api'))
            gdf = gpd.read_file(shp_path)

        elif file.filename.endswith('.shp'):
            gdf = gpd.read_file(file_path)

        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            return render_template('select_columns.html',
                                   columns=df.columns.tolist(),
                                   table_name=table_name, file_path=file_path)

        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
            return render_template('select_columns.html',
                                   columns=df.columns.tolist(),
                                   table_name=table_name, file_path=file_path)
        else:
            flash("Format de fichier non pris en charge.")
            return redirect(url_for('api'))

        if 'geometry' not in gdf.columns:
            flash("Erreur : colonne géométrique manquante.")
            return redirect(url_for('api'))
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)

        gdf.to_postgis(table_name, con=engine, schema='uploads', if_exists='replace', index=False)
        flash(f"Données intégrées dans la table '{table_name}'")

    except Exception as e:
        flash(f"Erreur d'intégration: {str(e)}")

    return redirect(url_for('api'))


@app.route('/integrate', methods=['POST'])
def integrate():
    x_col      = request.form['x_col']
    y_col      = request.form['y_col']
    table_name = request.form['table_name']
    file_path  = request.form['file_path']

    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        df['geometry'] = df.apply(lambda row: Point(row[x_col], row[y_col]), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
        gdf.to_postgis(table_name, con=engine, schema='uploads', if_exists='replace', index=False)
        flash(f"Table '{table_name}' intégrée avec succès avec géométrie.")
    except Exception as e:
        flash(f"Erreur lors de l'intégration des données: {str(e)}")

    return redirect(url_for('api'))


# =============================================================================
# ROUTES — PUBLICATION GEOSERVER
# =============================================================================

@app.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    if request.method == "GET":
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='uploads'"
            ))
            postgis_tables = [row[0] for row in result]
        return render_template('publish.html', postgis_tables=postgis_tables)

    data_source = request.form.get('data_source')
    layer_name  = request.form.get('layer_name', '').strip()
    style_name  = request.form.get('layer_style')

    if not layer_name:
        flash("Le nom de la couche est requis.")
        return redirect(url_for('publish'))

    try:
        if data_source == 'postgis':
            table_name = request.form.get('postgis_table')
            if not table_name:
                flash("Veuillez sélectionner une table PostGIS.")
                return redirect(url_for('publish'))
            success, message = publish_postgis_to_geoserver(table_name, layer_name, style_name)
            flash(message)

        elif data_source == 'file':
            file = request.files.get('file')
            if not file or file.filename == '':
                flash("Aucun fichier sélectionné.")
                return redirect(url_for('publish'))

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            try:
                if file.filename.endswith('.zip'):
                    success, message = publish_shapefile_to_geoserver(file_path, layer_name, style_name)
                elif file.filename.lower().endswith(('.tif', '.tiff', '.geotiff')):
                    success, message = publish_geotiff_to_geoserver(file_path, layer_name, style_name)
                else:
                    flash("Format de fichier non supporté.")
                    return redirect(url_for('publish'))
                flash(message)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
    except Exception as e:
        flash(f"Erreur lors de la publication : {str(e)}")

    return redirect(url_for('publish'))


def publish_shapefile_to_geoserver(zip_path, layer_name, style_name=None):
    gs_data_dir = "/path/to/geoserver/data_dir"
    dest_path   = os.path.join(gs_data_dir, "data", f"{layer_name}.zip")
    shutil.copy(zip_path, dest_path)

    url    = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/shapefiles/file.shp"
    resp   = requests.put(url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
                          params={'update': 'overwrite', 'filename': f"file://{dest_path}"})
    if resp.status_code in [200, 201]:
        return True, f"✅ Shapefile '{layer_name}' publié avec succès!"
    return False, f"Erreur GeoServer: {resp.text}"


def publish_geotiff_to_geoserver(tif_path, layer_name, style_name=None):
    gs_data_dir = "/path/to/geoserver/data_dir"
    dest_path   = os.path.join(gs_data_dir, "data", f"{layer_name}.tif")
    shutil.copy(tif_path, dest_path)

    url  = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{layer_name}/external.geotiff"
    resp = requests.put(url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
                        params={'configure': 'all', 'coverageName': layer_name,
                                'filename': f"file://{dest_path}"})
    if resp.status_code in [200, 201]:
        return True, f"✅ GeoTIFF '{layer_name}' publié avec succès!"
    return False, f"Erreur GeoServer: {resp.text}"


def publish_postgis_to_geoserver(table_name, layer_name, style_name):
    url      = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes"
    layer_xml= f"""<featureType>
        <name>{layer_name}</name>
        <nativeName>{table_name}</nativeName>
        <title>{layer_name}</title>
        <srs>EPSG:4326</srs>
        <enabled>true</enabled>
    </featureType>"""

    resp = requests.post(url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
                         headers={'Content-type': 'text/xml'}, data=layer_xml)
    if resp.status_code not in [200, 201]:
        return False, f"Erreur création couche: {resp.text}"

    if style_name:
        style_url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{layer_name}"
        style_xml = f"""<layer><defaultStyle><name>{style_name}</name></defaultStyle></layer>"""
        style_resp= requests.put(style_url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
                                 headers={'Content-type': 'text/xml'}, data=style_xml)
        if style_resp.status_code not in [200, 201]:
            return False, f"Couche créée mais erreur style: {style_resp.text}"

    return True, f"✅ Couche '{layer_name}' publiée avec style '{style_name}'"


# =============================================================================
# ROUTES — VISUALISATION
# =============================================================================

@app.route('/visualiser')
@login_required
def visualiser():
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='uploads'"
        ))
        tables = [row[0] for row in result]
    return render_template('visualiser.html', tables=tables)


@app.route('/visualiser/<table_name>')
@login_required
def visualiser_table(table_name):
    with engine.connect() as conn:
        gdf     = gpd.read_postgis(f"SELECT * FROM uploads.{table_name}", conn, geom_col='geometry')
        geojson = gdf.to_json()
        columns = [c for c in gdf.columns if c != 'geometry']
    return render_template('visualiser_table.html',
                           table_name=table_name, geojson=geojson,
                           columns=columns,
                           data=gdf.drop(columns='geometry').to_dict('records'))


@app.route('/visualiserg')
@login_required
def visualiserg():
    try:
        response = requests.get(
            f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/layers.json",
            auth=(GEOSERVER_USER, GEOSERVER_PASSWORD), timeout=30
        )
        if response.status_code != 200:
            flash(f"Erreur GeoServer (HTTP {response.status_code})")
            return redirect(url_for('index'))

        layers_data     = response.json()
        published_layers= []

        if isinstance(layers_data, dict) and 'layers' in layers_data:
            for layer in layers_data['layers'].get('layer', []):
                if isinstance(layer, dict):
                    name = str(layer.get('name', ''))
                    published_layers.append({
                        'name':       name,
                        'short_name': name.split(':')[-1] if ':' in name else name,
                        'href':       layer.get('href', '')
                    })

        if not published_layers:
            flash("Aucune couche trouvée dans le workspace spécifié")

        return render_template('visualiserg.html', layers=published_layers)

    except requests.exceptions.RequestException as e:
        flash(f"Erreur de connexion: {str(e)}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Erreur inattendue: {str(e)}")
        return redirect(url_for('index'))


@app.route('/get_layer_bounds')
def get_layer_bounds():
    layer_name = request.args.get('layer')
    if not layer_name:
        return jsonify({'success': False, 'error': 'Nom de couche manquant'})

    try:
        url  = f"{GEOSERVER_URL}/wms?service=WMS&version=1.1.1&request=GetCapabilities"
        resp = requests.get(url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD))
        if resp.status_code != 200:
            return jsonify({'success': False, 'error': 'Erreur GeoServer'})

        root = ET.fromstring(resp.content)
        ns   = {'wms': 'http://www.opengis.net/wms'}
        for layer in root.findall('.//wms:Layer/wms:Layer', ns):
            name = layer.find('wms:Name', ns)
            if name is not None and name.text == f"{WORKSPACE}:{layer_name}":
                bbox = layer.find('wms:LatLonBoundingBox', ns)
                if bbox is not None:
                    return jsonify({'success': True, 'bounds': [
                        float(bbox.get('minx')), float(bbox.get('miny')),
                        float(bbox.get('maxx')), float(bbox.get('maxy'))
                    ]})

        return jsonify({'success': False, 'error': 'Couche non trouvée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# =============================================================================
# ROUTES — NAVIRES (AIS)
# =============================================================================

@app.route('/api/ships')
def get_ships():
    ships = Ship.query.all()
    return jsonify([{
        'id':          s.ship_id,
        'name':        s.shipname or 'Inconnu',
        'lat':         s.lat if s.lat is not None else 0,
        'lon':         s.lon if s.lon is not None else 0,
        'speed':       s.speed if s.speed is not None else 'N/A',
        'course':      s.course or 0,
        'heading':     s.heading or 0,
        'destination': s.destination or 'Inconnu',
        'flag':        s.flag or 'Inconnu',
        'shiptype':    s.shiptype or 'Inconnu',
        'type_name':   s.type_name or 'Inconnu',
        'last_update': s.last_update.isoformat() if s.last_update else 'Inconnu',
    } for s in ships])


@app.route('/api/ships/search')
def search_ships():
    search_term = request.args.get('q', '')
    ship_type   = request.args.get('type', '')
    flag        = request.args.get('flag', '')

    query = Ship.query.filter(Ship.lat.isnot(None), Ship.lon.isnot(None))
    if search_term:
        query = query.filter(Ship.shipname.ilike(f'%{search_term}%'))
    if ship_type:
        query = query.filter(Ship.shiptype == ship_type)
    if flag:
        query = query.filter(Ship.flag == flag)

    return jsonify([{
        'id':          s.ship_id,
        'name':        s.shipname,
        'lat':         s.lat,
        'lon':         s.lon,
        'speed':       s.speed,
        'heading':     s.heading,
        'destination': s.destination,
        'flag':        s.flag,
        'type':        getattr(s, 'type_name', None),
        'last_update': s.last_update.strftime('%Y-%m-%d %H:%M') if s.last_update else None,
    } for s in query.limit(100).all()])


@app.route('/api/ships/stats')
def get_ship_stats():
    type_stats = db.session.query(
        Ship.shiptype, Ship.type_name, func.count(Ship.ship_id).label('count')
    ).group_by(Ship.shiptype, Ship.type_name).all()

    flag_stats = db.session.query(
        Ship.flag, func.count(Ship.ship_id).label('count')
    ).group_by(Ship.flag).all()

    return jsonify({
        'by_type': [{'type': t.shiptype, 'name': t.type_name, 'count': t.count} for t in type_stats],
        'by_flag': [{'flag': f.flag, 'count': f.count} for f in flag_stats],
    })


@app.route('/api/ship/<ship_id>')
def get_ship_details(ship_id):
    # FIX : paramètre renommé de 'shipname' → 'ship_id' pour correspondre à la route
    ship = Ship.query.get(ship_id)
    if not ship:
        return jsonify({'error': 'Ship not found'}), 404

    return jsonify({
        'id':          ship.ship_id,
        'name':        ship.shipname,
        'type':        ship.type_name,
        'flag':        ship.flag,
        'destination': ship.destination,
        'speed':       ship.speed,
        'last_update': ship.last_update.isoformat() if ship.last_update else None,
        'position':    {'lat': ship.lat, 'lon': ship.lon},
    })


# =============================================================================
# ROUTES — RESSOURCES DE SAUVETAGE
# =============================================================================

@app.route('/resources', methods=['GET'])
def get_resources():
    try:
        status  = request.args.get('status')
        type_id = request.args.get('type')
        base    = request.args.get('base')

        filters = ["r.is_active = TRUE"]
        params  = {}

        if status:
            filters.append("r.operational_status = :status")
            params['status'] = status
        if type_id:
            filters.append("r.type_id = :type_id")
            params['type_id'] = type_id
        if base:
            filters.append("r.base_id = :base")
            params['base'] = base

        filter_clause = " AND ".join(filters)
        base_query    = f"""
            SELECT r.*, rt.type_name, rb.base_name, rb.location as base_location,
                   ST_X(r.current_position) as longitude,
                   ST_Y(r.current_position) as latitude
            FROM mrcc.rescue_resources r
            JOIN mrcc.rescue_resource_types rt ON r.type_id = rt.type_id
            JOIN mrcc.rescue_bases rb ON r.base_id = rb.base_id
            WHERE {filter_clause}
        """
        count_query = f"""
            SELECT COUNT(*) as total FROM mrcc.rescue_resources r WHERE {filter_clause}
        """

        with db.engine.connect() as conn:
            try:
                result = conn.execute(text(base_query), params)
            except OperationalError:
                db.session.rollback()
                result = conn.execute(text(base_query), params)

            resources = []
            for row in result:
                resource = dict(row._mapping)
                if resource.get('longitude') and resource.get('latitude'):
                    resource['current_position'] = {
                        'latitude':  resource['latitude'],
                        'longitude': resource['longitude'],
                    }
                resources.append(resource)
            result.close()

            total = conn.execute(text(count_query), params).scalar()

        return jsonify({'data': resources, 'pagination': {'total': total}})

    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({'message': 'Database error'}), 500


@app.route('/resources', methods=['POST'])
def create_resource():
    try:
        data            = request.get_json()
        required_fields = ['resource_name', 'type_id', 'base_id', 'identifier_code']
        if any(f not in data for f in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO mrcc.rescue_resources
                      (resource_name, type_id, base_id, identifier_code, operational_status,
                       max_capacity, operational_range, speed, current_position)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))
                """, (
                    data['resource_name'], data['type_id'], data['base_id'],
                    data['identifier_code'], data.get('operational_status', 'available'),
                    data.get('max_capacity'), data.get('operational_range'), data.get('speed'),
                    data.get('current_position', {}).get('longitude'),
                    data.get('current_position', {}).get('latitude'),
                ))
                conn.commit()
        return jsonify({'message': 'Resource created successfully'}), 201

    except Exception as e:
        logger.error(f"Erreur création ressource: {str(e)}")
        if "Duplicate" in str(e):
            return jsonify({'message': 'Identifier code already exists'}), 400
        return jsonify({'message': 'Server error'}), 500


@app.route('/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT r.*, rt.type_name, rb.base_name, rb.location as base_location
                    FROM mrcc.rescue_resources r
                    JOIN mrcc.rescue_resource_types rt ON r.type_id = rt.type_id
                    JOIN mrcc.rescue_bases rb ON r.base_id = rb.base_id
                    WHERE r.resource_id=%s AND r.is_active=TRUE
                """, (resource_id,))
                resource = cur.fetchone()

                if not resource:
                    return jsonify({'message': 'Resource not found'}), 404

                resource = dict(resource)
                cur.execute("SELECT * FROM mrcc.resource_crew WHERE resource_id=%s AND is_active=TRUE",
                            (resource_id,))
                resource['crew'] = cur.fetchall()

                cur.execute("SELECT * FROM mrcc.resource_equipment WHERE resource_id=%s", (resource_id,))
                resource['equipment'] = cur.fetchall()

                return jsonify(resource)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'message': 'Server error'}), 500


@app.route('/resources/<int:resource_id>', methods=['PUT'])
def update_resource(resource_id):
    try:
        data = request.get_json()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query  = """
                    UPDATE mrcc.rescue_resources SET
                        resource_name=%s, identifier_code=%s, type_id=%s, base_id=%s,
                        max_capacity=%s, operational_range=%s, speed=%s,
                        operational_status=%s, notes=%s, last_updated=NOW()
                """
                params = [
                    data['resource_name'], data['identifier_code'], data['type_id'], data['base_id'],
                    data.get('max_capacity'), data.get('operational_range'), data.get('speed'),
                    data.get('operational_status', 'available'), data.get('notes'),
                ]
                if data.get('current_position'):
                    query += ", current_position = ST_SetSRID(ST_MakePoint(%s,%s),4326)"
                    params.extend([data['current_position']['longitude'], data['current_position']['latitude']])

                query += " WHERE resource_id=%s"
                params.append(resource_id)
                cur.execute(query, params)
                conn.commit()

        return jsonify({'success': True, 'message': 'Ressource mise à jour'})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/<int:resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE mrcc.rescue_resources SET is_active=FALSE, operational_status='out_of_service'
                    WHERE resource_id=%s
                """, (resource_id,))
                conn.commit()
        return jsonify({'success': True, 'message': 'Ressource supprimée'})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/<int:resource_id>/status', methods=['PUT'])
def update_resource_status(resource_id):
    try:
        data     = request.get_json()
        status   = data.get('status')
        position = data.get('position')
        notes    = data.get('notes')

        if not status:
            return jsonify({'message': 'Status is required'}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query  = "UPDATE mrcc.rescue_resources SET operational_status=%s, last_updated=NOW()"
                params = [status]

                if position:
                    query += ", current_position=ST_SetSRID(ST_MakePoint(%s,%s),4326)"
                    params.extend([position['longitude'], position['latitude']])
                    cur.execute("""
                        INSERT INTO mrcc.resource_position_history (resource_id, position)
                        VALUES (%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))
                    """, (resource_id, position['longitude'], position['latitude']))

                if notes:
                    query += ", current_status=%s"
                    params.append(notes)

                query += " WHERE resource_id=%s"
                params.append(resource_id)
                cur.execute(query, params)
                conn.commit()

        return jsonify({'message': 'Resource status updated successfully'})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'message': 'Server error'}), 500


@app.route('/resources/<int:resource_id>/position', methods=['POST'])
def update_resource_position(resource_id):
    try:
        data = request.get_json()
        lat  = data.get('latitude')
        lon  = data.get('longitude')

        if lat is None or lon is None:
            return jsonify({'error': 'Latitude et longitude requises'}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE mrcc.rescue_resources
                    SET current_position=ST_SetSRID(ST_MakePoint(%s,%s),4326), last_updated=NOW()
                    WHERE resource_id=%s
                """, (lon, lat, resource_id))
                cur.execute("""
                    INSERT INTO mrcc.resource_position_history (resource_id, position)
                    VALUES (%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))
                """, (resource_id, lon, lat))
                conn.commit()

        return jsonify({'success': True, 'message': 'Position mise à jour'})
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/<int:resource_id>/position-history', methods=['GET'])
def get_resource_position_history(resource_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT position_id,
                           ST_X(position) as longitude, ST_Y(position) as latitude,
                           recorded_at, notes
                    FROM mrcc.resource_position_history
                    WHERE resource_id=%s ORDER BY recorded_at DESC LIMIT 50
                """, (resource_id,))
                return jsonify([dict(r) for r in cur.fetchall()])
    except Exception as e:
        logger.error(str(e))
        return jsonify({'message': 'Server error'}), 500


@app.route('/resources/<int:resource_id>/crew', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_resource_crew(resource_id):
    try:
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM mrcc.resource_crew
                        WHERE resource_id=%s AND is_active=TRUE ORDER BY role, name
                    """, (resource_id,))
                    return jsonify([dict(r) for r in cur.fetchall()])

        data = request.get_json()

        if request.method == 'POST':
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO mrcc.resource_crew (resource_id, name, role, qualification)
                        VALUES (%s,%s,%s,%s) RETURNING crew_id
                    """, (resource_id, data['name'], data['role'], data.get('qualification')))
                    crew_id = cur.fetchone()[0]
                    conn.commit()
                    return jsonify({'success': True, 'crew_id': crew_id})

        if request.method == 'PUT':
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE mrcc.resource_crew SET name=%s, role=%s, qualification=%s
                        WHERE crew_id=%s AND resource_id=%s
                    """, (data['name'], data['role'], data.get('qualification'),
                          data.get('crew_id'), resource_id))
                    conn.commit()
                    return jsonify({'success': True})

        if request.method == 'DELETE':
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE mrcc.resource_crew SET is_active=FALSE
                        WHERE crew_id=%s AND resource_id=%s
                    """, (request.args.get('crew_id'), resource_id))
                    conn.commit()
                    return jsonify({'success': True})

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/<int:resource_id>/missions', methods=['GET', 'POST'])
def get_resource_missions(resource_id):
    try:
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT rm.*, i.incident_name, i.incident_type
                        FROM mrcc.resource_missions rm
                        LEFT JOIN incidents i ON rm.incident_id = i.incident_id
                        WHERE rm.resource_id=%s ORDER BY rm.start_time DESC LIMIT 20
                    """, (resource_id,))
                    return jsonify([dict(r) for r in cur.fetchall()])

        data = request.get_json()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO mrcc.resource_missions (resource_id, incident_id, start_time, notes)
                    VALUES (%s,%s,NOW(),%s) RETURNING mission_id
                """, (resource_id, data.get('incident_id'), data.get('notes')))
                mission_id = cur.fetchone()[0]
                conn.commit()
                return jsonify({'success': True, 'mission_id': mission_id})

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/export', methods=['GET'])
@login_required
def export_resources():
    try:
        format_type = request.args.get('format', 'csv')
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT r.resource_id, r.resource_name, r.identifier_code,
                           rt.type_name, rb.base_name, r.operational_status,
                           r.max_capacity, r.operational_range, r.speed,
                           ST_X(r.current_position) as longitude,
                           ST_Y(r.current_position) as latitude,
                           r.last_updated, r.created_at
                    FROM mrcc.rescue_resources r
                    JOIN mrcc.rescue_resource_types rt ON r.type_id = rt.type_id
                    JOIN mrcc.rescue_bases rb ON r.base_id = rb.base_id
                    WHERE r.is_active=TRUE ORDER BY r.resource_name
                """)
                resources = cur.fetchall()

        if format_type == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Nom', 'Code', 'Type', 'Base', 'Statut',
                             'Capacité', 'Rayon (km)', 'Vitesse (nœuds)',
                             'Latitude', 'Longitude', 'Dernière MAJ'])
            for r in resources:
                writer.writerow([
                    r['resource_id'], r['resource_name'], r['identifier_code'],
                    r['type_name'], r['base_name'], r['operational_status'],
                    r['max_capacity'], r['operational_range'], r['speed'],
                    r['latitude'], r['longitude'], r['last_updated']
                ])
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f'attachment; filename=resources_{datetime.now().strftime("%Y%m%d")}.csv'
            response.headers['Content-Type'] = 'text/csv'
            return response

        return jsonify(list(resources))

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/stats', methods=['GET'])
def get_resources_stats():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN operational_status='available'     THEN 1 END) as available,
                           COUNT(CASE WHEN operational_status='on_mission'    THEN 1 END) as on_mission,
                           COUNT(CASE WHEN operational_status='maintenance'   THEN 1 END) as maintenance,
                           COUNT(CASE WHEN operational_status='out_of_service'THEN 1 END) as out_of_service
                    FROM mrcc.rescue_resources WHERE is_active=TRUE
                """)
                general = dict(cur.fetchone())

                cur.execute("""
                    SELECT rt.type_name, COUNT(*) as count
                    FROM mrcc.rescue_resources r
                    JOIN mrcc.rescue_resource_types rt ON r.type_id=rt.type_id
                    WHERE r.is_active=TRUE GROUP BY rt.type_name ORDER BY count DESC
                """)
                by_type = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    SELECT rb.base_name, COUNT(*) as count
                    FROM mrcc.rescue_resources r
                    JOIN mrcc.rescue_bases rb ON r.base_id=rb.base_id
                    WHERE r.is_active=TRUE GROUP BY rb.base_name ORDER BY count DESC
                """)
                by_base = [dict(r) for r in cur.fetchall()]

                return jsonify({'general': general, 'by_type': by_type, 'by_base': by_base})

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resources/bulk-update', methods=['POST'])
@login_required
def bulk_update_resources():
    try:
        data         = request.get_json()
        resource_ids = data.get('resource_ids', [])
        updates      = data.get('updates', {})

        if not resource_ids or not updates:
            return jsonify({'error': 'Données manquantes'}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                set_clauses = []
                params      = []
                for field, value in updates.items():
                    if field in ['operational_status', 'base_id']:
                        set_clauses.append(f"{field}=%s")
                        params.append(value)

                if set_clauses:
                    query = f"UPDATE mrcc.rescue_resources SET {', '.join(set_clauses)}, last_updated=NOW() WHERE resource_id=ANY(%s)"
                    params.append(resource_ids)
                    cur.execute(query, params)
                    conn.commit()

        return jsonify({'success': True, 'updated': len(resource_ids)})

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/resources/types', methods=['GET'])
def get_resource_types_api():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT type_id, type_name, category, description FROM mrcc.rescue_resource_types ORDER BY type_name")
                return jsonify([dict(r) for r in cur.fetchall()])
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/resources/bases', methods=['GET'])
def get_bases_api():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT base_id, base_name, location, coordinates, is_active
                    FROM mrcc.rescue_bases WHERE is_active=TRUE ORDER BY base_name
                """)
                bases = []
                for row in cur.fetchall():
                    base = dict(row)
                    if base.get('coordinates'):
                        try:
                            coords = base['coordinates'].split(',')
                            if len(coords) == 2:
                                base['latitude']  = float(coords[0].strip())
                                base['longitude'] = float(coords[1].strip())
                        except Exception:
                            pass
                    bases.append(base)
                return jsonify(bases)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/resources/<int:resource_id>/history', methods=['GET'])
def get_resource_history(resource_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT rm.*, i.incident_name, i.incident_type, i.incident_date
                    FROM mrcc.resource_missions rm
                    LEFT JOIN incidents i ON rm.incident_id=i.incident_id
                    WHERE rm.resource_id=%s ORDER BY rm.start_time DESC LIMIT 20
                """, (resource_id,))
                return jsonify([dict(r) for r in cur.fetchall()])
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/resource-types', methods=['GET'])
def get_resource_types():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM mrcc.rescue_resource_types")
                return jsonify([dict(r) for r in cur.fetchall()])
    except Exception as e:
        return jsonify({'message': 'Server error'}), 500


@app.route('/bases', methods=['GET'])
def get_bases():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM mrcc.rescue_bases WHERE is_active=TRUE")
                bases = [dict(r) for r in cur.fetchall()]
                for base in bases:
                    base['coordinates'] = convert_point(base.get('coordinates'))
                return jsonify(bases)
    except Exception as e:
        return jsonify({'message': 'Server error'}), 500


# =============================================================================
# ROUTES — ÉVÉNEMENTS DE SAUVETAGE (ORM)
# =============================================================================

@app.route('/api/rescue-events', methods=['GET'])
@login_required
def api_get_rescue_events():
    try:
        query = RescueEvent.query
        for attr, val in [
            ('status',     request.args.get('status')),
            ('event_type', request.args.get('event_type')),
            ('priority',   request.args.get('priority')),
        ]:
            if val:
                query = query.filter(getattr(RescueEvent, attr) == val)

        search = request.args.get('search')
        if search:
            query = query.filter(db.or_(
                RescueEvent.event_number.ilike(f'%{search}%'),
                RescueEvent.vessel_name.ilike(f'%{search}%'),
                RescueEvent.location_name.ilike(f'%{search}%'),
            ))

        events = query.order_by(RescueEvent.created_at.desc()).all()
        stats  = {
            'total':           RescueEvent.query.count(),
            'active':          RescueEvent.query.filter_by(status='active').count(),
            'resolved':        RescueEvent.query.filter_by(status='resolved').count(),
            'persons_rescued': db.session.query(db.func.sum(RescueEvent.persons_rescued)).scalar() or 0,
        }
        return jsonify({'events': [e.to_dict() for e in events], 'stats': stats})

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500





# Route pour la page HTML des détails (sans /api/ dans le chemin)
@app.route('/rescue-events/<int:event_id>')
def event_detail_page(event_id):
    """Page HTML des détails d'un événement"""
    print("===================== PAGE HTML event_detail ===================== ")
    return render_template('event_detail.html', event_id=event_id)




@app.route('/api/rescue-events/<int:event_id>')
def get_rescue_event_api(event_id):
    """API endpoint - retourne JSON"""
    print("===================== API GET EVENT ===================== ")
    try:
        event = RescueEvent.query.get(event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        event_dict = {
            'event_id': event.event_id,
            'event_number': event.event_number,
            'event_type': event.event_type,
            'description': event.description,
            'priority': event.priority,
            'status': event.status,
            'latitude': float(event.latitude) if event.latitude else None,
            'longitude': float(event.longitude) if event.longitude else None,
            'persons_involved': event.persons_involved,
            'persons_rescued': event.persons_rescued,
            'persons_deceased': event.persons_deceased or 0,
            'persons_missing': event.persons_missing or 0,
            'distance_coast_km': float(event.distance_coast_km) if event.distance_coast_km else None,
            'location_name': event.location_name,
            'reported_by': event.reported_by,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'incident_time': event.incident_time.isoformat() if event.incident_time else None,
            'report_time': event.report_time.isoformat() if event.report_time else None,
            'resolved_at': event.resolved_at.isoformat() if event.resolved_at else None,
            'vessel_name': event.vessel_name,
            'vessel_type': event.vessel_type,
            'vessel_flag': event.vessel_flag,
            'vessel_imo': event.vessel_imo,
            'vessel_mmsi': event.vessel_mmsi,
            'wind_speed': float(event.wind_speed) if event.wind_speed else None,
            'wind_direction': event.wind_direction,
            'sea_state': event.sea_state,
            'visibility_km': float(event.visibility_km) if event.visibility_km else None,
            'water_temperature': float(event.water_temperature) if event.water_temperature else None,
            'current_speed': float(event.current_speed) if event.current_speed else None,
            'current_direction': event.current_direction,
            'notes': event.notes,
            'updates': []
        }
        
        return jsonify(event_dict)
        
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rescue-events', methods=['POST'])
@login_required
def api_create_rescue_event():
    try:
        data = request.get_json()
        year = datetime.now().year
        count = RescueEvent.query.filter(
            RescueEvent.event_number.like(f'MRCC-{year}-%')
        ).count() + 1

        # Créer le point géométrique à partir de la latitude/longitude
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        
        point_geom = None
        if data.get('latitude') and data.get('longitude'):
            point_geom = from_shape(Point(data['longitude'], data['latitude']), srid=4326)

        event = RescueEvent(
            event_number  = f'MRCC-{year}-{count:04d}',
            event_type    = data['event_type'],
           # id_event_type = data.get('event_type'),  # Ajout du champ id_type
            priority      = data.get('priority', 'normal'),
            latitude      = data['latitude'],
            longitude     = data['longitude'],
            geom          = point_geom,  # Ajout du point géométrique
            location_name = data.get('location_name'),
            distance_coast_km = data.get('distance_coast_km'),
            description   = data.get('description'),
            reported_by   = data.get('reported_by', current_user.username),
            incident_time = datetime.fromisoformat(data['incident_time']) if data.get('incident_time') else datetime.utcnow(),
            persons_involved = data.get('persons_involved', 1),
            persons_rescued  = data.get('persons_rescued', 0),
            persons_deceased = data.get('persons_deceased', 0),
            persons_missing  = data.get('persons_missing', 0),
            vessel_name   = data.get('vessel_name'),
            vessel_type   = data.get('vessel_type'),
            vessel_flag   = data.get('vessel_flag'),
            vessel_imo    = data.get('vessel_imo'),
            vessel_mmsi   = data.get('vessel_mmsi'),
            wind_speed    = data.get('wind_speed'),
            wind_direction= data.get('wind_direction'),
            current_speed = data.get('current_speed'),
            current_direction = data.get('current_direction'),
            sea_state     = data.get('sea_state'),
            visibility_km = data.get('visibility_km'),
            water_temperature = data.get('water_temperature'),
            notes         = data.get('notes'),
            created_by    = current_user.id,
        )
        
        db.session.add(event)
        db.session.commit()

        db.session.add(RescueUpdate(
            event_id    = event.event_id,
            user_id     = current_user.id,
            update_type = 'creation',
            content     = f'Événement créé par {current_user.username}',
        ))
        db.session.commit()
        
        return jsonify({'success': True, 'event_id': event.event_id})

    except Exception as e:
        db.session.rollback()
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>', methods=['GET'])
@login_required
def api_get_rescue_event(event_id):
    try:
        event   = RescueEvent.query.get_or_404(event_id)
        updates = RescueUpdate.query.filter_by(event_id=event_id).order_by(RescueUpdate.created_at.desc()).all()
        data    = event.to_dict()
        data['updates'] = [u.to_dict() for u in updates]
        return jsonify(data)
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>/status', methods=['PUT'])
@login_required
def api_update_event_status(event_id):
    try:
        data       = request.get_json()
        new_status = data.get('status')
        event      = RescueEvent.query.get_or_404(event_id)
        old_status = event.status
        event.status     = new_status
        event.updated_at = datetime.utcnow()
        if new_status == 'resolved':
            event.resolved_at = datetime.utcnow()

        db.session.add(RescueUpdate(
            event_id       = event_id,
            user_id        = current_user.id,
            update_type    = 'status_change',
            content        = f'Statut changé de {old_status} à {new_status}',
            previous_value = old_status,
            new_value      = new_status,
        ))
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>/update', methods=['POST'])
@login_required
def api_add_event_update(event_id):
    try:
        data = request.get_json()
        db.session.add(RescueUpdate(
            event_id    = event_id,
            user_id     = current_user.id,
            update_type = data.get('type', 'general'),
            content     = data.get('content'),
        ))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/export', methods=['GET'])
@login_required
def api_export_rescue_events():
    try:
        events  = RescueEvent.query.order_by(RescueEvent.created_at.desc()).all()
        output  = StringIO()
        writer  = csv.writer(output)
        writer.writerow(['N° Événement', 'Type', 'Statut', 'Priorité', 'Date',
                         'Lieu', 'Latitude', 'Longitude', 'Personnes', 'Sauvées', 'Navire'])
        for e in events:
            writer.writerow([
                e.event_number, e.event_type, e.status, e.priority,
                e.incident_time.strftime('%Y-%m-%d %H:%M') if e.incident_time else '',
                e.location_name or '', e.latitude, e.longitude,
                e.persons_involved, e.persons_rescued, e.vessel_name or ''
            ])

        response = make_response('\uFEFF' + output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=rescue_events_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        return response

    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-assets', methods=['GET'])
@login_required
def api_get_rescue_assets():
    try:
        assets = RescueAsset.query.filter_by(is_active=True).all()
        return jsonify([a.to_dict() for a in assets])
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/event-types', methods=['GET'])
def api_get_event_types():
    try:
        types = VueTypeCategorieSectEvent.query.all()
        return jsonify([{
            'id_type': t.id_type, 'id_secteur': t.id_secteur,
            'secteur': t.secteur, 'id_categorie': t.id_categorie,
            'categorie': t.categorie, 'type': t.type, 'mviewer': t.mviewer
        } for t in types])
    except Exception as e:
        logger.error(str(e))
        return jsonify([]), 200


# =============================================================================
# ROUTES — MÉTÉO MARINE
# =============================================================================

def fetch_marine_data(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wave_height,wind_wave_height,wind_wave_direction",
        "timezone": "auto", "forecast_days": 3
    }
    try:
        response = requests.get(MARINE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get('hourly', {}), dict):
            return None
        return data
    except Exception as e:
        logger.error(f"Erreur API marine pour {lat},{lon}: {str(e)}")
        return None


@app.route('/api/marine-data')
def marine_data():
    marine_result = {}
    alerts        = []

    for zone_id, zone in ZONES.items():
        data = fetch_marine_data(zone['lat'], zone['lon'])
        if not data or 'hourly' not in data:
            continue

        hourly   = data['hourly']
        times    = hourly.get('time', [])
        last_idx = len(times) - 1 if times else 0

        def safe_get(lst, idx, default=0.0):
            try:
                v = lst[idx]
                return float(v) if v is not None else default
            except (IndexError, TypeError, ValueError):
                return default

        wave_h   = hourly.get('wave_height', [])
        wind_wh  = hourly.get('wind_wave_height', [])
        wind_dir = hourly.get('wind_wave_direction', [])

        current = {
            'wave_height':    safe_get(wave_h, last_idx),
            'wind_speed':     safe_get(wind_wh, last_idx) * 1.94,
            'wind_direction': safe_get(wind_dir, last_idx),
            'time':           times[last_idx] if last_idx < len(times) else datetime.now().isoformat()
        }
        forecast = {
            'time':            times,
            'wave_height':     [safe_get(wave_h, i) for i in range(len(times))],
            'wind_speed_10m':  [safe_get(wind_wh, i) * 1.94 for i in range(len(times))],
            'wind_direction_10m': [safe_get(wind_dir, i) for i in range(len(times))]
        }
        marine_result[zone_id] = {
            'name': zone['name'], 'current': current,
            'forecast': forecast, 'coordinates': {'lat': zone['lat'], 'lon': zone['lon']}
        }

        if current['wind_speed'] > 25:
            alerts.append({'zone': zone['name'], 'type': 'vent',
                           'message': f"Vents forts ({current['wind_speed']:.1f} nœuds)",
                           'severity': 'warning'})
        if current['wave_height'] > 3:
            alerts.append({'zone': zone['name'], 'type': 'houle',
                           'message': f"Grosse houle ({current['wave_height']:.1f}m)",
                           'severity': 'danger'})

    return jsonify({
        'zones':        marine_result,
        'alerts':       alerts,
        'last_updated': datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    })


# =============================================================================
# ROUTES — CARTES MARINES
# =============================================================================

@app.route('/api/map_data')
def get_map_data():
    return jsonify({
        "depths": [
            {"lat": 35.7796, "lon": -5.8033, "depth": 12.5},
            {"lat": 33.5731, "lon": -7.5898, "depth": 8.2},
            {"lat": 31.5144, "lon": -9.7695, "depth": 15.7},
            {"lat": 28.4326, "lon": -11.1000, "depth": 22.3},
        ],
        "hazards": [
            {"lat": 35.7810, "lon": -5.8050, "type": "rock",  "description": "Rocher submergé"},
            {"lat": 33.5750, "lon": -7.5910, "type": "wreck", "description": "Épave à 10m"},
        ],
        "navigation_aids": [
            {"lat": 35.7800, "lon": -5.8000, "type": "buoy",       "name": "Bouée Tanger"},
            {"lat": 33.6000, "lon": -7.6000, "type": "lighthouse", "name": "Phare Casablanca"},
        ]
    })


@app.route('/api/depth_data')
def get_depth_data():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    base_depth      = 5 + (float(lat) * 100 % 50) + (float(lon) * 100 % 30)
    depth_variation = random.uniform(-3, 3)

    return jsonify({
        'depth':           round(base_depth + depth_variation, 1),
        'hazards':         simulate_hazards(lat, lon),
        'navigation_aids': simulate_navigation_aids(lat, lon)
    })


def simulate_hazards(lat, lon):
    lat_f = float(lat); lon_f = float(lon)
    return [{
        'type':        random.choice(['rock', 'wreck', 'reef']),
        'position':    [lat_f + random.uniform(-0.05, 0.05), lon_f + random.uniform(-0.05, 0.05)],
        'description': f"Danger {i+1}"
    } for i in range(random.randint(0, 3))]


def simulate_navigation_aids(lat, lon):
    lat_f = float(lat); lon_f = float(lon)
    return [{
        'type':     random.choice(['buoy', 'lighthouse', 'beacon']),
        'position': [lat_f + random.uniform(-0.1, 0.1), lon_f + random.uniform(-0.1, 0.1)],
        'name':     f"Aid {i+1}"
    } for i in range(random.randint(1, 4))]


# =============================================================================
# ROUTES — SIMULATION DE DÉRIVE
# =============================================================================

def haversine(lat1, lon1, lat2, lon2):
    R    = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a    = (np.sin(dlat/2)**2 +
            np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


def calculate_drift(start_lat, start_lon, current_speed, current_direction,
                    wind_speed, wind_direction, time_hours=1):
    current_rad = math.radians(450 - current_direction) % (2 * math.pi)
    wind_rad    = math.radians(450 - wind_direction)    % (2 * math.pi)

    current_distance = current_speed * 1.852 * time_hours
    wind_effect      = 0.3 * wind_speed * 1.852 * time_hours

    total_north = (current_distance * math.cos(current_rad) + wind_effect * math.cos(wind_rad))
    total_east  = (current_distance * math.sin(current_rad) + wind_effect * math.sin(wind_rad))

    lat_shift = total_north / 111.0
    lon_shift = total_east  / (111.0 * math.cos(math.radians(start_lat)))

    return start_lat + lat_shift, start_lon + lon_shift


@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json()

        start_lat         = float(data['start_lat'])
        start_lon         = float(data['start_lon'])
        rescue_lat        = float(data['rescue_lat'])
        rescue_lon        = float(data['rescue_lon'])
        current_speed     = float(data['current_speed'])
        current_direction = float(data['current_direction'])
        wind_speed        = float(data['wind_speed'])
        wind_direction    = float(data['wind_direction'])

        initial_distance = haversine(start_lat, start_lon, rescue_lat, rescue_lon)
        estimated_time   = initial_distance / (5 * 1.852)

        drift_lat, drift_lon = calculate_drift(
            start_lat, start_lon, current_speed, current_direction,
            wind_speed, wind_direction, estimated_time
        )

        distance_to_rescue = haversine(drift_lat, drift_lon, rescue_lat, rescue_lon)

        # Angle de dérive
        rescue_vec = np.array([rescue_lon - start_lon, rescue_lat - start_lat])
        drift_vec  = np.array([drift_lon  - start_lon, drift_lat  - start_lat])
        norms = np.linalg.norm(rescue_vec) * np.linalg.norm(drift_vec)
        drift_angle = np.degrees(np.arccos(np.clip(
            np.dot(rescue_vec, drift_vec) / norms if norms else 0, -1.0, 1.0
        )))

        total_drift_speed = math.sqrt(
            (current_speed * math.cos(math.radians(current_direction)) +
             0.3 * wind_speed * math.cos(math.radians(wind_direction)))**2 +
            (current_speed * math.sin(math.radians(current_direction)) +
             0.3 * wind_speed * math.sin(math.radians(wind_direction)))**2
        )

        return jsonify({
            'drift_lat':          drift_lat,
            'drift_lon':          drift_lon,
            'distance_to_rescue': initial_distance,
            'drift_angle':        drift_angle,
            'drift_speed':        total_drift_speed,
            'drift_time':         estimated_time,
            'rescue_offset':      distance_to_rescue,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# =============================================================================
# CLASSES — SIMULATION AVANCÉE DE DÉRIVE
# =============================================================================

class AdvancedDriftCalculator:
    def __init__(self):
        self.earth_radius  = 6371
        self.nautical_mile = 1.852

    def calculate_drift(self, start_position, current_data, wind_data,
                        object_type, sea_state, duration_hours, time_step=0.1):
        try:
            coeffs     = DRIFT_COEFFICIENTS.get(object_type, DRIFT_COEFFICIENTS['person'])
            sea_factor = SEA_STATE_FACTORS.get(sea_state, SEA_STATE_FACTORS[3])

            current_speed_ms = current_data['speed'] * self.nautical_mile * 1000 / 3600
            wind_speed_ms    = wind_data['speed']    * self.nautical_mile * 1000 / 3600

            current_dir_rad = np.radians(current_data['direction'])
            wind_dir_rad    = np.radians(wind_data['direction'])
            leeway_angle    = coeffs['leeway_angle'] * sea_factor['leeway_multiplier']

            current_u = current_speed_ms * np.sin(current_dir_rad)
            current_v = current_speed_ms * np.cos(current_dir_rad)

            wind_eff_speed = wind_speed_ms * coeffs['wind_effect']
            wind_u = wind_eff_speed * np.sin(wind_dir_rad + np.radians(leeway_angle))
            wind_v = wind_eff_speed * np.cos(wind_dir_rad + np.radians(leeway_angle))

            total_u     = current_u + wind_u
            total_v     = current_v + wind_v
            total_speed = np.sqrt(total_u**2 + total_v**2)

            positions    = []
            current_lat, current_lon = start_position
            cum_distance = 0

            n_steps = int(duration_hours / time_step) + 1
            for i in range(n_steps):
                hour         = i * time_step
                delta_sec    = time_step * 3600
                dist_step    = total_speed * delta_sec / 1000
                cum_distance+= dist_step
                direction    = np.degrees(np.arctan2(total_u, total_v)) % 360

                new_pos = self._calculate_new_position((current_lat, current_lon), dist_step, direction)
                positions.append({
                    'time':                 round(hour, 2),
                    'time_str':             self._format_time(hour),
                    'lat':                  new_pos[0],
                    'lon':                  new_pos[1],
                    'speed_knots':          total_speed * 3600 / (self.nautical_mile * 1000),
                    'direction':            direction,
                    'distance_from_start_km': self._calculate_distance(start_position, new_pos),
                    'cumulative_distance':  cum_distance,
                })
                current_lat, current_lon = new_pos

            metrics     = self._calculate_metrics(positions, duration_hours)
            search_area = self.calculate_search_area(positions)

            return {
                'trajectory':       positions,
                'hourly_positions': [p for p in positions if p['time'] % 1 < 0.01 or p['time'] % 1 > 0.99],
                'final_position':   positions[-1] if positions else None,
                'metrics':          metrics,
                'search_area':      search_area,
                'coefficients_used':coeffs,
                'sea_state':        sea_factor,
            }
        except Exception as e:
            logger.error(f"Erreur calculate_drift: {e}")
            return {
                'trajectory': [], 'hourly_positions': [],
                'final_position': {'lat': start_position[0], 'lon': start_position[1]},
                'metrics': {'avg_speed':0,'max_speed':0,'min_speed':0,'speed_std':0,
                            'total_distance':0,'max_distance':0,'avg_drift_rate':0},
                'search_area': {'radius_km':5.0,'area_km2':78.5,
                                'center':{'lat':start_position[0],'lon':start_position[1]}}
            }

    def _calculate_new_position(self, start_point, distance_km, bearing):
        try:
            lat1, lon1   = np.radians(start_point)
            bearing_rad  = np.radians(bearing)
            ang_dist     = distance_km / 6371
            lat2 = np.arcsin(np.sin(lat1)*np.cos(ang_dist) +
                             np.cos(lat1)*np.sin(ang_dist)*np.cos(bearing_rad))
            lon2 = lon1 + np.arctan2(
                np.sin(bearing_rad)*np.sin(ang_dist)*np.cos(lat1),
                np.cos(ang_dist) - np.sin(lat1)*np.sin(lat2)
            )
            return (float(np.degrees(lat2)), float(np.degrees(lon2)))
        except Exception:
            return start_point

    def _calculate_distance(self, point1, point2):
        try:
            p1 = (point1['lat'], point1['lon']) if isinstance(point1, dict) else (point1[0], point1[1])
            p2 = (point2['lat'], point2['lon']) if isinstance(point2, dict) else (point2[0], point2[1])
            return geodesic(p1, p2).kilometers
        except Exception:
            return 0

    def _calculate_metrics(self, positions, duration):
        if not positions or len(positions) < 2:
            return {'avg_speed':0,'max_speed':0,'min_speed':0,'speed_std':0,
                    'total_distance':0,'max_distance':0,'avg_drift_rate':0}
        speeds    = [p['speed_knots'] for p in positions]
        distances = [p['distance_from_start_km'] for p in positions]
        return {
            'avg_speed':      float(np.mean(speeds)),
            'max_speed':      float(np.max(speeds)),
            'min_speed':      float(np.min(speeds)),
            'speed_std':      float(np.std(speeds)),
            'total_distance': float(distances[-1]),
            'max_distance':   float(max(distances)),
            'avg_drift_rate': float(distances[-1] / duration) if duration > 0 else 0,
        }

    def _format_time(self, hours):
        total_seconds = int(hours * 3600)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"{h:02d}:{m:02d}"

    def calculate_search_area(self, positions, confidence_level=0.95):
        try:
            if not positions or len(positions) < 2:
                return {'radius_km':5.0,'area_km2':78.5,
                        'center':{'lat':positions[0]['lat'] if positions else 33.5731,
                                  'lon':positions[0]['lon'] if positions else -7.5898}}
            lats = [p['lat'] for p in positions]
            lons = [p['lon'] for p in positions]
            center_lat = float(np.mean(lats))
            center_lon = float(np.mean(lons))
            radius_km  = max(5.0, float(1.96 * np.sqrt(
                (np.std(lats)*111.32)**2 +
                (np.std(lons)*111.32*np.cos(np.radians(center_lat)))**2
            )))
            return {'radius_km': radius_km, 'area_km2': float(np.pi * radius_km**2),
                    'center': {'lat': center_lat, 'lon': center_lon},
                    'confidence_level': confidence_level}
        except Exception:
            return {'radius_km':5.0,'area_km2':78.5,
                    'center':{'lat':33.5731,'lon':-7.5898},'confidence_level':confidence_level}


class DriftUncertaintyModel:
    def generate_ensemble(self, base_simulation, n_members=50):
        try:
            final_pos = base_simulation.get('final_position', {})
            center = {'lat': final_pos.get('lat', 33.5731), 'lon': final_pos.get('lon', -7.5898)} \
                     if isinstance(final_pos, dict) else {'lat': 33.5731, 'lon': -7.5898}
            return {
                'dispersion': {'mean_radius': 5.0, 'max_radius': 10.0, 'members': n_members},
                'most_probable_area': {'center': center, 'probability': 0.68, 'radius_km': 5.0}
            }
        except Exception:
            return {
                'dispersion': {'mean_radius': 5.0, 'max_radius': 10.0, 'members': n_members},
                'most_probable_area': {'center': {'lat': 33.5731, 'lon': -7.5898},
                                       'probability': 0.68, 'radius_km': 5.0}
            }


class SearchPatternGenerator:
    def __init__(self):
        self.patterns = SEARCH_PATTERNS
        self.assets   = MRCC_ASSETS

    def _to_tuple(self, point):
        if isinstance(point, dict):
            return (float(point.get('lat', 33.5731)), float(point.get('lon', -7.5898)))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            return (float(point[0]), float(point[1]))
        return (33.5731, -7.5898)

    def generate_expanding_square(self, center, initial_leg=0.5, max_legs=8):
        try:
            lat, lon   = self._to_tuple(center)
            points     = [(lat, lon)]
            leg_km     = initial_leg * 1.852
            lat_step   = leg_km / 111.32
            lon_step   = leg_km / (111.32 * np.cos(np.radians(lat)))
            directions = [(1,0),(0,1),(-1,0),(0,-1)]
            cur_lat, cur_lon = lat, lon
            for leg in range(1, max_legs + 1):
                d = directions[(leg - 1) % 4]
                for _ in range((leg + 1) // 2):
                    cur_lat += d[0] * lat_step
                    cur_lon += d[1] * lon_step
                    points.append((float(cur_lat), float(cur_lon)))
            return points
        except Exception:
            return [(33.5731, -7.5898)]

    def generate_sector_search(self, center, radius_nautical=2, sectors=8):
        try:
            lat, lon   = self._to_tuple(center)
            points     = [(lat, lon)]
            radius_km  = radius_nautical * 1.852
            lat_r      = radius_km / 111.32
            lon_r      = radius_km / (111.32 * np.cos(np.radians(lat)))
            for i in range(sectors + 1):
                angle = np.radians(i * 360 / sectors)
                points.append((float(lat + lat_r * np.cos(angle)), float(lon + lon_r * np.sin(angle))))
                points.append((lat, lon))
            return points
        except Exception:
            return [(33.5731, -7.5898)]

    def generate_parallel_track(self, start_point, end_point, track_spacing_nautical=0.3):
        try:
            start = self._to_tuple(start_point)
            end   = self._to_tuple(end_point)
            points= []
            bearing    = self._bearing(start, end)
            length     = geodesic(start, end).kilometers
            spacing_km = track_spacing_nautical * 1.852
            perp       = (bearing + 90) % 360
            n_tracks   = max(3, int(length / spacing_km)) if length > 0 else 3
            for i in range(n_tracks):
                offset = (i - n_tracks//2) * spacing_km
                ts = self._offset_point(start, perp, offset)
                te = self._offset_point(end,   perp, offset)
                points.extend([ts, te])
            return points
        except Exception:
            return [self._to_tuple(start_point)]

    def _bearing(self, p1, p2):
        lat1, lon1 = np.radians(p1); lat2, lon2 = np.radians(p2)
        dlon = lon2 - lon1
        x    = np.sin(dlon) * np.cos(lat2)
        y    = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        return (np.degrees(np.arctan2(x, y)) + 360) % 360

    def _offset_point(self, point, bearing, distance_km):
        lat, lon = np.radians(point)
        b = np.radians(bearing)
        d = distance_km / 6371
        lat2 = np.arcsin(np.sin(lat)*np.cos(d) + np.cos(lat)*np.sin(d)*np.cos(b))
        lon2 = lon + np.arctan2(np.sin(b)*np.sin(d)*np.cos(lat),
                                np.cos(d) - np.sin(lat)*np.sin(lat2))
        return (float(np.degrees(lat2)), float(np.degrees(lon2)))


# ─── Instances globales ───────────────────────────────────────────────────────
drift_calculator  = AdvancedDriftCalculator()
uncertainty_model = DriftUncertaintyModel()
pattern_generator = SearchPatternGenerator()


@app.route('/api/simulate-drift', methods=['POST'])
def api_simulate_drift():
    """API de simulation de dérive avancée"""
    try:
        data = request.get_json()
        logger.info(f"Simulation demandée avec paramètres: {data}")
        
        # Validation des champs obligatoires
        required_fields = ['start_lat', 'start_lon', 'current_speed', 'current_direction', 
                          'wind_speed', 'wind_direction']
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'error': f'Champ manquant: {field}'
                }), 400
        
        # Extraction des paramètres avec conversion sécurisée
        try:
            start_position = (
                float(data['start_lat']),
                float(data['start_lon'])
            )
            
            current_data = {
                'speed': float(data['current_speed']),
                'direction': float(data['current_direction'])
            }
            
            wind_data = {
                'speed': float(data['wind_speed']),
                'direction': float(data['wind_direction'])
            }
            
            object_type = str(data.get('object_type', 'person'))
            sea_state = int(data.get('sea_state', 3))
            duration_hours = int(data.get('simulation_hours', 24))
            time_step = float(data.get('time_step', 0.1))
            water_temperature = float(data.get('water_temperature', 18))
            has_survival_gear = bool(data.get('has_survival_gear', False))
            persons_count = int(data.get('persons', 1))
            hours_since = float(data.get('hours_since', 0))
            visibility_km = float(data.get('visibility', 10))
            use_ensemble = bool(data.get('use_ensemble', False))
            
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False, 
                'error': f'Erreur de conversion des données: {str(e)}'
            }), 400
        
        # Exécuter la simulation principale
        simulation_results = drift_calculator.calculate_drift(
            start_position, current_data, wind_data,
            object_type, sea_state, duration_hours, time_step
        )
        
        # S'assurer que simulation_results a la structure attendue
        if not simulation_results.get('trajectory'):
            simulation_results['trajectory'] = []
        if not simulation_results.get('hourly_positions'):
            simulation_results['hourly_positions'] = []
        if not simulation_results.get('final_position'):
            simulation_results['final_position'] = {
                'lat': start_position[0], 
                'lon': start_position[1],
                'time': duration_hours,
                'distance_from_start_km': 0,
                'speed_knots': 0,
                'direction': 0
            }
        if 'metrics' not in simulation_results:
            simulation_results['metrics'] = {
                'avg_speed': 0,
                'max_speed': 0,
                'min_speed': 0,
                'speed_std': 0,
                'total_distance': 0,
                'max_distance': 0,
                'avg_drift_rate': 0
            }
        if 'search_area' not in simulation_results:
            simulation_results['search_area'] = {
                'radius_km': 5.0,
                'area_km2': 78.5,
                'center': {
                    'lat': start_position[0],
                    'lon': start_position[1]
                },
                'confidence_level': 0.95
            }
        
        # Calculer les métriques supplémentaires
        if simulation_results['trajectory']:
            speeds = [p.get('speed_knots', 0) for p in simulation_results['trajectory']]
            distances = [p.get('distance_from_start_km', 0) for p in simulation_results['trajectory']]
            
            simulation_results['metrics']['total_distance'] = distances[-1] if distances else 0
            simulation_results['metrics']['max_distance'] = max(distances) if distances else 0
            simulation_results['metrics']['avg_speed'] = sum(speeds) / len(speeds) if speeds else 0
            simulation_results['metrics']['max_speed'] = max(speeds) if speeds else 0
        
        # Générer l'analyse de risque
        environment_data = {
            'water_temperature': water_temperature,
            'sea_state': sea_state,
            'visibility_km': visibility_km,
            'wind_speed': wind_data['speed']
        }
        
        incident_data = {
            'hours_since_incident': hours_since,
            'type': object_type,
            'persons_on_board': persons_count,
            'has_survival_gear': has_survival_gear,
            'available_assets': 3
        }
        
        risk_analysis = analyze_risk(
            simulation_results, environment_data, incident_data
        )
        
        # Générer les motifs de recherche
        final_pos = simulation_results.get('final_position', {})
        center_lat = final_pos.get('lat', start_position[0]) if isinstance(final_pos, dict) else start_position[0]
        center_lon = final_pos.get('lon', start_position[1]) if isinstance(final_pos, dict) else start_position[1]
        
        search_patterns = {
            'expanding_square': generate_expanding_square_pattern(center_lat, center_lon),
            'sector_search': generate_sector_search_pattern(center_lat, center_lon),
            'parallel_track': generate_parallel_track_pattern(center_lat, center_lon)
        }
        
        # Construire la réponse
        response = {
            'success': True,
            'simulation_results': {
                'trajectory': simulation_results.get('trajectory', []),
                'hourly_positions': simulation_results.get('hourly_positions', []),
                'final_position': simulation_results.get('final_position', {
                    'lat': start_position[0],
                    'lon': start_position[1],
                    'time': duration_hours,
                    'distance_from_start_km': 0,
                    'speed_knots': 0,
                    'direction': 0
                }),
                'metrics': simulation_results.get('metrics', {}),
                'search_area': simulation_results.get('search_area', {}),
                'total_drift_distance': simulation_results.get('metrics', {}).get('total_distance', 0),
                'average_speed': simulation_results.get('metrics', {}).get('avg_speed', 0),
                'max_distance': simulation_results.get('metrics', {}).get('max_distance', 0)
            },
            'risk_analysis': risk_analysis,
            'search_patterns': search_patterns,
            'metadata': {
                'simulation_time': datetime.now().isoformat(),
                'parameters_used': {
                    'start_lat': start_position[0],
                    'start_lon': start_position[1],
                    'current_speed': current_data['speed'],
                    'current_direction': current_data['direction'],
                    'wind_speed': wind_data['speed'],
                    'wind_direction': wind_data['direction'],
                    'object_type': object_type,
                    'sea_state': sea_state,
                    'duration_hours': duration_hours,
                    'time_step': time_step
                },
                'mrcc_center': {'lat': 33.5731, 'lon': -7.5898}
            }
        }
        
        logger.info("Simulation réussie")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erreur simulation: {str(e)}", exc_info=True)
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': e.__class__.__name__,
            'traceback': traceback.format_exc()
        }), 500


def analyze_risk(simulation_results, environment_data, incident_data):
    """Analyse des risques simplifiée"""
    try:
        # Score environnemental
        env_score = 0
        env_factors = []
        
        water_temp = environment_data.get('water_temperature', 18)
        if water_temp < 10:
            env_score += 30
            env_factors.append('Eau très froide - hypothermie rapide')
        elif water_temp < 15:
            env_score += 20
            env_factors.append('Eau froide - risque d\'hypothermie')
        elif water_temp < 20:
            env_score += 10
            env_factors.append('Eau tempérée - risque modéré')
        
        sea_state = environment_data.get('sea_state', 3)
        env_score += sea_state * 5
        env_factors.append(f'État de la mer: {sea_state}/5')
        
        wind_speed = environment_data.get('wind_speed', 0)
        if wind_speed > 30:
            env_score += 25
            env_factors.append('Vent violent')
        elif wind_speed > 20:
            env_score += 15
            env_factors.append('Vent fort')
        
        env_score = min(100, env_score)
        
        # Score opérationnel
        op_score = 0
        op_factors = []
        
        final_pos = simulation_results.get('final_position', {})
        if isinstance(final_pos, dict):
            distance = final_pos.get('distance_from_start_km', 0)
            if distance > 100:
                op_score += 30
                op_factors.append('Très éloigné des côtes')
            elif distance > 50:
                op_score += 20
                op_factors.append('Éloigné des côtes')
            elif distance > 20:
                op_score += 10
                op_factors.append('À distance modérée des côtes')
        
        hours_since = incident_data.get('hours_since_incident', 0)
        op_score += min(30, hours_since * 2)
        op_factors.append(f'Temps écoulé: {hours_since}h')
        
        op_score = min(100, op_score)
        
        # Score médical
        med_score = 0
        med_factors = []
        
        incident_type = incident_data.get('type', 'person')
        med_score += 30
        med_factors.append(f'Type: {incident_type}')
        
        persons = incident_data.get('persons_on_board', 1)
        if persons > 10:
            med_score += 25
            med_factors.append('Groupe important')
        elif persons > 5:
            med_score += 15
            med_factors.append('Groupe moyen')
        
        has_survival_gear = incident_data.get('has_survival_gear', False)
        if not has_survival_gear:
            med_score += 20
            med_factors.append('Absence d\'équipement de survie')
        
        med_score = min(100, med_score)
        
        # Score de navigation
        nav_score = 0
        nav_factors = ['Navigation standard']
        
        # Score global
        global_score = (env_score * 0.3 + op_score * 0.3 + med_score * 0.4)
        
        # Déterminer le niveau de priorité
        if global_score >= 80:
            priority_level = {'level': 'CRITIQUE', 'color': 'red', 'code': 'EMERGENCY'}
        elif global_score >= 60:
            priority_level = {'level': 'ÉLEVÉ', 'color': 'orange', 'code': 'PRIORITY'}
        elif global_score >= 40:
            priority_level = {'level': 'MODÉRÉ', 'color': 'yellow', 'code': 'STANDARD'}
        else:
            priority_level = {'level': 'FAIBLE', 'color': 'green', 'code': 'ROUTINE'}
        
        # Générer recommandations
        recommendations = []
        if global_score > 80:
            recommendations.extend([
                "🚨 DÉCLENCHER ALERTE GÉNÉRALE",
                "🚁 DÉPLOYER TOUS MOYENS AÉRIENS",
                "🛥️ MOBILISER FLOTTE DE SAUVETAGE"
            ])
        elif global_score > 60:
            recommendations.extend([
                "🔴 DÉCLENCHER ALERTE RÉGIONALE",
                "🚁 PRÉPARER HÉLICOPTÈRES",
                "🛥️ MOBILISER PATROUILLEURS"
            ])
        elif global_score > 40:
            recommendations.extend([
                "🟡 SURVEILLANCE ACCRUE",
                "🛥️ PRÉPARER MOYENS D'INTERVENTION"
            ])
        else:
            recommendations.extend([
                "🟢 SURVEILLANCE STANDARD",
                "🛥️ MOYENS EN ALERTE"
            ])
        
        # Temps de survie estimé
        survival_time = 12
        if water_temp < 10:
            survival_time = 3
        elif water_temp < 15:
            survival_time = 6
        elif water_temp < 20:
            survival_time = 12
        else:
            survival_time = 24
        
        if has_survival_gear:
            survival_time = min(48, survival_time * 2)
        
        return {
            'assessment_date': datetime.now().isoformat(),
            'global_score': global_score,
            'priority_level': priority_level,
            'risk_factors': {
                'environmental': {'score': env_score, 'factors': env_factors},
                'operational': {'score': op_score, 'factors': op_factors},
                'medical': {'score': med_score, 'factors': med_factors, 'estimated_survival_hours': survival_time},
                'navigational': {'score': nav_score, 'factors': nav_factors}
            },
            'recommendations': recommendations,
            'requires_immediate_action': global_score > 75,
            'estimated_survival_time': survival_time
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse risque: {e}")
        return {
            'assessment_date': datetime.now().isoformat(),
            'global_score': 50,
            'priority_level': {'level': 'MODÉRÉ', 'color': 'yellow', 'code': 'STANDARD'},
            'risk_factors': {},
            'recommendations': ['🟡 Analyser la situation', '🛥️ Préparer moyens d\'intervention'],
            'requires_immediate_action': False,
            'estimated_survival_time': 12
        }


def generate_expanding_square_pattern(center_lat, center_lon, initial_leg=0.5, max_legs=8):
    """Génère un motif de recherche en carré expansif"""
    points = [(center_lat, center_lon)]
    
    leg_km = initial_leg * 1.852
    lat_step = leg_km / 111.32
    lon_step = leg_km / (111.32 * np.cos(np.radians(center_lat)))
    
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    current_lat, current_lon = center_lat, center_lon
    
    for leg in range(1, max_legs + 1):
        direction = directions[(leg - 1) % 4]
        step_multiplier = (leg + 1) // 2
        
        for _ in range(step_multiplier):
            current_lat += direction[0] * lat_step
            current_lon += direction[1] * lon_step
            points.append((current_lat, current_lon))
    
    return points


def generate_sector_search_pattern(center_lat, center_lon, radius_nautical=2, sectors=8):
    """Génère un motif de recherche sectorielle"""
    points = [(center_lat, center_lon)]
    
    radius_km = radius_nautical * 1.852
    lat_radius = radius_km / 111.32
    lon_radius = radius_km / (111.32 * np.cos(np.radians(center_lat)))
    
    for i in range(sectors + 1):
        angle = (i * 360 / sectors)
        angle_rad = np.radians(angle)
        
        sector_lat = center_lat + lat_radius * np.cos(angle_rad)
        sector_lon = center_lon + lon_radius * np.sin(angle_rad)
        points.append((sector_lat, sector_lon))
        points.append((center_lat, center_lon))
    
    return points


def generate_parallel_track_pattern(center_lat, center_lon, track_spacing_nautical=0.3, n_tracks=5):
    """Génère un motif de traces parallèles"""
    points = []
    spacing_km = track_spacing_nautical * 1.852
    lat_spacing = spacing_km / 111.32
    lon_spacing = spacing_km / (111.32 * np.cos(np.radians(center_lat)))
    
    for i in range(-n_tracks//2, n_tracks//2 + 1):
        offset_lat = center_lat + i * lat_spacing
        start_lon = center_lon - 0.5  # 0.5 degrés vers l'ouest
        end_lon = center_lon + 0.5    # 0.5 degrés vers l'est
        points.append((offset_lat, start_lon))
        points.append((offset_lat, end_lon))
    
    return points

@app.route('/api/search-patterns', methods=['POST'])
def api_search_patterns():
    try:
        data       = request.get_json()
        center     = (data['lat'], data['lon'])
        radius     = data.get('radius', 2)
        patterns   = {
            'expanding_square': pattern_generator.generate_expanding_square(center),
            'sector_search':    pattern_generator.generate_sector_search(center, radius),
            'parallel_track':   pattern_generator.generate_parallel_track(
                center, data.get('end_point', center), data.get('spacing', 0.3)
            ),
        }
        pattern_type = data.get('pattern', 'expanding_square')
        return jsonify({
            'success': True,
            'pattern_type': pattern_type,
            'coordinates':  patterns.get(pattern_type, patterns['expanding_square']),
            'metadata':     {'center': center, 'generated_at': datetime.now().isoformat()}
        })
    except Exception as e:
        logger.error(str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get-search-patterns', methods=['POST'])
def api_get_search_patterns():
    data = request.get_json()
    return jsonify(generate_search_patterns(data['lat'], data['lon'], data.get('radius', 10)))


def generate_search_patterns(center_lat, center_lon, radius_km):
    patterns = {'expanding_square': [], 'sector_search': [], 'parallel_track': []}
    for i in range(5):
        side = radius_km * (i + 1) / 5
        lat_r = side / 111.32
        lon_r = side / (111.32 * np.cos(np.radians(center_lat)))
        patterns['expanding_square'].extend([
            [center_lat + lat_r, center_lon + lon_r],
            [center_lat + lat_r, center_lon - lon_r],
            [center_lat - lat_r, center_lon - lon_r],
            [center_lat - lat_r, center_lon + lon_r],
        ])
    return patterns


@app.route('/api/maritime-routes', methods=['GET'])
def api_maritime_routes():
    return jsonify({
        'success': True,
        'routes':       MARITIME_ROUTES,
        'fishing_zones':FISHING_ZONES,
        'mrcc_zones':   MRCC_MAROC['zones'],
    })


# =============================================================================
# ROUTES API OPTIMISÉES - BALISES PLB
# =============================================================================

from flask_caching import Cache
from sqlalchemy import func, or_, and_, desc
import json

# Configuration du cache
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})

@app.route('/api/balises', methods=['GET'])
def api_get_all_balises():
    """Récupérer toutes les balises avec pagination optimisée"""
    try:
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        
        # Limitation pour performance
        if per_page > 100:
            per_page = 100
        
        query = BalisePLB.query
        
        # Recherche optimisée avec OR
        if search and len(search) >= 2:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    BalisePLB.registration_number.ilike(search_pattern),
                    BalisePLB.unit_name.ilike(search_pattern),
                    BalisePLB.mmsi.ilike(search_pattern),
                    BalisePLB.uin.ilike(search_pattern),
                    BalisePLB.owner.ilike(search_pattern),
                    BalisePLB.manufacturer.ilike(search_pattern)
                )
            )
        
        # Filtre par statut
        if status_filter:
            query = query.filter(BalisePLB.beacon_status == status_filter)
        
        # Pagination avec count optimisé
        total = query.count()
        balises = query.order_by(desc(BalisePLB.id)).offset((page - 1) * per_page).limit(per_page).all()
        
        # Calcul des pages
        pages = (total + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'data': [b.to_dict_light() for b in balises],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages,
                'has_next': page < pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération balises: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ──────────────────────────────────────────────────────────────────
# ROUTES API - STATISTIQUES BALISES
# ──────────────────────────────────────────────────────────────────

@app.route('/api/balises/stats', methods=['GET'])
def api_get_balises_stats():
    """Récupérer les statistiques des balises"""
    try:
        total = BalisePLB.query.count()
        actives = BalisePLB.query.filter(BalisePLB.beacon_status == 'Actif').count()
        expired = BalisePLB.query.filter(BalisePLB.beacon_status == 'Expiré').count()
        maintenance = BalisePLB.query.filter(BalisePLB.beacon_status == 'Maintenance').count()
        inactif = BalisePLB.query.filter(BalisePLB.beacon_status == 'Inactif').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'actives': actives,
                'expired': expired,
                'maintenance': maintenance,
                'inactif': inactif
            }
        })
    except Exception as e:
        logger.error(f"Erreur stats balises: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises/manufacturers', methods=['GET'])
def api_get_balises_manufacturers():
    """Récupérer les statistiques par fabricant"""
    try:
        from sqlalchemy import func
        
        manufacturers = db.session.query(
            BalisePLB.manufacturer, 
            func.count(BalisePLB.id).label('count')
        ).filter(
            BalisePLB.manufacturer.isnot(None),
            BalisePLB.manufacturer != ''
        ).group_by(
            BalisePLB.manufacturer
        ).order_by(
            func.count(BalisePLB.id).desc()
        ).limit(10).all()
        
        return jsonify({
            'success': True,
            'manufacturers': [{'name': m[0] or 'Inconnu', 'count': m[1]} for m in manufacturers]
        })
    except Exception as e:
        logger.error(f"Erreur fabricants balises: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises/status-distribution', methods=['GET'])
def api_get_balises_status_distribution():
    """Récupérer la distribution des statuts"""
    try:
        from sqlalchemy import func
        
        status_counts = db.session.query(
            BalisePLB.beacon_status, 
            func.count(BalisePLB.id).label('count')
        ).filter(
            BalisePLB.beacon_status.isnot(None)
        ).group_by(
            BalisePLB.beacon_status
        ).all()
        
        # Couleurs par statut
        status_colors = {
            'Actif': '#198754',
            'Inactif': '#6c757d',
            'Expiré': '#dc3545',
            'Maintenance': '#0dcaf0'
        }
        
        return jsonify({
            'success': True,
            'distribution': [
                {
                    'status': s[0], 
                    'count': s[1],
                    'color': status_colors.get(s[0], '#6c757d')
                } for s in status_counts if s[0]
            ]
        })
    except Exception as e:
        logger.error(f"Erreur distribution statuts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises/<int:balise_id>', methods=['GET'])
@cache.cached(timeout=600, key_prefix=lambda: f'balise_{request.view_args["balise_id"]}')
def api_get_balise(balise_id):
    """Récupérer une balise par son ID (avec cache)"""
    try:
        balise = BalisePLB.query.get(balise_id)
        if not balise:
            return jsonify({'success': False, 'error': 'Balise non trouvée'}), 404
        return jsonify({'success': True, 'data': balise.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises', methods=['POST'])
def api_create_balise():
    """Créer une nouvelle balise"""
    try:
        data = request.get_json()
        
        balise = BalisePLB(
            registration_number=data.get('registration_number'),
            unit_name=data.get('unit_name'),
            port=data.get('port'),
            mmsi=data.get('mmsi'),
            tac=data.get('tac'),
            activity_type=data.get('activity_type'),
            uin=data.get('uin'),
            serial_number_manufacturer=data.get('serial_number_manufacturer'),
            serial_number_sar=data.get('serial_number_sar'),
            registration_date=data.get('registration_date'),
            battery_expiration_date=data.get('battery_expiration_date'),
            manufacturer=data.get('manufacturer'),
            beacon_type=data.get('beacon_type'),
            model=data.get('model'),
            beacon_status=data.get('beacon_status', 'Actif'),
            owner=data.get('owner'),
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            secondary_phone_number=data.get('secondary_phone_number'),
            address=data.get('address'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone_number=data.get('emergency_contact_phone_number'),
            secondary_emergency_contact_name=data.get('secondary_emergency_contact_name'),
            secondary_emergency_contact_phone_number=data.get('secondary_emergency_contact_phone_number')
        )
        
        db.session.add(balise)
        db.session.commit()
        
        # Invalider le cache des stats
        cache.delete('balises_stats')
        
        return jsonify({'success': True, 'message': 'Balise créée avec succès', 'id': balise.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur création balise: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises/<int:balise_id>', methods=['PUT'])
def api_update_balise(balise_id):
    """Mettre à jour une balise"""
    try:
        balise = BalisePLB.query.get(balise_id)
        if not balise:
            return jsonify({'success': False, 'error': 'Balise non trouvée'}), 404
        
        data = request.get_json()
        
        # Mise à jour des champs
        updatable_fields = [
            'registration_number', 'unit_name', 'port', 'mmsi', 'tac', 'activity_type',
            'uin', 'serial_number_manufacturer', 'serial_number_sar', 'registration_date',
            'battery_expiration_date', 'manufacturer', 'beacon_type', 'model',
            'beacon_status', 'owner', 'email', 'phone_number', 'secondary_phone_number',
            'address', 'emergency_contact_name', 'emergency_contact_phone_number',
            'secondary_emergency_contact_name', 'secondary_emergency_contact_phone_number'
        ]
        
        for field in updatable_fields:
            if field in data and data[field] is not None:
                setattr(balise, field, data[field])
        
        balise.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Invalider les caches
        cache.delete('balises_stats')
        cache.delete(f'balise_{balise_id}')
        
        return jsonify({'success': True, 'message': 'Balise mise à jour avec succès'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur mise à jour balise: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/balises/<int:balise_id>', methods=['DELETE'])
def api_delete_balise(balise_id):
    """Supprimer une balise"""
    try:
        balise = BalisePLB.query.get(balise_id)
        if not balise:
            return jsonify({'success': False, 'error': 'Balise non trouvée'}), 404
        
        db.session.delete(balise)
        db.session.commit()
        
        # Invalider les caches
        cache.delete('balises_stats')
        cache.delete(f'balise_{balise_id}')
        
        return jsonify({'success': True, 'message': 'Balise supprimée avec succès'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur suppression balise: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recherche-balise', methods=['POST'])
def api_recherche_balise():
    """Recherche rapide optimisée (pour le formulaire principal)"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'error': 'Veuillez entrer un code'}), 400
        
        if len(code) < 3:
            return jsonify({'error': 'Le code doit contenir au moins 3 caractères'}), 400
        
        search_pattern = f'%{code}%'
        
        # Requête optimisée avec .first()
        balise = BalisePLB.query.filter(
            or_(
                BalisePLB.registration_number.ilike(search_pattern),
                BalisePLB.mmsi.ilike(search_pattern),
                BalisePLB.uin.ilike(search_pattern),
                db.cast(BalisePLB.serial_number_manufacturer, db.String).ilike(search_pattern),
                db.cast(BalisePLB.serial_number_sar, db.String).ilike(search_pattern),
                BalisePLB.unit_name.ilike(search_pattern)
            )
        ).first()
        
        if balise:
            return jsonify(balise.to_dict())
        else:
            return jsonify({'error': 'Aucune balise trouvée avec ce code'}), 404
            
    except Exception as e:
        logger.error(f"Erreur recherche balise: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/balises/export', methods=['GET'])
def api_export_balises():
    """Exporter toutes les balises en CSV (optimisé pour gros volume)"""
    try:
        import csv
        from io import StringIO
        
        # Récupérer toutes les balises par lots
        batch_size = 1000
        offset = 0
        all_balises = []
        
        while True:
            batch = BalisePLB.query.offset(offset).limit(batch_size).all()
            if not batch:
                break
            all_balises.extend(batch)
            offset += batch_size
        
        output = StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            'ID', 'N° Enregistrement', 'Nom Unité', 'Port', 'MMSI', 'UIN',
            'Statut', 'Propriétaire', 'Email', 'Téléphone', 'Fabricant',
            'Modèle', 'Type', 'Date enregistrement', 'Expiration batterie'
        ])
        
        for b in all_balises:
            writer.writerow([
                b.id, b.registration_number or '', b.unit_name or '', b.port or '',
                b.mmsi or '', b.uin or '', b.beacon_status or '', b.owner or '',
                b.email or '', b.phone_number or '', b.manufacturer or '',
                b.model or '', b.beacon_type or '', b.registration_date or '',
                b.battery_expiration_date or ''
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=balises_plb_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.data = '\uFEFF' + response.data.decode('utf-8')
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur export: {str(e)}")
        return jsonify({'error': str(e)}), 500














# =============================================================================
# ROUTES API - GESTION PLB AVEC CYCLE DE VIE
# =============================================================================

from datetime import datetime, timedelta
import json
import qrcode
import base64
from io import BytesIO
from weasyprint import HTML
import tempfile
import os

# ==================== CRUD PRINCIPAL ====================

@app.route('/api/plb', methods=['GET'])
def api_get_plb_list():
    """Récupérer la liste des PLB avec pagination et filtres"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        vessel = request.args.get('vessel', '')
        
        query = BalisePLB.query
        
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    BalisePLB.registration_number.ilike(search_pattern),
                    BalisePLB.uin.ilike(search_pattern),
                    BalisePLB.mmsi.ilike(search_pattern),
                    BalisePLB.unit_name.ilike(search_pattern),
                    BalisePLB.owner.ilike(search_pattern)
                )
            )
        
        if status:
            query = query.filter(BalisePLB.beacon_status == status)
        
        if vessel:
            query = query.filter(BalisePLB.unit_name.ilike(f'%{vessel}%'))
        
        paginated = query.order_by(BalisePLB.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        # Statistiques avancées
        today = datetime.now().date()
        stats = {
            'total': BalisePLB.query.count(),
            'actifs': BalisePLB.query.filter(BalisePLB.beacon_status == 'Actif').count(),
            'expired_battery': BalisePLB.query.filter(
                BalisePLB.battery_expiration_date < today.isoformat(),
                BalisePLB.beacon_status == 'Actif'
            ).count(),
            'maintenance': BalisePLB.query.filter(BalisePLB.beacon_status == 'Maintenance').count(),
            'transfers_last_month': PLBTransfer.query.filter(
                PLBTransfer.transfer_date >= datetime.now() - timedelta(days=30)
            ).count()
        }
        
        return jsonify({
            'success': True,
            'data': [p.to_dict_light() for p in paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages
            },
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération PLB: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plb/<int:plb_id>', methods=['GET'])
def api_get_plb(plb_id):
    """Récupérer les détails complets d'une PLB avec historique"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        history = PLBHistory.query.filter_by(plb_id=plb_id).all()
        transfers = PLBTransfer.query.filter_by(plb_id=plb_id).all()
        maintenance = PLBMaintenance.query.filter_by(plb_id=plb_id).all()
        notifications = PLBNotification.query.filter_by(plb_id=plb_id).all()
        
        data = plb.to_dict()
        data['history'] = [h.to_dict() for h in history]
        data['transfers'] = [t.to_dict() for t in transfers]
        data['maintenance'] = [m.to_dict() for m in maintenance]
        data['notifications'] = [n.to_dict() for n in notifications]
        
        # Calcul des prochaines échéances
        today = datetime.now().date()
        if plb.battery_expiration_date:
            try:
                expiry_date = datetime.strptime(plb.battery_expiration_date, '%Y-%m-%d').date()
                data['days_until_battery_expiry'] = (expiry_date - today).days
            except:
                data['days_until_battery_expiry'] = None
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"Erreur récupération PLB {plb_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plb', methods=['POST'])
def api_create_plb():
    """Créer une nouvelle PLB avec traçabilité"""
    try:
        data = request.get_json()
        
        # Vérifier si le code hex existe déjà (via registration_number ou uin)
        existing = BalisePLB.query.filter(
            or_(
                BalisePLB.registration_number == data.get('registration_number'),
                BalisePLB.uin == data.get('uin')
            )
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Cette balise existe déjà'}), 400
        
        # Valider le code hexadécimal si fourni
        hex_code = data.get('registration_number', '')
        if hex_code and not validate_hex_code(hex_code):
            return jsonify({'success': False, 'error': 'Code hexadécimal invalide (15 caractères requis)'}), 400
        
        # Créer la PLB
        plb = BalisePLB(
            registration_number=hex_code,
            unit_name=data.get('unit_name'),
            port=data.get('port'),
            mmsi=data.get('mmsi'),
            tac=data.get('tac'),
            activity_type=data.get('activity_type'),
            uin=data.get('uin'),
            serial_number_manufacturer=data.get('serial_number_manufacturer'),
            serial_number_sar=data.get('serial_number_sar'),
            registration_date=datetime.now().strftime('%Y-%m-%d'),
            battery_expiration_date=data.get('battery_expiration_date'),
            manufacturer=data.get('manufacturer'),
            beacon_type=data.get('beacon_type', 'PLB'),
            model=data.get('model'),
            beacon_status='Actif',
            owner=data.get('owner'),
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            secondary_phone_number=data.get('secondary_phone_number'),
            address=data.get('address'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone_number=data.get('emergency_contact_phone_number'),
            secondary_emergency_contact_name=data.get('secondary_emergency_contact_name'),
            secondary_emergency_contact_phone_number=data.get('secondary_emergency_contact_phone_number'),
            created_by=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(plb)
        db.session.flush()
        
        # Ajouter à l'historique
        history = PLBHistory(
            plb_id=plb.id,
            action='CREATION',
            comment=f"Création de la balise PLB par {current_user.username if current_user.is_authenticated else 'System'}",
            user_id=current_user.id if current_user.is_authenticated else None,
            user_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(history)
        
        # Créer notification pour test mensuel
        notification = PLBNotification(
            plb_id=plb.id,
            notification_type='TEST_DUE',
            message=f"Premier test mensuel requis pour la PLB {plb.registration_number}",
            scheduled_date=datetime.now().date() + timedelta(days=30),
            status='PENDING'
        )
        db.session.add(notification)
        
        # Notification pour expiration batterie
        if plb.battery_expiration_date:
            try:
                expiry_date = datetime.strptime(plb.battery_expiration_date, '%Y-%m-%d').date()
                notification_battery = PLBNotification(
                    plb_id=plb.id,
                    notification_type='BATTERY_EXPIRY',
                    message=f"La batterie de la PLB {plb.registration_number} expire le {plb.battery_expiration_date}",
                    scheduled_date=expiry_date - timedelta(days=30),
                    status='PENDING'
                )
                db.session.add(notification_battery)
            except:
                pass
        
        db.session.commit()
        
        # Envoyer email de confirmation
        send_plb_registration_email(plb)
        
        return jsonify({'success': True, 'data': plb.to_dict(), 'message': 'PLB créée avec succès'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur création PLB: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== TRANSFERT PROPRIÉTAIRE/NAVIRE ====================

@app.route('/api/plb/<int:plb_id>/transfer', methods=['POST'])
def api_transfer_plb(plb_id):
    """Transférer une PLB à un nouveau propriétaire ou navire"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        data = request.get_json()
        
        transfer_type = data.get('transfer_type', 'BOTH')  # OWNER_CHANGE, VESSEL_CHANGE, BOTH
        
        # Sauvegarder les anciennes valeurs
        old_owner = plb.owner
        old_owner_email = plb.email
        old_owner_phone = plb.phone_number
        old_vessel_name = plb.unit_name
        old_vessel_mmsi = plb.mmsi
        
        # Créer l'enregistrement de transfert
        transfer = PLBTransfer(
            plb_id=plb.id,
            transfer_type=transfer_type,
            old_owner=old_owner,
            old_owner_email=old_owner_email,
            old_owner_phone=old_owner_phone,
            old_vessel_name=old_vessel_name,
            old_vessel_mmsi=old_vessel_mmsi,
            new_owner=data.get('new_owner', old_owner),
            new_owner_email=data.get('new_owner_email', old_owner_email),
            new_owner_phone=data.get('new_owner_phone', old_owner_phone),
            new_vessel_name=data.get('new_vessel_name', old_vessel_name),
            new_vessel_mmsi=data.get('new_vessel_mmsi', old_vessel_mmsi),
            comment=data.get('comment', ''),
            created_by=current_user.id if current_user.is_authenticated else None,
            created_by_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(transfer)
        
        # Mettre à jour la PLB
        if transfer_type in ['OWNER_CHANGE', 'BOTH']:
            plb.owner = data.get('new_owner', plb.owner)
            plb.email = data.get('new_owner_email', plb.email)
            plb.phone_number = data.get('new_owner_phone', plb.phone_number)
        
        if transfer_type in ['VESSEL_CHANGE', 'BOTH']:
            plb.unit_name = data.get('new_vessel_name', plb.unit_name)
            plb.mmsi = data.get('new_vessel_mmsi', plb.mmsi)
            # Si MMSI change, ajouter remarque dans historique
            if data.get('new_vessel_mmsi') and data.get('new_vessel_mmsi') != old_vessel_mmsi:
                transfer.comment += " - CHANGEMENT MMSI: Recodage nécessaire de la balise"
        
        # Ajouter à l'historique
        history = PLBHistory(
            plb_id=plb.id,
            action='TRANSFERT',
            field_changed='owner_and_vessel',
            old_value=json.dumps({'owner': old_owner, 'vessel': old_vessel_name, 'mmsi': old_vessel_mmsi}),
            new_value=json.dumps({'owner': plb.owner, 'vessel': plb.unit_name, 'mmsi': plb.mmsi}),
            comment=data.get('comment', ''),
            user_id=current_user.id if current_user.is_authenticated else None,
            user_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(history)
        
        plb.updated_at = datetime.now()
        
        db.session.commit()
        
        # Envoyer notifications
        send_transfer_notification(plb, {
            'name': old_owner,
            'email': old_owner_email,
            'phone': old_owner_phone
        })
        
        return jsonify({'success': True, 'message': 'Transfert effectué avec succès', 'transfer': transfer.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur transfert PLB {plb_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== MAINTENANCE ET TESTS ====================

@app.route('/api/plb/<int:plb_id>/maintenance', methods=['POST'])
def api_add_plb_maintenance(plb_id):
    """Ajouter un enregistrement de maintenance/test"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        data = request.get_json()
        
        maintenance = PLBMaintenance(
            plb_id=plb.id,
            maintenance_type=data.get('maintenance_type'),  # TEST_MENSUEL, BATTERY_CHANGE, INSPECTION, REPAIR
            maintenance_date=datetime.now(),
            performed_by=data.get('performed_by', current_user.username if current_user.is_authenticated else 'Unknown'),
            result=data.get('result', 'OK'),
            notes=data.get('notes', ''),
            battery_type=data.get('battery_type'),
            battery_serial=data.get('battery_serial'),
            new_expiry_date=data.get('new_expiry_date'),
            test_signal_received=data.get('test_signal_received', False),
            gps_fix_ok=data.get('gps_fix_ok', False),
            signal_strength=data.get('signal_strength'),
            created_by=current_user.id if current_user.is_authenticated else None,
            created_by_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(maintenance)
        
        # Mettre à jour la PLB si changement de batterie
        if data.get('maintenance_type') == 'BATTERY_CHANGE' and data.get('new_expiry_date'):
            plb.battery_expiration_date = data.get('new_expiry_date')
        
        # Mettre à jour la date de dernier test
        if data.get('maintenance_type') == 'TEST_MENSUEL':
            # Ajouter notification pour prochain test
            next_test_notification = PLBNotification(
                plb_id=plb.id,
                notification_type='TEST_DUE',
                message=f"Prochain test mensuel requis pour la PLB {plb.registration_number}",
                scheduled_date=datetime.now().date() + timedelta(days=30),
                status='PENDING'
            )
            db.session.add(next_test_notification)
        
        # Ajouter à l'historique
        history = PLBHistory(
            plb_id=plb.id,
            action='MAINTENANCE',
            field_changed=data.get('maintenance_type'),
            new_value=f"{data.get('maintenance_type')} - Résultat: {data.get('result', 'OK')}",
            comment=data.get('notes', ''),
            user_id=current_user.id if current_user.is_authenticated else None,
            user_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(history)
        
        plb.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Maintenance enregistrée', 'maintenance': maintenance.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur maintenance PLB {plb_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plb/<int:plb_id>/test', methods=['POST'])
def api_record_plb_test(plb_id):
    """Enregistrer un test mensuel simplifié"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        data = request.get_json()
        
        maintenance = PLBMaintenance(
            plb_id=plb.id,
            maintenance_type='TEST_MENSUEL',
            maintenance_date=datetime.now(),
            performed_by=data.get('performed_by', current_user.username if current_user.is_authenticated else 'Unknown'),
            result=data.get('result', 'OK'),
            notes=data.get('notes', ''),
            test_signal_received=data.get('test_signal_received', True),
            gps_fix_ok=data.get('gps_fix_ok', True),
            signal_strength=data.get('signal_strength'),
            created_by=current_user.id if current_user.is_authenticated else None,
            created_by_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(maintenance)
        
        # Ajouter notification pour prochain test
        next_test = PLBNotification(
            plb_id=plb.id,
            notification_type='TEST_DUE',
            message=f"Prochain test mensuel pour PLB {plb.registration_number}",
            scheduled_date=datetime.now().date() + timedelta(days=30),
            status='PENDING'
        )
        db.session.add(next_test)
        
        # Historique
        history = PLBHistory(
            plb_id=plb.id,
            action='TEST',
            field_changed='test_mensuel',
            new_value=f"Test du {datetime.now().strftime('%d/%m/%Y')}: {data.get('result', 'OK')}",
            comment=data.get('notes', ''),
            user_id=current_user.id if current_user.is_authenticated else None,
            user_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(history)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Test enregistré avec succès'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== FIN DE VIE / DÉSAFFECTATION ====================

@app.route('/api/plb/<int:plb_id>/decommission', methods=['POST'])
def api_decommission_plb(plb_id):
    """Mettre une PLB hors service (perdue, détruite, vendue)"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        data = request.get_json()
        
        reason = data.get('reason')  # PERDU, DETRUIT, VENDU
        comment = data.get('comment', '')
        
        plb.beacon_status = 'Inactif'
        plb.updated_at = datetime.now()
        
        # Ajouter à l'historique
        history = PLBHistory(
            plb_id=plb.id,
            action='DECOMMISSION',
            field_changed='status',
            old_value='Actif',
            new_value='Inactif',
            comment=f"Mise hors service - Motif: {reason} - {comment}",
            user_id=current_user.id if current_user.is_authenticated else None,
            user_name=current_user.username if current_user.is_authenticated else 'System'
        )
        db.session.add(history)
        
        # Annuler les notifications en attente
        pending_notifications = PLBNotification.query.filter_by(
            plb_id=plb.id,
            status='PENDING'
        ).all()
        
        for notif in pending_notifications:
            notif.status = 'CANCELLED'
        
        db.session.commit()
        
        # Envoyer notification
        send_decommission_notification(plb, reason, comment)
        
        return jsonify({'success': True, 'message': f'PLB mise hors service - Motif: {reason}'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur décommission PLB {plb_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== IMPRESSION FICHE PDF ====================

@app.route('/api/plb/<int:plb_id>/print', methods=['GET'])
def api_print_plb_card(plb_id):
    """Générer et imprimer la fiche PLB au format PDF"""
    try:
        plb = BalisePLB.query.get_or_404(plb_id)
        history = PLBHistory.query.filter_by(plb_id=plb_id).limit(20).all()
        maintenance = PLBMaintenance.query.filter_by(plb_id=plb_id).order_by(PLBMaintenance.maintenance_date.desc()).limit(10).all()
        transfers = PLBTransfer.query.filter_by(plb_id=plb_id).all()
        
        # Générer QR code
        qr_image = generate_plb_qr_code(plb)
        
        # Rendre le template HTML
        html_content = render_template('plb_card.html', 
                                       plb=plb, 
                                       history=history, 
                                       maintenance=maintenance,
                                       transfers=transfers,
                                       qr_image=qr_image,
                                       today=datetime.now())
        
        # Générer PDF
        pdf = HTML(string=html_content).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=PLB_{plb.registration_number}_{plb.unit_name}.pdf'
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur génération PDF PLB {plb_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== NOTIFICATIONS PLANIFIÉES ====================

def check_plb_notifications():
    """Vérifier les notifications planifiées (à exécuter quotidiennement par cron/task scheduler)"""
    today = datetime.now().date()
    
    # Notifications à envoyer
    pending = PLBNotification.query.filter(
        PLBNotification.scheduled_date <= today,
        PLBNotification.status == 'PENDING'
    ).all()
    
    for notification in pending:
        plb = BalisePLB.query.get(notification.plb_id)
        if plb and plb.beacon_status == 'Actif':
            try:
                if notification.notification_type == 'TEST_DUE':
                    send_email(
                        f"[MRCC Maroc] Rappel - Test mensuel PLB {plb.registration_number}",
                        plb.email,
                        f"Bonjour {plb.owner},\n\nLe test mensuel de votre PLB est dû.\n\nDate limite: {notification.scheduled_date}\n\nCordialement,\nMRCC Maroc"
                    )
                elif notification.notification_type == 'BATTERY_EXPIRY':
                    send_email(
                        f"[MRCC Maroc] Alerte - Expiration batterie PLB {plb.registration_number}",
                        plb.email,
                        f"Bonjour {plb.owner},\n\nLa batterie de votre PLB expire dans 30 jours.\n\nDate d'expiration: {plb.battery_expiration_date}\n\nVeuillez la remplacer.\n\nCordialement,\nMRCC Maroc"
                    )
                
                notification.sent_at = datetime.now()
                notification.status = 'SENT'
                notification.sent_to = plb.email
                db.session.commit()
                
            except Exception as e:
                notification.retry_count += 1
                if notification.retry_count >= 3:
                    notification.status = 'FAILED'
                db.session.commit()
                logger.error(f"Erreur envoi notification {notification.id}: {str(e)}")


# ==================== FONCTIONS UTILITAIRES ====================

def validate_hex_code(hex_code):
    """Valider le code hexadécimal PLB (15 caractères hexadécimaux)"""
    if not hex_code:
        return True  # Optionnel
    import re
    return bool(re.match(r'^[0-9A-Fa-f]{15}$', hex_code))


def generate_plb_qr_code(plb):
    """Générer un QR code pour la PLB"""
    try:
        qr_data = f"""
        PLB - MRCC MAROC
        Code: {plb.registration_number}
        UIN: {plb.uin}
        Navire: {plb.unit_name}
        MMSI: {plb.mmsi}
        Propriétaire: {plb.owner}
        Statut: {plb.beacon_status}
        Dernière MAJ: {plb.updated_at.strftime('%d/%m/%Y') if plb.updated_at else 'N/A'}
        """
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="#001F4D", back_color="white")
        
        # Convertir en base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        logger.error(f"Erreur génération QR code: {str(e)}")
        return None


def send_plb_registration_email(plb):
    """Envoyer email de confirmation d'enregistrement"""
    subject = f"[MRCC Maroc] Enregistrement PLB - {plb.registration_number}"
    body = f"""
    Bonjour {plb.owner},
    
    Votre balise PLB a été enregistrée avec succès dans le système MRCC Maroc.
    
    Détails de l'enregistrement:
    - Code: {plb.registration_number}
    - UIN: {plb.uin}
    - Navire: {plb.unit_name}
    - MMSI: {plb.mmsi}
    - Date d'enregistrement: {plb.registration_date}
    
    Informations importantes:
    - Test mensuel: à effectuer tous les mois
    - Expiration batterie: {plb.battery_expiration_date}
    
    Pour toute question, contactez le MRCC Maroc.
    
    Cordialement,
    MRCC Maroc
    """
    
    if plb.email:
        send_email(subject, plb.email, body)


def send_transfer_notification(plb, old_owner):
    """Envoyer notification de transfert"""
    subject = f"[MRCC Maroc] Transfert PLB - {plb.registration_number}"
    
    # Email au nouveau propriétaire
    if plb.email:
        new_body = f"""
        Bonjour {plb.owner},
        
        La balise PLB {plb.registration_number} vous a été transférée.
        
        Informations:
        - Navire: {plb.unit_name}
        - MMSI: {plb.mmsi}
        
        Veuillez vérifier que la balise est correctement programmée avec ces informations.
        
        Cordialement,
        MRCC Maroc
        """
        send_email(subject, plb.email, new_body)
    
    # Email à l'ancien propriétaire
    if old_owner.get('email'):
        old_body = f"""
        Bonjour {old_owner.get('name')},
        
        La balise PLB {plb.registration_number} a été transférée à nouveau propriétaire.
        
        Veuillez vous assurer que cette balise n'est plus associée à vos navires.
        
        Cordialement,
        MRCC Maroc
        """
        send_email(subject, old_owner['email'], old_body)


def send_decommission_notification(plb, reason, comment):
    """Envoyer notification de mise hors service"""
    if plb.email:
        subject = f"[MRCC Maroc] PLB hors service - {plb.registration_number}"
        body = f"""
        Bonjour {plb.owner},
        
        La balise PLB {plb.registration_number} a été mise hors service.
        
        Motif: {reason}
        Commentaire: {comment}
        Date: {datetime.now().strftime('%d/%m/%Y')}
        
        Si vous souhaitez réactiver cette balise, veuillez contacter le MRCC Maroc.
        
        Cordialement,
        MRCC Maroc
        """
        send_email(subject, plb.email, body)


# ==================== ROUTES POUR TEMPLATE ====================

@app.route('/plb-management')
@login_required
def plb_management():
    """Page de gestion des PLB"""
    # Ne pas passer de variable 'plb' ici - c'est la page principale
    return render_template('plb_management.html', today=datetime.now())



# =============================================================================
# MODÈLES COMPLÉMENTAIRES PLE CYCLE DE VIE PLB
# =============================================================================




#=============================================================================
@app.route('/api/test', methods=['GET'])
def api_test():
    return jsonify({'message': 'API test OK', 'timestamp': str(datetime.now()), 'status': 'success'})


@app.route('/api/test-db', methods=['GET'])
def api_test_db():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mrcc.mrcc_temple_plb")
        count  = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return jsonify({'status': 'success', 'message': 'Connexion DB réussie', 'record_count': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =============================================================================
# ROUTES — MOYENS (engagement / désengagement)
# =============================================================================

@app.route("/<int:alerte_id>/engager_moyen_double", methods=["POST"])
@login_required
def engager_moyen_double(alerte_id):
    print("========== engamenet moyens ==========")
    moyen_id = request.form.get("moyen_id")
    try:
        with closing(get_db_connection()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id FROMmrcc.moyens_secours_alertes WHERE alerte_id=%s AND moyen_id=%s
                    """, (alerte_id, moyen_id))
                    if cur.fetchone():
                        flash("Ce moyen est déjà engagé sur cette alerte", "warning")
                        return redirect(url_for("details_alerte", alerte_id=alerte_id))

                    cur.execute("""
                        INSERT INTOmrcc.moyens_secours_alertes (alerte_id, moyen_id, statut)
                        VALUES (%s,%s,'en_route')
                    """, (alerte_id, moyen_id))
                    cur.execute("""
                        INSERT INTO mrcc.mises_a_jour_alertes (alerte_id, user_id, contenu)
                        VALUES (%s,%s,%s)
                    """, (alerte_id, current_user.id, f"Moyen #{moyen_id} engagé"))
                    conn.commit()
                    flash("Moyen engagé avec succès", "success")
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
    return redirect(url_for("details_alerte", alerte_id=alerte_id))


@app.route("/<int:alerte_id>/desengager_moyen/<int:moyen_alerte_id>", methods=["POST"])
@login_required
def desengager_moyen(alerte_id, moyen_alerte_id):
    try:
        with closing(get_db_connection()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROMmrcc.moyens_secours_alertes WHERE id=%s AND alerte_id=%s
                    """, (moyen_alerte_id, alerte_id))
                    cur.execute("""
                        INSERT INTO mrcc.mises_a_jour_alertes (alerte_id, user_id, contenu)
                        VALUES (%s,%s,%s)
                    """, (alerte_id, current_user.id, "Moyen désengagé"))
                    conn.commit()
                    flash("Moyen désengagé avec succès", "success")
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
    return redirect(url_for("details_alerte", alerte_id=alerte_id))


# =============================================================================
# ROUTES — ASSET DEPLOYMENT / CARTOGRAPHIE RISQUES
# =============================================================================

@app.route('/api/asset-deployment', methods=['POST'])
@login_required
def api_asset_deployment():
    try:
        data     = request.get_json()
        priority = data.get('priority', 'STANDARD')

        deployment_plan = [{
            'asset':               asset.get('name', 'Inconnu'),
            'type':                asset.get('type', 'vessel'),
            'travel_time_hours':   2.0,
            'search_capacity':     50,
            'recommended_pattern': 'expanding_square'
        } for asset in MRCC_ASSETS.get('vessels', [])]

        return jsonify({
            'success': True,
            'deployment_plan': deployment_plan,
            'estimated_coverage_time': max((p['travel_time_hours'] for p in deployment_plan), default=0),
            'recommendations': ["Déployer moyens disponibles", "Coordonner avec MRCC"],
        })
    except Exception as e:
        logger.error(str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cartographie-risques')
@login_required
def cartographie_risques():
    # Stub : à connecter à la vraie source de données
    return render_template('cartographie_risques.html', error="Aucune donnée d'inspection disponible")



#=============================================================================
#   MBTILES - SERVIR LES CARTES OFFLINE
#============================================================================
# app.py - Ajoutez ces routes

import sqlite3
import struct
from flask import send_file, abort, Response
import zlib


# =============================================================================
# SERVEUR MBTILES
# =============================================================================

import sqlite3
import zlib
import os

# Chemin vers votre dossier MBTiles
MBTILES_DIR = 'G:/Projets/crts/crtsServ/webapps/geomaritime/data/data/mbtiles'

@app.route('/mbtiles/test')
def test_mbtiles():
    """Test si le dossier MBTiles est accessible"""
    result = {
        'directory': MBTILES_DIR,
        'exists': os.path.exists(MBTILES_DIR),
        'files': []
    }
    
    if os.path.exists(MBTILES_DIR):
        for f in os.listdir(MBTILES_DIR):
            if f.endswith('.mbtiles'):
                file_path = os.path.join(MBTILES_DIR, f)
                file_size = os.path.getsize(file_path)
                result['files'].append({
                    'name': f,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })
    
    return jsonify(result)


@app.route('/mbtiles/<path:filename>/info')
def get_mbtiles_info(filename):
    """Récupère les informations du fichier MBTiles"""
    try:
        mbtiles_path = os.path.join(MBTILES_DIR, filename)
        
        if not os.path.exists(mbtiles_path):
            return jsonify({'error': 'File not found'}), 404
        
        conn = sqlite3.connect(mbtiles_path)
        cursor = conn.cursor()
        
        # Récupérer les métadonnées
        cursor.execute("SELECT name, value FROM metadata")
        metadata = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Récupérer les niveaux de zoom disponibles
        cursor.execute("SELECT MIN(zoom_level), MAX(zoom_level) FROM tiles")
        min_zoom, max_zoom = cursor.fetchone()
        
        # Compter les tuiles
        cursor.execute("SELECT COUNT(*) FROM tiles")
        tile_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'name': metadata.get('name', filename),
            'format': metadata.get('format', 'png'),
            'min_zoom': min_zoom or 0,
            'max_zoom': max_zoom or 18,
            'tile_count': tile_count,
            'bounds': metadata.get('bounds', '-180,-90,180,90'),
            'attribution': metadata.get('attribution', '&copy; Navionics'),
            'description': metadata.get('description', '')
        })
        
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/mbtiles/<path:filename>/<int:z>/<int:x>/<int:y>.png')
def serve_mbtiles_tile(filename, z, x, y):
    """Sert une tuile depuis un fichier MBTiles"""
    try:
        mbtiles_path = os.path.join(MBTILES_DIR, filename)
        
        if not os.path.exists(mbtiles_path):
            return jsonify({'error': f'MBTiles file not found: {filename}'}), 404
        
        conn = sqlite3.connect(mbtiles_path)
        cursor = conn.cursor()
        
        # Conversion XYZ → TMS (y inversé pour MBTiles)
        y_tms = (1 << z) - 1 - y
        
        cursor.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
            (z, x, y_tms)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            tile_data = row[0]
            # Décompresser si les données sont compressées
            if tile_data and len(tile_data) > 2 and tile_data[:2] == b'\x78\x9c':
                try:
                    tile_data = zlib.decompress(tile_data)
                except:
                    pass
            return Response(tile_data, mimetype='image/png')
        else:
            # Tuile vide - image transparente 1x1
            empty_tile = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(empty_tile, mimetype='image/png')
            
    except Exception as e:
        print(f"Erreur MBTiles: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# GESTIONNAIRES D'ERREURS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'message': 'Bad request'}), 400

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Erreur serveur: {str(e)}")
    return jsonify({'success': False, 'error': 'Erreur interne du serveur'}), 500


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5052, debug=True, use_reloader=False)
