from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models.personnel import Personnel, Grade, Emploi, UniteOrganisationnelle
from app.models.affiliation import PartiPolitique, Syndicat
from app.utils.decorators import check_droit
from app.services.export_service import export_personnel_excel
from app.services.pdf_service import generate_fiche_personnel
from datetime import datetime
import os
import io
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
bp = Blueprint('personnel', __name__, url_prefix='/personnel')

@bp.route('/')
@login_required
@check_droit('PERSONNEL', 'lire')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtres
    grade_id = request.args.get('grade_id')
    unite_id = request.args.get('unite_id')
    statut = request.args.get('statut')
    search = request.args.get('search')
    
    query = Personnel.query
    
    if grade_id:
        query = query.filter_by(grade_id=grade_id)
    if unite_id:
        query = query.filter_by(unite_orga_id=unite_id)
    if statut:
        query = query.filter_by(statut=statut)
    if search:
        query = query.filter(
            db.or_(
                Personnel.nom.ilike(f'%{search}%'),
                Personnel.prenom.ilike(f'%{search}%'),
                Personnel.matricule.ilike(f'%{search}%')
            )
        )
    
    pagination = query.paginate(page=page, per_page=per_page)
    
    # Données pour les filtres
    grades = Grade.query.all()
    unites = UniteOrganisationnelle.query.all()
    
     # Calcul des KPI
    total_personnel = Personnel.query.count()
    actifs = Personnel.query.filter_by(statut='ACTIF').count()
    inactifs = Personnel.query.filter_by(statut='INACTIF').count()
    
    # Statistiques démographiques
    hommes = Personnel.query.filter_by(sexe='Masculin').count()
    femmes = Personnel.query.filter_by(sexe='Féminin').count()
    
    # Âge moyen
    ages = []
    for p in Personnel.query.all():
        if p.date_de_naissance:
            age = (datetime.now().date() - p.date_de_naissance).days // 365
            ages.append(age)
    
    age_moyen = round(sum(ages) / len(ages)) if ages else 0
    age_min = min(ages) if ages else 0
    age_max = max(ages) if ages else 0
    
    # Ancienneté
    anciennetes = []
    for p in Personnel.query.all():
        if p.date_recrutement:
            anciennete = (datetime.now().date() - p.date_recrutement).days // 365
            anciennetes.append(anciennete)
    
    anciennete_moyenne = round(sum(anciennetes) / len(anciennetes)) if anciennetes else 0
    anciennete_min = min(anciennetes) if anciennetes else 0
    anciennete_max = max(anciennetes) if anciennetes else 0
    
    # Situation familiale
    maries = Personnel.query.filter(Personnel.situation_famille == 'MARIE').count()
    total_enfants = db.session.query(db.func.sum(Personnel.nb_enfants)).scalar() or 0
    nb_enfants_moyen = round(total_enfants / total_personnel, 1) if total_personnel > 0 else 0
    
    # Départs prévus
    today = datetime.now().date()
    six_months = today + timedelta(days=180)
    departs_prevus = Personnel.query.filter(Personnel.date_prevue_depart >= today).count()
    departs_6mois = Personnel.query.filter(
        Personnel.date_prevue_depart.between(today, six_months)
    ).count()
    
    # Top grades
    top_grades = db.session.query(
        Grade.libelle,
        db.func.count(Personnel.id).label('count')
    ).join(Personnel, Personnel.grade_id == Grade.id)\
     .group_by(Grade.id)\
     .order_by(db.text('count DESC')).limit(5).all()
    
    # Top unités
    top_unites = db.session.query(
        UniteOrganisationnelle.unite_organisat.label('nom'),
        db.func.count(Personnel.id).label('count')
    ).join(Personnel, Personnel.unite_orga_id == UniteOrganisationnelle.id)\
     .group_by(UniteOrganisationnelle.id)\
     .order_by(db.text('count DESC')).limit(5).all()
    
    stats = {
        'total_personnel': total_personnel,
        'actifs': actifs,
        'inactifs': inactifs,
        'taux_activite': round(actifs / total_personnel * 100, 1) if total_personnel > 0 else 0,
        'taux_inactivite': round(inactifs / total_personnel * 100, 1) if total_personnel > 0 else 0,
        'nouveaux_mois': Personnel.query.filter(
            Personnel.date_recrutement >= datetime.now().replace(day=1)
        ).count(),
        'hommes': hommes,
        'femmes': femmes,
        'pourcentage_hommes': round(hommes / total_personnel * 100, 1) if total_personnel > 0 else 0,
        'pourcentage_femmes': round(femmes / total_personnel * 100, 1) if total_personnel > 0 else 0,
        'age_moyen': age_moyen,
        'age_min': age_min,
        'age_max': age_max,
        'anciennete_moyenne': anciennete_moyenne,
        'anciennete_min': anciennete_min,
        'anciennete_max': anciennete_max,
        'maries': maries,
        'taux_mariage': round(maries / total_personnel * 100, 1) if total_personnel > 0 else 0,
        'total_enfants': total_enfants,
        'nb_enfants_moyen': nb_enfants_moyen,
        'departs_prevus': departs_prevus,
        'departs_6mois': departs_6mois,
        'top_grades': [{'libelle': g[0], 'count': g[1]} for g in top_grades],
        'top_unites': [{'nom': u[0], 'count': u[1]} for u in top_unites],
    }
    
    return render_template('personnel/index.html',
                         personnel=pagination.items,
                         pagination=pagination,
                         stats=stats,
                         grades=grades,
                         unites=unites,
                         filtres=request.args)



