# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, requests, time
logger = logging.getLogger(__name__)
from django.core.cache import cache
from django.template import Template, RequestContext
from core.models import Organisateur, Famille, Rattachement
from fiche_famille.forms.famille_quotients import Formulaire_saisie_api_particulier

URL_API = "https://particulier.api.gouv.fr"


def Check_token(token):
    headers = {"Authorization": "Bearer %s" % token, "Accept": "application/json"}
    reponse = requests.get(URL_API + "/api/introspect", headers=headers, params={"token": token})
    return reponse.status_code == 200


class Resultat:
    def __init__(self, request=None, famille=None, individu=None, reponse=None, erreurs=[]):
        self.request = request
        self.famille = famille
        self.individu = individu
        self.code_reponse = reponse.status_code if reponse != None else None
        self.json_reponse = reponse.json() if reponse != None else {}
        self.succes = self.code_reponse == 200
        self.data = self.json_reponse.get("data", {}) if self.json_reponse else None
        if erreurs:
            # Erreurs données manuellement
            self.erreurs = erreurs
        else:
            # Erreurs retournées par l'API
            self.erreurs = ["%s : %s. %s." % (individu, erreur["title"], erreur["detail"]) for erreur in self.json_reponse.get("errors", [])]

    def Get_html_erreurs(self):
        return self.individu.Get_nom() + " <ul class='p-0 m-0' style='list-style-type:none;'>%s</ul>" % "".join(["<li><i class='icon fa fa-warning text-danger'></i> %s</li>" % erreur for erreur in self.erreurs])

    def Get_html_detail(self):
        context = {
            "individu": self.individu,
            "data": self.data,
        }
        html = """
        <div class="row">
            <div class="col-7">
                <p><i class='fa fa-check-circle text-success margin-r-5'></i>Dossier trouvé avec l'identité de {{ individu }}</p>
                <dl>
                    {% if data.allocataires %}
                        <dt>Allocataires</dt>
                        <dd>
                            {% for allocataire in data.allocataires %}
                                <div>
                                    {{ allocataire.prenoms|title }} {{ allocataire.nom_naissance }}{% if allocataire.nom_usage %} ({{ allocataire.nom_usage }}){% endif %}, 
                                    né{% if allocataire.sexe == "F" %}e{% endif %} le {{ allocataire.date_naissance|date_eng_fr }}
                                </div>
                            {% endfor %}
                        </dd>
                    {% endif %}
                    {% if data.enfants %}
                        <dt>Enfants</dt>
                        <dd>
                            {% for enfant in data.enfants %}
                                <div>
                                    {{ enfant.prenoms|title }} {{ enfant.nom_naissance }}{% if enfant.nom_usage %} ({{ enfant.nom_usage }}){% endif %}, 
                                    né{% if enfant.sexe == "F" %}e{% endif %} le {{ enfant.date_naissance|date_eng_fr }}
                                </div>
                            {% endfor %}
                        </dd>
                    {% endif %}
                    {% if data.adresse %}
                        <dt>Adresse déclarée</dt>
                        <dd>
                            {% if data.adresse.numero_libelle_voie %}{{ data.adresse.numero_libelle_voie|title }}{% endif %}
                            {% if data.adresse.lieu_dit %}{{ data.adresse.lieu_dit|title }}{% endif %}
                            {{ data.adresse.code_postal_ville }} 
                            {{ data.adresse.pays }}
                        </dd>
                    {% endif %}
                </dl>
            </div>
            <div class="col-5">
                <div class="small-box bg-info">
                    <div class="inner">
                        <h3>{{ data.quotient_familial.valeur }}</h3>
                        <p>{{ data.quotient_familial.fournisseur }}</p>
                    </div>
                    <div class="icon"><i class="fa fa-euro"></i></div>
                    <span class="small-box-footer">
                        <div>Quotient en {{ data.quotient_familial.mois|nom_mois|lower }} {{ data.quotient_familial.annee }}</div>
                        <div>Dernier recalcul en {{ data.quotient_familial.mois_calcul|nom_mois|lower }} {{ data.quotient_familial.annee_calcul }}</div>
                    </span>
                </div>
            </div>
        </div>
        """
        return Template(html).render(RequestContext(self.request, context))

    def Get_html_resultat(self):
        context = {
            "individu": self.individu,
            "data": self.data,
            "form": Formulaire_saisie_api_particulier(idfamille=self.famille.pk, data_quotient=self.data["quotient_familial"]),
        }
        html = self.Get_html_detail()
        html += """
        {% load crispy_forms_tags %}
        <div style="border-top: 1px solid #e9ecef;padding-top: 1rem;">
            {% crispy form %}
        </div>
        <div class="buttonHolder">
            <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                {% if data.quotient_familial.valeur %}
                    <button type="button" class="btn btn-primary" onclick="enregistrer_quotient()"><i class="fa fa-check margin-r-5"></i> Enregistrer ce quotient</button>
                {% endif %}
                <button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i> Annuler</button>
            </div>
        </div>
        """
        return Template(html).render(RequestContext(self.request, context))


