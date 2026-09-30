from app import db

# Modèles personnel
from app.models.personnel import Grade, Emploi, UniteOrganisationnelle, Personnel

# Modèles absence
from app.models.absence import Absence

# Modèles formation - utilisez les noms exacts de votre fichier formation.py
from app.models.formation import Formation, InscriptionFormation, SessionFormation, PresenceFormation

# Modèles mission
from app.models.mission import Mission, NatureMission, MoyenDeplacement, MissionCommentaire

# Modèles affiliation
from app.models.affiliation import PartiPolitique, Syndicat, AffiliationPolitique, AffiliationSyndicale, JournalAffiliation

# Modèles auth
from app.models.auth import Utilisateur, DroitAcces

from app.utils.decorators import register_template_filters
# register_template_filters(app)