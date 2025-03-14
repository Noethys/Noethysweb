# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from django.contrib import messages
from django.db.models import ProtectedError
from django.db import transaction
from django.contrib.admin.utils import NestedObjects
from core.views import crud
from core.models import Individu, Famille, Rattachement, Utilisateur, Inscription
from core.utils import utils_historique, utils_questionnaires
from fiche_individu.forms.individu import Formulaire
from fiche_individu.views import individu as INDIVIDU
from fiche_famille.views.famille import Onglet
from fiche_famille.utils import utils_internet

import logging

logger = logging.getLogger(__name__)
from core.models import Consentement


def Get_individus_existants(request):
    nom = request.POST.get("nom", "")
    prenom = request.POST.get("prenom", "")
    resultat = ""
    if nom or prenom:
        html = ""

        # Recherche les noms exactement identiques
        individus_identiques = Individu.objects.filter(nom__iexact=nom, prenom__iexact=prenom).order_by('nom')
        if individus_identiques.exists():
            if len(individus_identiques) == 1:
                texte = "Un individu existant dans la base de données porte"
            else:
                texte = "%d individus existants dans la base de données portent" % len(individus_identiques)
            html += """
            <div class="alert alert-warning alert-dismissible">
                <h4><i class="icon fa fa-warning"></i> Attention au doublon !</h4>
                %s exactement le même nom que vous avez saisi. Vérifiez que l'individu que vous souhaitez créer n'est pas celui qui existe déjà.
            </div>
            """ % texte

        # Recherche les noms approchant
        individus_approchant = Individu.objects.filter(nom__icontains=nom, prenom__icontains=prenom).order_by('nom')[:20]
        if individus_approchant.exists():
            html += """
            <style>
                .doublons {
                    background: #f4f4f4;
                    padding: 10px;
                    margin-bottom: 10px;
                }
                .doublons li {
                    display: inline;
                    white-space: nowrap;
                    margin-right: 20px;
                }
            </style>
            <div class="doublons">
                <strong>Individus paronymes existants</strong>
                <ul class="list-unstyled">
                    {% for individu in individus %}
                        <li><i class="icon fa fa-caret-right"></i> {{ individu.nom }} {{ individu.prenom }}</li>
                    {% endfor %}
                </ul>
            </div>
            """

        context = {'individus': individus_approchant}
        resultat = Template(html).render(RequestContext(request, context))

    return HttpResponse(resultat)



class Page(Onglet):
    model = Individu
    url_liste = "famille_resume"
    description_saisie = "Saisissez les informations sur l'individu et cliquez sur le bouton Valider."
    objet_singulier = "un individu"
    objet_pluriel = "des individus"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Ajouter un individu"
        context['onglet_actif'] = "resume"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfamille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        return reverse_lazy("individu_resume", kwargs={'idindividu': self.object.idindividu, 'idfamille': self.Get_idfamille()})



