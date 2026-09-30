from app import db
from datetime import datetime

class Grade(db.Model):
    __tablename__ = 'grade'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    libelle = db.Column(db.String(100), nullable=False)
    ordre_hierarchique = db.Column(db.Integer, nullable=False)
    categorie = db.Column(db.String(10))
    clt = db.Column(db.Integer)
    actif = db.Column(db.Boolean, default=True)
    
    personnels = db.relationship('Personnel', backref='grade_ref', lazy=True)


class Emploi(db.Model):
    __tablename__ = 'emploi'
    
    id = db.Column(db.Integer, primary_key=True)
    code_emploi = db.Column(db.String(50))
    identifiant_emploi = db.Column(db.String(200))
    
    personnels = db.relationship('Personnel', backref='emploi_ref', lazy=True)


class UniteOrganisationnelle(db.Model):
    __tablename__ = 'unite_organisationnelle'
    
    id = db.Column(db.Integer, primary_key=True)
    id_uo = db.Column(db.String(50))
    unite_organisat = db.Column(db.String(200))
    type_uo = db.Column(db.String(50))
    entite_sup = db.Column(db.String(200))
    entite_categorie = db.Column(db.String(100))
    local_geo = db.Column(db.String(100))
    fonctionnement = db.Column(db.String(100))
    pole = db.Column(db.String(255))
    
    personnels = db.relationship('Personnel', backref='unite_ref', lazy=True)


class Personnel(db.Model):
    __tablename__ = 'personnel'
    
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    nom_complet = db.Column(db.String(200))
    carte_identite = db.Column(db.String(10), unique=True)
    sexe = db.Column(db.String(10))
    date_de_naissance = db.Column(db.Date)
    annee_naissance = db.Column(db.Integer)
    lieu_naissance = db.Column(db.String(100))
    
    # Informations familiales
    nom_pere = db.Column(db.String(100))
    nom_mere = db.Column(db.String(100))
    profession_pere = db.Column(db.String(100))
    profession_mere = db.Column(db.String(100))
    situation_famille = db.Column(db.String(20))
    nb_enfants = db.Column(db.Integer, default=0)
    profession_conjoint = db.Column(db.String(100))
    
    # Informations professionnelles
    date_entree = db.Column(db.Date)
    date_recrutement = db.Column(db.Date)
    type_recrutement = db.Column(db.String(50))
    date_affectation_unite = db.Column(db.Date)
    regime = db.Column(db.String(50))
    position_adm = db.Column(db.String(100))
    metier_de_base = db.Column(db.String(100))
    statut = db.Column(db.String(20), default='ACTIF')
    detache = db.Column(db.String(10))
    
    # Clés étrangères
    grade_id = db.Column(db.Integer, db.ForeignKey('grade.id'))
    emploi_id = db.Column(db.Integer, db.ForeignKey('emploi.id'))
    unite_orga_id = db.Column(db.Integer, db.ForeignKey('unite_organisationnelle.id'))
    
    # Nouvelles colonnes pour les affiliations
    affiliation_politique_id = db.Column(db.Integer, db.ForeignKey('partis_politiques.id'))
    affiliation_syndicale_id = db.Column(db.Integer, db.ForeignKey('syndicats.id'))
    
    # Coordonnées
    adresse = db.Column(db.Text)
    telephone = db.Column(db.String(20))
    telephone_personnel = db.Column(db.String(20))
    email_professionnel = db.Column(db.String(255))
    email_personnel = db.Column(db.String(255))
    contact_urgence = db.Column(db.String(100))
    
    # Informations financières
    numero_cnss = db.Column(db.String(20))
    compte_bancaire = db.Column(db.String(50))
    
    # Autres
    expertise = db.Column(db.Text)
    
    # Dates de départ
    date_prevue_depart = db.Column(db.Date)
    annee_depart = db.Column(db.Integer)
    age_depart = db.Column(db.Float)
    maintien = db.Column(db.String(50))
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    date_suppression = db.Column(db.Date)
    
    
    # Relations - CORRECTION ICI : remplacer FormationPersonnel par InscriptionFormation
    absences = db.relationship('Absence', backref='agent_absences', lazy='dynamic', cascade='all, delete-orphan')
    formations = db.relationship('InscriptionFormation', backref='agent_formations', lazy='dynamic', cascade='all, delete-orphan')
    missions = db.relationship('Mission', backref='agent_missions', lazy='dynamic', cascade='all, delete-orphan')
    
    # Relations pour les affiliations
    affiliation_politique = db.relationship('PartiPolitique', foreign_keys=[affiliation_politique_id])
    affiliation_syndicale = db.relationship('Syndicat', foreign_keys=[affiliation_syndicale_id])
    
    def __repr__(self):
        return f'<Personnel {self.matricule} - {self.nom} {self.prenom}>'
    
    @property
    def full_name(self):
        return f"{self.nom} {self.prenom}"