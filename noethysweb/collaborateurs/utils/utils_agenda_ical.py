# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, html, secrets
from django.urls import reverse
from django.db.models import Max

CATEGORIE_EMAIL = "collaborateur_agenda_ical"

EMAIL_OBJET_DEFAUT = "Votre planning dans votre agenda"

EMAIL_HTML_DEFAUT = """<p>Bonjour {COLLABORATEUR_PRENOM},</p>
<p>Vous pouvez désormais retrouver votre planning directement dans l'agenda de votre téléphone ou de votre ordinateur. Il contient {CONTENU_AGENDA} et se met à jour automatiquement.</p>
<p>Votre lien personnel : {LIEN_ICAL}</p>
<p><b>Comment l'ajouter à votre agenda ?</b></p>
<ul>
<li><b>iPhone ou iPad</b> : allez dans Réglages &gt; Calendrier (ou Réglages &gt; Apps &gt; Calendrier) &gt; Comptes &gt; Ajouter un compte &gt; Autre &gt; Ajouter un calendrier avec abonnement, collez votre lien personnel puis touchez « Suivant » et « Enregistrer ».</li>
<li><b>Mac</b> : ouvrez l'application Calendrier, choisissez Fichier &gt; Nouvel abonnement à un calendrier, collez votre lien personnel puis cliquez sur « S'abonner ».</li>
<li><b>Google Agenda (et téléphones Android)</b> : depuis un ordinateur, ouvrez Google Agenda, cliquez sur le + à côté de « Autres agendas », choisissez « À partir de l'URL », collez votre lien personnel puis cliquez sur « Ajouter un agenda ». L'agenda apparaîtra ensuite sur votre téléphone Android connecté au même compte Google.</li>
<li><b>Outlook</b> : dans le calendrier, cliquez sur « Ajouter un calendrier » puis « S'abonner à partir du web » (Outlook.com, Microsoft 365) ou « À partir d'Internet » (Outlook pour Windows), collez votre lien personnel puis validez.</li>
</ul>
<p>Collez le lien tel quel, sans le modifier. Selon l'application, les modifications de votre planning apparaissent après quelques minutes à quelques heures (jusqu'à 24 heures pour Google Agenda).</p>
<p>Ce lien est personnel : ne le communiquez pas. Votre agenda est en lecture seule : pour toute modification de votre planning, adressez-vous à votre responsable.</p>
<p>Cordialement,</p>
<p>{UTILISATEUR_SIGNATURE}</p>"""


def Get_url(request=None, collaborateur=None):
    if not collaborateur.token_ical:
        return None
    return request.build_absolute_uri(reverse("planning_equipe_ical", kwargs={"token": collaborateur.token_ical}))


def Generer_jeton(collaborateur=None):
    """ Crée ou remplace le jeton : l'ancien lien cesse de fonctionner """
    collaborateur.token_ical = secrets.token_urlsafe(32)
    collaborateur.ical_date_creation = datetime.datetime.now()
    collaborateur.ical_dernier_acces = None
    collaborateur.save(update_fields=["token_ical", "ical_date_creation", "ical_dernier_acces"])


def Desactiver(collaborateur=None):
    collaborateur.token_ical = None
    collaborateur.ical_date_creation = None
    collaborateur.ical_dernier_acces = None
    collaborateur.save(update_fields=["token_ical", "ical_date_creation", "ical_dernier_acces"])


def Texte_contenu(collaborateur=None, arbre=None):
    """ Description des données intégrées à l'agenda (mot-clé {CONTENU_AGENDA} de l'email) """
    if collaborateur.ical_affectation_id:
        if arbre is None:
            from collaborateurs.utils.utils_affectations import Arbre
            arbre = Arbre()
        texte = "vos évènements de l'affectation %s" % (arbre.Get_chemin(collaborateur.ical_affectation_id) or collaborateur.ical_affectation.nom)
    else:
        texte = "tous vos évènements"
    if collaborateur.ical_absences:
        texte += " ainsi que vos absences et congés validés"
    return texte


def Get_date_dernier_envoi(collaborateur=None):
    """ Date du dernier envoi du lien par email (emails de la catégorie dédiée effectivement envoyés) """
    from core.models import Destinataire
    return Destinataire.objects.filter(collaborateur=collaborateur, mail__categorie=CATEGORIE_EMAIL, date_envoi__isnull=False).aggregate(date=Max("date_envoi"))["date"]


def Preparer_email(request=None, collaborateur=None, adresse=""):
    """ Crée l'email (modèle par défaut de la catégorie ou texte standard) et renvoie l'URL de l'éditeur d'emails """
    import json
    from core.models import ModeleEmail, Mail, Destinataire
    url = Get_url(request, collaborateur)
    modele_email = ModeleEmail.objects.filter(categorie=CATEGORIE_EMAIL, defaut=True).first()
    mail = Mail.objects.create(
        categorie=CATEGORIE_EMAIL,
        objet=modele_email.objet if modele_email else EMAIL_OBJET_DEFAUT,
        html=modele_email.html if modele_email else EMAIL_HTML_DEFAUT,
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )
    valeurs = {
        "{COLLABORATEUR_CIVILITE}": collaborateur.get_civilite_display(),
        "{COLLABORATEUR_NOM}": html.escape(collaborateur.nom or ""),
        "{COLLABORATEUR_PRENOM}": html.escape(collaborateur.prenom or collaborateur.nom or ""),
        "{LIEN_ICAL}": "<a href='%s'>%s</a>" % (html.escape(url), html.escape(url)),
        "{URL_ICAL}": html.escape(url),
        "{CONTENU_AGENDA}": html.escape(Texte_contenu(collaborateur)),
    }
    destinataire = Destinataire.objects.create(categorie="collaborateur", collaborateur=collaborateur, adresse=adresse, valeurs=json.dumps(valeurs))
    mail.destinataires.add(destinataire)
    return reverse("editeur_emails", kwargs={"pk": mail.pk})