class Ajouter(crud.Ajouter):
    """ Classe à surcharger obligatoirement """
    # form_class = Formulaire
    # template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        categorie = int(form.cleaned_data["categorie"])
        titulaire = form.cleaned_data["titulaire"]
        idfamille = int(self.request.POST["idfamille"])

        if idfamille == 0:
            famille = self.Creation_famille()
        else:
            famille = Famille.objects.get(pk=idfamille)

        if action == "CREER":
            # Sauvegarde de l'individu à créer
            self.object = form.save()

            # Création des questionnaires de type individu
            utils_questionnaires.Creation_reponses(categorie="individu", liste_instances=[self.object])

            # Recherche d'une adresse à rattacher
            if categorie in (1, 2):
                rattachements = Rattachement.objects.prefetch_related('individu').filter(famille=famille)
                for rattachement in rattachements:
                    if rattachement.individu.adresse_auto == None:
                        self.object.adresse_auto = rattachement.individu.pk
                        self.object.save()
                        self.object.Maj_infos()
                        break

            #  Fournir un identifiant et un mot de passe à l'individu créé lors de la création d'une famille.
            individu = Individu.objects.get(pk=self.object.idindividu)
            internet_identifiant_individu = utils_internet.CreationIdentifiantIndividu(IDindividu=individu.pk)
            internet_mdp_individu, date_expiration_mdp_individu = utils_internet.CreationMDP()
            individu.internet_identifiant = internet_identifiant_individu
            individu.internet_mdp = internet_mdp_individu

            # Vous pouvez aussi créer un utilisateur pour l'individu si nécessaire
            utilisateur_individu = Utilisateur(
                username=internet_identifiant_individu,
                categorie="individu",  # Ou une autre catégorie, selon votre besoin
                force_reset_password=True,
                date_expiration_mdp=date_expiration_mdp_individu
            )
            utilisateur_individu.set_password(internet_mdp_individu)
            utilisateur_individu.save()

            # Association de l'utilisateur à l'individu
            individu.utilisateur = utilisateur_individu
            individu.save()
            # Renvoie vers la fiche individuelle
            url_success = reverse_lazy("individu_resume", kwargs={'idindividu': self.object.idindividu, 'idfamille': famille.pk})

        if action == "RATTACHER":
            # Récupération de l'individu à rattacher
            self.object = form.cleaned_data["individu"]

            # Renvoie vers la fiche famille
            url_success = reverse_lazy("famille_resume", kwargs={'idfamille': famille.pk})

        # Sauvegarde du rattachement
        rattachement = Rattachement(famille=famille, individu=self.object, categorie=categorie, titulaire=titulaire)
        rattachement.save()
        # MAJ des infos de la famille
        famille.Maj_infos()

        return HttpResponseRedirect(url_success)

    @transaction.atomic
    def Creation_famille(self):
        """ Le transaction.atomic permet de faire que les enregistrements suivants soient tous effectués en même temps dans la db """
        famille = Famille.objects.create()

        # Création des questionnaires de type famille
        utils_questionnaires.Creation_reponses(categorie="famille", liste_instances=[famille])

        # Création et enregistrement des codes pour le portail
        internet_identifiant = utils_internet.CreationIdentifiant(IDfamille=famille.pk)
        internet_mdp, date_expiration_mdp = utils_internet.CreationMDP()

        # Mémorisation des codes internet dans la table familles
        famille.internet_identifiant = internet_identifiant
        famille.internet_mdp = internet_mdp

        # Création de l'utilisateur
        utilisateur = Utilisateur(username=internet_identifiant, categorie="famille", force_reset_password=True, date_expiration_mdp=date_expiration_mdp)
        utilisateur.set_password(internet_mdp)
        utilisateur.save()
        # Association de l'utilisateur à la famille
        famille.utilisateur = utilisateur
        famille.save()
        return famille

class Ajouter_individu(Page, Ajouter):
    """ Ajouter un individu depuis la fiche famille """
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Creer_famille(INDIVIDU.Page, Ajouter):
    """ Créer une famille en ajoutant un individu """
    form_class = Formulaire
    template_name = "core/crud/edit.html"


