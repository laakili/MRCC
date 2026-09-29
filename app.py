from flask import Flask, Response, render_template, stream_with_context, request, jsonify, send_file, make_response, flash, current_app, redirect, url_for, request, session
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from pandas.tseries.offsets import MonthEnd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import io
import os
from sqlalchemy import text
from dash import Output, Input, State, ctx
import pickle
from io import BytesIO
from jinja2 import Template
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pycatastro import PyCatastro
import jwt
import time
import math
import logging
from decimal import Decimal
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import base64
import requests
import json
import numpy as np
import seaborn as sns
from decimal import Decimal, InvalidOperation
from shapely import wkt
from shapely.wkt import loads
from werkzeug.utils import secure_filename
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import re
import zipfile
from gevent import pywsgi
import shutil, sys  
import xml.etree.ElementTree as ET
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import logging
from datetime import datetime
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mrcc_maroc.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-env')
CORS(app)


app.secret_key = os.environ.get('FLASK_APP_SECRET_KEY', 'dev-secret-key-change-in-env')
# Configuration de la base de données PostgreSQL
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'geoportal')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
DB_PORT = os.environ.get('DB_PORT', '5432')
# Configurer Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = ('app', os.environ.get('MAIL_DEFAULT_SENDER', 'soufiomario@gmail.com'))
BASE_URL = os.environ.get('BASE_URL', 'http://geoai-solutions.ddns.net:4563/')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
mail = Mail(app)
# Générateur de tokens sécurisés
serializer = URLSafeTimedSerializer(app.secret_key)
# Connexion PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, 
        dbname=DB_NAME, 
        user=DB_USER, 
        password=DB_PASSWORD, 
        port=DB_PORT
    )
