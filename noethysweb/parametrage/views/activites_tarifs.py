# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from parametrage.views.activites import Onglet
from core.models import Tarif, Activite, TarifLigne, CombiTarif, NomTarif, LISTE_METHODES_TARIFS, DICT_COLONNES_TARIFS
from parametrage.forms.activites_tarifs import Formulaire, FORMSET_UNITES_JOURN, FORMSET_UNITES_FORFAIT, FORMSET_UNITES_CREDIT
from django.db.models import Q
from copy import deepcopy



class Page(Onglet):
    model = Tarif
    url_liste = "activites_tarifs_liste"
    url_ajouter = "activites_tarifs_ajouter"
    url_modifier = "activites_tarifs_modifier"
    url_supprimer = "activites_tarifs_supprimer"
    url_dupliquer = "activites_tarifs_dupliquer"
    description_liste = "Vous pouvez saisir ici des tarifs pour chaque nom de tarif. Sélectionnez un nom de tarif dans la liste et cliquez sur Ajouter. Important : Lors d'une évolution de tarif, vous devez créer de nouveaux tarifs (Ne modifiez pas le tarif existant)."
    description_saisie = "Saisissez toutes les informations concernant le tarif et cliquez sur le bouton Enregistrer."
    objet_singulier = "un tarif"
    objet_pluriel = "des tarifs"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Tarifs"
        context['onglet_actif'] = "tarifs"
        context['liste_methodes_tarifs'] = LISTE_METHODES_TARIFS
        context['dict_colonnes_tarifs'] = DICT_COLONNES_TARIFS
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Nom de tarif"
        context['url_liste'] = self.url_liste
        context['idactivite'] = self.Get_idactivite()
        context['liste_categories'] = [(item.pk, item.nom) for item in NomTarif.objects.filter(activite_id=self.Get_idactivite()).order_by("nom")]
        if context['liste_categories']:
            # Si au moins un nom de tarif existe
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idactivite': self.Get_idactivite(), 'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
            ]
        else:
            # Si aucun nom de tarif existe
            context['box_introduction'] = self.description_liste + "<br><b>Vous devez avoir enregistré au moins un nom de tarif avant de pouvoir ajouter des tarifs !</b>"
        return context

    def Get_categorie(self):
        nom_tarif = self.kwargs.get('categorie', None)
        if nom_tarif:
            return nom_tarif
        nom_tarif = NomTarif.objects.filter(activite_id=self.Get_idactivite()).order_by("nom")
        return nom_tarif[0].pk if nom_tarif else 0

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idactivite"] = self.Get_idactivite()
        form_kwargs["categorie"] = self.Get_categorie()
        form_kwargs["methode"] = self.request.POST.get("methode")
        form_kwargs["tarifs_lignes_data"] = self.request.POST.get("tarifs_lignes_data")
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idactivite': self.Get_idactivite(), 'categorie': self.Get_categorie()})



class Liste(Page, crud.Liste):
    model = Tarif
    template_name = "parametrage/activite_liste.html"

    def get_queryset(self):
        conditions = Q(activite=self.Get_idactivite()) & Q(nom_tarif=self.Get_categorie()) & ~Q(type="EVENEMENT") & self.Get_filtres("Q")
        return Tarif.objects.prefetch_related("categories_tarifs").filter(conditions)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        # context['colonne_regroupement'] = 2
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtarif', 'date_debut', 'nom_tarif', 'description', 'type', 'methode']

        categories = columns.TextColumn("Catégories", sources=None, processor='Get_categories')
        type = columns.TextColumn("Type", sources=["type"], processor='Get_type')
        methode = columns.TextColumn("Méthode", sources=["methode"], processor='Get_methode')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtarif', 'date_debut', 'description', 'categories', 'type', 'methode']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['-date_debut']

        def Get_type(self, instance, *args, **kwargs):
            return instance.get_type_display()

        def Get_methode(self, instance, *args, **kwargs):
            return instance.get_methode_display()

        def Get_categories(self, instance, *args, **kwargs):
            return ", ".join([categorie.nom for categorie in instance.categories_tarifs.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idactivite dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.activite.idactivite, instance.nom_tarif_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.activite.idactivite, instance.nom_tarif_id, instance.pk])),
                self.Create_bouton_dupliquer(url=reverse(kwargs["view"].url_dupliquer, args=[instance.activite.idactivite, instance.nom_tarif_id, instance.pk])),
            ]
            return self.Create_boutons_actions(html)



