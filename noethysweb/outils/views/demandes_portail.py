# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PortailRenseignement, TypeSieste, Caisse, Individu, Secteur, CategorieTravail, RegimeAlimentaire, TypeMaladie, \
                        Medecin, ContactUrgence, Assurance, Information, QuestionnaireQuestion, Vaccin, Activite, Groupe,CategorieTarif
from core.data import data_civilites
from core.utils import utils_dates, utils_parametres
from portail.utils import utils_champs


def Traiter_demande(request=None, demande=None, etat=None):
    """ Traitement d'une demande donnée """
    redirection = None

    if etat == "VALIDE":
        # Récupération de la nouvelle valeur
        nouvelle_valeur = json.loads(demande.nouvelle_valeur) if demande.nouvelle_valeur else None

        # Famille
        if demande.categorie == "famille_caisse":
            if demande.code == "caisse":
                demande.famille.caisse_id = nouvelle_valeur
            elif demande.code == "allocataire":
                demande.famille.allocataire_id = nouvelle_valeur
            elif demande.code == "autorisation_cafpro":
                demande.famille.autorisation_cafpro = True if nouvelle_valeur == True else False
            else:
                setattr(demande.famille, demande.code, nouvelle_valeur)
            demande.famille.save()

        # Individu
        if demande.categorie in ("individu_identite", "individu_coords", "individu_medecin"):
            if demande.code == "type_sieste":
                demande.individu.type_sieste_id = nouvelle_valeur
            elif demande.code == "secteur":
                demande.individu.secteur_id = nouvelle_valeur
            elif demande.code == "categorie_travail":
                demande.individu.categorie_travail_id = nouvelle_valeur
            elif demande.code == "medecin":
                demande.individu.medecin_id = nouvelle_valeur
            else:
                setattr(demande.individu, demande.code, nouvelle_valeur)
            demande.individu.save()

        # Régimes alimentaires
        if demande.categorie == "individu_regimes_alimentaires":
            demande.individu.regimes_alimentaires.set(nouvelle_valeur)

        # Maladies
        if demande.categorie == "individu_maladies":
            demande.individu.maladies.set(nouvelle_valeur)

        # Inscription à une activité
        if demande.code == "inscrire_activite":
            idactivite, idgroupe, idcategorie_tarif = nouvelle_valeur.split(";")
            redirection = reverse_lazy("individu_inscriptions_ajouter", kwargs={"idfamille": demande.famille_id, "idindividu": demande.individu_id, "idactivite": int(idactivite), "idgroupe": int(idgroupe),"idcategorie_tarif": int(idcategorie_tarif) })
            messages.add_message(request, messages.WARNING, "Vous avez été redirigé vers la fiche famille afin de vérifier et confirmer l'inscription")

    # Modifie l'état de la demande
    demande.traitement_date = datetime.datetime.now()
    demande.traitement_utilisateur = request.user
    demande.etat = etat
    demande.save()

    return redirection

def Appliquer_modification(request):
    iddemande = int(request.POST["iddemande"])
    etat = request.POST["etat"]

    # Importation et traitement de la demande
    demande = PortailRenseignement.objects.select_related("famille", "individu").get(pk=iddemande)
    redirection = Traiter_demande(request=request, demande=demande, etat=etat)

    return JsonResponse({"succes": True, "redirection": redirection})


def Tout_valider(request):
    liste_pk = json.loads(request.POST["liste_demandes"])

    # Importation et traitement de chaque demande cochée
    for demande in PortailRenseignement.objects.select_related("famille", "individu").filter(pk__in=liste_pk):
        if demande.code != "inscrire_activite":
            Traiter_demande(request=request, demande=demande, etat="VALIDE")

    return JsonResponse({"resultat": "ok"})


def Get_labels():
    dict_labels = utils_champs.Get_labels_champs()

    # Ajout des tables spéciales
    for categorie, table in [("individu_contacts", ContactUrgence), ("individu_assurances", Assurance), ("individu_informations", Information), ("individu_vaccinations", Vaccin)]:
        for field in table._meta.get_fields():
            dict_labels[(categorie, field.name)] = "%s : %s" % (table._meta.verbose_name.capitalize(), field.verbose_name)

    # Ajout des questionnaires
    for question in QuestionnaireQuestion.objects.all():
        dict_labels["question_%d" % question.pk] = "Questionnaire : %s" % question.label

    return dict_labels


