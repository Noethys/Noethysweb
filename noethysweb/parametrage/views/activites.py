# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from copy import deepcopy
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.views.generic.detail import DetailView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Activite, Inscription, ResponsableActivite, Agrement, Groupe, Evenement, CategorieTarif, NomTarif, \
                        Unite, UniteRemplissage, Tarif, TarifLigne, CombiTarif, Ouverture, Remplissage, PortailPeriode
from core.views.base import CustomView
from parametrage.forms.activites import Formulaire


class Page(crud.Page):
    model = Activite
    url_liste = "activites_liste"
    url_ajouter = "activites_ajouter"
    url_modifier = "activites_resume"
    url_supprimer = "activites_supprimer"
    url_dupliquer = "activites_dupliquer"
    description_liste = "Voici ci-dessous la liste des activités."
    description_saisie = "Saisissez toutes les informations concernant l'activité à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une activité"
    objet_pluriel = "des activités"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
        {"label": "Ajouter avec assistant", "classe": "btn btn-default", "href": reverse_lazy("activites_assistant_liste"), "icone": "fa fa-magic"},
        {"label": "Importer/Exporter", "classe": "btn btn-default", "href": reverse_lazy("activites_import_export"), "icone": "fa fa-download"},
    ]


class Liste(Page, crud.Liste):
    model = Activite

    def get_queryset(self):
        return Activite.objects.prefetch_related("groupes_activites").filter(self.Get_filtres("Q"), structure__in=self.request.user.structures.all()).annotate(nbre_inscrits=Count("inscription"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idactivite", "nom", "date_debut", "date_fin"]
        groupes = columns.TextColumn("Groupes d'activités", sources=None, processor='Get_groupes')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        periode = columns.DisplayColumn("Validité", sources="date_fin", processor='Get_validite')
        nbre_inscrits = columns.TextColumn("Inscrits", sources="nbre_inscrits")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idactivite", "nom", "periode", "groupes", "nbre_inscrits", "actions"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["-date_fin", "nom"]

        def Get_validite(self, instance, **kwargs):
            if not instance.date_fin or instance.date_fin.year == 2999:
                return "Validité illimitée"
            else:
                return "Du %s au %s" % (instance.date_debut.strftime('%d/%m/%Y'), instance.date_fin.strftime('%d/%m/%Y'))

        def Get_groupes(self, instance, *args, **kwargs):
            return ", ".join([groupe.nom for groupe in instance.groupes_activites.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la duplication dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
                self.Create_bouton_dupliquer(url=reverse(kwargs["view"].url_dupliquer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        """ Renvoie vers la page résumé de l'activité """
        messages.add_message(self.request, messages.SUCCESS, 'Ajout enregistré')
        return reverse_lazy("activites_resume", kwargs={'idactivite': self.object.idactivite})


class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("article(s)", "article_activites")]

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])


class Onglet(CustomView):
    menu_code = "activites_liste"
    liste_onglets = [
        {"code": "resume", "label": "Résumé", "icone": "fa-home", "url": "activites_resume"},
        {"rubrique": "Généralités"},
        {"code": "generalites", "label": "Généralités", "icone": "fa-info-circle", "url": "activites_generalites"},
        {"code": "responsables", "label": "Responsables", "icone": "fa-user", "url": "activites_responsables_liste"},
        {"code": "agrements", "label": "Agréments", "icone": "fa-file-text-o", "url": "activites_agrements_liste"},
        {"code": "groupes", "label": "Groupes", "icone": "fa-users", "url": "activites_groupes_liste"},
        {"code": "renseignements", "label": "Renseignements", "icone": "fa-check-circle-o", "url": "activites_renseignements"},
        {"rubrique": "Unités"},
        {"code": "unites_conso", "label": "Unités de consommation", "icone": "fa-tag", "url": "activites_unites_conso_liste"},
        {"code": "unites_remplissage", "label": "Unités de remplissage", "icone": "fa-tag", "url": "activites_unites_remplissage_liste"},
        {"rubrique": "Calendrier"},
        {"code": "calendrier", "label": "Calendrier", "icone": "fa-calendar", "url": "activites_calendrier"},
        {"code": "evenements", "label": "Evénements", "icone": "fa-calendar-times-o", "url": "activites_evenements_liste"},
        {"rubrique": "Tarifs"},
        {"code": "categories_tarifs", "label": "Catégories de tarifs", "icone": "fa-euro", "url": "activites_categories_tarifs_liste"},
        {"code": "noms_tarifs", "label": "Noms de tarifs", "icone": "fa-euro", "url": "activites_noms_tarifs_liste"},
        {"code": "tarifs", "label": "Tarifs", "icone": "fa-euro", "url": "activites_tarifs_liste"},
        {"rubrique": "Portail"},
        {"code": "portail_parametres", "label": "Paramètres", "icone": "fa-gear", "url": "activites_portail_parametres"},
        {"code": "portail_periodes", "label": "Périodes de réservation", "icone": "fa-calendar", "url": "activites_portail_periodes_liste"},
    ]

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des activités"
        context['liste_onglets'] = self.liste_onglets
        context['activite'] = Activite.objects.get(pk=self.kwargs['idactivite'])
        return context

    def Get_idactivite(self):
        return self.kwargs.get('idactivite', None)


class Resume(Onglet, DetailView):
    template_name = "parametrage/activite_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        context['box_titre'] = self.object.nom
        context['box_introduction'] = "Ici résumé de l'activité..."
        context['onglet_actif'] = "resume"
        context['stats_inscrits'] = Inscription.objects.filter(activite_id=self.kwargs['idactivite']).count()
        context['stats_inscriptions'] = Inscription.objects.filter(activite_id=self.kwargs['idactivite']).values_list('date_debut__year', 'date_debut__month').annotate(nbre=Count('pk')).order_by('date_debut__year', 'date_debut__month')
        # context['stats_groupes'] = Inscription.objects.values('groupe__nom').filter(activite_id=self.kwargs['idactivite']).annotate(nbre=Count('pk'))
        # context['stats_categories'] = Inscription.objects.values('categorie_tarif__nom').filter(activite_id=self.kwargs['idactivite']).annotate(nbre=Count('pk'))
        return context

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])


class Dupliquer(Page, crud.Dupliquer):
    def post(self, request, **kwargs):
        # Récupération de l'objet à dupliquer
        activite = self.model.objects.get(pk=kwargs.get("pk", None))

        # Duplication de l'objet Activite
        nouvelle_activite = deepcopy(activite)
        nouvelle_activite.pk = None
        nouvelle_activite.nom = "Copie de %s" % activite.nom
        nouvelle_activite.save()
        nouvelle_activite.groupes_activites.set(activite.groupes_activites.all())
        nouvelle_activite.pieces.set(activite.pieces.all())
        nouvelle_activite.cotisations.set(activite.cotisations.all())
        nouvelle_activite.types_consentements.set(activite.types_consentements.all())

        def Get_correspondances(correspondances={}, objet=None):
            return {
                "activite_id": nouvelle_activite.pk,
                "unite_id": correspondances["Unite"][objet.unite_id] if getattr(objet, "unite_id", None) and "Unite" in correspondances else None,
                "groupe_id": correspondances["Groupe"][objet.groupe_id] if getattr(objet, "groupe_id", None) and "Groupe" in correspondances else None,
                "unite_remplissage_id": correspondances["UniteRemplissage"][objet.unite_remplissage_id] if getattr(objet, "unite_remplissage_id", None) and "UniteRemplissage" in correspondances else None,
                "tarif_id": correspondances["Tarif"][objet.tarif_id] if getattr(objet, "tarif_id", None) and "Tarif" in correspondances else None,
                "nom_tarif_id": correspondances["NomTarif"][objet.nom_tarif_id] if getattr(objet, "nom_tarif_id", None) and "NomTarif" in correspondances else None,
                "evenement_id": correspondances["Evenement"][objet.evenement_id] if getattr(objet, "evenement_id", None) and "Evenement" in correspondances else None,
            }

        # Duplications simples
        tables = [ResponsableActivite, Agrement, Groupe, Unite, Evenement, CategorieTarif, NomTarif,
                  UniteRemplissage, Tarif, TarifLigne, Ouverture, Remplissage, PortailPeriode]
        correspondances = {}
        for classe in tables:
            for objet in classe.objects.filter(activite=activite):
                nouvel_objet = deepcopy(objet)
                nouvel_objet.pk = None

                try:
                    # Traitement des ForeignKey
                    for key, valeur in Get_correspondances(correspondances, objet).items():
                        setattr(nouvel_objet, key, valeur)
                    nouvel_objet.save()

                    # Mémorisation des correspondances
                    correspondances.setdefault(objet._meta.object_name, {})
                    correspondances[objet._meta.object_name][objet.pk] = nouvel_objet.pk

                    # Duplication des champs manytomany
                    for field in classe._meta.get_fields():
                        if field.__class__.__name__ == "ManyToManyField":
                            getattr(nouvel_objet, field.name).set(getattr(objet, field.name).all(), through_defaults=Get_correspondances(correspondances, objet))
                except:
                    pass

        # Unite de remplissage
        for objet in UniteRemplissage.objects.filter(activite=nouvelle_activite):
            try:
                objet.unites.set(Unite.objects.filter(pk__in=[correspondances["Unite"][obj.pk] for obj in objet.unites.all()]))
            except:
                pass

        # Tarif
        for objet in Tarif.objects.filter(activite=nouvelle_activite):
            try:
                objet.categories_tarifs.set(CategorieTarif.objects.filter(pk__in=[correspondances["CategorieTarif"][obj.pk] for obj in objet.categories_tarifs.all()]))
                objet.groupes.set(Groupe.objects.filter(pk__in=[correspondances["Groupe"][obj.pk] for obj in objet.groupes.all()]))
            except:
                pass

        # CombiTarif
        for objet in CombiTarif.objects.filter(tarif_id__in=correspondances.get("Tarif", [])):
            try:
                nouvel_objet = deepcopy(objet)
                nouvel_objet.pk = None
                nouvel_objet.tarif_id = correspondances["Tarif"][objet.tarif_id]
                nouvel_objet.groupe_id = correspondances["Groupe"][objet.groupe_id] if objet.groupe_id else None
                nouvel_objet.save()
                nouvel_objet.unites.set(Unite.objects.filter(pk__in=[correspondances["Unite"][obj.pk] for obj in objet.unites.all()]))
            except:
                pass

        # Redirection
        url = reverse(self.url_modifier, args=[nouvelle_activite.pk,]) if "dupliquer_ouvrir" in request.POST else None
        return self.Redirection(url=url)