class Supprimer_individu(Page, crud.Supprimer):
    form_class = Formulaire
    template_name = "fiche_famille/famille_delete.html"
    mode = "supprimer"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Supprimer un individu"
        context['onglet_actif'] = "resume"
        context['erreurs_protection'] += self.Recherche_protections()
        return context

    def Recherche_protections(self):
        erreurs_protection = []

        famille = self.get_famille()
        individu = self.get_object()

        # Recherche si l'individu à supprimer est le dernier titulaire de la famille
        rattachements = Rattachement.objects.filter(famille=famille, titulaire=True).exclude(individu=individu)
        if not rattachements:
            # S'il reste un autre membre, on empêche la suppression du dernier titulaire
            if Rattachement.objects.filter(famille=famille).exclude(individu=individu).exists():
                erreurs_protection.append("Il est impossible de %s le dernier titulaire s'il reste au moins un autre membre dans la famille." % self.mode)

            # Si c'est le dernier membre, on essaye de supprimer la fiche famille
            collector = NestedObjects(using='default')
            collector.collect([famille])
            if collector.protected:
                erreurs_protection.append("Il est impossible de supprimer la fiche famille car elle est associée aux données suivantes : %s." % crud.Formate_liste_objets(objets=collector.protected))

        return erreurs_protection

    def form_invalid(self, form):
        """ Pour compatibilité avec Django 4 """
        response = self.delete(self.request)
        return response

    def delete(self, request, *args, **kwargs):
        """ Empêche la suppression du dernier individu si la famille ne peut être supprimée """
        famille = self.get_famille()
        individu = self.get_object()

        # Supprime la famille si besoin
        reponse = self.Supprime_famille(request=request, individu=individu, famille=famille)
        if reponse:
            return reponse

        # Suppression de l'individu
        reponse = super(Supprimer_individu, self).delete(request, *args, **kwargs)

        # MAJ des infos de la famille
        try:
            famille.Maj_infos()
        except:
            pass

        return reponse

    def Supprime_famille(self, request=None, individu=None, famille=None):
        """ Supprime la famille si besoin"""

        # Vérifier si l'individu à supprimer est le dernier titulaire de la famille
        rattachements = Rattachement.objects.filter(famille=famille, titulaire=True).exclude(individu=individu)

        if not rattachements:
            # Vérifier s'il reste d'autres membres dans la famille
            if Rattachement.objects.filter(famille=famille).exclude(individu=individu).exists():
                messages.add_message(request, messages.ERROR,
                                     "Vous ne pouvez pas %s le dernier titulaire car il reste au moins un autre membre dans la famille" % self.mode)
                return HttpResponseRedirect(self.get_success_url(), status=303)

            # Supprimer la famille en supprimant toutes ses dépendances
            try:
                with transaction.atomic():
                    logger.info(f"Tentative de suppression de la famille ID: {famille.pk}")

                    # Supprimer toutes les dépendances connues
                    Rattachement.objects.filter(famille=famille).delete()
                    Inscription.objects.filter(famille=famille).delete()
                    Consentement.objects.filter(famille=famille).delete()
                    Utilisateur.objects.filter(famille=famille).delete()

                    # # Vérification avant suppression
                    # liens_restants = self.verifier_liens_famille(famille.pk)
                    # if liens_restants:
                    #     logger.error(
                    #         f"Échec de suppression de la famille {famille.pk}. Liens restants : {liens_restants}")
                    #     messages.add_message(request, messages.ERROR,
                    #                          f"La suppression de la famille est impossible car elle est toujours liée à : {liens_restants}")
                    #     return HttpResponseRedirect(self.get_success_url(), status=303)

                    # Suppression de la famille
                    famille.delete()

                    logger.info(f"Famille ID {famille.pk} supprimée avec succès")
                    messages.add_message(self.request, messages.SUCCESS,
                                         "La fiche famille a été supprimée car il s'agissait du dernier membre de la famille")

                    # Supprimer la famille de l'historique des recherches
                    if "historique_recherche" in request.session:
                        request.session["historique_recherche"] = [
                            dict_historique for dict_historique in request.session["historique_recherche"]
                            if dict_historique["idfamille"] != famille.pk
                        ]
                        request.session.modified = True

            except ProtectedError as e:
                texte_resultats = crud.Formate_liste_objets(objets=e.protected_objects)
                logger.error(f"Échec de suppression de la famille {famille.pk} : {texte_resultats}")
                messages.add_message(request, messages.ERROR,
                                     "La suppression de la famille est impossible car cette famille est rattachée aux données suivantes : %s." % texte_resultats)
                return HttpResponseRedirect(self.get_success_url(), status=303)

        return None

    def verifier_liens_famille(self, idfamille):
        """ Vérifie s'il reste des liens bloquant la suppression de la famille """
        from django.db import connection

        tables = ["rattachements", "familles_individus_masques", "factures", "paiements", "quotients", "consentements", "contacts_urgence", "inscriptions"
                  , "devis", "portail_messages", "sondages_repondants", "liens", "pieces", "notes", "cotisations", "rappels", "assurances", "reglements", "destinataires"
                  , "lectures", "historique", "deductions", "pes_pieces", "destinataires_sms", "portail_renseignements", "prestations", "mandats", "prelevements"
                  , "payeurs", "ventilation", "attestations_fiscales", "attestations", "locations"]
        liens_bloquants = []

        for table in tables:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE famille_id = %s", [idfamille])
                count = cursor.fetchone()[0]
                if count > 0:
                    liens_bloquants.append(f"{table} ({count} enregistrements)")

        return ", ".join(liens_bloquants) if liens_bloquants else None
    def get_object(self):
        if not hasattr(self, "objet"):
            self.objet = Individu.objects.get(pk=self.kwargs['idindividu'])
        return self.objet

    def get_famille(self):
        if not hasattr(self, "famille"):
            self.famille = Famille.objects.get(pk=self.Get_idfamille())
        return self.famille

    def get_success_url(self):
        """ Renvoie vers la fiche famille après la suppression """
        # Revient à la liste des familles si la famille n'existe plus
        if not Famille.objects.filter(pk=self.kwargs['idfamille']).exists():
            return reverse_lazy("famille_liste")

        # Revient à la page Résumé de la fiche famille
        self.famille = self.get_famille()
        self.famille.Maj_infos()
        return reverse_lazy("famille_resume", kwargs={'idfamille': self.Get_idfamille()})