class Page(crud.Page):
    model = PortailRenseignement
    url_liste = "demandes_portail_liste"
    description_liste = "Voici ci-dessous la liste des modifications effectuées sur le portail à lire ou à valider."
    objet_singulier = "un renseignement à valider"
    objet_pluriel = "des renseignements à valider"


class Liste(Page, crud.Liste):
    model = PortailRenseignement
    template_name = "outils/demandes_portail.html"

    def get_queryset(self):
        self.afficher_renseignements_attente = utils_parametres.Get(nom="afficher_renseignements_attente", categorie="renseignements_attente", utilisateur=self.request.user, valeur=True)
        conditions = Q()
        if self.afficher_renseignements_attente:
            conditions &= Q(etat="ATTENTE")
        return PortailRenseignement.objects.select_related("famille", "individu", "traitement_utilisateur").filter(conditions).order_by("date")

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Historique du portail"
        context['box_titre'] = "Liste des modifications effectuées sur le portail"
        context['afficher_menu_brothers'] = True
        context['afficher_renseignements_attente'] = self.afficher_renseignements_attente
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_tout_valider", "action": "tout_valider()", "title": "Tout valider les demandes cochées", "label": "<i class='fa fa-check margin-r-5'></i>Tout valider"},
        ])
        return context

    class datatable_class(MyDatatable):
        filtres = ['idrenseignement', 'famille__nom', 'individu__nom', 'categorie']
        check = columns.CheckBoxSelectColumn(label="")
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor='Formate_individu')
        code = columns.TextColumn("Donnée", sources=['code'], processor='Formate_code')
        ancienne_valeur = columns.TextColumn("Ancienne valeur", sources=None, processor='Formate_ancienne_valeur')
        nouvelle_valeur = columns.TextColumn("Nouvelle valeur", sources=None, processor='Formate_nouvelle_valeur')
        traitement = columns.TextColumn("Traitement", sources=None, processor='Formate_traitement')
        etat = columns.TextColumn("Etat", sources=['etat'], processor='Formate_etat')
        boutons_validation = columns.TextColumn("Validation", sources=None, processor='Get_boutons_validation')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idrenseignement", "date", "famille", "individu", "code", "nouvelle_valeur", "ancienne_valeur",
                       "etat", "traitement", "boutons_validation", "actions"]
            ordering = ['date']
            labels = {
                "date": "Date",
                "traitement_date": "Traité le",
            }
            processors = {
                "date": helpers.format_date('%d/%m/%Y %H:%M'),
                "traitement_date": helpers.format_date('%d/%m/%Y %H:%M'),
            }

        def Formate_code(self, instance, **kwargs):
            # Recherche le label de la donnée
            if not hasattr(self, "dict_labels"):
                self.dict_labels = Get_labels()
            label = self.dict_labels.get(instance.code, instance.code)
            if (instance.categorie, instance.code) in self.dict_labels:
                label = self.dict_labels.get((instance.categorie, instance.code))
            # Insère une icône si donnée importante
            warning = False
            if instance.categorie in ("individu_questionnaire", "famille_questionnaire", "individu_informations", "famille_pieces", "individu_regimes_alimentaires"):
                warning = True
            if instance.categorie == "individu_coords" and instance.code in ("type_adresse", "ville_resid"):
                warning = True
            if instance.categorie == "individu_identite" and instance.code in ("nom", "prenom"):
                warning = True
            if instance.code == "inscrire_activite":
                label = "Inscription à une activité"
                warning = True
            if warning:
                label = "<i class='fa fa-warning text-yellow' title='Information importante'></i> " + label
            return label

        def Formate_traitement(self, instance, **kwargs):
            if instance.traitement_date:
                return "%s (%s)" % (utils_dates.ConvertDateToFR(instance.traitement_date), instance.traitement_utilisateur)
            return ""

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Formate_etat(self, instance, **kwargs):
            if instance.validation_auto:
                if instance.etat == "ATTENTE": return "<small class='badge badge-warning'>Non lu</small>"
                if instance.etat == "VALIDE": return "<small class='badge badge-success'>Lu</small>"
            else:
                if instance.etat == "ATTENTE": return "<small class='badge badge-warning'>Attente</small>"
                if instance.etat == "VALIDE": return "<small class='badge badge-success'>Validé</small>"
                if instance.etat == "REFUS": return "<small class='badge badge-danger'>Refusé</small>"

        def Formate_ancienne_valeur(self, instance, **kwargs):
            if not instance.ancienne_valeur:
                return ""
            return """<span class='text-danger'>%s</span>""" % self.Formate_valeur(json.loads(instance.ancienne_valeur), instance)

        def Formate_nouvelle_valeur(self, instance, **kwargs):
            if not instance.nouvelle_valeur:
                return ""
            return """<span class='text-success'>%s</span>""" % self.Formate_valeur(json.loads(instance.nouvelle_valeur), instance)

        def Get_boutons_validation(self, instance, *args, **kwargs):
            html = []
            if instance.validation_auto:
                if instance.etat == "ATTENTE":
                    html.append("""<button class='btn btn-primary btn-xs' onclick="traiter_demande(%d, 'VALIDE')" title='Marquer comme lu'><i class="fa fa-fw fa-eye"></i></button>""" % instance.pk)
                if instance.etat == "VALIDE":
                    html.append("""<button class='btn btn-danger btn-xs' onclick="traiter_demande(%d, 'ATTENTE')" title='Marquer comme non lu'><i class="fa fa-fw fa-eye-slash"></i></button>""" % instance.pk)
            else:
                if instance.etat in ("ATTENTE", "REFUS"):
                    html.append("""<button class='btn btn-success btn-xs' onclick="traiter_demande(%d, 'VALIDE')" title='Valider'><i class="fa fa-fw fa-thumbs-up"></i></button>""" % instance.pk)
                if instance.etat in ("ATTENTE", "VALIDE"):
                    html.append("""<button class='btn btn-danger btn-xs' onclick="traiter_demande(%d, 'REFUS')" title='Refuser'><i class="fa fa-fw fa-thumbs-down"></i></button>""" % instance.pk)
            return self.Create_boutons_actions(html)

        def Get_actions(self, instance, *args, **kwargs):
            html = []

            # Modifier les données
            if instance.idobjet and instance.categorie in ("individu_vaccinations", "individu_informations", "individu_contacts", "individu_assurances"):
                html.append(self.Create_bouton(url=reverse("%s_modifier" % instance.categorie, args=[instance.famille_id, instance.individu_id, instance.idobjet]), title="Modifier", icone="fa-pencil", args="target='_blank'"))
            elif instance.categorie in ("individu_identite", "individu_coords", "individu_questionnaire", "individu_regimes_alimentaires", "individu_maladies"):
                html.append(self.Create_bouton(url=reverse("%s_modifier" % instance.categorie, args=[instance.famille_id, instance.individu_id]), title="Modifier", icone="fa-pencil", args="target='_blank'"))
            elif instance.categorie in ("individu_medecin"):
                html.append(self.Create_bouton(url=reverse("individu_medical_liste", args=[instance.famille_id, instance.individu_id]), title="Modifier", icone="fa-pencil", args="target='_blank'"))
            elif instance.categorie in ("famille_pieces", "famille_reglements"):
                html.append(self.Create_bouton(url=reverse("%s_modifier" % instance.categorie, args=[instance.famille_id, instance.idobjet]), title="Modifier", icone="fa-pencil", args="target='_blank'"))
            elif instance.categorie in ("famille_caisse", "famille_questionnaire"):
                html.append(self.Create_bouton(url=reverse("%s_modifier" % instance.categorie, args=[instance.famille_id]), title="Modifier", icone="fa-pencil", args="target='_blank'"))

            # Ouvrir la fiche famille
            if instance.famille:
                html.append(self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users", args="target='_blank'"))

            # Ouvrir la fiche individuelle
            if instance.individu:
                html.append(self.Create_bouton(url=reverse("individu_resume", args=[instance.famille_id, instance.individu_id]), title="Ouvrir la fiche individuelle", icone="fa-user", args="target='_blank'"))
            return self.Create_boutons_actions(html)

        def Formate_valeur(self, valeur=None, instance=None):
            # Valeurs génériques
            if not valeur:
                return ""
            if isinstance(valeur, bool) and valeur == True:
                return "Oui"
            if valeur == "False":
                return "Non"

            # Dates
            if instance.code in ("date_naiss", "date_debut", "date_fin", "date"):
                try:
                    return utils_dates.ConvertDateENGtoFR(valeur)
                except:
                    return str(valeur)

            # Civilité
            if instance.code == "civilite":
                if not hasattr(self, "dict_civilites"):
                    self.dict_civilites = data_civilites.GetDictCivilites()
                return self.dict_civilites[int(valeur)]["label"]

            # Type de sieste
            if instance.code == "type_sieste":
                if not hasattr(self, "dict_siestes"):
                    self.dict_siestes = {type_sieste.pk: type_sieste.nom for type_sieste in TypeSieste.objects.all()}
                return self.dict_siestes.get(int(valeur), "?")

            # Caisse
            if instance.code == "caisse":
                if not hasattr(self, "dict_caisses"):
                    self.dict_caisses = {caisse.pk: caisse.nom for caisse in Caisse.objects.all()}
                return self.dict_caisses.get(int(valeur), "?")

            # Allocataire
            if instance.code in ("allocataire", "adresse_auto"):
                if not hasattr(self, "dict_individus"):
                    self.dict_individus = {individu.pk: individu.Get_nom() for individu in Individu.objects.all()}
                return self.dict_individus.get(int(valeur), "?")

            # Secteur
            if instance.code == "secteur":
                if not hasattr(self, "dict_secteurs"):
                    self.dict_secteurs = {secteur.pk: secteur.nom for secteur in Secteur.objects.all()}
                return self.dict_secteurs.get(int(valeur), "?")

            # Catégorie socio-pro.
            if instance.code == "categorie_travail":
                if not hasattr(self, "dict_categories_travail"):
                    self.dict_categories_travail = {categorie_travail.pk: categorie_travail.nom for categorie_travail in CategorieTravail.objects.all()}
                return self.dict_categories_travail.get(int(valeur), "?")

            # Régimes alimentaires
            if instance.code == "regimes_alimentaires":
                if not hasattr(self, "dict_regimes"):
                    self.dict_regimes = {regime.pk: regime.nom for regime in RegimeAlimentaire.objects.all()}
                return ", ".join([self.dict_regimes.get(idregime, "?") for idregime in valeur]) if valeur else ""

            # Maladies
            if instance.code == "maladies":
                if not hasattr(self, "dict_maladies"):
                    self.dict_maladies = {maladie.pk: maladie.nom for maladie in TypeMaladie.objects.all()}
                return ", ".join([self.dict_maladies.get(idmaladie, "?") for idmaladie in valeur]) if valeur else ""

            # Medecin
            if instance.code == "medecin":
                if not hasattr(self, "dict_medecins"):
                    self.dict_medecins = {medecin.pk: medecin.Get_nom() for medecin in Medecin.objects.all()}
                return self.dict_medecins.get(int(valeur), "?")

            # Inscription à une activité
            if instance.code == "inscrire_activite":
                if not hasattr(self, "dict_activites"):
                    self.dict_activites = {activite.pk: activite.nom for activite in Activite.objects.all()}
                    self.dict_groupes = {groupe.pk: groupe.nom for groupe in Groupe.objects.all()}
                    self.dict_categorie_tarif = {categorie_tarif.pk: categorie_tarif.nom for categorie_tarif in CategorieTarif.objects.all()}
                idactivite, idgroupe, idcategorie_tarif = valeur.split(";")
                return "%s (%s) - %s" % (self.dict_activites.get(int(idactivite), "?"), self.dict_groupes.get(int(idgroupe), "?"), self.dict_categorie_tarif.get(int(idcategorie_tarif), "?") )

            return valeur