class ClasseCommune(Page):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, **kwargs):
        context_data = super(ClasseCommune, self).get_context_data(**kwargs)
        activite = context_data["activite"]

        # Traitement du Combis tarifs
        if self.request.POST:
            context_data['formset_unites_journ'] = FORMSET_UNITES_JOURN(self.request.POST, instance=self.object, prefix='journ', form_kwargs={'activite': activite, 'prefixe': 'JOURN'})
            context_data['formset_unites_forfait'] = FORMSET_UNITES_FORFAIT(self.request.POST, instance=self.object, prefix='forfait', form_kwargs={'activite': activite, 'prefixe': 'FORFAIT'})
            context_data['formset_unites_credit'] = FORMSET_UNITES_CREDIT(self.request.POST, instance=self.object, prefix='credit', form_kwargs={'activite': activite, 'prefixe': 'CREDIT'})
        else:
            context_data['formset_unites_journ'] = FORMSET_UNITES_JOURN(instance=self.object, prefix='journ', form_kwargs={'activite': activite, 'prefixe': 'JOURN'})
            context_data['formset_unites_forfait'] = FORMSET_UNITES_FORFAIT(instance=self.object, prefix='forfait', form_kwargs={'activite': activite, 'prefixe': 'FORFAIT'})
            context_data['formset_unites_credit'] = FORMSET_UNITES_CREDIT(instance=self.object, prefix='credit', form_kwargs={'activite': activite, 'prefixe': 'CREDIT'})

        return context_data

    def form_valid(self, form):
        # Vérifie la validité du formulaire combi_tarifs
        type_tarif = form.cleaned_data["type"]
        if type_tarif == "JOURN":
            formsetclass = FORMSET_UNITES_JOURN
        elif type_tarif == "FORFAIT" and form.cleaned_data["conso_forfait_type"] == "CHOIX_CONSO":
            formsetclass = FORMSET_UNITES_FORFAIT
        elif type_tarif == "CREDIT":
            formsetclass = FORMSET_UNITES_CREDIT
        else: formsetclass = None

        if formsetclass:
            formset_combis_tarifs = formsetclass(self.request.POST, instance=self.object, prefix=type_tarif.lower(), form_kwargs={'activite': form.cleaned_data["activite"], 'prefixe': type_tarif})
            if formset_combis_tarifs.is_valid() == False:
                return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde du tarif
        self.object = form.save()

        # Lecture des lignes de tarifs existantes
        liste_lignes_existantes = []
        for ligne in TarifLigne.objects.filter(tarif=self.object).order_by("num_ligne"):
            dict_ligne = model_to_dict(ligne)
            dict_ligne.pop("idligne")
            liste_lignes_existantes.append(dict_ligne)

        # Sauvegarde des lignes de tarifs
        index_ligne = 0
        liste_lignes = []
        liste_dict_lignes = []
        for dict_ligne in form.cleaned_data["tarifs_lignes_data_resultats"]:
            if len(dict_ligne) > 0:
                # Préparation des données
                data_dict = {
                    "activite": self.object.activite,
                    "tarif": self.object,
                    "code": self.object.methode,
                    "num_ligne": index_ligne,
                }
                data_dict.update(dict_ligne)

                # Sauvegarde de la ligne
                ligne = TarifLigne(**data_dict)
                liste_lignes.append(ligne)

                dict_ligne = model_to_dict(ligne)
                dict_ligne.pop("idligne")
                liste_dict_lignes.append(dict_ligne)

            index_ligne += 1

        # Si la liste existante et la nouvelle liste sont différentes, on supprime et sauvegarde tout
        if liste_lignes_existantes != liste_dict_lignes:
            TarifLigne.objects.filter(tarif=self.object).order_by("num_ligne").delete()
            for ligne in liste_lignes:
                ligne.save()

        # Sauvegarde des combi_tarifs
        if formsetclass:
            if formset_combis_tarifs.is_valid():
                for formline in formset_combis_tarifs.forms:
                    if formline.cleaned_data.get('DELETE') and form.instance.pk:
                        formline.instance.delete()
                    if formline.cleaned_data.get('DELETE') == False:
                        instance = formline.save(commit=False)
                        instance.tarif = self.object
                        instance.activite = self.object.activite
                        instance.type = self.object.type
                        instance.save()
                        formline.save_m2m()

        # Supprime les éventuels combi_tarifs d'un autre type déjà créé
        CombiTarif.objects.filter(tarif=self.object).exclude(type=type_tarif).delete()
        if type_tarif == "FORFAIT" and form.cleaned_data["conso_forfait_type"] != "CHOIX_CONSO":
            CombiTarif.objects.filter(tarif=self.object).delete()

        return HttpResponseRedirect(self.get_success_url())