class Detacher_individu(Supprimer_individu):
    form_class = Formulaire
    template_name = "fiche_famille/famille_detacher.html"
    mode = "détacher"
    check_protections = False

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Detacher_individu, self).get_context_data(**kwargs)
        context['box_titre'] = "Détacher un individu"

        # Recherche si des protections existent sur cet individu
        collector = NestedObjects(using='default')
        collector.collect([self.get_object()])

        # Importation des inscriptions de la famille
        inscriptions = [inscription.pk for inscription in Inscription.objects.filter(famille=self.get_famille())]

        # Exclusion des objets associés à d'autres fiches famille
        liste_objets_proteges = []
        for objet in collector.protected:
            idfamille_objet = getattr(objet, "famille_id", None)

            # Exclusions particulières
            if objet._meta.model_name == "consommation" and objet.inscription_id not in inscriptions:
                idfamille_objet = "EXCLURE"
            if objet._meta.model_name == "transport":
                idfamille_objet = "EXCLURE"

            if idfamille_objet == self.get_famille().pk or not idfamille_objet:
                liste_objets_proteges.append(objet)

        # Affichage des protections trouvées
        if liste_objets_proteges:
            context['erreurs_protection'].append("Il est rattaché aux données suivantes : %s." % crud.Formate_liste_objets(objets=liste_objets_proteges))

        return context

    def delete(self, request, *args, **kwargs):
        """ Supprime le rattachement de l'individu """
        famille = self.get_famille()
        individu = self.get_object()

        # Supprime la famille si besoin
        reponse = self.Supprime_famille(request=request, individu=individu, famille=famille)
        if reponse:
            return reponse

        # Supprime le rattachement
        rattachement = Rattachement.objects.filter(famille=famille, individu=individu).first()
        if rattachement:
            rattachement.delete()
        messages.add_message(self.request, messages.SUCCESS, "Détachement effectué avec succès")
        utils_historique.Ajouter(titre="Détachement d'un individu", detail="Détachement de %s" % individu.Get_nom(), utilisateur=self.request.user, famille=famille.pk)

        return HttpResponseRedirect(self.get_success_url())