class Api_particulier:
    def __init__(self, request=None, mois=None, annee=None):
        """ mois et annee : Mois de situation en option """
        self.request = request
        self.erreurs_generales = []
        self.erreurs_familles = {}
        self.mois = mois
        self.annee = annee
        self.nbre_requetes = 0
        self.Initialisation()

    def Initialisation(self):
        # Importation du numéro SIRET
        organisateur = cache.get("organisateur", None)
        if not organisateur:
            organisateur = cache.get_or_set("organisateur", Organisateur.objects.filter(pk=1).first())
        self.num_siret = organisateur.num_siret
        if not self.num_siret:
            self.erreurs_generales.append("Vous devez renseigner le numéro SIRET de la collectivité dans le menu Paramétrage > Organisateur > Numéro SIRET.")

        # Importation du token
        self.token = self.request.user.token_api_particulier
        if not self.token:
            self.erreurs_generales.append("Vous devez saisir votre jeton API Particulier dans le menu Paramétrage > API Particulier.")
        else:
            # Importation du mot de passe API Particulier
            mdp = cache.get("mdp_api_particulier_user%d" % self.request.user.pk)
            if not mdp:
                self.erreurs_generales.append("Vous n'avez pas saisi votre mot de passe API Particulier.")
            else:
                self.token += mdp

    def Consulter_famille(self, famille=None):
        """ famille = objet Famille ou idfamille """
        if self.erreurs_generales:
            return None

        # Importation de la famille
        if isinstance(famille, int):
            famille = Famille.objects.get(pk=famille)

        # Recherche QF pour chaque individu dans l'ordre : Allocataire, titulaire hélios, représentants.
        individus_etudies = []
        rattachements = [r.individu for r in Rattachement.objects.select_related("individu").filter(famille=famille, categorie=1, titulaire=True).order_by("pk")]
        for individu in [famille.allocataire, famille.titulaire_helios] + rattachements:
            if individu and individu not in individus_etudies and not self.erreurs_generales:
                resultat = self.Consulter_individu(famille=famille, individu=individu)
                if resultat:
                    if resultat.succes:
                        return resultat
                    else:
                        self.erreurs_familles.setdefault(famille.pk, [])
                        self.erreurs_familles[famille.pk] += resultat.erreurs
            individus_etudies.append(individu)

        return None

    def Consulter_individu(self, famille=None, individu=None):
        logger.debug("Consultation API Particulier pour %s..." % individu)
        if self.erreurs_generales:
            return None

        # Paramètres de base
        parametres = {
            "recipient": self.num_siret,
            "codeCogInseePaysNaissance": individu.pays_naiss_insee or "99100",
            "sexeEtatCivil": individu.Get_sexe(),
            "nomNaissance": individu.nom_jfille or individu.nom,
            "prenoms[]": individu.prenom.split(" ") if individu.prenom else [],
        }

        # Si on souhaite une situation sur un mois donné
        if self.mois and self.annee:
            parametres["mois"] = self.mois
            parametres["annee"] = self.annee

        # Si naissance en France, on doit fournir le COG de la ville de naissance
        if parametres["codeCogInseePaysNaissance"] == "99100":
            parametres["codeCogInseeCommuneNaissance"] = individu.ville_naiss_insee

        # Si date de naissance existante
        if individu.date_naiss:
            parametres["moisDateNaissance"] = individu.date_naiss.month
            parametres["anneeDateNaissance"] = individu.date_naiss.year

        # Recherche d'erreurs avant la requête
        erreurs_preventives = []
        if parametres["codeCogInseePaysNaissance"] == "99100" and not parametres["codeCogInseeCommuneNaissance"]:
            erreurs_preventives.append("%s : La ville de naissance n'a pas été renseignée ou le code INSEE de cette ville n'a pas été trouvée." % individu)
        if erreurs_preventives:
            return Resultat(request=self.request, famille=famille, individu=individu, erreurs=erreurs_preventives)

        return self.Envoi_requete(famille=famille, individu=individu, parametres=parametres)

    def Envoi_requete(self, famille=None, individu=None, parametres=None):
        headers = {
            "Authorization": "Bearer %s" % self.token,
            "Accept": "application/json"
        }

        # Compteur de requêtes pour respecter la volumétrie de 20 requêtes par seconde
        self.nbre_requetes += 1
        if self.nbre_requetes >= 20:
            time.sleep(1)
            self.nbre_requetes = 0

        # Appel HTTP
        reponse = requests.get(URL_API + "/v3/dss/quotient_familial/identite", headers=headers, params=parametres)
        if reponse.status_code in (401, 403):
            self.erreurs_generales.append("%s : %s" % (reponse.json()["errors"][0]["title"], reponse.json()["errors"][0]["detail"]))
            return None

        return Resultat(request=self.request, famille=famille, individu=individu, reponse=reponse)

    def Get_html_erreurs(self, idfamille=None):
        context = {"erreurs": self.erreurs_generales}
        if idfamille:
            context["erreurs"] += self.erreurs_familles.get(idfamille, [])
        html = """
        <ul class='p-0' style='list-style-type:none;'>
            {% for erreur in erreurs %}
                <li><i class='icon fa fa-warning text-danger'></i> {{ erreur }}</li>
            {% endfor %}
        </ul>
        <div class="buttonHolder">
            <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                <button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i> Fermer</button>
            </div>
        </div>
        """
        return Template(html).render(RequestContext(self.request, context))

    def Get_html_erreurs_famille(self, idfamille=None):
        context = {"erreurs": self.erreurs_familles.get(idfamille, [])}
        html = """
        <ul class='p-0 m-0' style='list-style-type:none;'>
            {% for erreur in erreurs %}
                <li><i class='icon fa fa-warning text-danger'></i> {{ erreur }}</li>
            {% endfor %}
        </ul>
        """
        return Template(html).render(RequestContext(self.request, context))
