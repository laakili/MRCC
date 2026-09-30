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
from flask_caching import Cache
from sqlalchemy import func, and_, or_


# =============================================================================
# ROUTES API - GESTION DES BALISES PLB (CRUD)
# =============================================================================

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