@bp.route('/ajouter', methods=['GET', 'POST'])
@login_required
@check_droit('PERSONNEL', 'creer')
def ajouter():
    if request.method == 'POST':
        # Traitement du formulaire
        personnel = Personnel()
        # Remplir les champs...
        db.session.add(personnel)
        db.session.commit()
        flash('Personnel ajouté avec succès.', 'success')
        return redirect(url_for('personnel.index'))
    
    grades = Grade.query.all()
    emplois = Emploi.query.all()
    unites = UniteOrganisationnelle.query.all()
    affiliations_politiques = AffiliationPolitique.query.all()
    affiliations_syndicales = AffiliationSyndicale.query.all()
    
    return render_template('personnel/ajouter.html',
                         grades=grades,
                         emplois=emplois,
                         unites=unites,
                         aff_politiques=affiliations_politiques,
                         aff_syndicales=affiliations_syndicales)


@bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@check_droit('PERSONNEL', 'modifier')
def modifier(id):
    """Modifier un personnel"""
    personnel = Personnel.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Mise à jour des champs de base
            personnel.matricule = request.form['matricule']
            personnel.nom = request.form['nom']
            personnel.prenom = request.form['prenom']
            personnel.carte_identite = request.form['carte_identite']
            personnel.sexe = request.form.get('sexe')
            
            # Date de naissance
            if request.form.get('date_naissance'):
                personnel.date_de_naissance = datetime.strptime(request.form['date_naissance'], '%Y-%m-%d').date()
            
            personnel.annee_naissance = request.form.get('annee_naissance', type=int)
            personnel.lieu_naissance = request.form.get('lieu_naissance')
            
            # Informations familiales
            personnel.nom_pere = request.form.get('nom_pere')
            personnel.nom_mere = request.form.get('nom_mere')
            personnel.profession_pere = request.form.get('profession_pere')
            personnel.profession_mere = request.form.get('profession_mere')
            personnel.situation_famille = request.form.get('situation_famille')
            personnel.nb_enfants = request.form.get('nb_enfants', type=int) or 0
            personnel.profession_conjoint = request.form.get('profession_conjoint')
            
            # Informations professionnelles
            if request.form.get('date_entree'):
                personnel.date_entree = datetime.strptime(request.form['date_entree'], '%Y-%m-%d').date()
            
            if request.form.get('date_recrutement'):
                personnel.date_recrutement = datetime.strptime(request.form['date_recrutement'], '%Y-%m-%d').date()
            
            personnel.type_recrutement = request.form.get('type_recrutement')
            personnel.statut = request.form.get('statut', 'ACTIF')
            
            # Grade, emploi, unité
            personnel.grade_id = request.form.get('grade_id', type=int) or None
            personnel.emploi_id = request.form.get('emploi_id', type=int) or None
            personnel.unite_orga_id = request.form.get('unite_orga_id', type=int) or None
            
            if request.form.get('date_affectation_unite'):
                personnel.date_affectation_unite = datetime.strptime(request.form['date_affectation_unite'], '%Y-%m-%d').date()
            
            personnel.regime = request.form.get('regime')
            personnel.position_adm = request.form.get('position_adm')
            personnel.metier_de_base = request.form.get('metier_de_base')
            personnel.expertise = request.form.get('expertise')
            
            # Informations de départ
            if request.form.get('date_prevue_depart'):
                personnel.date_prevue_depart = datetime.strptime(request.form['date_prevue_depart'], '%Y-%m-%d').date()
            
            personnel.annee_depart = request.form.get('annee_depart', type=int)
            personnel.age_depart = request.form.get('age_depart', type=float)
            personnel.maintien = request.form.get('maintien')
            
            # Coordonnées
            personnel.adresse = request.form.get('adresse')
            personnel.telephone = request.form.get('telephone')
            personnel.telephone_personnel = request.form.get('telephone_personnel')
            personnel.email_professionnel = request.form.get('email_professionnel')
            personnel.email_personnel = request.form.get('email_personnel')
            personnel.contact_urgence = request.form.get('contact_urgence')
            
            # Informations financières
            personnel.numero_cnss = request.form.get('numero_cnss')
            personnel.compte_bancaire = request.form.get('compte_bancaire')
            
            # Affiliations
            personnel.affiliation_politique_id = request.form.get('affiliation_politique_id', type=int) or None
            personnel.affiliation_syndicale_id = request.form.get('affiliation_syndicale_id', type=int) or None
            
            # Traitement de la photo
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo and photo.filename:
                    # Sécuriser le nom du fichier
                    extension = os.path.splitext(photo.filename)[1]
                    filename = secure_filename(f"{personnel.matricule}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}")
                    
                    # Chemin complet pour la sauvegarde
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    
                    # Sauvegarder le fichier
                    photo.save(filepath)
                    
                    # Mettre à jour le chemin dans la base de données
                    personnel.photo_path = filename
            
            db.session.commit()
            flash('Personnel modifié avec succès.', 'success')
            return redirect(url_for('personnel.fiche', id=personnel.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'danger')
            # Log l'erreur pour le débogage
            print(f"Erreur modification personnel: {str(e)}")
    
    # Données pour les formulaires (requête GET)
    grades = Grade.query.order_by(Grade.ordre_hierarchique).all()
    emplois = Emploi.query.order_by(Emploi.identifiant_emploi).all()
    unites = UniteOrganisationnelle.query.order_by(UniteOrganisationnelle.unite_organisat).all()
    partis = PartiPolitique.query.filter_by(actif=True).all()
    syndicats = Syndicat.query.filter_by(actif=True).all()
    
    return render_template('personnel/modifier.html',
                         personnel=personnel,
                         grades=grades,
                         emplois=emplois,
                         unites=unites,
                         partis_politiques=partis,
                         syndicats=syndicats)



@bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
@check_droit('PERSONNEL', 'supprimer')
def supprimer(id):
    personnel = Personnel.query.get_or_404(id)
    db.session.delete(personnel)
    db.session.commit()
    flash('Personnel supprimé avec succès.', 'success')
    return redirect(url_for('personnel.index'))


@bp.route('/export/excel')
@login_required
@check_droit('PERSONNEL', 'exporter')
def export_excel():
    # Récupérer les filtres
    grade_id = request.args.get('grade_id')
    unite_id = request.args.get('unite_id')
    
    output = export_personnel_excel(grade_id, unite_id)
    
    return send_file(
        output,
        download_name='personnel.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/imprimer/<int:id>')
@login_required
@check_droit('PERSONNEL', 'imprimer')
def imprimer_fiche(id):
    personnel = Personnel.query.get_or_404(id)
    pdf = generate_fiche_personnel(personnel)
    
    return send_file(
        io.BytesIO(pdf),
        download_name=f'fiche_{personnel.matricule}.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@bp.route('/api/liste')
@login_required
def api_liste():
    personnel = Personnel.query.all()
    return jsonify([{
        'id': p.id,
        'matricule': p.matricule,
        'nom': p.nom,
        'prenom': p.prenom,
        'grade': p.grade_ref.libelle if p.grade_ref else None
    } for p in personnel])

@bp.route('/fiche/<int:id>')
@login_required
@check_droit('PERSONNEL', 'lire')
def fiche_lire(id):
    """Afficher la fiche détaillée d'un personnel"""
    personnel = Personnel.query.get_or_404(id)
    return render_template('personnel/fiche.html', personnel=personnel)


@bp.route('/fiche/<int:id>')
@login_required
@check_droit('PERSONNEL', 'imprimer')
def fiche(id):
    personnel = Personnel.query.get_or_404(id)
    return render_template('personnel/fiche.html', personnel=personnel)