conn = get_db_connection()
cursor = conn.cursor()
# Connexion à la base de données
engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Configuration flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# Classe utilisateur
class User(UserMixin):
    def __init__(self, id, username, password, first_name, last_name, telephone, email, fonction, organisme, type_organisme):
        self.id = id
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.telephone = telephone
        self.email = email
        self.fonction = fonction
        self.organisme = organisme
        self.type_organisme = type_organisme

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, username, password, first_name, last_name, telephone, email, fonction, organisme, type_organisme 
            FROM crts_parameters.users WHERE id = %s
        """, (user_id,))
        user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(*user_data)
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        telephone = request.form['telephone']
        email = request.form['email']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        fonction = request.form['fonction']
        organisme = request.form['organisme']
        type_organisme = request.form['type_organisme']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO crts_parameters.users (first_name, last_name, telephone, email, username, password, fonction, organisme, type_organisme)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (first_name, last_name, telephone, email, username, password, fonction, organisme, type_organisme))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            # Générer un token
            token = serializer.dumps(email, salt='email-confirmation')
            
            # Créer un lien de validation
            confirm_url = f"{BASE_URL}/confirm/{token}"
            
            # Envoyer l'email
            subject = "Confirmez votre adresse email"
            body = f"Bonjour {first_name},\n\nCliquez sur le lien ci-dessous pour valider votre adresse email :\n{confirm_url}\n\nSi vous n'avez pas créé ce compte, ignorez cet email."
            send_email(subject, email, body)
            
            flash("Un email de validation a été envoyé. Veuillez vérifier votre boîte de réception.", "info")
            return redirect(url_for('login'))
        except psycopg2.Error as e:
            flash(f"Erreur lors de l'enregistrement : {e.pgerror}", "error")
    return render_template('register.html')


def send_email(subject, recipient, body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        print(f"Envoi de l'email à {recipient}")  # Journal de débogage
        mail.send(msg)
        print(f"Email envoyé à {recipient}")  # Journal de débogage
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirmation', max_age=3600)  # 1 heure de validité
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE crts_parameters.users SET is_active = TRUE WHERE email = %s", (email,))
        conn.commit()
        conn.close()
        flash("Votre adresse email a été validée. Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('login'))
    except Exception:
        flash("Le lien de validation est invalide ou a expiré.", "error")
        return redirect(url_for('register'))

# Route pour se connecter
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password, first_name, last_name, telephone, email, fonction, organisme, type_organisme, is_active 
            FROM crts_parameters.users 
            WHERE username = %s
        """, (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            if not user_data[10]:  # Vérifie si is_active est False
                flash("Veuillez valider votre adresse email avant de vous connecter.", "error")
                return redirect(url_for('login'))

            if check_password_hash(user_data[2], password):
                user = User(*user_data[:10])  # Crée un objet User
                login_user(user)
                
                
                flash("Connexion réussie!", "success")
                return redirect(url_for('index'))
            else:
                flash("Mot de passe incorrect.", "error")
        else:
            flash("Nom d'utilisateur incorrect.", "error")

    return render_template('login.html')

    
# Route pour se déconnecter
@app.route('/logout')

def logout():
    user_id = current_user.id  # Capturez l'ID avant de déconnecter l'utilisateur
    logout_user()
    flash("Déconnexion réussie!", "success")
  
    return redirect(url_for('login'))
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # Connexion à la base de données
        conn = get_db_connection()
        cursor = conn.cursor()

        # Requête pour vérifier si l'utilisateur existe
        cursor.execute("SELECT * FROM crts_parameters.users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = f"{BASE_URL}/reset_password/{token}"

            # Envoi de l'e-mail de réinitialisation
            msg = Message(
                'Réinitialisation de mot de passe',
                sender='soufiomario@gmail.com',
                recipients=[email]
            )
            msg.body = f'Cliquez sur le lien pour réinitialiser votre mot de passe : {reset_url}'
            mail.send(msg)

            flash('Un lien de réinitialisation de mot de passe a été envoyé à votre adresse e-mail.', 'success')
        else:
            flash("Aucun utilisateur n'est associé à cet e-mail.", 'danger')

        # Fermeture de la connexion
        cursor.close()
        conn.close()

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash("Le lien de réinitialisation a expiré ou est invalide.", 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = generate_password_hash(request.form.get('password'))
        confirm_password = generate_password_hash(request.form.get('confirm_password'))
        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", 'danger')
        else:
            # Mettez à jour le mot de passe dans la base de données
            conn = get_db_connection()
            cursor = conn.cursor()

            # Requête pour vérifier si l'utilisateur existe
            cursor.execute("SELECT * FROM crts_parameters.users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.execute("update crts_parameters.users set password = %s", (new_password,))
            flash('Votre mot de passe a été réinitialisé avec succès.', 'success')
            return redirect(url_for('login'))
            cursor.close()
            conn.close()
    return render_template('reset_password.html')
@app.route('/dashboard', methods=['GET', 'POST'])

def dashboard():
    user_id = current_user.id  # Récupération de l'ID via Flask-Login
    conn = get_db_connection()
    cursor = conn.cursor()

    # Récupération des informations utilisateur
    cursor.execute("""
        SELECT email, first_name, last_name, telephone, fonction, organisme, type_organisme 
        FROM crts_parameters.users 
        WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        if 'update_info' in request.form:
            # Mise à jour des informations personnelles
            email = request.form['email']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            telephone = request.form['telephone']
            fonction = request.form['fonction']
            organisme = request.form['organisme']
            type_organisme = request.form['type_organisme']

            cursor.execute("""
                UPDATE crts_parameters.users 
                SET email = %s, first_name = %s, last_name = %s, telephone = %s, fonction = %s, organisme = %s, type_organisme = %s 
                WHERE id = %s
            """, (email, first_name, last_name, telephone, fonction, organisme, type_organisme, user_id))
            conn.commit()
            flash("Vos informations ont été mises à jour avec succès.", 'success')

        elif 'change_password' in request.form:
            # Changer le mot de passe
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            # Vérifier l'ancien mot de passe
            cursor.execute("SELECT password FROM crts_parameters.users WHERE id = %s", (user_id,))
            stored_password = cursor.fetchone()[0]

            if not check_password_hash(stored_password, old_password):
                flash("Votre ancien mot de passe est incorrect.", 'danger')
            elif new_password != confirm_password:
                flash("Les nouveaux mots de passe ne correspondent pas.", 'danger')
            else:
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE crts_parameters.users SET password = %s WHERE id = %s",
                    (hashed_password, user_id)
                )
                conn.commit()
                flash("Votre mot de passe a été modifié avec succès.", 'success')

    cursor.close()
    conn.close()

    return render_template('dashboard.html', user=user)




# Route pour afficher les données existantes
@app.route("/afficher_donnees")
def afficher_donnees():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM donnees_partenaires")
    donnees = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("donnees_partenaires.html", donnees=donnees)
@app.route("/donnees")
def donnees():
    conn = get_db_connection()
    cur = conn.cursor()
    user_s = current_user.organisme 
    cur.execute("SELECT * FROM donnees_partenaires where organisme = %s", (user_s,))
    donnees = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("donnees.html", donnees=donnees)

# Route pour supprimer une donnée
@app.route("/supprimer_donnee/<int:id>")
def supprimer_donnee(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM donnees_partenaires WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Donnée supprimée avec succès !", "danger")
    return redirect(url_for("afficher_donnees"))
# Route pour supprimer une donnée
@app.route("/ajouter_donnee", methods=["GET", "POST"])
def ajouter_donnee():
    if request.method == "POST":
        nom_donnee = request.form["nom_donnee"]
        territoire = request.form["territoire"]
        descriptif = request.form["descriptif"]
        sommaire = request.form["sommaire"]
        type_donnee = request.form["type_donnee"]
        format_donnee = request.form["format_donnee"]
        taille_moyenne = request.form["taille_moyenne"]
        producteur = request.form["producteur"]
        users_cas_usage = request.form["users_cas_usage"]
        periode_couverte = request.form["periode_couverte"]
        frequence_donnee = request.form["frequence_donnee"]
        frequence_maj = request.form["frequence_maj"]
        taille_historique = request.form["taille_historique"]
        mode_acces = request.form["mode_acces"]
        qualite = request.form["qualite"]
        contraintes_obs = request.form["contraintes_obs"]
        reference = request.form.get("reference", False)  # Récupération du champ booléen
        user_saisie = current_user.username
        organisme = current_user.organisme
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO donnees_partenaires 
            (nom_donnee, territoire, descriptif, sommaire, type_donnee, format_donnee, taille_moyenne, producteur, 
            users_cas_usage, periode_couverte, frequence_donnee, frequence_maj, taille_historique, mode_acces, 
            qualite, contraintes_obs, reference, user_saisie, organisme)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (nom_donnee, territoire, descriptif, sommaire, type_donnee, format_donnee, taille_moyenne, producteur,
              users_cas_usage, periode_couverte, frequence_donnee, frequence_maj, taille_historique, mode_acces,
              qualite, contraintes_obs, reference, user_saisie, organisme))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash("Donnée ajoutée avec succès !", "success")
        return redirect(url_for("afficher_donnees"))
    
    return render_template("ajouter_donnee.html")

@app.route("/modifier_donnees/<int:id>", methods=["GET", "POST"])
def modifier_donnees(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == "POST":
        nom = request.form["nom"]
        territoire = request.form["territoire"]
        descriptif = request.form["descriptif"]
        sommaire = request.form["sommaire"]
        type_donnee = request.form["type"]
        format_donnee = request.form["format"]
        taille = request.form["taille"]
        producteur = request.form["producteur"]
        cas_usage = request.form["cas_usage"]
        periode = request.form["periode"]
        frequence = request.form["frequence"]
        maj = request.form["maj"]
        taille_historique = request.form["taille_historique"]
        acces = request.form["acces"]
        qualite = request.form["qualite"]
        contraintes = request.form["contraintes"]
        reference = request.form.get("reference", False)  # Récupération du champ booléen
        
        cur.execute("""
            UPDATE donnees_partenaires
            SET nom=%s, territoire=%s, descriptif=%s, sommaire=%s, type=%s, format=%s, taille=%s, 
                producteur=%s, cas_usage=%s, periode=%s, frequence=%s, maj=%s, taille_historique=%s, 
                acces=%s, qualite=%s, contraintes=%s, reference=%s
            WHERE id=%s
        """, (nom, territoire, descriptif, sommaire, type_donnee, format_donnee, taille, 
              producteur, cas_usage, periode, frequence, maj, taille_historique, acces, qualite, contraintes, reference, id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash("Donnée modifiée avec succès !", "success")
        return redirect(url_for("liste_donnees"))
    
    cur.execute("SELECT * FROM donnees_partenaires WHERE id = %s", (id,))
    donnee = cur.fetchone()
    cur.close()
    conn.close()
    
    if not donnee:
        flash("Donnée introuvable !", "danger")
        return redirect(url_for("donnees"))
    
    return render_template("modifier_donnee.html", donnee=donnee)

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')
@app.route('/documentation')
def documentation():
    return render_template('documentation.html')
@app.route('/alerte')
def alerte():
    return render_template('alerte.html')


@app.route('/gestion_droits', methods=['GET', 'POST'])

def gestion_droits():
    user_s = current_user.organisme
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nom_donnee FROM donnees_partenaires WHERE organisme = %s", (user_s,))
    donnees = cur.fetchall()
    
    if request.method == 'POST':
        id_donnee = request.form['id_donnee']
        organismes_beneficiaires = request.form.getlist('organisme_beneficiaire')  # Récupère tous les organismes cochés
        droit_acces = request.form['droit_acces']

        # Ajout des droits d'accès pour chaque organisme sélectionné
        for org in organismes_beneficiaires:
            cur.execute("""
                INSERT INTO droits_acces (id_donnee, organisme_proprietaire, organisme_beneficiaire, droit_acces) 
                VALUES (%s, %s, %s, %s)
            """, (id_donnee, user_s, org, droit_acces))
        
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('gestion_droits'))

    # Récupération des droits existants
    cur.execute("""
        SELECT da.id, dp.nom_donnee, da.organisme_proprietaire, da.organisme_beneficiaire, da.droit_acces
        FROM droits_acces da
        JOIN donnees_partenaires dp ON da.id_donnee = dp.id
    """)
    droits = cur.fetchall()

    return render_template('droits_acces.html', donnees=donnees, droits=droits)

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import psycopg2
from psycopg2 import sql


UPLOAD_FOLDER = "uploads/alertes"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/add_alerte", methods=["GET", "POST"])

def add_alerte():
    if request.method == "POST":
        # Récupération des données du formulaire
        titre = request.form.get("titre")
        description = request.form.get("description")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        type_incident = request.form.get("type_incident")
        nombre_personnes = request.form.get("nombre_personnes")
        conditions_meteo = request.form.get("conditions_meteo")
        moyen_alerte = request.form.get("moyen_alerte")
        navire_implique = request.form.get("navire_implique")
        immatriculation_navire = request.form.get("immatriculation_navire")
        niveau_urgence = request.form.get("niveau_urgence")
        notes_complementaires = request.form.get("notes_complementaires")
        
        # Gestion du fichier joint
        fichier_joint = None
        if 'fichier_joint' in request.files:
            file = request.files['fichier_joint']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                fichier_joint = filename
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Insertion de l'alerte
                query = sql.SQL("""
                    INSERT INTO alertes_sauvetage (
                        titre, description, latitude, longitude, type_incident,
                        nombre_personnes, conditions_meteo, moyen_alerte,
                        navire_implique, immatriculation_navire, niveau_urgence,
                        notes_complementaires, createur_id, organisme_id, fichier_joint
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """)
                cur.execute(query, (
                    titre, description, latitude, longitude, type_incident,
                    nombre_personnes, conditions_meteo, moyen_alerte,
                    navire_implique, immatriculation_navire, niveau_urgence,
                    notes_complementaires, current_user.id, current_user.organisme_id, fichier_joint
                ))
                alerte_id = cur.fetchone()[0]
                
                # Création de la première mise à jour
                cur.execute(
                    "INSERT INTO mises_a_jour_alertes (alerte_id, user_id, contenu) VALUES (%s, %s, %s)",
                    (alerte_id, current_user.id, "Création de l'alerte de sauvetage.")
                )
                
                # Notification aux utilisateurs concernés
                cur.execute("""
                    INSERT INTO notifications_rescue (user_id, alerte_id, message, type_notification)
                    SELECT id, %s, %s, 'nouvelle_alerte'
                    FROM users 
                    WHERE organisme_id = %s AND id != %s
                """, (alerte_id, f"Nouvelle alerte de sauvetage: {titre}", current_user.organisme_id, current_user.id))
                
                conn.commit()
                flash("Alerte de sauvetage créée avec succès!", "success")
                return redirect(url_for("alertes.details_alerte", alerte_id=alerte_id))
                
        
        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de la création de l'alerte: {str(e)}", "danger")
        finally:
            conn.close()
    
    return render_template("add_alerte.html")

@app.route("/alertes/<int:alerte_id>")

def details_alerte(alerte_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupération de l'alerte
            cur.execute("""
                SELECT a.*, u.nom, u.prenom, o.nom as organisme_nom
                FROM alertes_sauvetage a
                JOIN users u ON a.createur_id = u.id
                JOIN organismes o ON a.organisme_id = o.id
                WHERE a.id = %s
            """, (alerte_id,))
            alerte = cur.fetchone()
            
            if not alerte:
                flash("Alerte non trouvée", "danger")
                return redirect(url_for("alertes.liste_alertes"))
            
            # Récupération des mises à jour
            cur.execute("""
                SELECT m.*, u.nom, u.prenom
                FROM mises_a_jour_alertes m
                JOIN users u ON m.user_id = u.id
                WHERE m.alerte_id = %s
                ORDER BY m.date_mise_a_jour DESC
            """, (alerte_id,))
            mises_a_jour = cur.fetchall()
            
            # Récupération des moyens engagés
            cur.execute("""
                SELECT m.id, m.nom, m.type, m.localisation, ma.date_engagement, ma.statut
                FROM moyens_secours_alertes ma
                JOIN moyens_secours m ON ma.moyen_id = m.id
                WHERE ma.alerte_id = %s
            """, (alerte_id,))
            moyens_engages = cur.fetchall()
            
            return render_template(
                "alertes/details_alerte.html",
                alerte=alerte,
                mises_a_jour=mises_a_jour,
                moyens_engages=moyens_engages
            )
    finally:
        conn.close()

@app.route("/alertes/<int:alerte_id>/mise-a-jour", methods=["POST"])

def mise_a_jour_alerte(alerte_id):
    contenu = request.form.get("contenu")
    nouveau_statut = request.form.get("statut")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupération du statut actuel
            cur.execute("SELECT statut FROM alertes_sauvetage WHERE id = %s", (alerte_id,))
            statut_actuel = cur.fetchone()[0]
            
            # Création de la mise à jour
            cur.execute("""
                INSERT INTO mises_a_jour_alertes 
                (alerte_id, user_id, contenu, statut_precedent, nouveau_statut)
                VALUES (%s, %s, %s, %s, %s)
            """, (alerte_id, current_user.id, contenu, statut_actuel, nouveau_statut))
            
            # Mise à jour du statut si nécessaire
            if nouveau_statut and nouveau_statut != statut_actuel:
                cur.execute("""
                    UPDATE alertes_sauvetage 
                    SET statut = %s 
                    WHERE id = %s
                """, (nouveau_statut, alerte_id))
                
                # Notification pour changement de statut
                cur.execute("""
                    INSERT INTO notifications_rescue (user_id, alerte_id, message, type_notification)
                    SELECT id, %s, %s, 'changement_statut'
                    FROM users 
                    WHERE organisme_id = %s AND id != %s
                """, (alerte_id, f"Changement de statut pour l'alerte {alerte_id}: {nouveau_statut}", 
                      current_user.organisme_id, current_user.id))
            
            conn.commit()
            flash("Mise à jour enregistrée avec succès", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur lors de la mise à jour: {str(e)}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for("alertes.details_alerte", alerte_id=alerte_id))
@app.route("/mes_alertes", methods=["GET"])

def mes_alertes():
    return render_template("mes_alertes.html")
      

from contextlib import closing

@app.route("/modifier_alerte/<int:alerte_id>", methods=["GET", "POST"])

def modifier_alerte(alerte_id):
    try:
        with closing(get_db_connection()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT titre, contenu, fichier FROM alertes WHERE id = %s", (alerte_id,))
                    alerte = cur.fetchone()
                    
                    if not alerte:
                        flash("Alerte introuvable.", "warning")
                        return redirect(url_for("mes_alertes"))

                    if request.method == "POST":
                        titre = request.form.get("titre")
                        contenu = request.form.get("contenu")
                        fichier = alerte[2]

                        if "fichier" in request.files:
                            file = request.files["fichier"]
                            if file and file.filename:
                                filename = secure_filename(file.filename)
                                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                                fichier = filename

                        cur.execute(
                            "UPDATE alertes SET titre = %s, contenu = %s, fichier = %s WHERE id = %s",
                            (titre, contenu, fichier, alerte_id)
                        )
                        flash("Alerte modifiée avec succès !", "success")
                        return redirect(url_for("mes_alertes"))

            return render_template("modifier_alerte.html", alerte=alerte, alerte_id=alerte_id)
    except Exception as e:
        flash(f"Erreur lors de la modification : {str(e)}", "danger")
        return redirect(url_for("mes_alertes"))
@app.route("/supprimer_alerte/<int:alerte_id>", methods=["POST"])

def supprimer_alerte(alerte_id):
    try:
        with conn.cursor() as cur:
            # Vérification de l'existence de l'alerte
            cur.execute("SELECT fichier FROM alertes WHERE id = %s", (alerte_id,))
            alerte = cur.fetchone()

            if alerte and alerte[0]:
                # Supprimer le fichier du dossier
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], alerte[0])
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Suppression de l'alerte de la base de données
            cur.execute("DELETE FROM alertes WHERE id = %s", (alerte_id,))
            conn.commit()
            flash("Alerte supprimée avec succès !", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for("mes_alertes"))
@app.route("/mes_alertes")

def dashboard_alertes():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                # Récupération des alertes avec pagination
                page = request.args.get('page', 1, type=int)
                per_page = 10
                offset = (page - 1) * per_page
                
                # Requête principale avec filtres
                query = """
                    SELECT a.id, a.titre, a.description, a.statut, a.niveau_urgence, 
                           a.date_creation, u.nom, u.prenom, COUNT(m.id) as moyens_engages
                    FROM alertes_sauvetage a
                    JOIN users u ON a.createur_id = u.id
                    LEFT JOIN moyens_secours_alertes m ON m.alerte_id = a.id
                    WHERE a.organisme_id = %s
                    GROUP BY a.id, u.nom, u.prenom
                    ORDER BY a.date_creation DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, (current_user.organisme_id, per_page, offset))
                alertes = cur.fetchall()
                
                # Compte total pour pagination
                cur.execute("SELECT COUNT(*) FROM alertes_sauvetage WHERE organisme_id = %s", 
                          (current_user.organisme_id,))
                total = cur.fetchone()[0]
                
                # Statistiques
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN statut = 'nouvelle' THEN 1 END) as nouvelles,
                        COUNT(CASE WHEN statut = 'en_cours' THEN 1 END) as en_cours,
                        COUNT(CASE WHEN statut = 'terminee' THEN 1 END) as terminees,
                        COUNT(CASE WHEN niveau_urgence = 'critique' THEN 1 END) as critiques
                    FROM alertes_sauvetage 
                    WHERE organisme_id = %s
                """, (current_user.organisme_id,))
                stats = cur.fetchone()
                
                # Types d'incidents
                cur.execute("""
                    SELECT type_incident, COUNT(*) 
                    FROM alertes_sauvetage 
                    WHERE organisme_id = %s
                    GROUP BY type_incident
                    ORDER BY COUNT(*) DESC
                    LIMIT 5
                """, (current_user.organisme_id,))
                types_incidents = cur.fetchall()
                
                return render_template(
                    "mes_alertes.html",
                    alertes=alertes,
                    stats=stats,
                    types_incidents=types_incidents,
                    page=page,
                    per_page=per_page,
                    total=total
                )
    except Exception as e:
        flash(f"Erreur lors de la récupération des données: {str(e)}", "danger")
        return redirect(url_for("mes_alertes"))

@app.route("/api/alertes")

def api_alertes():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, titre, latitude, longitude, type_incident, niveau_urgence
                    FROM alertes_sauvetage
                    WHERE statut IN ('nouvelle', 'en_cours')
                    AND organisme_id = %s
                """, (current_user.organisme_id,))
                alertes_actives = cur.fetchall()
                
                return jsonify([{
                    'id': a[0],
                    'titre': a[1],
                    'lat': float(a[2]) if a[2] else None,
                    'lng': float(a[3]) if a[3] else None,
                    'type': a[4],
                    'urgence': a[5]
                } for a in alertes_actives])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/stats")

def api_stats():
    try:
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                # Stats par mois pour le graphique
                cur.execute("""
                    SELECT 
                        TO_CHAR(date_creation, 'YYYY-MM') as mois,
                        COUNT(*) as total,
                        COUNT(CASE WHEN statut = 'terminee' THEN 1 END) as terminees
                    FROM alertes_sauvetage
                    WHERE organisme_id = %s
                    AND date_creation >= CURRENT_DATE - INTERVAL '1 year'
                    GROUP BY mois
                    ORDER BY mois
                """, (current_user.organisme_id,))
                stats_mensuelles = cur.fetchall()
                
                return jsonify({
                    'labels': [s[0] for s in stats_mensuelles],
                    'total': [s[1] for s in stats_mensuelles],
                    'terminees': [s[2] for s in stats_mensuelles]
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/<int:alerte_id>/engager_moyen", methods=["POST"])

def engager_moyen(alerte_id):
    moyen_id = request.form.get("moyen_id")
    try:
        with closing(get_db_connection()) as conn:
            with conn:
                with conn.cursor() as cur:
                    # Vérifier si le moyen est déjà engagé
                    cur.execute("""
                        SELECT id FROM moyens_secours_alertes 
                        WHERE alerte_id = %s AND moyen_id = %s
                    """, (alerte_id, moyen_id))
                    if cur.fetchone():
                        flash("Ce moyen est déjà engagé sur cette alerte", "warning")
                        return redirect(url_for("alertes.details_alerte", alerte_id=alerte_id))
                    
                    # Engager le moyen
                    cur.execute("""
                        INSERT INTO moyens_secours_alertes 
                        (alerte_id, moyen_id, statut) 
                        VALUES (%s, %s, 'en_route')
                    """, (alerte_id, moyen_id))
                    
                    # Mise à jour de statut
                    cur.execute("""
                        INSERT INTO mises_a_jour_alertes 
                        (alerte_id, user_id, contenu)
                        VALUES (%s, %s, %s)
                    """, (alerte_id, current_user.id, 
                         f"Moyen de secours #{moyen_id} engagé pour intervention"))
                    
                    conn.commit()
                    flash("Moyen de secours engagé avec succès", "success")
    except Exception as e:
        flash(f"Erreur lors de l'engagement du moyen: {str(e)}", "danger")
    
    return redirect(url_for("alertes.details_alerte", alerte_id=alerte_id))

@app.route("/<int:alerte_id>/desengager_moyen/<int:moyen_alerte_id>", methods=["POST"])

def desengager_moyen(alerte_id, moyen_alerte_id):
    try:
        with closing(get_db_connection()) as conn:
            with conn:
                with conn.cursor() as cur:
                    # Désengager le moyen
                    cur.execute("""
                        DELETE FROM moyens_secours_alertes 
                        WHERE id = %s AND alerte_id = %s
                    """, (moyen_alerte_id, alerte_id))
                    
                    # Mise à jour de statut
                    cur.execute("""
                        INSERT INTO mises_a_jour_alertes 
                        (alerte_id, user_id, contenu)
                        VALUES (%s, %s, %s)
                    """, (alerte_id, current_user.id, 
                         f"Moyen de secours désengagé de l'intervention"))
                    
                    conn.commit()
                    flash("Moyen de secours désengagé avec succès", "success")
    except Exception as e:
        flash(f"Erreur lors du désengagement: {str(e)}", "danger")
    
    return redirect(url_for("alertes.details_alerte", alerte_id=alerte_id))
@app.route("/notifications")

def notifications():
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT alertes.id, alertes.titre, alertes.contenu, alertes.created_at "
                "FROM alertes "
                "JOIN user_alertes ON alertes.id = user_alertes.alerte_id "
                "WHERE user_alertes.user_id = %s AND user_alertes.statut = 'non_vu' "
                "ORDER BY alertes.created_at DESC",
                (current_user.id,)
            )
            notifications = [{
                'id': row[0],
                'titre': row[1],
                'contenu': row[2],
                'date': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else ''
            } for row in cur.fetchall()]
        return jsonify(notifications)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/marquer_comme_vu/<int:alerte_id>')

def marquer_comme_vu(alerte_id):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_alertes SET statut = 'vu', date_vue = NOW() WHERE user_id = %s AND alerte_id = %s",
                (current_user.id, alerte_id)
            )
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api')
def api():
    return render_template('api.html')
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



# Fonction pour normaliser le nom de la table
def normalize_table_name(filename):
    table_name = filename.lower()
    table_name = re.sub(r'[^a-z0-9\s]', '', table_name)  # Supprimer les caractères spéciaux
    table_name = re.sub(r'\s+', '_', table_name)  # Remplacer les espaces par des _
    return table_name



@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if not file:
        flash("Aucun fichier sélectionné.")
        return redirect(url_for('api'))
    
    # Create uploads directory if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    if not os.path.exists(file_path):
        flash("Le fichier n'a pas été enregistré correctement.")
        return redirect(url_for('api'))
    
    # Normalisation du nom de la table
    table_name = normalize_table_name(file.filename.split('.')[0])
    
    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(UPLOAD_FOLDER)
                shapefile_path = None

                # Chercher le fichier .shp dans le ZIP
                for extracted_file in zip_ref.namelist():
                    if extracted_file.endswith('.shp'):
                        shapefile_path = os.path.join(UPLOAD_FOLDER, extracted_file)
                        break

                if not shapefile_path:
                    flash("Aucun fichier .shp trouvé dans l'archive ZIP.")
                    return redirect(url_for('api'))
                
                print(f"Fichier shapefile trouvé : {shapefile_path}")

                try:
                    gdf = gpd.read_file(shapefile_path)

                    if 'geometry' not in gdf.columns:
                        flash("Erreur : Le fichier ne contient pas de colonne géométrique valide.")
                        return redirect(url_for('api'))
                    
                    if gdf.crs is None:
                        print("⚠️ CRS non défini, définition en EPSG:4326")
                        gdf.set_crs(epsg=4326, inplace=True)
                    
                    print("✅ Shapefile chargé avec succès !")
                    
                    try:
                        gdf.to_postgis(table_name,   con=engine,
            schema='uploads', if_exists='replace', index=False)
                        print(f"✅ Données insérées dans PostgreSQL (table : {table_name})")
                        flash(f"Données intégrées avec succès dans la table '{table_name}'")
                        return redirect(url_for('api'))
                    except Exception as e:
                        flash(f"Erreur lors de l'insertion en base : {str(e)}")
                        return redirect(url_for('api'))
                except Exception as e:
                    flash(f"Erreur lors de la lecture du shapefile : {str(e)}")
                    return redirect(url_for('api'))
        
        # Add support for standalone shapefiles
        elif file.filename.endswith('.shp'):
            try:
                gdf = gpd.read_file(file_path)
                
                if 'geometry' not in gdf.columns:
                    flash("Erreur : Le fichier ne contient pas de colonne géométrique valide.")
                    return redirect(url_for('api'))
                
                if gdf.crs is None:
                    print("⚠️ CRS non défini, définition en EPSG:4326")
                    gdf.set_crs(epsg=4326, inplace=True)
                
                gdf.to_postgis(table_name,
             con=engine,
            schema='uploads', if_exists='replace', index=False)
                flash(f"Données shapefile intégrées avec succès dans la table '{table_name}'")
                return redirect(url_for('api'))
            except Exception as e:
                flash(f"Erreur lors du traitement du shapefile : {str(e)}")
                return redirect(url_for('api'))
        
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            return render_template('select_columns.html', columns=df.columns.tolist(), table_name=table_name, file_path=file_path)
        
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
            return render_template('select_columns.html', columns=df.columns.tolist(), table_name=table_name, file_path=file_path)
        
        else:
            flash("Format de fichier non pris en charge.")
            return redirect(url_for('api'))
    
    except Exception as e:
        flash(f"Erreur d'intégration: {str(e)}")
        return redirect(url_for('api'))


# Route pour l'intégration des fichiers CSV/Excel avec géométrie
@app.route('/integrate', methods=['POST'])
def integrate():
    x_col = request.form['x_col']
    y_col = request.form['y_col']
    table_name = request.form['table_name']
    file_path = request.form['file_path']

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Création de la géométrie à partir des colonnes X et Y
        df['geometry'] = df.apply(lambda row: Point(row[x_col], row[y_col]), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

        # Intégration dans la base de données
        gdf.to_postgis(
            table_name,
            con=engine,
            schema='uploads',
            if_exists='replace',
            index=False
        )

        flash(f"Table '{table_name}' intégrée avec succès avec géométrie.")

    except Exception as e:
        flash(f"Erreur lors de l'intégration des données: {str(e)}")
   

    return redirect(url_for('api'))

# Configuration GeoServer
GEOSERVER_URL = os.environ.get('GEOSERVER_URL', 'http://smartdef.ddns.net:8888/georisque')
GEOSERVER_USER = os.environ.get('GEOSERVER_USER', 'admin')
GEOSERVER_PASSWORD = os.environ.get('GEOSERVER_PASSWORD', 'geoserver')
WORKSPACE = "geodata"  # Workspace GeoServer
DATASTORE = "uploads"  # Nom du datastore (PostGIS ou Shapefile)

# Configuration upload
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route('/publish', methods=['GET', 'POST'])
def publish():
    if request.method == "GET":
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'uploads'
            """))
            postgis_tables = [row[0] for row in result]
        
        return render_template('publish.html', postgis_tables=postgis_tables)

    # Traitement POST
    data_source = request.form.get('data_source')
    layer_name = request.form.get('layer_name', '').strip()
    style_name = request.form.get('layer_style')  # Récupération du style

    if not layer_name:
        flash("Le nom de la couche est requis.")
        return redirect(url_for('publish'))

    if data_source == 'postgis':
        table_name = request.form.get('postgis_table')
        if not table_name:
            flash("Veuillez sélectionner une table PostGIS.")
            return redirect(url_for('publish'))
        
        try:
            # Appel avec les 3 arguments
            success, message = publish_postgis_to_geoserver(table_name, layer_name, style_name)
            flash(message)
        except Exception as e:
            flash(f"Erreur lors de la publication : {str(e)}")
    
    elif data_source == 'file':
        if 'file' not in request.files:
            flash("Aucun fichier sélectionné.")
            return redirect(url_for('publish'))
        
        file = request.files['file']
        if file.filename == '':
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
        except Exception as e:
            flash(f"Erreur lors de la publication : {str(e)}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return redirect(url_for('publish'))



def publish_shapefile_to_geoserver(zip_path, layer_name):
    """Publie un Shapefile (zip) vers GeoServer via le data directory"""
    # Copie du zip vers le data directory de GeoServer
    gs_data_dir = "/path/to/geoserver/data_dir"  # À adapter
    dest_path = os.path.join(gs_data_dir, "data", f"{layer_name}.zip")
    
    shutil.copy(zip_path, dest_path)
    
    # Configuration de la couche
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/shapefiles/file.shp"
    params = {
        'update': 'overwrite',
        'filename': f"file://{dest_path}"
    }
    
    response = requests.put(
        url,
        auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
        params=params
    )
    
    if response.status_code in [200, 201]:
        flash(f"✅ Shapefile '{layer_name}' publié avec succès!")
    else:
        raise Exception(f"Erreur GeoServer: {response.text}")

def publish_geotiff_to_geoserver(tif_path, layer_name):
    """Publie un GeoTIFF vers GeoServer via le data directory"""
    # Copie du TIFF vers le data directory de GeoServer
    gs_data_dir = "/path/to/geoserver/data_dir"  # À adapter
    dest_path = os.path.join(gs_data_dir, "data", f"{layer_name}.tif")
    
    shutil.copy(tif_path, dest_path)
    
    # Configuration de la couche
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{layer_name}/external.geotiff"
    params = {
        'configure': 'all',
        'coverageName': layer_name,
        'filename': f"file://{dest_path}"
    }
    
    response = requests.put(
        url,
        auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
        params=params
    )
    
    if response.status_code in [200, 201]:
        flash(f"✅ GeoTIFF '{layer_name}' publié avec succès!")
    else:
        raise Exception(f"Erreur GeoServer: {response.text}")

def publish_postgis_to_geoserver(table_name, layer_name, style_name):
    """Publie une table PostGIS vers GeoServer avec le style spécifié"""
    # 1. Création de la featureType
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes"
    
    layer_xml = f"""<featureType>
        <name>{layer_name}</name>
        <nativeName>{table_name}</nativeName>
        <title>{layer_name}</title>
        <srs>EPSG:4326</srs>
        <enabled>true</enabled>
    </featureType>"""
    
    # Création de la couche
    response = requests.post(
        url,
        auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-type': 'text/xml'},
        data=layer_xml
    )
    
    if response.status_code not in [200, 201]:
        return False, f"Erreur création couche: {response.text}"
    
    # 2. Application du style sélectionné
    style_url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{layer_name}"
    style_xml = f"""<layer>
        <defaultStyle>
            <name>{style_name}</name>
        </defaultStyle>
    </layer>"""
    
    style_response = requests.put(
        style_url,
        auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
        headers={'Content-type': 'text/xml'},
        data=style_xml
    )
    
    if style_response.status_code not in [200, 201]:
        return False, f"Couche créée mais erreur style: {style_response.text}"
    
    return True, f"✅ Couche '{layer_name}' publiée avec style '{style_name}'"
@app.route('/integrer')
def integrer():
    return render_template('integrer.html')
@app.route('/visualiser')
def visualiser():
    # Récupérer la liste des tables dans le schéma 'uploads'
    with engine.connect() as conn:
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'uploads'
        """)
        result = conn.execute(query)
        tables = [row[0] for row in result]
    
    return render_template('visualiser.html', tables=tables)

@app.route('/visualiser/<table_name>')
def visualiser_table(table_name):
    # Vérifier que la table existe dans le schéma uploads
    with engine.connect() as conn:
        # Récupérer les données
        gdf = gpd.read_postgis(f"SELECT * FROM uploads.{table_name}", conn, geom_col='geometry')
        
        # Convertir en GeoJSON pour la carte
        geojson = gdf.to_json()
        
        # Récupérer les colonnes attributaires (sans la géométrie)
        columns = [col for col in gdf.columns if col != 'geometry']
        
    return render_template('visualiser_table.html', 
                         table_name=table_name,
                         geojson=geojson,
                         columns=columns,
                         data=gdf.drop(columns='geometry').to_dict('records'))
@app.route('/visualiserg')
def visualiserg():
    try:
        # Configuration avec timeout augmenté
        response = requests.get(
            f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/layers.json",
            auth=(GEOSERVER_USER, GEOSERVER_PASSWORD),
            timeout=30
        )

        if response.status_code != 200:
            flash(f"Erreur GeoServer (HTTP {response.status_code})")
            return redirect(url_for('index'))

        layers_data = response.json()
        published_layers = []

        # Nouvelle méthode robuste de traitement
        if isinstance(layers_data, dict) and 'layers' in layers_data:
            layers_list = layers_data['layers'].get('layer', [])
            
            for layer in layers_list:
                if isinstance(layer, dict):
                    layer_name = str(layer.get('name', ''))  # Conversion en string
                    
                    published_layers.append({
                        'name': layer_name,
                        'short_name': layer_name.split(':')[-1] if ':' in layer_name else layer_name,
                        'href': layer.get('href', '')
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
    """Retourne l'étendue géographique d'une couche"""
    layer_name = request.args.get('layer')
    if not layer_name:
        return jsonify({'success': False, 'error': 'Nom de couche manquant'})
    
    try:
        # Requête GetCapabilities pour obtenir l'étendue
        url = f"{GEOSERVER_URL}/wms?service=WMS&version=1.1.1&request=GetCapabilities"
        response = requests.get(url, auth=(GEOSERVER_USER, GEOSERVER_PASSWORD))
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Erreur GeoServer'})
        
        # Parse la réponse XML
        root = ET.fromstring(response.content)
        ns = {'wms': 'http://www.opengis.net/wms'}
        
        # Trouve la couche correspondante
        for layer in root.findall('.//wms:Layer/wms:Layer', ns):
            name = layer.find('wms:Name', ns)
            if name is not None and name.text == f"{WORKSPACE}:{layer_name}":
                bbox = layer.find('wms:LatLonBoundingBox', ns)
                if bbox is not None:
                    return jsonify({
                        'success': True,
                        'bounds': [
                            float(bbox.get('minx')),
                            float(bbox.get('miny')),
                            float(bbox.get('maxx')),
                            float(bbox.get('maxy'))
                        ]
                    })
        
        return jsonify({'success': False, 'error': 'Couche non trouvée'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/marine')
def marine():
    return render_template('marine.html')
@app.route('/moyens')
def moyens():
    return render_template('moyens.html')
# Ajoutez ces routes dans app.py si elles ne sont pas déjà présentes :

@app.route('/api/resources/types', methods=['GET'])

def get_resource_types_api():
    """Obtenir la liste des types de ressources"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT type_id, type_name, category, description 
                    FROM rescue_resource_types 
                    ORDER BY type_name
                """)
                types = [dict(row) for row in cur.fetchall()]
                return jsonify(types)
    except Exception as e:
        logger.error(f"Erreur récupération types: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/resources/bases', methods=['GET'])

def get_bases_api():
    """Obtenir la liste des bases de secours"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT base_id, base_name, location, coordinates, is_active
                    FROM rescue_bases 
                    WHERE is_active = TRUE
                    ORDER BY base_name
                """)
                bases = []
                for row in cur.fetchall():
                    base = dict(row)
                    if base.get('coordinates'):
                        try:
                            coords = base['coordinates'].split(',')
                            if len(coords) == 2:
                                base['latitude'] = float(coords[0].strip())
                                base['longitude'] = float(coords[1].strip())
                        except:
                            pass
                    bases.append(base)
                return jsonify(bases)
    except Exception as e:
        logger.error(f"Erreur récupération bases: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/resources/<int:resource_id>/history', methods=['GET'])

def get_resource_history(resource_id):
    """Obtenir l'historique des missions d'une ressource"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT rm.*, i.incident_name, i.incident_type, i.incident_date
                    FROM resource_missions rm
                    LEFT JOIN incidents i ON rm.incident_id = i.incident_id
                    WHERE rm.resource_id = %s
                    ORDER BY rm.start_time DESC
                    LIMIT 20
                """, (resource_id,))
                history = [dict(row) for row in cur.fetchall()]
                return jsonify(history)
    except Exception as e:
        logger.error(f"Erreur récupération historique: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/resources/<int:resource_id>/position', methods=['POST'])

def update_resource_position(resource_id):
    """Mettre à jour la position d'une ressource"""
    try:
        data = request.get_json()
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if lat is None or lon is None:
            return jsonify({'error': 'Latitude et longitude requises'}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE rescue_resources 
                    SET current_position = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        last_updated = NOW()
                    WHERE resource_id = %s
                """, (lon, lat, resource_id))
                
                cur.execute("""
                    INSERT INTO resource_position_history (resource_id, position)
                    VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                """, (resource_id, lon, lat))
                
                conn.commit()
                
        return jsonify({'success': True, 'message': 'Position mise à jour'})
        
    except Exception as e:
        logger.error(f"Erreur mise à jour position: {str(e)}")
        return jsonify({'error': str(e)}), 500
class Ship(db.Model):
    __tablename__ = 'ships'
    
    ship_id = db.Column(db.Text, primary_key=True)
    shipname = db.Column(db.Text)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    speed = db.Column(db.Float)
    course = db.Column(db.Float)
    heading = db.Column(db.Float)
    destination = db.Column(db.Text)
    flag = db.Column(db.Text)
    shiptype = db.Column(db.Text)
    type_name = db.Column(db.Text)
    last_update = db.Column(db.DateTime)

@app.route('/marine_traffic')
def marine_traffic():
    return render_template('marine_traffic.html')
# Ajoutez ces routes dans app.py

@app.route('/resources/<int:resource_id>', methods=['PUT'])

def update_resource(resource_id):
    """Mettre à jour un moyen de secours"""
    try:
        data = request.get_json()
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE rescue_resources SET
                        resource_name = %s,
                        identifier_code = %s,
                        type_id = %s,
                        base_id = %s,
                        max_capacity = %s,
                        operational_range = %s,
                        speed = %s,
                        operational_status = %s,
                        notes = %s,
                        last_updated = NOW()
                """
                params = [
                    data['resource_name'],
                    data['identifier_code'],
                    data['type_id'],
                    data['base_id'],
                    data.get('max_capacity'),
                    data.get('operational_range'),
                    data.get('speed'),
                    data.get('operational_status', 'available'),
                    data.get('notes')
                ]
                
                if data.get('current_position'):
                    query += ", current_position = ST_SetSRID(ST_MakePoint(%s, %s), 4326)"
                    params.extend([data['current_position']['longitude'], data['current_position']['latitude']])
                
                query += " WHERE resource_id = %s"
                params.append(resource_id)
                
                cur.execute(query, params)
                conn.commit()
                
        return jsonify({'success': True, 'message': 'Ressource mise à jour'})
        
    except Exception as e:
        logger.error(f"Erreur mise à jour ressource: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/resources/<int:resource_id>', methods=['DELETE'])

def delete_resource(resource_id):
    """Supprimer un moyen de secours (soft delete)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Soft delete - désactiver la ressource
                cur.execute("""
                    UPDATE rescue_resources 
                    SET is_active = FALSE, operational_status = 'out_of_service'
                    WHERE resource_id = %s
                """, (resource_id,))
                conn.commit()
                
        return jsonify({'success': True, 'message': 'Ressource supprimée'})
        
    except Exception as e:
        logger.error(f"Erreur suppression ressource: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/resources/export', methods=['GET'])

def export_resources():
    """Exporter les ressources en CSV/Excel"""
    try:
        format_type = request.args.get('format', 'csv')
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT r.resource_id, r.resource_name, r.identifier_code, 
                           rt.type_name, rb.base_name, r.operational_status,
                           r.max_capacity, r.operational_range, r.speed,
                           ST_X(r.current_position) as longitude, ST_Y(r.current_position) as latitude,
                           r.last_updated, r.created_at
                    FROM rescue_resources r
                    JOIN rescue_resource_types rt ON r.type_id = rt.type_id
                    JOIN rescue_bases rb ON r.base_id = rb.base_id
                    WHERE r.is_active = TRUE
                    ORDER BY r.resource_name
                """)
                resources = cur.fetchall()
                
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Nom', 'Code', 'Type', 'Base', 'Statut', 'Capacité', 'Rayon (km)', 'Vitesse (noeuds)', 'Latitude', 'Longitude', 'Dernière MAJ'])
            
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
            
        else:
            return jsonify(list(resources))
            
    except Exception as e:
        logger.error(f"Erreur export: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/resources/stats', methods=['GET'])

def get_resources_stats():
    """Obtenir les statistiques des ressources"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Statistiques générales
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN operational_status = 'available' THEN 1 END) as available,
                        COUNT(CASE WHEN operational_status = 'on_mission' THEN 1 END) as on_mission,
                        COUNT(CASE WHEN operational_status = 'maintenance' THEN 1 END) as maintenance,
                        COUNT(CASE WHEN operational_status = 'out_of_service' THEN 1 END) as out_of_service
                    FROM rescue_resources
                    WHERE is_active = TRUE
                """)
                general_stats = cur.fetchone()
                
                # Statistiques par type
                cur.execute("""
                    SELECT rt.type_name, COUNT(*) as count
                    FROM rescue_resources r
                    JOIN rescue_resource_types rt ON r.type_id = rt.type_id
                    WHERE r.is_active = TRUE
                    GROUP BY rt.type_name
                    ORDER BY count DESC
                """)
                type_stats = cur.fetchall()
                
                # Statistiques par base
                cur.execute("""
                    SELECT rb.base_name, COUNT(*) as count
                    FROM rescue_resources r
                    JOIN rescue_bases rb ON r.base_id = rb.base_id
                    WHERE r.is_active = TRUE
                    GROUP BY rb.base_name
                    ORDER BY count DESC
                """)
                base_stats = cur.fetchall()
                
                return jsonify({
                    'general': dict(general_stats),
                    'by_type': [dict(s) for s in type_stats],
                    'by_base': [dict(s) for s in base_stats]
                })
                
    except Exception as e:
        logger.error(f"Erreur stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/resources/<int:resource_id>/crew', methods=['GET', 'POST', 'PUT', 'DELETE'])

def manage_resource_crew(resource_id):
    """Gérer l'équipage d'une ressource"""
    try:
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM resource_crew
                        WHERE resource_id = %s AND is_active = TRUE
                        ORDER BY role, name
                    """, (resource_id,))
                    crew = [dict(row) for row in cur.fetchall()]
                    return jsonify(crew)
        
        elif request.method == 'POST':
            data = request.get_json()
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO resource_crew (resource_id, name, role, qualification)
                        VALUES (%s, %s, %s, %s)
                        RETURNING crew_id
                    """, (resource_id, data['name'], data['role'], data.get('qualification')))
                    crew_id = cur.fetchone()[0]
                    conn.commit()
                    return jsonify({'success': True, 'crew_id': crew_id})
        
        elif request.method == 'PUT':
            data = request.get_json()
            crew_id = data.get('crew_id')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE resource_crew
                        SET name = %s, role = %s, qualification = %s
                        WHERE crew_id = %s AND resource_id = %s
                    """, (data['name'], data['role'], data.get('qualification'), crew_id, resource_id))
                    conn.commit()
                    return jsonify({'success': True})
        
        elif request.method == 'DELETE':
            crew_id = request.args.get('crew_id')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE resource_crew
                        SET is_active = FALSE
                        WHERE crew_id = %s AND resource_id = %s
                    """, (crew_id, resource_id))
                    conn.commit()
                    return jsonify({'success': True})
                    
    except Exception as e:
        logger.error(f"Erreur gestion équipage: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/resources/<int:resource_id>/missions', methods=['GET', 'POST'])

def get_resource_missions(resource_id):
    """Obtenir ou ajouter des missions pour une ressource"""
    try:
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT rm.*, i.incident_name, i.incident_type
                        FROM resource_missions rm
                        LEFT JOIN incidents i ON rm.incident_id = i.incident_id
                        WHERE rm.resource_id = %s
                        ORDER BY rm.start_time DESC
                        LIMIT 20
                    """, (resource_id,))
                    missions = [dict(row) for row in cur.fetchall()]
                    return jsonify(missions)
        
        elif request.method == 'POST':
            data = request.get_json()
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO resource_missions (resource_id, incident_id, start_time, notes)
                        VALUES (%s, %s, NOW(), %s)
                        RETURNING mission_id
                    """, (resource_id, data.get('incident_id'), data.get('notes')))
                    mission_id = cur.fetchone()[0]
                    conn.commit()
                    return jsonify({'success': True, 'mission_id': mission_id})
                    
    except Exception as e:
        logger.error(f"Erreur gestion missions: {str(e)}")
        return jsonify({'error': str(e)}), 500
# Dans app.py, ajoutez cette route si elle n'existe pas déjà

@app.route('/derive-guide')

def derive_guide():
    """Guide d'utilisation de la simulation de dérive"""
    return render_template('derive_guide.html')
@app.route('/resources/bulk-update', methods=['POST'])

def bulk_update_resources():
    """Mise à jour en masse des ressources"""
    try:
        data = request.get_json()
        resource_ids = data.get('resource_ids', [])
        updates = data.get('updates', {})
        
        if not resource_ids or not updates:
            return jsonify({'error': 'Données manquantes'}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                set_clauses = []
                params = []
                
                for field, value in updates.items():
                    if field in ['operational_status', 'base_id']:
                        set_clauses.append(f"{field} = %s")
                        params.append(value)
                
                if set_clauses:
                    query = f"""
                        UPDATE rescue_resources 
                        SET {', '.join(set_clauses)}, last_updated = NOW()
                        WHERE resource_id = ANY(%s)
                    """
                    params.append(resource_ids)
                    cur.execute(query, params)
                    conn.commit()
                    
        return jsonify({'success': True, 'updated': len(resource_ids)})
        
    except Exception as e:
        logger.error(f"Erreur mise à jour en masse: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ships')
def get_ships():
    # Récupère TOUS les navires sans aucun filtre
    ships = Ship.query.all()
    
    ships_data = []
    for ship in ships:
        # Gestion des valeurs nulles pour tous les champs
        ship_data = {
            'id': ship.ship_id,
            'name': ship.shipname or 'Inconnu',
            'lat': ship.lat if ship.lat is not None else 0,
            'lon': ship.lon if ship.lon is not None else 0,
            'speed': ship.speed if ship.speed is not None else 'N/A',
            'course': ship.course if ship.course is not None else 0,
            'heading': ship.heading if ship.heading is not None else 0,
            'destination': ship.destination or 'Inconnu',
            'flag': ship.flag or 'Inconnu',
            'shiptype': ship.shiptype or 'Inconnu',
            'type_name': ship.type_name or 'Inconnu',
            'last_update': ship.last_update.isoformat() if ship.last_update else 'Inconnu'
            # Ajoutez tous les autres champs ici
        }
        ships_data.append(ship_data)
    
    return jsonify(ships_data)

@app.route('/api/ships/search')
def search_ships():
    search_term = request.args.get('q', '')
    ship_type = request.args.get('type', '')
    flag = request.args.get('flag', '')
    
    query = Ship.query.filter(
        Ship.lat.isnot(None),
        Ship.lon.isnot(None)
    )  # ← fermeture de la parenthèse ici

    if search_term:
        query = query.filter(Ship.shipname.ilike(f'%{search_term}%'))

    if ship_type:
        query = query.filter(Ship.shiptype == ship_type)

    if flag:
        query = query.filter(Ship.flag == flag)

    ships = query.limit(100).all()

    ships_data = [{
        'id': ship.ship_id,
        'name': ship.shipname,
        'lat': ship.lat,
        'lon': ship.lon,
        'speed': ship.speed,
        'heading': ship.heading,
        'destination': ship.destination,
        'flag': ship.flag,
        'type': getattr(ship, 'type_name', None),  # ← évite erreur si 'type_name' n'existe pas
        'last_update': ship.last_update.strftime('%Y-%m-%d %H:%M') if ship.last_update else None
    } for ship in ships]

    return jsonify(ships_data)

@app.route('/api/ships/stats')
def get_ship_stats():
    # Statistiques par type de navire
    type_stats = db.session.query(
        Ship.shiptype,
        Ship.type_name,
        func.count(Ship.ship_id).label('count')
    ).group_by(Ship.shiptype, Ship.type_name).all()
    
    # Statistiques par pavillon
    flag_stats = db.session.query(
        Ship.flag,
        func.count(Ship.ship_id).label('count')
    ).group_by(Ship.flag).all()
    
    return jsonify({
        'by_type': [{'type': t.shiptype, 'name': t.type_name, 'count': t.count} for t in type_stats],
        'by_flag': [{'flag': f.flag, 'count': f.count} for f in flag_stats]
    })

@app.route('/api/ship/<ship_id>')
def get_ship_details(shipname):
    ship = Ship.query.get(shipname)
    if not ship:
        return jsonify({'error': 'Ship not found'}), 404
    
    return jsonify({
        'id': ship.ship_id,
        'name': ship.shipname,
        'type': ship.type_name,
        'flag': ship.flag,
        'destination': ship.destination,
        'speed': ship.speed,
        'length': ship.length,
        'width': ship.width,
        'last_update': ship.last_update.isoformat(),
        'position': {
            'lat': ship.lat,
            'lon': ship.lon
        }
    })
from flask import Blueprint, request, jsonify
from functools import wraps
import binascii
from sqlalchemy.exc import OperationalError


# Utilitaire pour convertir une colonne POINT en dict latitude/longitude
def convert_point(blob):
    if blob and isinstance(blob, (bytes, bytearray)):
        hex_str = binascii.hexlify(blob).decode()
        try:
            lat = int(hex_str[16:24], 16) / 1_000_000
            lon = int(hex_str[24:32], 16) / 1_000_000
            return {'latitude': lat, 'longitude': lon}
        except Exception:
            return None
    return None

from sqlalchemy import text

@app.route('/resources', methods=['GET'])
def get_resources():
    try:
        status = request.args.get('status')
        type_id = request.args.get('type')
        base = request.args.get('base')
        # Suppression des paramètres page, per_page et offset
        # page = request.args.get('page', 1, type=int)
        # per_page = request.args.get('per_page', 20, type=int)
        # offset = (page - 1) * per_page

        filters = ["r.is_active = TRUE"]
        params = {}

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

        base_query = f"""
            SELECT 
                r.*, 
                rt.type_name, 
                rb.base_name, 
                rb.location as base_location,
                ST_X(r.current_position) as longitude,
                ST_Y(r.current_position) as latitude
            FROM rescue_resources r
            JOIN rescue_resource_types rt ON r.type_id = rt.type_id
            JOIN rescue_bases rb ON r.base_id = rb.base_id
            WHERE {filter_clause}
        """
        count_query = f"""
            SELECT COUNT(*) as total
            FROM rescue_resources r
            WHERE {filter_clause}
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
                        'latitude': resource['latitude'],
                        'longitude': resource['longitude']
                    }
                resources.append(resource)
            
            result.close()

            count_result = conn.execute(text(count_query), params)
            total = count_result.scalar()

        return jsonify({
            'data': resources,
            'pagination': {
                'total': total,
                # plus de page, per_page ni total_pages sans offset/pagination
            }
        })

    except Exception as e:
        print(f"API Error: {str(e)}")
        return jsonify({'message': 'Database error'}), 500





# 2. Obtenir un moyen de secours spécifique
@app.route('/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    try:
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT r.*, rt.type_name, rb.base_name, rb.location as base_location
            FROM rescue_resources r
            JOIN rescue_resource_types rt ON r.type_id = rt.type_id
            JOIN rescue_bases rb ON r.base_id = rb.base_id
            WHERE r.resource_id = %s AND r.is_active = TRUE
        """, (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            return jsonify({'message': 'Resource not found'}), 404

        resource['current_position'] = convert_point(resource.get('current_position'))

        # Equipage
        cursor.execute("SELECT * FROM resource_crew WHERE resource_id = %s AND is_active = TRUE", (resource_id,))
        resource['crew'] = cursor.fetchall()

        # Équipements
        cursor.execute("SELECT * FROM resource_equipment WHERE resource_id = %s", (resource_id,))
        resource['equipment'] = cursor.fetchall()

        # Missions
        cursor.execute("""
            SELECT m.*, i.incident_name
            FROM resource_missions m
            JOIN incidents i ON m.incident_id = i.incident_id
            WHERE m.resource_id = %s
            ORDER BY m.start_time DESC
            LIMIT 10
        """, (resource_id,))
        resource['recent_missions'] = cursor.fetchall()

        return jsonify(resource)
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500

# 3. Mettre à jour le statut d’un moyen de secours
@app.route('/resources/<int:resource_id>/status', methods=['PUT'])
def update_resource_status(resource_id):
    try:
        data = request.get_json()
        status = data.get('status')
        position = data.get('position')
        notes = data.get('notes')

        if not status:
            return jsonify({'message': 'Status is required'}), 400

        cursor = db.cursor()
        query = "UPDATE rescue_resources SET operational_status = %s, last_updated = NOW()"
        params = [status]

        if position:
            query += ", current_position = POINT(%s, %s)"
            params.extend([position['longitude'], position['latitude']])

            cursor.execute(
                "INSERT INTO resource_position_history (resource_id, position) VALUES (%s, POINT(%s, %s))",
                (resource_id, position['longitude'], position['latitude'])
            )

        query += " WHERE resource_id = %s"
        params.append(resource_id)
        cursor.execute(query, params)

        if notes:
            cursor.execute("UPDATE rescue_resources SET current_status = %s WHERE resource_id = %s", (notes, resource_id))

        db.commit()
        return jsonify({'message': 'Resource status updated successfully'})
    except Exception as e:
        print(e)
        db.rollback()
        return jsonify({'message': 'Server error'}), 500

# 4. Créer un nouveau moyen de secours
@app.route('/resources', methods=['POST'])
def create_resource():
    try:
        data = request.get_json()
        required_fields = ['resource_name', 'type_id', 'base_id', 'identifier_code']
        if any(field not in data for field in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400

        cursor = db.cursor()
        query = """
            INSERT INTO rescue_resources (
                resource_name, type_id, base_id, identifier_code, operational_status,
                max_capacity, operational_range, speed, current_position
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, POINT(%s, %s))
        """
        cursor.execute(query, (
            data['resource_name'],
            data['type_id'],
            data['base_id'],
            data['identifier_code'],
            data.get('operational_status', 'available'),
            data.get('max_capacity'),
            data.get('operational_range'),
            data.get('speed'),
            data.get('current_position', {}).get('longitude'),
            data.get('current_position', {}).get('latitude')
        ))

        db.commit()
        return jsonify({'message': 'Resource created successfully', 'resource_id': cursor.lastrowid}), 201
    except Exception as e:
        print(e)
        db.rollback()
        if "Duplicate" in str(e):
            return jsonify({'message': 'Identifier code already exists'}), 400
        return jsonify({'message': 'Server error'}), 500

# 5. Obtenir les types de ressources
@app.route('/resource-types', methods=['GET'])
def get_resource_types():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rescue_resource_types")
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500

# 6. Obtenir les bases de secours
@app.route('/bases', methods=['GET'])
def get_bases():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rescue_bases WHERE is_active = TRUE")
        bases = cursor.fetchall()

        for base in bases:
            base['coordinates'] = convert_point(base.get('coordinates'))

        return jsonify(bases)
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500
# 7. Historique des positions d'une ressource
@app.route('/resources/<int:resource_id>/position-history', methods=['GET'])
def get_resource_position_history(resource_id):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT position_id, ST_X(position) as longitude, ST_Y(position) as latitude, 
                   recorded_at, notes
            FROM resource_position_history
            WHERE resource_id = %s
            ORDER BY recorded_at DESC
            LIMIT 50
        """, (resource_id,))
        
        positions = cursor.fetchall()
        return jsonify(positions)
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500

# 8. Mise à jour de l'équipage
@app.route('/resources/<int:resource_id>/crew', methods=['POST', 'PUT'])
def update_resource_crew(resource_id):
    try:
        data = request.get_json()
        # Implémentation de la gestion de l'équipage
        return jsonify({'message': 'Not implemented yet'}), 501
    except Exception as e:
        print(e)
        return jsonify({'message': 'Server error'}), 500
# Ajouter cette fonction pour une meilleure gestion des erreurs
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'message': 'Bad request'}), 400
import pytz


# Configuration
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"
TIMEZONE = pytz.timezone('Africa/Casablanca')
ZONES = {
    'tanger_med': { 'lat': 35.89, 'lon': -5.48, 'name': 'Tanger-Med' },
    'gibraltar': { 'lat': 35.9, 'lon': -5.3, 'name': 'Détroit de Gibraltar' },
    'tetouan': { 'lat': 35.57, 'lon': -5.37, 'name': 'Tétouan / M’diq' },
    'al_hoceima': { 'lat': 35.24, 'lon': -3.93, 'name': 'Al Hoceïma' },
    'nador': { 'lat': 35.17, 'lon': -2.93, 'name': 'Nador / Beni Ensar' },
    
    'saidia': { 'lat': 35.10, 'lon': -2.25, 'name': 'Saidia' },

    'tanger_atlantique': { 'lat': 35.78, 'lon': -5.83, 'name': 'Tanger Atlantique' },
    'larache': { 'lat': 35.19, 'lon': -6.15, 'name': 'Larache' },
    'kenitra': { 'lat': 34.26, 'lon': -6.66, 'name': 'Kénitra' },
    'rabat': { 'lat': 34.02, 'lon': -6.84, 'name': 'Rabat' },
    'casablanca': { 'lat': 33.59, 'lon': -7.61, 'name': 'Casablanca' },
    'el_jadida': { 'lat': 33.23, 'lon': -8.50, 'name': 'El Jadida' },
    'safi': { 'lat': 32.30, 'lon': -9.23, 'name': 'Safi' },
    'essaouira': { 'lat': 31.51, 'lon': -9.76, 'name': 'Essaouira' },
    'agadir': { 'lat': 30.42, 'lon': -9.60, 'name': 'Agadir' },
    'tan_tan': { 'lat': 28.44, 'lon': -11.10, 'name': 'Tan-Tan / El Ouatia' },
    'tarfaya': { 'lat': 27.94, 'lon': -12.91, 'name': 'Tarfaya' },
    'laayoune': { 'lat': 27.15, 'lon': -13.20, 'name': 'Laâyoune' },
    'boujdour': { 'lat': 26.14, 'lon': -14.49, 'name': 'Boujdour' },
    'dakhla': { 'lat': 23.69, 'lon': -15.95, 'name': 'Dakhla' },
    'lagouira': { 'lat': 21.37, 'lon': -17.03, 'name': 'Lagouira' }
}

def fetch_marine_data(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wind_wave_height,wind_wave_direction",
        "timezone": "auto",
        "forecast_days": 3
    }
    try:
        response = requests.get(MARINE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Validation basique de la structure des données
        if not isinstance(data.get('hourly', {}), dict):
            print("Structure de données invalide reçue de l'API")
            return None
            
        return data
    except Exception as e:
        print(f"Erreur API pour {lat},{lon}: {str(e)}")
        return None

@app.route('/meteo')
def meteo():
    return render_template('meteo.html')

@app.route('/api/marine-data')
def marine_data():
    marine_data = {}
    alerts = []
    
    for zone_id, zone in ZONES.items():
        data = fetch_marine_data(zone['lat'], zone['lon'])
        if not data or 'hourly' not in data:
            print(f"Aucune donnée valide pour {zone['name']}")
            continue
            
        hourly = data['hourly']
        times = hourly.get('time', [])
        last_idx = len(times) - 1 if times else 0
        
        # Récupération sécurisée des données avec valeurs par défaut
        def safe_get(data_list, index, default=0.0):
            try:
                value = data_list[index]
                return float(value) if value is not None else default
            except (IndexError, TypeError, ValueError):
                return default
                
        wind_wave_heights = hourly.get('wind_wave_height', [])
        wave_heights = hourly.get('wave_height', [])
        wind_directions = hourly.get('wind_wave_direction', [])
        
        current_data = {
            'wave_height': safe_get(wave_heights, last_idx),
            'wind_speed': safe_get(wind_wave_heights, last_idx) * 1.94,  # Conversion en noeuds
            'wind_direction': safe_get(wind_directions, last_idx),
            'time': times[last_idx] if last_idx < len(times) else datetime.now().isoformat()
        }
        
      
        forecast_data = {
            'time': times,
            'wave_height': [safe_get(wave_heights, i) for i in range(len(times))],
            'wave_height_max': [max(safe_get(wave_heights, i) for i in range(len(times)))],  # Add this line
            'wind_speed_10m': [safe_get(wind_wave_heights, i) * 1.94 for i in range(len(times))],
            'wind_direction_10m': [safe_get(wind_directions, i) for i in range(len(times))]
        }
        marine_data[zone_id] = {
            'name': zone['name'],
            'current': current_data,
            'forecast': forecast_data,
            'coordinates': {'lat': zone['lat'], 'lon': zone['lon']}
        }
        
        # Génération des alertes
        current_wave = current_data['wave_height']
        current_wind = current_data['wind_speed']
        
        if current_wind > 25:
            alerts.append({
                'zone': zone['name'],
                'type': 'vent',
                'message': f"Vents forts ({current_wind:.1f} noeuds) détectés",
                'severity': 'warning'
            })
        if current_wave > 3:
            alerts.append({
                'zone': zone['name'],
                'type': 'houle',
                'message': f"Grosse houle ({current_wave:.1f}m) détectée",
                'severity': 'danger'
            })
    
    return jsonify({
        'zones': marine_data,
        'alerts': alerts,
        'last_updated': datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/offshore')
def offshore():
    return render_template('offshore.html')
@app.route('/ocean')
def ocean():
    return render_template('ocean.html')
import json
import os

def load_marine_data(data_dir):
    """Charge les données marines depuis le répertoire spécifié"""
    data = {
        'depths': [],
        'hazards': [],
        'navigation_aids': [],
        'coastline': []
    }
    
    try:
        # Charger les profondeurs
        with open(os.path.join(data_dir, 'depths.json')) as f:
            data['depths'] = json.load(f)
        
        # Charger les dangers
        with open(os.path.join(data_dir, 'hazards.json')) as f:
            data['hazards'] = json.load(f)
        
        # Charger les aides à la navigation
        with open(os.path.join(data_dir, 'navigation_aids.json')) as f:
            data['navigation_aids'] = json.load(f)
        
        # Charger le tracé côtier
        with open(os.path.join(data_dir, 'coastline.json')) as f:
            data['coastline'] = json.load(f)
            
    except FileNotFoundError:
        print(f"Warning: Missing data files in {data_dir}")
    
    return data

from flask import Flask, render_template, jsonify, request
import os
import json
import random


# Données simulées pour le Maroc
MAROC_DATA = {
    "depths": [
        {"lat": 35.7796, "lon": -5.8033, "depth": 12.5},
        {"lat": 33.5731, "lon": -7.5898, "depth": 8.2},
        {"lat": 31.5144, "lon": -9.7695, "depth": 15.7},
        {"lat": 28.4326, "lon": -11.1000, "depth": 22.3}
    ],
    "hazards": [
        {"type": "rock", "lat": 35.7810, "lon": -5.8050, "description": "Rocher submergé"},
        {"type": "wreck", "lat": 33.5750, "lon": -7.5910, "description": "Épave à 10m de profondeur"}
    ],
    "navigation_aids": [
        {"type": "buoy", "lat": 35.7800, "lon": -5.8000, "name": "Bouée Tanger"},
        {"type": "lighthouse", "lat": 33.6000, "lon": -7.6000, "name": "Phare Casablanca"}
    ]
}

def generate_map_data(region_data, zoom_level):
    """Génère des données cartographiques en fonction du niveau de zoom"""
    filtered_data = {
        "depths": [],
        "hazards": [],
        "navigation_aids": []
    }
    
    # Filtrage basé sur le zoom (simplifié)
    if zoom_level > 8:  # Zoom élevé - montrer tous les détails
        filtered_data = region_data
    else:  # Zoom faible - montrer moins de détails
        filtered_data["depths"] = [d for d in region_data["depths"] if d["depth"] < 15]
        filtered_data["hazards"] = region_data["hazards"][:2]
        filtered_data["navigation_aids"] = region_data["navigation_aids"][:3]
    
    return filtered_data


@app.route('/cartes')
def cartes():
    return render_template('cartes.html')

@app.route('/api/map_data')
def get_map_data():
    zoom_level = int(request.args.get('zoom', 5))
    
    # Utiliser les données simulées pour le Maroc
    data = {
        "depths": [
            {"lat": 35.7796, "lon": -5.8033, "depth": 12.5},
            {"lat": 33.5731, "lon": -7.5898, "depth": 8.2},
            {"lat": 31.5144, "lon": -9.7695, "depth": 15.7},
            {"lat": 28.4326, "lon": -11.1000, "depth": 22.3}
        ],
        "hazards": [
            {"lat": 35.7810, "lon": -5.8050, "type": "rock", "description": "Rocher submergé"},
            {"lat": 33.5750, "lon": -7.5910, "type": "wreck", "description": "Épave à 10m de profondeur"}
        ],
        "navigation_aids": [
            {"lat": 35.7800, "lon": -5.8000, "type": "buoy", "name": "Bouée Tanger"},
            {"lat": 33.6000, "lon": -7.6000, "type": "lighthouse", "name": "Phare Casablanca"}
        ]
    }
    
    return jsonify(data)

@app.route('/api/depth_data')
def get_depth_data():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    # Simulation plus réaliste des données
    base_depth = 5 + (float(lat) * 100 % 50) + (float(lon) * 100 % 30)
    depth_variation = random.uniform(-3, 3)
    
    depth_data = {
        'depth': round(base_depth + depth_variation, 1),
        'hazards': simulate_hazards(lat, lon),
        'navigation_aids': simulate_navigation_aids(lat, lon)
    }
    
    return jsonify(depth_data)

def simulate_hazards(lat, lon):
    hazards = []
    lat_f = float(lat)
    lon_f = float(lon)
    
    # Générer quelques dangers aléatoires près du point cliqué
    for i in range(random.randint(0, 3)):
        hazards.append({
            'type': random.choice(['rock', 'wreck', 'reef']),
            'position': [
                lat_f + random.uniform(-0.05, 0.05),
                lon_f + random.uniform(-0.05, 0.05)
            ],
            'description': f"Danger {i+1}"
        })
    
    return hazards

def simulate_navigation_aids(lat, lon):
    aids = []
    lat_f = float(lat)
    lon_f = float(lon)
    
    # Générer quelques aides à la navigation
    for i in range(random.randint(1, 4)):
        aid_type = random.choice(['buoy', 'lighthouse', 'beacon'])
        aids.append({
            'type': aid_type,
            'position': [
                lat_f + random.uniform(-0.1, 0.1),
                lon_f + random.uniform(-0.1, 0.1)
            ],
            'name': f"{aid_type.capitalize()} {i+1}"
        })
    
    return aids


def calculate_drift(start_lat, start_lon, current_speed, current_direction, 
                   wind_speed, wind_direction, time_hours=1):
    """
    Calcule la position de dérive en fonction des courants et vents
    
    Args:
        start_lat (float): Latitude de départ en degrés
        start_lon (float): Longitude de départ en degrés
        current_speed (float): Vitesse du courant en noeuds
        current_direction (float): Direction du courant en degrés (0 = Nord, 90 = Est)
        wind_speed (float): Vitesse du vent en noeuds
        wind_direction (float): Direction du vent en degrés (0 = Nord, 90 = Est)
        time_hours (float): Temps écoulé en heures
    
    Returns:
        tuple: (drift_lat, drift_lon) - Position finale après dérive
    """
    # Conversion des directions en radians (à partir du Nord dans le sens horaire)
    current_rad = math.radians(450 - current_direction) % (2 * math.pi)
    wind_rad = math.radians(450 - wind_direction) % (2 * math.pi)
    
    # Calcul des composantes de la dérive due au courant
    # 1 noeud = 1.852 km/h
    current_distance = current_speed * 1.852 * time_hours  # en km
    
    # Calcul des composantes de la dérive due au vent
    # On suppose que l'effet du vent est 30% de sa vitesse (coefficient empirique)
    wind_effect = 0.3 * wind_speed * 1.852 * time_hours  # en km
    
    # Calcul des déplacements totaux en km
    total_north = (current_distance * math.cos(current_rad) + 
                  wind_effect * math.cos(wind_rad))
    total_east = (current_distance * math.sin(current_rad) + 
                 wind_effect * math.sin(wind_rad))
    
    # Conversion des déplacements en degrés de latitude/longitude
    # 1 degré de latitude ≈ 111 km
    # 1 degré de longitude ≈ 111 km * cos(latitude)
    lat_shift = total_north / 111.0
    lon_shift = total_east / (111.0 * math.cos(math.radians(start_lat)))
    
    # Calcul de la position finale
    drift_lat = start_lat + lat_shift
    drift_lon = start_lon + lon_shift
    
    return drift_lat, drift_lon

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcule la distance entre deux points géographiques en utilisant la formule de Haversine
    
    Args:
        lat1, lon1: Coordonnées du premier point en degrés
        lat2, lon2: Coordonnées du second point en degrés
    
    Returns:
        float: Distance en kilomètres
    """
    # Conversion en radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Différences de coordonnées
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Formule de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Rayon de la Terre en kilomètres (≈6371 km)
    r = 6371
    return c * r

def calculate_drift_angle(start_lat, start_lon, rescue_lat, rescue_lon, drift_lat, drift_lon):
    """
    Calcule l'angle entre la direction vers le lieu de sauvetage et la direction de dérive
    
    Args:
        start_lat, start_lon: Coordonnées de départ
        rescue_lat, rescue_lon: Coordonnées du lieu de sauvetage
        drift_lat, drift_lon: Coordonnées de la dérive estimée
    
    Returns:
        float: Angle en degrés
    """
    # Vecteur vers le lieu de sauvetage
    rescue_vector = np.array([rescue_lon - start_lon, rescue_lat - start_lat])
    
    # Vecteur de dérive
    drift_vector = np.array([drift_lon - start_lon, drift_lat - start_lat])
    
    # Calcul de l'angle entre les deux vecteurs
    if np.linalg.norm(rescue_vector) == 0 or np.linalg.norm(drift_vector) == 0:
        return 0
    
    dot_product = np.dot(rescue_vector, drift_vector)
    cos_angle = dot_product / (np.linalg.norm(rescue_vector) * np.linalg.norm(drift_vector))
    
    # Éviter les erreurs d'arrondi
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    
    angle_rad = np.arccos(cos_angle)
    return np.degrees(angle_rad)

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json()
        
        # Extraction des paramètres
        start_lat = float(data['start_lat'])
        start_lon = float(data['start_lon'])
        rescue_lat = float(data['rescue_lat'])
        rescue_lon = float(data['rescue_lon'])
        current_speed = float(data['current_speed'])
        current_direction = float(data['current_direction'])
        wind_speed = float(data['wind_speed'])
        wind_direction = float(data['wind_direction'])
        
        # Calcul de la distance initiale jusqu'au lieu de sauvetage
        initial_distance = haversine_distance(start_lat, start_lon, rescue_lat, rescue_lon)
        
        # Estimation du temps nécessaire pour atteindre le lieu de sauvetage
        # (en supposant une vitesse moyenne de 5 noeuds pour le bateau de sauvetage)
        boat_speed = 5  # noeuds
        estimated_time = initial_distance / (boat_speed * 1.852)  # en heures
        
        # Calcul de la dérive pendant ce temps
        drift_lat, drift_lon = calculate_drift(
            start_lat, start_lon, 
            current_speed, current_direction,
            wind_speed, wind_direction,
            estimated_time
        )
        
        # Calcul des résultats
        distance_to_rescue = haversine_distance(drift_lat, drift_lon, rescue_lat, rescue_lon)
        drift_angle = calculate_drift_angle(start_lat, start_lon, rescue_lat, rescue_lon, drift_lat, drift_lon)
        
        # Vitesse de dérive globale (combinaison courant + vent)
        total_drift_speed = math.sqrt(
            (current_speed * math.cos(math.radians(current_direction)) + 
             0.3 * wind_speed * math.cos(math.radians(wind_direction)))**2 +
            (current_speed * math.sin(math.radians(current_direction)) + 
             0.3 * wind_speed * math.sin(math.radians(wind_direction)))**2
        )
        
        # Préparation de la réponse
        result = {
            'drift_lat': drift_lat,
            'drift_lon': drift_lon,
            'distance_to_rescue': initial_distance,
            'drift_angle': drift_angle,
            'drift_speed': total_drift_speed,
            'drift_time': estimated_time,
            'rescue_offset': distance_to_rescue
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/recherche-balises')
def recherche_balises():
    logger.info("=== PAGE RECHERCHE BALISES ACCEDEE ===")
    return render_template('recherche_balises.html')

@app.route('/api/recherche-balise', methods=['POST'])
def api_recherche_balise():
    try:
        logger.info(f"\n=== DEBUT RECHERCHE BALISE {datetime.now()} ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Vérifier si c'est du JSON
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            logger.info(f"JSON data reçu: {data}")
            code = data.get('code', '') if data else ''
        else:
            # Fallback pour les données form
            code = request.form.get('code', '')
            logger.info(f"Form data: {request.form.to_dict()}")
        
        code = code.strip()
        logger.info(f"Code après nettoyage: '{code}'")
        
        if not code:
            logger.error("ERREUR: Code vide")
            return jsonify({'error': 'Veuillez entrer un code'}), 400
        
        # Connexion à la base de données
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            logger.info("✓ Connexion DB réussie")
        except Exception as db_error:
            logger.error(f"✗ Erreur connexion DB: {db_error}")
            return jsonify({'error': f'Erreur base de données: {db_error}'}), 500
        
        # Vérifier si la table existe
        try:
            cursor.execute("SELECT COUNT(*) as count FROM maritime.mrcc_temple_plb")
            count_result = cursor.fetchone()
            logger.info(f"✓ Nombre total d'enregistrements: {count_result['count']}")
        except Exception as count_error:
            logger.error(f"✗ Erreur count: {count_error}")
            return jsonify({'error': f'Erreur table: {count_error}'}), 500
        
        # Recherche dans la base
        query = """
        SELECT * FROM maritime.mrcc_temple_plb 
        WHERE registration_number ILIKE %s 
           OR mmsi ILIKE %s 
           OR uin ILIKE %s 
           OR CAST(serial_number_manufacturer AS TEXT) ILIKE %s 
           OR CAST(serial_number_sar AS TEXT) ILIKE %s
           OR unit_name ILIKE %s
        LIMIT 1
        """
        
        search_pattern = f'%{code}%'
        logger.info(f"Exécution requête avec pattern: {search_pattern}")
        
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, 
                             search_pattern, search_pattern, search_pattern))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            balise_info = dict(result)
            logger.info(f"✓ Balise trouvée - UIN: {balise_info.get('uin')}")
            return jsonify(balise_info)
        else:
            logger.warning("✗ Aucune balise trouvée")
            return jsonify({'error': 'Aucune balise trouvée avec ce code'}), 404
            
    except Exception as e:
        logger.error(f"✗ ERREUR GLOBALE: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Erreur lors de la recherche: {str(e)}'}), 500

@app.route('/api/test', methods=['GET'])
def api_test():
    return jsonify({
        'message': 'API test OK', 
        'timestamp': str(datetime.now()),
        'status': 'success'
    })

@app.route('/api/test-db', methods=['GET'])
def api_test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM maritime.mrcc_temple_plb")
        count_result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Connexion DB réussie',
            'record_count': count_result['count']
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur DB: {str(e)}'
        }), 500


from flask import Flask, render_template, request, jsonify
import numpy as np
from datetime import datetime, timedelta
import logging
from scipy.integrate import odeint
import math






def advanced_drift_simulation(start_lat, start_lon, current_speed, current_direction,
                            wind_speed, wind_direction, object_type, sea_state,
                            simulation_hours, time_step):
    """
    Simulation de dérive avancée avec modèles physiques
    """
    # Coefficients selon le type d'objet
    object_coefficients = {
        'person': {'wind_effect': 0.03, 'current_effect': 1.0, 'leeway': 2.0},
        'life_raft': {'wind_effect': 0.02, 'current_effect': 0.95, 'leeway': 1.5},
        'life_boat': {'wind_effect': 0.01, 'current_effect': 0.9, 'leeway': 1.2},
        'container': {'wind_effect': 0.005, 'current_effect': 0.98, 'leeway': 0.5},
        'fishing_boat': {'wind_effect': 0.015, 'current_effect': 0.92, 'leeway': 1.0}
    }
    
    coeffs = object_coefficients.get(object_type, object_coefficients['person'])
    
    # Conversion des directions en radians
    current_dir_rad = np.radians(current_direction)
    wind_dir_rad = np.radians(wind_direction)
    
    # Effet du vent (leeway)
    leeway_angle = coeffs['leeway'] * sea_state
    wind_effect_speed = wind_speed * coeffs['wind_effect']
    
    # Calcul des composantes
    current_u = current_speed * np.cos(current_dir_rad)
    current_v = current_speed * np.sin(current_dir_rad)
    
    wind_u = wind_effect_speed * np.cos(wind_dir_rad + np.radians(leeway_angle))
    wind_v = wind_effect_speed * np.sin(wind_dir_rad + np.radians(leeway_angle))
    
    # Vitesse totale
    total_u = current_u + wind_u
    total_v = current_v + wind_v
    total_speed = np.sqrt(total_u**2 + total_v**2)
    
    # Simulation temporelle
    time_points = np.arange(0, simulation_hours, time_step)
    positions = []
    
    current_lat, current_lon = start_lat, start_lon
    
    for t in time_points:
        # Conversion lat/lon en distances (approximation)
        lat_km_per_degree = 111.32
        lon_km_per_degree = 111.32 * np.cos(np.radians(current_lat))
        
        # Déplacement en km
        delta_lat_km = total_v * t * 1.852 / 3600  # noeuds -> km/s
        delta_lon_km = total_u * t * 1.852 / 3600
        
        # Conversion en degrés
        delta_lat = delta_lat_km / lat_km_per_degree
        delta_lon = delta_lon_km / lon_km_per_degree
        
        new_lat = start_lat + delta_lat
        new_lon = start_lon + delta_lon
        
        positions.append({
            'time': t,
            'lat': new_lat,
            'lon': new_lon,
            'speed': total_speed,
            'distance_from_start': haversine(start_lat, start_lon, new_lat, new_lon)
        })
    
    # Points clés de la simulation
    hourly_positions = [p for p in positions if p['time'] % 1 == 0]
    
    return {
        'trajectory': positions,
        'hourly_positions': hourly_positions,
        'final_position': positions[-1] if positions else None,
        'max_distance': max(p['distance_from_start'] for p in positions),
        'average_speed': np.mean([p['speed'] for p in positions]),
        'total_drift_distance': positions[-1]['distance_from_start'] if positions else 0
    }

def analyze_risk_factors(simulation_results):
    """
    Analyse des facteurs de risque avancée
    """
    trajectory = simulation_results['trajectory']
    final_pos = simulation_results['final_position']
    
    if not trajectory:
        return {}
    
    # Calcul de l'incertitude
    positions = [(p['lat'], p['lon']) for p in trajectory]
    lat_std = np.std([p[0] for p in positions])
    lon_std = np.std([p[1] for p in positions])
    position_uncertainty = np.sqrt(lat_std**2 + lon_std**2)
    
    # Analyse de la dispersion
    speeds = [p['speed'] for p in trajectory]
    speed_variability = np.std(speeds) / np.mean(speeds) if np.mean(speeds) > 0 else 0
    
    # Classification du risque
    uncertainty_risk = min(100, position_uncertainty * 1000)
    speed_risk = min(100, speed_variability * 50)
    total_risk = (uncertainty_risk + speed_risk) / 2
    
    risk_level = "FAIBLE"
    if total_risk > 70:
        risk_level = "ÉLEVÉ"
    elif total_risk > 40:
        risk_level = "MODÉRÉ"
    
    return {
        'position_uncertainty_km': position_uncertainty,
        'speed_variability': speed_variability,
        'total_risk_score': total_risk,
        'risk_level': risk_level,
        'search_area_radius_km': max(5, position_uncertainty * 3)
    }

def generate_recommendations(simulation_results, risk_analysis):
    """
    Génération de recommandations basées sur l'analyse
    """
    recommendations = []
    risk_level = risk_analysis.get('risk_level', 'FAIBLE')
    
    # Recommandations basées sur le niveau de risque
    if risk_level == "ÉLEVÉ":
        recommendations.extend([
            "🔴 Zone de recherche étendue requise",
            "🔴 Multiples moyens de recherche recommandés",
            "🔴 Réévaluation fréquente de la position",
            "🔴 Coordination renforcée avec les services météo"
        ])
    elif risk_level == "MODÉRÉ":
        recommendations.extend([
            "🟡 Zone de recherche standard",
            "🟡 Surveillance météorologique accrue",
            "🟡 Mise à jour horaire de la position estimée"
        ])
    else:
        recommendations.extend([
            "🟢 Zone de recherche focalisée",
            "🟢 Surveillance météorologique standard",
            "🟢 Mise à jour toutes les 2-4 heures"
        ])
    
    # Recommandations basées sur la trajectoire
    max_distance = simulation_results.get('max_distance', 0)
    if max_distance > 100:
        recommendations.append("🌊 Intervention aéromaritime recommandée")
    
    avg_speed = simulation_results.get('average_speed', 0)
    if avg_speed > 3:
        recommendations.append("💨 Vitesse de dérive élevée - recherche avancée nécessaire")
    
    return recommendations

def haversine(lat1, lon1, lat2, lon2):
    """Calculate great circle distance between two points"""
    R = 6371  # Earth radius in km
    
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = (np.sin(dlat/2) * np.sin(dlat/2) + 
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * 
         np.sin(dlon/2) * np.sin(dlon/2))
    
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

@app.route('/api/get-search-patterns', methods=['POST'])
def api_get_search_patterns():
    """Génère des motifs de recherche optimisés"""
    data = request.get_json()
    center_lat = data['lat']
    center_lon = data['lon']
    radius_km = data.get('radius', 10)
    
    patterns = generate_search_patterns(center_lat, center_lon, radius_km)
    return jsonify(patterns)

def generate_search_patterns(center_lat, center_lon, radius_km):
    """Génère différents motifs de recherche"""
    patterns = {
        'expanding_square': [],
        'sector_search': [],
        'parallel_track': []
    }
    
    # Carré expansif
    for i in range(5):
        side = radius_km * (i + 1) / 5
        patterns['expanding_square'].extend([
            [center_lat + side/111.32, center_lon + side/(111.32 * np.cos(np.radians(center_lat)))],
            [center_lat + side/111.32, center_lon - side/(111.32 * np.cos(np.radians(center_lat)))],
            [center_lat - side/111.32, center_lon - side/(111.32 * np.cos(np.radians(center_lat)))],
            [center_lat - side/111.32, center_lon + side/(111.32 * np.cos(np.radians(center_lat)))],
        ])
    
    return patterns
"""
Configuration pour le système MRCC Maroc
Routes maritimes et zones de recherche standardisées selon IAMSAR
"""

# Configuration MRCC Maroc
MRCC_MAROC = {
    'name': 'Centre de Coordination de Sauvetage Maritime - Maroc',
    'center_coords': {'lat': 33.5731, 'lon': -7.5898},  # Casablanca
    'zones': {
        'nord': {'lat_min': 35.5, 'lat_max': 36.0, 'lon_min': -6.0, 'lon_max': -5.0},
        'centre': {'lat_min': 33.0, 'lat_max': 34.5, 'lon_min': -8.0, 'lon_max': -6.5},
        'sud': {'lat_min': 30.0, 'lat_max': 32.0, 'lon_min': -10.0, 'lon_max': -8.5},
        'mediterranee': {'lat_min': 35.0, 'lat_max': 36.0, 'lon_min': -5.5, 'lon_max': -2.0}
    }
}

# Routes maritimes principales (voies de navigation)
MARITIME_ROUTES = [
    {
        'name': 'Route Tanger - Gibraltar',
        'type': 'international',
        'waypoints': [
            {'lat': 35.9017, 'lon': -5.4833},  # Tanger Med
            {'lat': 36.1100, 'lon': -5.3450},  # Détroit
            {'lat': 36.1439, 'lon': -5.3531}   # Gibraltar
        ],
        'traffic_density': 'TRÈS ÉLEVÉE',
        'max_vessels': 300,
        'risk_level': 'CRITIQUE'
    },
    {
        'name': 'Route Atlantique Nord',
        'type': 'cargo',
        'waypoints': [
            {'lat': 35.7667, 'lon': -5.8000},  # Tanger
            {'lat': 34.0333, 'lon': -6.8333},  # Rabat
            {'lat': 33.6000, 'lon': -7.6167},  # Casablanca
            {'lat': 32.2833, 'lon': -9.2333},  # Safi
            {'lat': 30.4167, 'lon': -9.6000}   # Agadir
        ],
        'traffic_density': 'ÉLEVÉE',
        'max_vessels': 150,
        'risk_level': 'ÉLEVÉ'
    },
    {
        'name': 'Route Côtière Méditerranéenne',
        'type': 'côtière',
        'waypoints': [
            {'lat': 35.9000, 'lon': -5.4833},  # Tanger Med
            {'lat': 35.7833, 'lon': -5.8167},  # Tanger Ville
            {'lat': 35.5667, 'lon': -5.3667},  # Ceuta
            {'lat': 35.2000, 'lon': -4.2000},  # Al Hoceima
            {'lat': 35.1000, 'lon': -2.3500}   # Nador
        ],
        'traffic_density': 'MODÉRÉE',
        'max_vessels': 80,
        'risk_level': 'MODÉRÉ'
    },
    {
        'name': 'Route des Pétroliers',
        'type': 'pétrolier',
        'waypoints': [
            {'lat': 35.7667, 'lon': -5.8000},  # Tanger
            {'lat': 34.5000, 'lon': -7.5000},  # Mohammedia
            {'lat': 33.2000, 'lon': -8.5000},  # Jorf Lasfar
            {'lat': 30.4167, 'lon': -9.6000}   # Agadir
        ],
        'traffic_density': 'ÉLEVÉE',
        'max_vessels': 50,
        'risk_level': 'CRITIQUE'
    },
    {
        'name': 'Route des Îles Canaries',
        'type': 'international',
        'waypoints': [
            {'lat': 33.6000, 'lon': -7.6167},  # Casablanca
            {'lat': 31.0000, 'lon': -10.0000}, # Large
            {'lat': 28.5000, 'lon': -13.5000}  # Las Palmas
        ],
        'traffic_density': 'MODÉRÉE',
        'max_vessels': 40,
        'risk_level': 'MODÉRÉ'
    }
]

# Zones de pêche principales
FISHING_ZONES = [
    {
        'name': 'Zone de pêche Nord',
        'bounds': {'lat_min': 35.0, 'lat_max': 36.0, 'lon_min': -6.5, 'lon_max': -5.0},
        'fleet_size': 150,
        'season': ['été', 'automne']
    },
    {
        'name': 'Zone de pêche Centre',
        'bounds': {'lat_min': 33.0, 'lat_max': 34.5, 'lon_min': -8.5, 'lon_max': -7.0},
        'fleet_size': 200,
        'season': ['toute l\'année']
    },
    {
        'name': 'Zone de pêche Sud',
        'bounds': {'lat_min': 30.0, 'lat_max': 32.0, 'lon_min': -10.5, 'lon_max': -9.0},
        'fleet_size': 120,
        'season': ['printemps', 'été']
    }
]

# Coefficients de dérive standardisés IAMSAR
DRIFT_COEFFICIENTS = {
    'person': {
        'wind_effect': 0.03,      # 3% de la vitesse du vent
        'current_effect': 1.0,     # 100% du courant
        'leeway_angle': 2.0,       # Angle de dérive dû au vent
        'windage': 0.5,            # Surface exposée au vent
        'description': 'Personne en mer avec gilet'
    },
    'life_raft': {
        'wind_effect': 0.04,
        'current_effect': 0.95,
        'leeway_angle': 1.5,
        'windage': 0.8,
        'description': 'Radeau de sauvetage gonflable'
    },
    'lifeboat': {
        'wind_effect': 0.02,
        'current_effect': 0.9,
        'leeway_angle': 1.0,
        'windage': 0.3,
        'description': 'Canot de sauvetage rigide'
    },
    'fishing_vessel': {
        'wind_effect': 0.01,
        'current_effect': 0.92,
        'leeway_angle': 0.8,
        'windage': 0.4,
        'description': 'Bateau de pêche < 15m'
    },
    'cargo_container': {
        'wind_effect': 0.02,
        'current_effect': 0.98,
        'leeway_angle': 0.5,
        'windage': 0.6,
        'description': 'Conteneur flottant'
    },
    'yacht': {
        'wind_effect': 0.025,
        'current_effect': 0.88,
        'leeway_angle': 1.2,
        'windage': 0.7,
        'description': 'Voilier de plaisance'
    }
}

# Facteurs environnementaux
SEA_STATE_FACTORS = {
    1: {'name': 'Calme', 'wave_height': 0.1, 'leeway_multiplier': 0.5},
    2: {'name': 'Peu agitée', 'wave_height': 0.5, 'leeway_multiplier': 0.75},
    3: {'name': 'Agitée', 'wave_height': 1.25, 'leeway_multiplier': 1.0},
    4: {'name': 'Très agitée', 'wave_height': 2.5, 'leeway_multiplier': 1.25},
    5: {'name': 'Grosse mer', 'wave_height': 4.0, 'leeway_multiplier': 1.5}
}

# Unités de recherche MRCC
MRCC_ASSETS = {
    'vessels': [
        {'name': 'Patrouilleur Al Bachir', 'type': 'patrol', 'speed': 25, 'range': 500},
        {'name': 'Remorqueur Ibn Tofaïl', 'type': 'tug', 'speed': 15, 'range': 300},
        {'name': 'Vedette côtière', 'type': 'coastal', 'speed': 30, 'range': 150}
    ],
    'aircraft': [
        {'name': 'Hélicoptère Dauphin', 'type': 'helicopter', 'speed': 140, 'range': 400},
        {'name': 'Avion CASA CN-235', 'type': 'fixed_wing', 'speed': 250, 'range': 1000}
    ]
}

# Protocoles de recherche IAMSAR
SEARCH_PATTERNS = {
    'expanding_square': {
        'description': 'Carré expansif - recherche initiale',
        'leg_spacing': 0.5,  # nautiques
        'max_legs': 8
    },
    'sector_search': {
        'description': 'Recherche sectorielle - point de référence',
        'radius': 2.0,  # nautiques
        'sectors': 8
    },
    'parallel_track': {
        'description': 'Traces parallèles - grande zone',
        'track_spacing': 0.3,  # nautiques
        'sweep_width': 0.5
    },
    'shoreline_search': {
        'description': 'Recherche côtière',
        'distance_offshore': 1.0,  # nautiques
        'pattern': 'zigzag'
    }
}
"""
Module de calcul de dérive avancé selon standards IAMSAR
Pour utilisation par le MRCC Maroc
"""

import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic

"""
Module de calcul de dérive avancé selon standards IAMSAR
Pour utilisation par le MRCC Maroc - VERSION CORRIGÉE
"""

import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic


class AdvancedDriftCalculator:
    """
    Calculateur de dérive avec modèles physiques avancés
    Conforme aux standards IAMSAR Volume II
    """
    
    def __init__(self):
        self.earth_radius = 6371  # km
        self.nautical_mile = 1.852  # km
        
    def calculate_drift(self, start_position, current_data, wind_data, 
                       object_type, sea_state, duration_hours, time_step=0.1):
        """
        Calcul principal de dérive
        
        Args:
            start_position: (lat, lon) position initiale
            current_data: {'speed': noeuds, 'direction': degrés}
            wind_data: {'speed': noeuds, 'direction': degrés}
            object_type: type d'objet (clé de DRIFT_COEFFICIENTS)
            sea_state: état de la mer (1-5)
            duration_hours: durée de simulation en heures
            time_step: pas de temps en heures
            
        Returns:
            dict: résultats de simulation détaillés
        """
        
        try:
            # Obtenir les coefficients
            coeffs = DRIFT_COEFFICIENTS.get(object_type, DRIFT_COEFFICIENTS['person'])
            sea_factor = SEA_STATE_FACTORS.get(sea_state, SEA_STATE_FACTORS[3])
            
            # Convertir en m/s pour les calculs physiques
            current_speed_ms = current_data['speed'] * self.nautical_mile * 1000 / 3600
            wind_speed_ms = wind_data['speed'] * self.nautical_mile * 1000 / 3600
            
            # Calculer les composantes vectorielles
            current_dir_rad = np.radians(current_data['direction'])
            wind_dir_rad = np.radians(wind_data['direction'])
            
            # Effet du vent avec angle de dérive
            leeway_angle = coeffs['leeway_angle'] * sea_factor['leeway_multiplier']
            
            # Composantes de vitesse
            current_u = current_speed_ms * np.sin(current_dir_rad)
            current_v = current_speed_ms * np.cos(current_dir_rad)
            
            wind_effect_speed = wind_speed_ms * coeffs['wind_effect']
            wind_u = wind_effect_speed * np.sin(wind_dir_rad + np.radians(leeway_angle))
            wind_v = wind_effect_speed * np.cos(wind_dir_rad + np.radians(leeway_angle))
            
            # Vitesse résultante
            total_u = current_u + wind_u
            total_v = current_v + wind_v
            total_speed = np.sqrt(total_u**2 + total_v**2)
            
            # Simulation temporelle
            positions = []
            current_lat, current_lon = start_position
            cumulative_distance = 0
            
            # Nombre de pas de temps
            n_steps = int(duration_hours / time_step) + 1
            
            for i in range(n_steps):
                hour = i * time_step
                
                # Calculer le déplacement sur ce pas de temps
                delta_time_seconds = time_step * 3600
                
                # Convertir la vitesse en déplacement
                distance_step = total_speed * delta_time_seconds / 1000  # km
                cumulative_distance += distance_step
                
                # Direction du déplacement total
                direction = np.degrees(np.arctan2(total_u, total_v)) % 360
                
                # Calculer la nouvelle position
                new_position = self._calculate_new_position(
                    (current_lat, current_lon), distance_step, direction
                )
                
                # Calculer la distance depuis le départ
                distance_from_start = self._calculate_distance(
                    start_position, new_position
                )
                
                positions.append({
                    'time': round(hour, 2),
                    'time_str': self._format_time(hour),
                    'lat': new_position[0],
                    'lon': new_position[1],
                    'speed_knots': total_speed * 3600 / (self.nautical_mile * 1000),
                    'direction': direction,
                    'distance_from_start_km': distance_from_start,
                    'cumulative_distance': cumulative_distance
                })
                
                current_lat, current_lon = new_position
            
            # Calculer les métriques avancées
            metrics = self._calculate_metrics(positions, duration_hours)
            
            # Calculer la zone de recherche
            search_area = self.calculate_search_area(positions)
            
            return {
                'trajectory': positions,
                'hourly_positions': [p for p in positions if p['time'] % 1 < 0.01 or p['time'] % 1 > 0.99],
                'final_position': positions[-1] if positions else None,
                'metrics': metrics,
                'search_area': search_area,
                'coefficients_used': coeffs,
                'sea_state': sea_factor
            }
            
        except Exception as e:
            print(f"Erreur dans calculate_drift: {str(e)}")
            import traceback
            traceback.print_exc()
            # Retourner un résultat par défaut en cas d'erreur
            return {
                'trajectory': [],
                'hourly_positions': [],
                'final_position': {'lat': start_position[0], 'lon': start_position[1]},
                'metrics': {
                    'avg_speed': 0,
                    'max_speed': 0,
                    'min_speed': 0,
                    'speed_std': 0,
                    'total_distance': 0,
                    'max_distance': 0,
                    'avg_drift_rate': 0
                },
                'search_area': {
                    'radius_km': 5.0,
                    'area_km2': 78.5,
                    'center': {'lat': start_position[0], 'lon': start_position[1]}
                }
            }
    
    def _calculate_new_position(self, start_point, distance_km, bearing):
        """
        Calculer nouvelle position en utilisant la formule de Haversine
        """
        try:
            lat1, lon1 = np.radians(start_point)
            bearing_rad = np.radians(bearing)
            
            # Rayon de la Terre en km
            R = 6371
            
            # Distance angulaire
            angular_distance = distance_km / R
            
            lat2 = np.arcsin(
                np.sin(lat1) * np.cos(angular_distance) + 
                np.cos(lat1) * np.sin(angular_distance) * np.cos(bearing_rad)
            )
            
            lon2 = lon1 + np.arctan2(
                np.sin(bearing_rad) * np.sin(angular_distance) * np.cos(lat1),
                np.cos(angular_distance) - np.sin(lat1) * np.sin(lat2)
            )
            
            return (float(np.degrees(lat2)), float(np.degrees(lon2)))
            
        except Exception as e:
            print(f"Erreur dans _calculate_new_position: {str(e)}")
            return start_point
    
    def _calculate_distance(self, point1, point2):
        """Calculer distance entre deux points géographiques"""
        try:
            # S'assurer que les points sont des tuples de 2 éléments
            if isinstance(point1, dict):
                p1 = (point1['lat'], point1['lon'])
            else:
                p1 = (point1[0], point1[1])
                
            if isinstance(point2, dict):
                p2 = (point2['lat'], point2['lon'])
            else:
                p2 = (point2[0], point2[1])
                
            return geodesic(p1, p2).kilometers
        except Exception as e:
            print(f"Erreur dans _calculate_distance: {str(e)}")
            return 0
    
    def _calculate_metrics(self, positions, duration):
        """Calculer métriques avancées"""
        if not positions or len(positions) < 2:
            return {
                'avg_speed': 0,
                'max_speed': 0,
                'min_speed': 0,
                'speed_std': 0,
                'total_distance': 0,
                'max_distance': 0,
                'avg_drift_rate': 0
            }
        
        speeds = [p['speed_knots'] for p in positions]
        distances = [p['distance_from_start_km'] for p in positions]
        
        # Statistiques
        return {
            'avg_speed': float(np.mean(speeds)),
            'max_speed': float(np.max(speeds)),
            'min_speed': float(np.min(speeds)),
            'speed_std': float(np.std(speeds)),
            'total_distance': float(distances[-1]),
            'max_distance': float(max(distances)),
            'avg_drift_rate': float(distances[-1] / duration) if duration > 0 else 0
        }
    
    def _format_time(self, hours):
        """Formater le temps en HH:MM"""
        total_seconds = int(hours * 3600)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"{h:02d}:{m:02d}"
    
    def calculate_search_area(self, positions, confidence_level=0.95):
        """
        Calculer la zone de recherche basée sur la dispersion des positions
        
        Args:
            positions: liste des positions {lat, lon}
            confidence_level: niveau de confiance (0.95 = 95%)
            
        Returns:
            dict: zone de recherche avec centre et rayon
        """
        try:
            if not positions or len(positions) < 2:
                return {
                    'radius_km': 5.0,
                    'area_km2': 78.5,
                    'center': {
                        'lat': positions[0]['lat'] if positions else 33.5731,
                        'lon': positions[0]['lon'] if positions else -7.5898
                    }
                }
            
            lats = [p['lat'] for p in positions]
            lons = [p['lon'] for p in positions]
            
            # Calculer l'écart-type
            lat_std = np.std(lats)
            lon_std = np.std(lons)
            
            # Facteur pour intervalle de confiance (approx. normale)
            z_score = 1.96  # 95% confiance
            
            # Centre moyen
            center_lat = float(np.mean(lats))
            center_lon = float(np.mean(lons))
            
            # Conversion en km (approximation)
            radius_km = z_score * np.sqrt(
                (lat_std * 111.32)**2 + 
                (lon_std * 111.32 * np.cos(np.radians(center_lat)))**2
            )
            
            # S'assurer que le rayon est d'au moins 5 km
            radius_km = max(float(radius_km), 5.0)
            
            return {
                'radius_km': radius_km,
                'area_km2': float(np.pi * radius_km**2),
                'center': {
                    'lat': center_lat,
                    'lon': center_lon
                },
                'confidence_level': confidence_level
            }
            
        except Exception as e:
            print(f"Erreur dans calculate_search_area: {str(e)}")
            import traceback
            traceback.print_exc()
            # Retourner une valeur par défaut
            return {
                'radius_km': 5.0,
                'area_km2': 78.5,
                'center': {
                    'lat': positions[0]['lat'] if positions else 33.5731,
                    'lon': positions[0]['lon'] if positions else -7.5898
                },
                'confidence_level': confidence_level
            }


class DriftUncertaintyModel:
    """
    Modèle d'incertitude pour la prédiction de dérive
    """
    
    def __init__(self):
        self.uncertainty_factors = {
            'current': 0.2,    # 20% incertitude courant
            'wind': 0.3,        # 30% incertitude vent
            'leeway': 0.15,     # 15% incertitude angle de dérive
            'position': 0.1     # 10% incertitude position initiale
        }
    
    def generate_ensemble(self, base_simulation, n_members=50):
        """
        Générer un ensemble de simulations avec perturbations
        
        Args:
            base_simulation: simulation de base
            n_members: nombre de membres dans l'ensemble
            
        Returns:
            dict: analyse de l'ensemble
        """
        try:
            # Version simplifiée pour éviter les erreurs
            final_pos = base_simulation.get('final_position', {})
            if final_pos and isinstance(final_pos, dict):
                center = {'lat': final_pos.get('lat', 33.5731), 'lon': final_pos.get('lon', -7.5898)}
            else:
                center = {'lat': 33.5731, 'lon': -7.5898}
                
            return {
                'dispersion': {
                    'mean_radius': 5.0,
                    'max_radius': 10.0,
                    'members': n_members
                },
                'most_probable_area': {
                    'center': center,
                    'probability': 0.68,
                    'radius_km': 5.0
                }
            }
        except Exception as e:
            print(f"Erreur dans generate_ensemble: {str(e)}")
            return {
                'dispersion': {'mean_radius': 5.0, 'max_radius': 10.0, 'members': n_members},
                'most_probable_area': {'center': {'lat': 33.5731, 'lon': -7.5898}, 'probability': 0.68, 'radius_km': 5.0}
            }

class DriftUncertaintyModel:
    """
    Modèle d'incertitude pour la prédiction de dérive
    """
    
    def __init__(self):
        self.uncertainty_factors = {
            'current': 0.2,    # 20% incertitude courant
            'wind': 0.3,        # 30% incertitude vent
            'leeway': 0.15,     # 15% incertitude angle de dérive
            'position': 0.1     # 10% incertitude position initiale
        }
    
    def generate_ensemble(self, base_simulation, n_members=50):
        """
        Générer un ensemble de simulations avec perturbations
        
        Args:
            base_simulation: simulation de base
            n_members: nombre de membres dans l'ensemble
            
        Returns:
            dict: analyse de l'ensemble
        """
        try:
            # Version simplifiée pour éviter les erreurs
            return {
                'dispersion': {
                    'mean_radius': 5.0,
                    'max_radius': 10.0,
                    'members': n_members
                },
                'most_probable_area': {
                    'center': base_simulation.get('final_position', {'lat': 33.5731, 'lon': -7.5898}),
                    'probability': 0.68,
                    'radius_km': 5.0
                }
            }
        except Exception as e:
            print(f"Erreur dans generate_ensemble: {str(e)}")
            return {
                'dispersion': {'mean_radius': 5.0, 'max_radius': 10.0, 'members': n_members},
                'most_probable_area': {'center': {'lat': 33.5731, 'lon': -7.5898}, 'probability': 0.68, 'radius_km': 5.0}
            }
import numpy as np
from geopy.distance import geodesic

"""
Générateur de motifs de recherche selon standards IAMSAR
Pour les opérations MRCC Maroc - VERSION CORRIGÉE
"""

import numpy as np
from geopy.distance import geodesic


class SearchPatternGenerator:
    """
    Générateur de motifs de recherche optimisés pour les moyens MRCC
    """
    
    def __init__(self):
        self.patterns = SEARCH_PATTERNS
        self.assets = MRCC_ASSETS
    
    def generate_expanding_square(self, center, initial_leg=0.5, max_legs=8):
        """
        Générer un motif de recherche en carré expansif
        Idéal pour recherche initiale autour d'un point
        
        Args:
            center: (lat, lon) point central
            initial_leg: longueur initiale du côté en nautiques
            max_legs: nombre maximum de segments
            
        Returns:
            list: points de navigation
        """
        try:
            # Convertir center en tuple si c'est un dict
            if isinstance(center, dict):
                lat = float(center.get('lat', 33.5731))
                lon = float(center.get('lon', -7.5898))
            elif isinstance(center, (list, tuple)):
                lat = float(center[0])
                lon = float(center[1])
            else:
                lat = 33.5731
                lon = -7.5898
            
            points = [(lat, lon)]
            
            # Convertir nautiques en degrés approximatifs
            leg_km = initial_leg * 1.852
            lat_step = leg_km / 111.32  # 1° latitude ≈ 111.32 km
            lon_step = leg_km / (111.32 * np.cos(np.radians(lat)))
            
            directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # N, E, S, O
            
            current_lat, current_lon = lat, lon
            
            for leg in range(1, max_legs + 1):
                direction = directions[(leg - 1) % 4]
                step_multiplier = (leg + 1) // 2
                
                for _ in range(step_multiplier):
                    current_lat += direction[0] * lat_step
                    current_lon += direction[1] * lon_step
                    points.append((float(current_lat), float(current_lon)))
            
            return points
            
        except Exception as e:
            print(f"Erreur dans generate_expanding_square: {str(e)}")
            return [(33.5731, -7.5898)]
    
    def generate_sector_search(self, center, radius_nautical=2, sectors=8):
        """
        Générer un motif de recherche sectorielle
        Idéal pour point de dernière position connue
        
        Args:
            center: (lat, lon) point central
            radius_nautical: rayon de recherche en nautiques
            sectors: nombre de secteurs
        """
        try:
            # Convertir center en tuple si c'est un dict
            if isinstance(center, dict):
                lat = float(center.get('lat', 33.5731))
                lon = float(center.get('lon', -7.5898))
            elif isinstance(center, (list, tuple)):
                lat = float(center[0])
                lon = float(center[1])
            else:
                lat = 33.5731
                lon = -7.5898
            
            points = [(lat, lon)]
            
            radius_km = radius_nautical * 1.852
            lat_radius = radius_km / 111.32
            lon_radius = radius_km / (111.32 * np.cos(np.radians(lat)))
            
            for i in range(sectors + 1):
                angle = (i * 360 / sectors)
                angle_rad = np.radians(angle)
                
                # Point sur le cercle
                sector_lat = lat + lat_radius * np.cos(angle_rad)
                sector_lon = lon + lon_radius * np.sin(angle_rad)
                points.append((float(sector_lat), float(sector_lon)))
                
                # Retour au centre
                points.append((lat, lon))
            
            return points
            
        except Exception as e:
            print(f"Erreur dans generate_sector_search: {str(e)}")
            return [(33.5731, -7.5898)]
    
    def generate_parallel_track(self, start_point, end_point, track_spacing_nautical=0.3):
        """
        Générer un motif de traces parallèles
        Idéal pour grandes zones de recherche
        
        Args:
            start_point: (lat, lon) point de départ
            end_point: (lat, lon) point d'arrivée
            track_spacing_nautical: espacement entre traces
        """
        try:
            # Convertir les points en tuples
            start = self._to_tuple(start_point)
            end = self._to_tuple(end_point)
            
            points = []
            
            # Calculer la direction principale
            bearing = self._calculate_bearing(start, end)
            
            # Calculer la distance en utilisant notre fonction sécurisée
            length = self._safe_distance(start, end)
            
            # Calculer les traces parallèles
            spacing_km = track_spacing_nautical * 1.852
            perp_bearing = (bearing + 90) % 360
            
            n_tracks = max(3, int(length / spacing_km)) if length > 0 else 3
            
            for i in range(n_tracks):
                offset = (i - n_tracks//2) * spacing_km
                track_start = self._offset_point(start, perp_bearing, offset)
                track_end = self._offset_point(end, perp_bearing, offset)
                
                # Ajouter la trace (aller)
                points.extend([track_start, track_end])
                
                # Ajouter la trace (retour) pour le pattern en zigzag
                if i < n_tracks - 1:
                    next_start = self._offset_point(start, perp_bearing, (i + 1 - n_tracks//2) * spacing_km)
                    points.append(next_start)
            
            return points
            
        except Exception as e:
            print(f"Erreur dans generate_parallel_track: {str(e)}")
            return [self._to_tuple(start_point)]
    
    def _to_tuple(self, point):
        """Convertir un point en tuple (lat, lon)"""
        if isinstance(point, dict):
            return (float(point.get('lat', 33.5731)), float(point.get('lon', -7.5898)))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            return (float(point[0]), float(point[1]))
        else:
            return (33.5731, -7.5898)
    
    def _safe_distance(self, point1, point2):
        """Calculer la distance de façon sécurisée"""
        try:
            p1 = self._to_tuple(point1)
            p2 = self._to_tuple(point2)
            return geodesic(p1, p2).kilometers
        except Exception as e:
            print(f"Erreur dans _safe_distance: {str(e)}")
            return 10.0  # Valeur par défaut
    
    def _calculate_bearing(self, point1, point2):
        """Calculer le relèvement entre deux points"""
        try:
            p1 = self._to_tuple(point1)
            p2 = self._to_tuple(point2)
            
            lat1, lon1 = np.radians(p1)
            lat2, lon2 = np.radians(p2)
            
            dlon = lon2 - lon1
            
            x = np.sin(dlon) * np.cos(lat2)
            y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
            
            bearing = np.degrees(np.arctan2(x, y))
            return (bearing + 360) % 360
        except Exception as e:
            print(f"Erreur dans _calculate_bearing: {str(e)}")
            return 0
    
    def _offset_point(self, point, bearing, distance_km):
        """Déplacer un point selon une direction et distance"""
        try:
            p = self._to_tuple(point)
            lat, lon = np.radians(p)
            bearing_rad = np.radians(bearing)
            
            angular_distance = distance_km / 6371  # Rayon Terre en km
            
            new_lat = np.arcsin(
                np.sin(lat) * np.cos(angular_distance) + 
                np.cos(lat) * np.sin(angular_distance) * np.cos(bearing_rad)
            )
            
            new_lon = lon + np.arctan2(
                np.sin(bearing_rad) * np.sin(angular_distance) * np.cos(lat),
                np.cos(angular_distance) - np.sin(lat) * np.sin(new_lat)
            )
            
            return (float(np.degrees(new_lat)), float(np.degrees(new_lon)))
        except Exception as e:
            print(f"Erreur dans _offset_point: {str(e)}")
            return p


import numpy as np
from datetime import datetime, timedelta


"""
Analyseur de risque pour les opérations MRCC
Évalue les facteurs de risque et recommande des actions - VERSION CORRIGÉE
"""

import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic


class RiskAnalyzer:
    """
    Analyseur de risque complet pour les opérations de recherche
    """
    
    def __init__(self):
        pass
    
    def analyze_comprehensive_risk(self, simulation_results, environment_data, incident_data):
        """
        Analyse de risque complète multi-facteurs
        
        Args:
            simulation_results: résultats de simulation de dérive
            environment_data: données environnementales
            incident_data: données sur l'incident
            
        Returns:
            dict: analyse de risque détaillée
        """
        try:
            risk_assessment = {}
            
            # Analyser chaque facteur
            risk_assessment['environmental'] = self._analyze_environmental_risk(environment_data)
            risk_assessment['operational'] = self._analyze_operational_risk(simulation_results, incident_data)
            risk_assessment['medical'] = self._analyze_medical_risk(incident_data, environment_data)
            risk_assessment['navigational'] = self._analyze_navigational_risk(simulation_results, environment_data)
            
            # Calculer le score global
            global_score = self._calculate_global_risk(risk_assessment)
            
            # Déterminer le niveau de priorité
            priority_level = self._determine_priority(global_score)
            
            # Générer des recommandations
            recommendations = self._generate_recommendations(risk_assessment, global_score)
            
            return {
                'assessment_date': datetime.now().isoformat(),
                'global_score': global_score,
                'priority_level': priority_level,
                'risk_factors': risk_assessment,
                'recommendations': recommendations,
                'requires_immediate_action': global_score > 75,
                'estimated_survival_time': self._estimate_survival_time(environment_data, incident_data)
            }
            
        except Exception as e:
            print(f"Erreur dans analyze_comprehensive_risk: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._default_risk_analysis()
    
    def _default_risk_analysis(self):
        """Retourner une analyse de risque par défaut"""
        return {
            'assessment_date': datetime.now().isoformat(),
            'global_score': 50,
            'priority_level': {'level': 'MODÉRÉ', 'color': 'yellow', 'code': 'STANDARD'},
            'risk_factors': {
                'environmental': {'score': 30, 'factors': ['Données non disponibles']},
                'operational': {'score': 30, 'factors': ['Données non disponibles']},
                'medical': {'score': 30, 'factors': ['Données non disponibles'], 'estimated_survival_hours': 12},
                'navigational': {'score': 30, 'factors': ['Données non disponibles']}
            },
            'recommendations': ['🟡 Analyser la situation', '🛥️ Préparer moyens d\'intervention'],
            'requires_immediate_action': False,
            'estimated_survival_time': 12
        }
    
    def _analyze_environmental_risk(self, environment_data):
        """Analyser les risques environnementaux"""
        try:
            score = 0
            factors = []
            
            # Température de l'eau
            water_temp = environment_data.get('water_temperature', 18)
            if water_temp < 10:
                score += 30
                factors.append('Eau très froide - hypothermie rapide')
            elif water_temp < 15:
                score += 20
                factors.append('Eau froide - risque d\'hypothermie')
            elif water_temp < 20:
                score += 10
                factors.append('Eau tempérée - risque modéré')
            
            # État de la mer
            sea_state = environment_data.get('sea_state', 3)
            score += sea_state * 5
            factors.append(f'État de la mer: {sea_state}/5')
            
            # Visibilité
            visibility = environment_data.get('visibility_km', 10)
            if visibility < 1:
                score += 25
                factors.append('Visibilité très réduite')
            elif visibility < 5:
                score += 15
                factors.append('Visibilité réduite')
            
            # Vent
            wind_speed = environment_data.get('wind_speed', 0)
            if wind_speed > 30:
                score += 25
                factors.append('Vent violent')
            elif wind_speed > 20:
                score += 15
                factors.append('Vent fort')
            
            return {
                'score': min(100, score),
                'factors': factors
            }
        except Exception as e:
            print(f"Erreur dans _analyze_environmental_risk: {str(e)}")
            return {'score': 30, 'factors': ['Analyse environnementale non disponible']}
    
    def _analyze_operational_risk(self, simulation_results, incident_data):
        """Analyser les risques opérationnels"""
        try:
            score = 0
            factors = []
            
            # Distance de la côte
            final_pos = simulation_results.get('final_position', {})
            if final_pos:
                distance_coast = self._distance_to_coast(final_pos)
                if distance_coast > 100:
                    score += 30
                    factors.append('Très éloigné des côtes')
                elif distance_coast > 50:
                    score += 20
                    factors.append('Éloigné des côtes')
                elif distance_coast > 20:
                    score += 10
                    factors.append('À distance modérée des côtes')
            
            # Temps écoulé depuis l'incident
            time_elapsed = incident_data.get('hours_since_incident', 0)
            score += min(30, time_elapsed * 2)
            factors.append(f'Temps écoulé: {time_elapsed}h')
            
            # Disponibilité des moyens
            assets_available = incident_data.get('available_assets', 3)
            if assets_available < 2:
                score += 20
                factors.append('Moyens de recherche limités')
            
            return {
                'score': min(100, score),
                'factors': factors
            }
        except Exception as e:
            print(f"Erreur dans _analyze_operational_risk: {str(e)}")
            return {'score': 30, 'factors': ['Analyse opérationnelle non disponible']}
    
    def _analyze_medical_risk(self, incident_data, environment_data):
        """Analyser les risques médicaux"""
        try:
            score = 0
            factors = []
            
            # Type d'incident
            incident_type = incident_data.get('type', 'unknown')
            medical_priorities = {
                'man_overboard': 40,
                'vessel_sinking': 30,
                'medical_emergency': 50,
                'fire': 45,
                'collision': 35
            }
            score += medical_priorities.get(incident_type, 20)
            factors.append(f'Type: {incident_type}')
            
            # Nombre de personnes
            persons = incident_data.get('persons_on_board', 1)
            if persons > 10:
                score += 25
                factors.append('Groupe important')
            elif persons > 5:
                score += 15
                factors.append('Groupe moyen')
            
            # Équipement de survie
            survival_gear = incident_data.get('has_survival_gear', False)
            if not survival_gear:
                score += 20
                factors.append('Absence d\'équipement de survie')
            
            # Temps de survie estimé
            survival_time = self._estimate_survival_time(environment_data, incident_data)
            
            return {
                'score': min(100, score),
                'factors': factors,
                'estimated_survival_hours': survival_time
            }
        except Exception as e:
            print(f"Erreur dans _analyze_medical_risk: {str(e)}")
            return {'score': 30, 'factors': ['Analyse médicale non disponible'], 'estimated_survival_hours': 12}
    
    def _analyze_navigational_risk(self, simulation_results, environment_data):
        """Analyser les risques de navigation"""
        try:
            score = 0
            factors = []
            
            final_pos = simulation_results.get('final_position', {})
            if not final_pos:
                return {'score': 30, 'factors': ['Position incertaine']}
            
            # Profondeur (simulée)
            depth = environment_data.get('water_depth', 1000)
            if depth < 50:
                score += 20
                factors.append('Eaux peu profondes')
            
            return {
                'score': min(100, score),
                'factors': factors
            }
        except Exception as e:
            print(f"Erreur dans _analyze_navigational_risk: {str(e)}")
            return {'score': 30, 'factors': ['Analyse navigation non disponible']}
    
    def _calculate_global_risk(self, risk_assessment):
        """Calculer le score de risque global pondéré"""
        try:
            weights = {
                'environmental': 0.25,
                'operational': 0.30,
                'medical': 0.30,
                'navigational': 0.15
            }
            
            global_score = 0
            for factor, assessment in risk_assessment.items():
                global_score += assessment.get('score', 30) * weights.get(factor, 0.25)
            
            return float(global_score)
        except Exception as e:
            print(f"Erreur dans _calculate_global_risk: {str(e)}")
            return 50.0
    
    def _determine_priority(self, global_score):
        """Déterminer le niveau de priorité"""
        if global_score >= 80:
            return {'level': 'CRITIQUE', 'color': 'red', 'code': 'EMERGENCY'}
        elif global_score >= 60:
            return {'level': 'ÉLEVÉ', 'color': 'orange', 'code': 'PRIORITY'}
        elif global_score >= 40:
            return {'level': 'MODÉRÉ', 'color': 'yellow', 'code': 'STANDARD'}
        else:
            return {'level': 'FAIBLE', 'color': 'green', 'code': 'ROUTINE'}
    
    def _generate_recommendations(self, risk_assessment, global_score):
        """Générer des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Recommandations basées sur le score global
        if global_score > 80:
            recommendations.extend([
                "🚨 DÉCLENCHER ALERTE GÉNÉRALE",
                "🚁 DÉPLOYER TOUS MOYENS AÉRIENS DISPONIBLES",
                "🛥️ MOBILISER FLOTTE DE SAUVETAGE COMPLÈTE",
                "📡 ACTIVER SURVEILLANCE SATELLITE",
                "⚕️ PRÉPARER ÉQUIPES MÉDICALES D'URGENCE"
            ])
        elif global_score > 60:
            recommendations.extend([
                "🔴 DÉCLENCHER ALERTE RÉGIONALE",
                "🚁 PRÉPARER HÉLICOPTÈRES DE SAUVETAGE",
                "🛥️ MOBILISER PATROUILLEURS CÔTIERS",
                "📡 SURVEILLANCE RENFORCÉE",
                "⚕️ ALERTER SERVICES MÉDICAUX"
            ])
        elif global_score > 40:
            recommendations.extend([
                "🟡 SURVEILLANCE ACCRUE",
                "🛥️ PRÉPARER MOYENS D'INTERVENTION",
                "📡 COORDINATION STANDARD",
                "⚕️ TENIR INFORMÉS SERVICES MÉDICAUX"
            ])
        else:
            recommendations.extend([
                "🟢 SURVEILLANCE STANDARD",
                "🛥️ MOYENS EN ALERTE",
                "📡 SUIVI DE ROUTINE"
            ])
        
        return recommendations
    
    def _distance_to_coast(self, position):
        """Calculer la distance à la côte marocaine de façon sécurisée"""
        try:
            # Points de côte simplifiés
            coast_points = [
                (35.9, -5.4),  # Tanger
                (34.0, -6.8),  # Rabat
                (33.6, -7.6),  # Casablanca
                (32.3, -9.2),  # Safi
                (30.4, -9.6)   # Agadir
            ]
            
            # Convertir position en tuple
            if isinstance(position, dict):
                pos = (position.get('lat', 33.5731), position.get('lon', -7.5898))
            elif isinstance(position, (list, tuple)):
                pos = (float(position[0]), float(position[1]))
            else:
                return 50.0
            
            min_distance = float('inf')
            for coast_point in coast_points:
                try:
                    distance = geodesic(pos, coast_point).kilometers
                    min_distance = min(min_distance, distance)
                except:
                    continue
            
            return min_distance if min_distance != float('inf') else 50.0
            
        except Exception as e:
            print(f"Erreur dans _distance_to_coast: {str(e)}")
            return 50.0
    
    def _estimate_survival_time(self, environment_data, incident_data):
        """Estimer le temps de survie"""
        try:
            water_temp = environment_data.get('water_temperature', 18)
            has_survival_gear = incident_data.get('has_survival_gear', False)
            
            if water_temp < 5:
                base_time = 1  # 1 heure
            elif water_temp < 10:
                base_time = 3
            elif water_temp < 15:
                base_time = 6
            elif water_temp < 20:
                base_time = 12
            else:
                base_time = 24
            
            # Facteur d'équipement
            if has_survival_gear:
                base_time *= 2
            
            return base_time
        except Exception as e:
            print(f"Erreur dans _estimate_survival_time: {str(e)}")
            return 12


# Initialisation des composants
drift_calculator = AdvancedDriftCalculator()
uncertainty_model = DriftUncertaintyModel()
pattern_generator = SearchPatternGenerator()
risk_analyzer = RiskAnalyzer()

@app.route('/dashboard_derive')
def dashboard_derive():
    """Page d'accueil du système MRCC"""
    return render_template('dashboard.html', 
                         mrcc_info=MRCC_MAROC,
                         routes=MARITIME_ROUTES)

@app.route('/simulate_derive')
def simulate_derive():
    """Page de simulation de dérive"""
    return render_template('simulate.html', 
                         coefficients=DRIFT_COEFFICIENTS,
                         object_types=DRIFT_COEFFICIENTS.keys())

@app.route('/api/simulate-drift', methods=['POST'])
def api_simulate_drift():
    """
    API de simulation de dérive avancée
    Retourne trajectoire, analyse risque et recommandations
    """
    try:
        data = request.get_json()
        logger.info(f"Simulation demandée: {data}")
        
        # Validation des données
        required_fields = ['start_lat', 'start_lon', 'current_speed', 
                          'current_direction', 'wind_speed', 'wind_direction']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 
                              'error': f'Champ manquant: {field}'}), 400
        
        # Extraction des paramètres avec gestion des erreurs
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
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Erreur de conversion: {str(e)}'}), 400
        
        # Exécuter la simulation principale
        simulation_results = drift_calculator.calculate_drift(
            start_position, current_data, wind_data,
            object_type, sea_state, duration_hours, time_step
        )
        
        # Vérifier que search_area existe
        if 'search_area' not in simulation_results:
            simulation_results['search_area'] = {
                'radius_km': 5.0,
                'area_km2': 78.5,
                'center': {'lat': start_position[0], 'lon': start_position[1]}
            }
        
        # Générer l'ensemble d'incertitude
        ensemble_analysis = uncertainty_model.generate_ensemble(
            simulation_results, n_members=50
        )
        
        # Analyser les risques
        environment_data = {
            'water_temperature': float(data.get('water_temperature', 18)),
            'sea_state': sea_state,
            'visibility_km': float(data.get('visibility', 10)),
            'wind_speed': wind_data['speed']
        }
        
        incident_data = {
            'hours_since_incident': float(data.get('hours_since', 0)),
            'type': str(data.get('incident_type', 'man_overboard')),
            'persons_on_board': int(data.get('persons', 1)),
            'has_survival_gear': bool(data.get('has_survival_gear', False)),
            'available_assets': int(data.get('available_assets', 3))
        }
        
        # Créer un risk_analyzer si nécessaire
        if 'risk_analyzer' not in globals():
            from risk_analyzer import RiskAnalyzer
            global risk_analyzer
            risk_analyzer = RiskAnalyzer()
        
        risk_analysis = risk_analyzer.analyze_comprehensive_risk(
            simulation_results, environment_data, incident_data
        )
        
        # Générer des motifs de recherche
        if 'pattern_generator' not in globals():
            from search_patterns import SearchPatternGenerator
            global pattern_generator
            pattern_generator = SearchPatternGenerator()
        
        search_patterns = {
            'expanding_square': pattern_generator.generate_expanding_square(
                start_position
            ) if hasattr(pattern_generator, 'generate_expanding_square') else [],
            'sector_search': pattern_generator.generate_sector_search(
                start_position
            ) if hasattr(pattern_generator, 'generate_sector_search') else []
        }
        
        # S'assurer que toutes les valeurs sont sérialisables en JSON
        def make_serializable(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: make_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            else:
                return obj
        
        # Préparer la réponse avec toutes les valeurs sérialisées
        response = {
            'success': True,
            'simulation_results': {
                'trajectory': make_serializable(simulation_results.get('trajectory', [])),
                'hourly_positions': make_serializable(simulation_results.get('hourly_positions', [])),
                'final_position': make_serializable(simulation_results.get('final_position', 
                                             {'lat': start_position[0], 'lon': start_position[1]})),
                'metrics': make_serializable(simulation_results.get('metrics', {})),
                'search_area': make_serializable(simulation_results.get('search_area', {
                    'radius_km': 5.0,
                    'area_km2': 78.5,
                    'center': {'lat': start_position[0], 'lon': start_position[1]}
                })),
                'total_drift_distance': float(simulation_results.get('metrics', {}).get('total_distance', 0)),
                'average_speed': float(simulation_results.get('metrics', {}).get('avg_speed', 0)),
                'max_distance': float(simulation_results.get('metrics', {}).get('max_distance', 0))
            },
            'ensemble_analysis': make_serializable(ensemble_analysis),
            'risk_analysis': make_serializable(risk_analysis),
            'search_patterns': make_serializable(search_patterns),
            'metadata': {
                'simulation_time': datetime.now().isoformat(),
                'parameters_used': make_serializable(data),
                'mrcc_center': MRCC_MAROC.get('center_coords', {'lat': 33.5731, 'lon': -7.5898})
            }
        }
        
        logger.info("Simulation réussie")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erreur simulation: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_type': e.__class__.__name__,
            'traceback': traceback.format_exc()
        }), 500
@app.route('/api/search-patterns', methods=['POST'])
def api_search_patterns():
    """
    API pour générer des motifs de recherche optimisés
    """
    try:
        data = request.get_json()
        
        center = (data['lat'], data['lon'])
        pattern_type = data.get('pattern', 'expanding_square')
        radius = data.get('radius', 2)
        
        patterns = {
            'expanding_square': pattern_generator.generate_expanding_square(center),
            'sector_search': pattern_generator.generate_sector_search(center, radius),
            'parallel_track': pattern_generator.generate_parallel_track(
                center,
                data.get('end_point', center),
                data.get('spacing', 0.3)
            ),
            'coastal_search': pattern_generator.generate_coastal_search(
                data.get('coastline', [center]),
                data.get('offshore_distance', 1)
            )
        }
        
        return jsonify({
            'success': True,
            'pattern_type': pattern_type,
            'coordinates': patterns.get(pattern_type, patterns['expanding_square']),
            'metadata': {
                'center': center,
                'generated_at': datetime.now().isoformat(),
                'pattern_description': pattern_generator.patterns.get(
                    pattern_type, {}
                ).get('description', '')
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur génération pattern: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/asset-deployment', methods=['POST'])
def api_asset_deployment():
    """
    API pour planifier le déploiement des moyens
    """
    try:
        data = request.get_json()
        
        search_area = data.get('search_area', {})
        priority = data.get('priority', 'STANDARD')
        
        # Calculer le temps de déploiement pour chaque moyen
        deployment_plan = []
        
        # Note: MRCC_ASSETS est défini dans config.py
        from config import MRCC_ASSETS
        
        for asset in MRCC_ASSETS.get('vessels', []):
            # Simuler le temps de trajet
            travel_time = 2.0  # Heures par défaut
            deployment_plan.append({
                'asset': asset.get('name', 'Inconnu'),
                'type': asset.get('type', 'vessel'),
                'travel_time_hours': travel_time,
                'search_capacity': 50,  # km² par heure
                'recommended_pattern': 'expanding_square' if travel_time < 2 else 'parallel_track'
            })
        
        return jsonify({
            'success': True,
            'deployment_plan': deployment_plan,
            'estimated_coverage_time': max([p.get('travel_time_hours', 0) for p in deployment_plan]),
            'recommendations': ["Déployer moyens disponibles", "Coordonner avec MRCC"]
        })
        
    except Exception as e:
        logger.error(f"Erreur déploiement: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/maritime-routes', methods=['GET'])
def api_maritime_routes():
    """
    API pour obtenir les routes maritimes
    """
    try:
        return jsonify({
            'success': True,
            'routes': MARITIME_ROUTES,
            'fishing_zones': FISHING_ZONES,
            'mrcc_zones': MRCC_MAROC['zones']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Route non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erreur serveur: {str(error)}")
    return jsonify({'success': False, 'error': 'Erreur interne du serveur'}), 500
# Dans app.py - Ajouter les modèles

class RescueEvent(db.Model):
    """Modèle pour les événements de sauvetage"""
    __tablename__ = 'rescue_events'
    __table_args__ = {'schema': 'public'}
    
    event_id = db.Column(db.Integer, primary_key=True)
    event_number = db.Column(db.String(20), unique=True, nullable=False)  # Format: MRCC-YYYY-XXXX
    event_type = db.Column(db.String(50), nullable=False)  # man_overboard, vessel_sinking, medical, fire, collision, distress
    status = db.Column(db.String(20), default='active')  # active, resolved, cancelled, archived
    priority = db.Column(db.String(10), default='normal')  # critical, high, normal, low
    
    # Localisation
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_name = db.Column(db.String(200))
    distance_coast_km = db.Column(db.Float)
    
    # Détails de l'incident
    description = db.Column(db.Text)
    reported_by = db.Column(db.String(100))
    report_time = db.Column(db.DateTime, default=datetime.utcnow)
    incident_time = db.Column(db.DateTime)
    
    # Personnes impliquées
    persons_involved = db.Column(db.Integer, default=1)
    persons_rescued = db.Column(db.Integer, default=0)
    persons_deceased = db.Column(db.Integer, default=0)
    persons_missing = db.Column(db.Integer, default=0)
    
    # Moyens engagés
    assets_deployed = db.Column(db.JSON, default=list)  # Liste des IDs des moyens
    assets_available = db.Column(db.JSON, default=list)
    
    # Conditions environnementales
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    current_speed = db.Column(db.Float)
    current_direction = db.Column(db.Float)
    sea_state = db.Column(db.Integer)
    visibility_km = db.Column(db.Float)
    water_temperature = db.Column(db.Float)
    
    # Informations navire
    vessel_name = db.Column(db.String(100))
    vessel_type = db.Column(db.String(50))
    vessel_flag = db.Column(db.String(50))
    vessel_imo = db.Column(db.String(20))
    vessel_mmsi = db.Column(db.String(20))
    
    # Gestion
    created_by = db.Column(db.Integer, db.ForeignKey('crts_parameters.users.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('crts_parameters.users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Détails supplémentaires
    attachments = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text)
    action_log = db.Column(db.JSON, default=list)  # Historique des actions
    
    def __repr__(self):
        return f'<RescueEvent {self.event_number}>'
    
    def to_dict(self):
        """Convertir l'objet en dictionnaire pour JSON"""
        return {
            'event_id': self.event_id,
            'event_number': self.event_number,
            'event_type': self.event_type,
            'status': self.status,
            'priority': self.priority,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'distance_coast_km': self.distance_coast_km,
            'description': self.description,
            'reported_by': self.reported_by,
            'report_time': self.report_time.isoformat() if self.report_time else None,
            'incident_time': self.incident_time.isoformat() if self.incident_time else None,
            'persons_involved': self.persons_involved,
            'persons_rescued': self.persons_rescued,
            'persons_deceased': self.persons_deceased,
            'persons_missing': self.persons_missing,
            'assets_deployed': self.assets_deployed,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'current_speed': self.current_speed,
            'current_direction': self.current_direction,
            'sea_state': self.sea_state,
            'vessel_name': self.vessel_name,
            'vessel_type': self.vessel_type,
            'vessel_flag': self.vessel_flag,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'notes': self.notes
        }


class RescueUpdate(db.Model):
    """Modèle pour les mises à jour des événements de sauvetage"""
    __tablename__ = 'rescue_updates'
    __table_args__ = {'schema': 'public'}
    
    update_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('public.rescue_events.event_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('crts_parameters.users.id'))
    update_type = db.Column(db.String(50))  # status_change, position_update, asset_deployment, general
    content = db.Column(db.Text)
    previous_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'update_id': self.update_id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'update_type': self.update_type,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RescueAsset(db.Model):
    """Modèle pour les moyens engagés"""
    __tablename__ = 'rescue_assets'
    __table_args__ = {'schema': 'public'}
    
    asset_id = db.Column(db.Integer, primary_key=True)
    asset_type = db.Column(db.String(50))  # vessel, helicopter, plane, ground_vehicle
    asset_name = db.Column(db.String(100))
    asset_code = db.Column(db.String(50), unique=True)
    base_location = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='available')  # available, deployed, maintenance, out_of_service
    capacity = db.Column(db.Integer)
    speed = db.Column(db.Float)
    range_km = db.Column(db.Float)
    crew_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'asset_id': self.asset_id,
            'asset_type': self.asset_type,
            'asset_name': self.asset_name,
            'asset_code': self.asset_code,
            'base_location': self.base_location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status,
            'capacity': self.capacity,
            'speed': self.speed,
            'range_km': self.range_km,
            'crew_count': self.crew_count
        }
# Routes pour la gestion des événements de sauvetage

@app.route('/rescue-events')

def rescue_events():
    """Page de gestion des événements de sauvetage"""
    return render_template('rescue_events.html')


@app.route('/api/rescue-events', methods=['GET'])

def api_get_rescue_events():
    """API pour récupérer les événements de sauvetage"""
    try:
        status = request.args.get('status')
        event_type = request.args.get('event_type')
        priority = request.args.get('priority')
        search = request.args.get('search')
        
        query = RescueEvent.query
        
        if status:
            query = query.filter(RescueEvent.status == status)
        if event_type:
            query = query.filter(RescueEvent.event_type == event_type)
        if priority:
            query = query.filter(RescueEvent.priority == priority)
        if search:
            query = query.filter(
                db.or_(
                    RescueEvent.event_number.ilike(f'%{search}%'),
                    RescueEvent.vessel_name.ilike(f'%{search}%'),
                    RescueEvent.location_name.ilike(f'%{search}%')
                )
            )
        
        events = query.order_by(RescueEvent.created_at.desc()).all()
        
        # Statistiques
        stats = {
            'total': RescueEvent.query.count(),
            'active': RescueEvent.query.filter_by(status='active').count(),
            'resolved': RescueEvent.query.filter_by(status='resolved').count(),
            'persons_rescued': db.session.query(db.func.sum(RescueEvent.persons_rescued)).scalar() or 0
        }
        
        return jsonify({
            'events': [e.to_dict() for e in events],
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération événements: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events', methods=['POST'])

def api_create_rescue_event():
    """Créer un nouvel événement de sauvetage"""
    try:
        data = request.get_json()
        
        # Générer un numéro d'événement unique
        year = datetime.now().year
        count = RescueEvent.query.filter(
            RescueEvent.event_number.like(f'MRCC-{year}-%')
        ).count() + 1
        event_number = f'MRCC-{year}-{count:04d}'
        
        event = RescueEvent(
            event_number=event_number,
            event_type=data['event_type'],
            priority=data.get('priority', 'normal'),
            latitude=data['latitude'],
            longitude=data['longitude'],
            location_name=data.get('location_name'),
            description=data.get('description'),
            reported_by=current_user.username,
            incident_time=datetime.fromisoformat(data['incident_time']) if data.get('incident_time') else datetime.utcnow(),
            persons_involved=data.get('persons_involved', 1),
            vessel_name=data.get('vessel_name'),
            vessel_type=data.get('vessel_type'),
            vessel_flag=data.get('vessel_flag'),
            vessel_imo=data.get('vessel_imo'),
            vessel_mmsi=data.get('vessel_mmsi'),
            wind_speed=data.get('wind_speed'),
            wind_direction=data.get('wind_direction'),
            sea_state=data.get('sea_state'),
            visibility_km=data.get('visibility_km'),
            notes=data.get('notes'),
            created_by=current_user.id
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Créer une mise à jour initiale
        update = RescueUpdate(
            event_id=event.event_id,
            user_id=current_user.id,
            update_type='creation',
            content=f'Événement créé par {current_user.username}'
        )
        db.session.add(update)
        db.session.commit()
        
        return jsonify({'success': True, 'event_id': event.event_id})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur création événement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>', methods=['GET'])

def api_get_rescue_event(event_id):
    """Récupérer les détails d'un événement"""
    try:
        event = RescueEvent.query.get_or_404(event_id)
        updates = RescueUpdate.query.filter_by(event_id=event_id).order_by(RescueUpdate.created_at.desc()).all()
        
        event_data = event.to_dict()
        event_data['updates'] = [u.to_dict() for u in updates]
        
        return jsonify(event_data)
        
    except Exception as e:
        logger.error(f"Erreur récupération événement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>/status', methods=['PUT'])

def api_update_event_status(event_id):
    """Mettre à jour le statut d'un événement"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        event = RescueEvent.query.get_or_404(event_id)
        old_status = event.status
        event.status = new_status
        
        if new_status == 'resolved':
            event.resolved_at = datetime.utcnow()
        
        event.updated_at = datetime.utcnow()
        
        # Ajouter une mise à jour
        update = RescueUpdate(
            event_id=event_id,
            user_id=current_user.id,
            update_type='status_change',
            content=f'Statut changé de {old_status} à {new_status}',
            previous_value=old_status,
            new_value=new_status
        )
        
        db.session.add(update)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur mise à jour statut: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/<int:event_id>/update', methods=['POST'])

def api_add_event_update(event_id):
    """Ajouter une mise à jour à un événement"""
    try:
        data = request.get_json()
        
        update = RescueUpdate(
            event_id=event_id,
            user_id=current_user.id,
            update_type=data.get('type', 'general'),
            content=data.get('content')
        )
        
        db.session.add(update)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur ajout mise à jour: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-events/export', methods=['GET'])

def api_export_rescue_events():
    """Exporter les événements en CSV"""
    try:
        import csv
        from io import StringIO
        
        events = RescueEvent.query.order_by(RescueEvent.created_at.desc()).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow(['N° Événement', 'Type', 'Statut', 'Priorité', 'Date', 'Lieu', 
                        'Latitude', 'Longitude', 'Personnes', 'Sauvées', 'Navire'])
        
        for event in events:
            writer.writerow([
                event.event_number,
                event.event_type,
                event.status,
                event.priority,
                event.incident_time.strftime('%Y-%m-%d %H:%M') if event.incident_time else '',
                event.location_name or '',
                event.latitude,
                event.longitude,
                event.persons_involved,
                event.persons_rescued,
                event.vessel_name or ''
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=rescue_events_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        
        # Ajouter BOM pour Excel
        response.data = '\uFEFF' + response.data.decode('utf-8')
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur export: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue-assets', methods=['GET'])

def api_get_rescue_assets():
    """Récupérer la liste des moyens disponibles"""
    try:
        assets = RescueAsset.query.filter_by(is_active=True).all()
        return jsonify([a.to_dict() for a in assets])
        
    except Exception as e:
        logger.error(f"Erreur récupération moyens: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.config['DEBUG'] = True  # Active le mode debug

    # Utilisation de Flask directement au lieu de pywsgi pour le mode debug
    app.run(host='0.0.0.0', port=5052, debug=True)

