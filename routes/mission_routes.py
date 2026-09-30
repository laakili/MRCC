from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.mission import Mission, NatureMission, MoyenDeplacement, MissionCommentaire
from app.models.personnel import Personnel, UniteOrganisationnelle
from app.models.auth import Utilisateur
from app.utils.decorators import check_droit
from app.services.export_service import export_missions_excel
from app.services.pdf_service import generate_ordre_mission_pdf
from datetime import datetime, timedelta
import io
import os
from app.forms.mission_forms import MissionForm
# Définir le blueprint
bp = Blueprint('mission', __name__, url_prefix='/missions')

# ==================== GESTION DES MISSIONS ====================

@bp.route('/')
@login_required
@check_droit('MISSION', 'lire')
def index():
    """Liste des missions avec filtres"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtres
    annee = request.args.get('annee')
    statut = request.args.get('statut')
    nature_id = request.args.get('nature_id', type=int)
    personnel_id = request.args.get('personnel_id', type=int)
    unite_id = request.args.get('unite_id', type=int)
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    search = request.args.get('search')
    
    query = Mission.query
    
    if annee:
        query = query.filter_by(annee=annee)
    if statut:
        query = query.filter_by(statut=statut)
    if nature_id:
        query = query.filter_by(nature_id=nature_id)
    if personnel_id:
        query = query.filter_by(personnel_id=personnel_id)
    if unite_id:
        query = query.join(Personnel).filter(Personnel.unite_orga_id == unite_id)
    if date_debut:
        query = query.filter(Mission.date_debut >= datetime.strptime(date_debut, '%Y-%m-%d'))
    if date_fin:
        query = query.filter(Mission.date_fin <= datetime.strptime(date_fin, '%Y-%m-%d'))
    if search:
        query = query.filter(
            db.or_(
                Mission.numero_ordre_mission.ilike(f'%{search}%'),
                Mission.theme.ilike(f'%{search}%'),
                Mission.lieu_mission.ilike(f'%{search}%')
            )
        )
    
    # Tri
    tri = request.args.get('tri', '-date_debut')
    if tri.startswith('-'):
        order = db.desc(getattr(Mission, tri[1:]))
    else:
        order = db.asc(getattr(Mission, tri))
    
    pagination = query.order_by(order).paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistiques
    stats = {
        'total': Mission.query.count(),
        'en_cours': Mission.query.filter(Mission.statut.in_(['SOUMIS', 'VALIDE'])).count(),
        'terminees': Mission.query.filter_by(statut='TERMINE').count(),
        'montant_total': db.session.query(db.func.sum(Mission.montant_reel)).scalar() or 0
    }
    
    # Données pour les filtres
    annees = db.session.query(Mission.annee).distinct().order_by(Mission.annee.desc()).all()
    annees = [str(a[0]) for a in annees if a[0]]
    
    natures = NatureMission.query.filter_by(actif=True).all()
    unites = UniteOrganisationnelle.query.order_by(UniteOrganisationnelle.unite_organisat).all()
    personnels = Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    
    return render_template('missions/index.html',
                         missions=pagination.items,
                         pagination=pagination,
                         stats=stats,
                         annees=annees,
                         natures=natures,
                         unites=unites,
                         personnels=personnels,
                         filtres=request.args)



@bp.route('/ajouter', methods=['GET', 'POST'])
@login_required
@check_droit('MISSION', 'creer')
def ajouter():
    """Créer une nouvelle mission"""
    form = MissionForm()
    
    # Remplir les choix des select
    form.personnel_id.choices = [(0, 'Sélectionner un agent')] + [
        (p.id, f"{p.matricule} - {p.nom} {p.prenom}") 
        for p in Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    ]
    
    form.nature_id.choices = [(0, 'Sélectionner')] + [
        (n.id, n.libelle) 
        for n in NatureMission.query.filter_by(actif=True).all()
    ]
    
    form.moyen_deplacement_id.choices = [(0, 'Sélectionner')] + [
        (m.id, m.libelle) 
        for m in MoyenDeplacement.query.filter_by(actif=True).all()
    ]
    
    if form.validate_on_submit():
        try:
            # Générer un numéro d'ordre
            annee = datetime.now().year
            count = Mission.query.filter(Mission.annee == annee).count() + 1
            numero = f"OM-{annee}-{count:04d}"
            
            mission = Mission(
                numero_ordre_mission=numero,
                personnel_id=form.personnel_id.data,

                n_note_frais=form.n_note_frais.data,
                date_facture=form.date_facture.data,

                theme=form.theme.data,
                objectif=form.objectif.data,
                nature_id=form.nature_id.data,
                nature_mission_detail=form.nature_mission_detail.data,

                lieu_depart=form.lieu_depart.data,
                lieu_destination=form.lieu_destination.data,
                lieu_mission=form.lieu_mission.data,

                date_debut=form.date_debut.data,
                date_fin=form.date_fin.data,
                duree_prevue=form.duree_prevue.data,

                montant_estime=form.montant_estime.data,
                avance_demandee=form.avance_demandee.data,

                moyen_deplacement_id=form.moyen_deplacement_id.data or None,
                vehicule_service=form.vehicule_service.data,

                hebergement_necessaire=form.hebergement_necessaire.data,
                type_hebergement=form.type_hebergement.data,
                adresse_hebergement=form.adresse_hebergement.data,

                statut='BROUILLON',
                annee=annee,
                created_by=current_user.id
            )
            
            db.session.add(mission)
            db.session.commit()
            
            flash(f'Mission créée avec succès. N° {numero}', 'success')
            return redirect(url_for('mission.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création : {str(e)}', 'danger')
    
    # Données pour les templates (en plus du formulaire)
    personnels = Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    natures = NatureMission.query.filter_by(actif=True).all()
    moyens = MoyenDeplacement.query.filter_by(actif=True).all()
    unites = UniteOrganisationnelle.query.order_by(UniteOrganisationnelle.unite_organisat).all()
    
    return render_template('missions/ajouter.html',
                         form=form,
                         personnels=personnels,
                         natures=natures,
                         moyens=moyens,
                         unites=unites,
                         now=datetime.now())


@bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@check_droit('MISSION', 'modifier')
def modifier(id):
    """Modifier une mission"""
    mission = Mission.query.get_or_404(id)
    
    # Vérifier que la mission est modifiable
    if mission.statut not in ['BROUILLON', 'REFUSE']:
        flash('Cette mission ne peut plus être modifiée.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs
            mission.personnel_id = request.form['personnel_id']
            mission.theme = request.form['theme']
            mission.objectif = request.form.get('objectif')
            mission.nature_id = request.form['nature_id']
            mission.nature_mission_detail = request.form.get('nature_mission_detail')
            mission.lieu_depart = request.form['lieu_depart']
            mission.lieu_destination = request.form['lieu_destination']
            mission.lieu_mission = request.form['lieu_mission']
            
            mission.n_note_frais = request.form.get("n_note_frais")
            mission.date_facture = request.form.get("date_facture")
            # Mettre à jour les dates
            mission.date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d')
            if request.form.get('date_fin'):
                mission.date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d')
                mission.duree_prevue = (mission.date_fin - mission.date_debut).days + 1
            else:
                mission.date_fin = None
                mission.duree_prevue = None
            
            # Mettre à jour les montants
            mission.montant_estime = request.form.get('montant_estime', type=float)
            mission.avance_demandee = request.form.get('avance_demandee', type=float)
            
            # Mettre à jour les options
            mission.moyen_deplacement_id = request.form.get('moyen_deplacement_id', type=int)
            mission.vehicule_service = 'vehicule_service' in request.form
            mission.hebergement_necessaire = 'hebergement_necessaire' in request.form
            mission.type_hebergement = request.form.get('type_hebergement')
            mission.adresse_hebergement = request.form.get('adresse_hebergement')
            
            db.session.commit()
            flash('Mission modifiée avec succès.', 'success')
            return redirect(url_for('mission.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'danger')
    
    # Données pour les formulaires
    personnels = Personnel.query.filter_by(statut='ACTIF').order_by(Personnel.nom).all()
    natures = NatureMission.query.filter_by(actif=True).all()
    moyens = MoyenDeplacement.query.filter_by(actif=True).all()
    
    return render_template('missions/modifier.html',
                         mission=mission,
                         personnels=personnels,
                         natures=natures,
                         moyens=moyens)


@bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
@check_droit('MISSION', 'supprimer')
def supprimer(id):
    """Supprimer une mission"""
    mission = Mission.query.get_or_404(id)
    
    # Vérifier que la mission peut être supprimée
    if mission.statut not in ['BROUILLON', 'REFUSE']:
        flash('Seules les missions en brouillon ou refusées peuvent être supprimées.', 'warning')
        return redirect(url_for('mission.index'))
    
    try:
        db.session.delete(mission)
        db.session.commit()
        flash('Mission supprimée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'danger')
    
    return redirect(url_for('mission.index'))


@bp.route('/details/<int:id>')
@login_required
@check_droit('MISSION', 'lire')
def details(id):
    """Détails d'une mission"""
    mission = Mission.query.get_or_404(id)
    commentaires = MissionCommentaire.query.filter_by(mission_id=id).order_by(MissionCommentaire.created_at.desc()).all()
    
    return render_template('missions/details.html',
                         mission=mission,
                         commentaires=commentaires)