class Ajouter(ClasseCommune, crud.Ajouter):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Tarif %s" % NomTarif.objects.get(pk=self.Get_categorie()).nom
        return context


class Modifier(ClasseCommune, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_titre'] = "Tarif %s" % NomTarif.objects.get(pk=self.Get_categorie()).nom
        return context


class Supprimer(Page, crud.Supprimer):
    template_name = "parametrage/activite_delete.html"


class Dupliquer(Page, crud.Dupliquer):
    template_name = "parametrage/activite_dupliquer.html"

    def post(self, request, **kwargs):
        # Récupération du tarif à dupliquer
        tarif = self.model.objects.get(pk=kwargs.get("pk", None))

        # Duplication du tarif
        nouveau_tarif = deepcopy(tarif)
        nouveau_tarif.pk = None
        nouveau_tarif.description = "Copie du tarif ID%d" % tarif.pk
        nouveau_tarif.save()
        nouveau_tarif.categories_tarifs.set(tarif.categories_tarifs.all())
        nouveau_tarif.groupes.set(tarif.groupes.all())
        nouveau_tarif.cotisations.set(tarif.cotisations.all())
        nouveau_tarif.caisses.set(tarif.caisses.all())

        # Duplication des combinaisons de tarifs
        for combi in CombiTarif.objects.filter(tarif=tarif):
            nouvelle_combi = deepcopy(combi)
            nouvelle_combi.pk = None
            nouvelle_combi.tarif = nouveau_tarif
            nouvelle_combi.save()
            nouvelle_combi.unites.set(combi.unites.all())

        # Duplication des lignes de tarifs
        for ligne in TarifLigne.objects.filter(tarif=tarif):
            nouvelle_ligne = deepcopy(ligne)
            nouvelle_ligne.pk = None
            nouvelle_ligne.tarif = nouveau_tarif
            nouvelle_ligne.save()

        # Redirection vers l'objet dupliqué
        if "dupliquer_ouvrir" in request.POST:
            if nouveau_tarif.evenement:
                # Si on duplique un tarif associé à un événement
                url = reverse(self.url_modifier, args=[nouveau_tarif.activite.idactivite, nouveau_tarif.evenement_id, nouveau_tarif.pk])
            else:
                # Si on duplique un tarif normal
                url = reverse(self.url_modifier, args=[nouveau_tarif.activite.idactivite, nouveau_tarif.nom_tarif_id, nouveau_tarif.pk])
        else:
            url = None

        return self.Redirection(url=url)