# ==================== WORKFLOW DE VALIDATION ====================

@bp.route('/soumettre/<int:id>', methods=['POST'])
@login_required
@check_droit('MISSION', 'modifier')
def soumettre(id):
    """Soumettre une mission pour validation"""
    mission = Mission.query.get_or_404(id)
    
    if mission.statut != 'BROUILLON':
        flash('Cette mission ne peut pas être soumise.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    mission.statut = 'SOUMIS'
    mission.date_soumission = datetime.now()
    db.session.commit()
    
    flash('Mission soumise pour validation.', 'success')
    return redirect(url_for('mission.details', id=id))


@bp.route('/valider/<int:id>', methods=['POST'])
@login_required
@check_droit('MISSION', 'modifier')
def valider(id):
    """Valider une mission"""
    mission = Mission.query.get_or_404(id)
    
    if mission.statut != 'SOUMIS':
        flash('Seules les missions soumises peuvent être validées.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    mission.statut = 'VALIDE'
    mission.valide_par = current_user.id
    mission.date_validation = datetime.now()
    db.session.commit()
    
    flash('Mission validée.', 'success')
    return redirect(url_for('mission.details', id=id))


@bp.route('/refuser/<int:id>', methods=['POST'])
@login_required
@check_droit('MISSION', 'modifier')
def refuser(id):
    """Refuser une mission"""
    mission = Mission.query.get_or_404(id)
    
    if mission.statut != 'SOUMIS':
        flash('Seules les missions soumises peuvent être refusées.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    mission.statut = 'REFUSE'
    mission.motif_refus = request.form['motif_refus']
    mission.valide_par = current_user.id
    mission.date_validation = datetime.now()
    db.session.commit()
    
    flash('Mission refusée.', 'warning')
    return redirect(url_for('mission.details', id=id))


@bp.route('/terminer/<int:id>', methods=['POST'])
@login_required
@check_droit('MISSION', 'modifier')
def terminer(id):
    """Marquer une mission comme terminée"""
    mission = Mission.query.get_or_404(id)
    
    if mission.statut != 'VALIDE':
        flash('Seules les missions validées peuvent être terminées.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    mission.statut = 'TERMINE'
    mission.effectuee = True
    
    # Calculer la durée réelle
    if mission.date_fin:
        mission.duree_reelle = (mission.date_fin - mission.date_debut).days + 1
    else:
        mission.duree_reelle = mission.duree_prevue
    
    mission.montant_reel = request.form.get('montant_reel', type=float)
    mission.rapport_remis = 'rapport_remis' in request.form
    
    if mission.rapport_remis:
        mission.date_remise_rapport = datetime.now()
    
    db.session.commit()
    flash('Mission terminée.', 'success')
    return redirect(url_for('mission.details', id=id))


# ==================== COMMENTAIRES ====================

@bp.route('/commentaire/ajouter/<int:mission_id>', methods=['POST'])
@login_required
def ajouter_commentaire(mission_id):
    """Ajouter un commentaire sur une mission"""
    commentaire = MissionCommentaire(
        mission_id=mission_id,
        utilisateur_id=current_user.id,
        commentaire=request.form['commentaire']
    )
    db.session.add(commentaire)
    db.session.commit()
    
    flash('Commentaire ajouté.', 'success')
    return redirect(url_for('mission.details', id=mission_id))


# ==================== EXPORT ET IMPRESSION ====================

@bp.route('/export/excel')
@login_required
@check_droit('MISSION', 'exporter')
def export_excel():
    """Export Excel des missions"""
    # Récupérer les filtres
    annee = request.args.get('annee')
    statut = request.args.get('statut')
    nature_id = request.args.get('nature_id', type=int)
    
    output = export_missions_excel(annee, statut, nature_id)
    
    filename = f"missions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@bp.route('/imprimer/<int:id>')
@login_required
@check_droit('MISSION', 'imprimer')
def imprimer_ordre(id):
    """Imprimer l'ordre de mission"""
    mission = Mission.query.get_or_404(id)
    
    if mission.statut != 'VALIDE':
        flash('Seules les missions validées peuvent être imprimées.', 'warning')
        return redirect(url_for('mission.details', id=id))
    
    pdf = generate_ordre_mission_pdf(mission)
    
    return send_file(
        io.BytesIO(pdf),
        download_name=f'ordre_mission_{mission.numero_ordre_mission}.pdf',
        as_attachment=False,
        mimetype='application/pdf'
    )


# ==================== STATISTIQUES ====================

@bp.route('/statistiques')
@login_required
@check_droit('MISSION', 'lire')
def statistiques():
    """Page de statistiques des missions"""
    # Statistiques par année
    stats_par_annee = db.session.query(
        Mission.annee,
        db.func.count(Mission.id).label('nb_missions'),
        db.func.sum(Mission.montant_reel).label('montant_total')
    ).group_by(Mission.annee).order_by(Mission.annee).all()
    
    # Statistiques par nature
    stats_par_nature = db.session.query(
        NatureMission.libelle,
        db.func.count(Mission.id).label('nb_missions')
    ).join(Mission).group_by(NatureMission.libelle).all()
    
    # Statistiques par statut
    stats_par_statut = db.session.query(
        Mission.statut,
        db.func.count(Mission.id).label('nb_missions')
    ).group_by(Mission.statut).all()
    
    return render_template('missions/statistiques.html',
                         stats_par_annee=stats_par_annee,
                         stats_par_nature=stats_par_nature,
                         stats_par_statut=stats_par_statut)


# ==================== API POUR SELECTS DYNAMIQUES ====================

@bp.route('/api/personnel')
@login_required
def api_personnel():
    """API pour récupérer la liste du personnel"""
    search = request.args.get('q', '')
    unite_id = request.args.get('unite_id', type=int)
    
    query = Personnel.query.filter_by(statut='ACTIF')
    
    if unite_id:
        query = query.filter_by(unite_orga_id=unite_id)
    
    if search:
        query = query.filter(
            db.or_(
                Personnel.nom.ilike(f'%{search}%'),
                Personnel.prenom.ilike(f'%{search}%'),
                Personnel.matricule.ilike(f'%{search}%')
            )
        )
    
    personnels = query.limit(20).all()
    
    return jsonify([{
        'id': p.id,
        'text': f"{p.matricule} - {p.nom} {p.prenom}",
        'unite': p.unite_ref.unite_organisat if p.unite_ref else ''
    } for p in personnels])


@bp.route('/api/stats')
@login_required
def api_stats():
    """API pour les statistiques (utilisée par les graphiques)"""
    # Missions par mois pour l'année en cours
    annee_courante = datetime.now().year
    
    stats_mois = db.session.query(
        db.extract('month', Mission.date_debut).label('mois'),
        db.func.count(Mission.id).label('nb_missions')
    ).filter(db.extract('year', Mission.date_debut) == annee_courante)\
     .group_by('mois').order_by('mois').all()
    
    mois_labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    mois_data = [0] * 12
    
    for stat in stats_mois:
        mois_index = int(stat[0]) - 1
        mois_data[mois_index] = stat[1]
    
    return jsonify({
        'mois_labels': mois_labels,
        'mois_data': mois_data,
        'total_missions': Mission.query.count(),
        'missions_année': Mission.query.filter(db.extract('year', Mission.date_debut) == annee_courante).count()
    })