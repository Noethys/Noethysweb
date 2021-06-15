# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, TemplateView
from django.urls import reverse_lazy, reverse
from core.views.base import CustomView
from core.views.mydatatableview import MyDatatableView, MyMultipleDatatableView
from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from core.utils import utils_texte, utils_historique
from core.models import FiltreListe, Consommation, Inscription
import json
from django.db.models import Q, Count
from django.contrib.admin.utils import NestedObjects


class Page(CustomView):

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion %s" % getattr(self, "objet_pluriel", "")
        context['url_liste'] = getattr(self, "url_liste", "")
        context['url_ajouter'] = getattr(self, "url_ajouter", "")
        # Définit l'URL de suppression groupée
        if getattr(self, "url_supprimer_plusieurs", ""):
            if "url_supprimer_plusieurs" not in context:
                context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"listepk": "xxx"})
        return context


class Liste_commun():
    template_name = "core/crud/liste_in_box.html"

    def Get_condition_structure(self):
        """ Retourne une condition sql pour sélectionner les données associées à une structure ou toutes les structures """
        # condition = Q(structure=self.request.user.structure_actuelle) | Q(structure__isnull=True)
        condition = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        return condition

    def Get_filtres(self, mode=None):
        # Importe la liste des filtres
        if not hasattr(self, "filtres_liste"):
            nom_liste = str(self)[1:str(self).find(".Liste")]
            self.filtres_liste = []
            for item in FiltreListe.objects.filter(nom=nom_liste):
                dict_filtre = json.loads(item.parametres)
                dict_filtre.update({"idfiltre": item.pk})
                self.filtres_liste.append(dict_filtre)

        # Conversion en filtre Q
        if mode == "Q":
            conditions = Q()
            for filtre in self.filtres_liste:
                champ = filtre["champ"]
                criteres = filtre.get("criteres", [])
                if filtre["condition"] == "EGAL": conditions &= Q(**{champ: criteres[0]})
                if filtre["condition"] == "DIFFERENT": conditions &= ~Q(**{champ: criteres[0]})
                if filtre["condition"] == "CONTIENT": conditions &= Q(**{champ + "__icontains": criteres[0]})
                if filtre["condition"] == "NE_CONTIENT_PAS": conditions &= ~Q(**{champ + "__icontains": criteres[0]})
                if filtre["condition"] == "EST_VIDE": conditions &= (Q(**{champ: ''}) | Q(**{champ + "__isnull": True}))
                if filtre["condition"] == "EST_PAS_VIDE": conditions &= (~Q(**{champ: ''}) & Q(**{champ + "__isnull": False}))
                if filtre["condition"] == "SUPERIEUR": conditions &= Q(**{champ + "__gt": criteres[0]})
                if filtre["condition"] == "SUPERIEUR_EGAL": conditions &= Q(**{champ + "__gte": criteres[0]})
                if filtre["condition"] == "INFERIEUR": conditions &= Q(**{champ + "__lt": criteres[0]})
                if filtre["condition"] == "INFERIEUR_EGAL": conditions &= Q(**{champ + "__lte": criteres[0]})
                if filtre["condition"] == "COMPRIS": conditions &= (Q(**{champ + "__gte": criteres[0]}) & Q(**{champ + "__lte": criteres[1]}))
                if filtre["condition"] == "VRAI": conditions &= Q(**{champ: True})
                if filtre["condition"] == "FAUX": conditions &= Q(**{champ: False})
                if filtre["condition"] in ("INSCRIT", "PRESENT"):
                    type_champ, champ = champ.split(":")
                    type_criteres, liste_criteres = criteres[0].split(":")
                    liste_criteres = [int(x) for x in liste_criteres.split(";")]

                    if type_criteres == "groupes_activites": condition = Q(activite__groupes_activites__in=liste_criteres)
                    if type_criteres == "activites": condition = Q(activite__in=liste_criteres)
                    if type_criteres == "groupes": condition = Q(groupe__in=liste_criteres)

                    # Recherche les inscrits ou les présents
                    if filtre["condition"] == "INSCRIT":
                        donnee = "famille" if type_champ == "fpresent" else "individu"
                        resultats = [resultat[donnee] for resultat in Inscription.objects.values(donnee).filter(condition).annotate(nbre=Count('pk'))]
                    if filtre["condition"] == "PRESENT":
                        donnee = "inscription__famille" if type_champ == "fpresent" else "individu"
                        condition &= Q(date__gte=criteres[1]) & Q(date__lte=criteres[2])
                        resultats = [resultat[donnee] for resultat in Consommation.objects.values(donnee).filter(condition).annotate(nbre=Count('pk'))]

                    # Création de la condition
                    conditions &= Q(**{champ + "__in": resultats})

            return conditions
        else:
            return self.filtres_liste

    def Get_selections_filtres(self, noms=[], filtres=[]):
        conditions = Q()
        for filtre in filtres.children:
            try:
                if filtre[0] in noms:
                    conditions &= Q(**{filtre[0]: filtre[1]})
            except:
                pass
        return conditions

    def get_context_data(self, **kwargs):
        context = super(Liste_commun, self).get_context_data(**kwargs)
        context['box_introduction'] = getattr(self, "description_liste", "")
        context['box_titre'] = "Liste %s" % getattr(self, "objet_pluriel", "")
        context['impression_titre'] = "Liste %s" % getattr(self, "objet_pluriel", "")
        context['boutons_liste'] = getattr(self, "boutons_liste", [])
        context['active_deplacements'] = False
        context['colonne_regroupement'] = None
        context['filtres_liste'] = self.Get_filtres()
        return context


class Liste(Liste_commun, MyDatatableView):
    pass

class ListeMultiple(Liste_commun, MyMultipleDatatableView):
    pass

class CustomListe(Liste_commun, TemplateView):
    pass



class BaseView():

    def get_context_data(self, **kwargs):
        context = super(BaseView, self).get_context_data(**kwargs)
        context['box_titre'] = "%s %s" % (self.verbe_action, getattr(self, "objet_singulier", ""))
        context['box_introduction'] = getattr(self, "description_saisie", "")
        return context

    def get_form_kwargs(self, **kwargs):
        """ Ajoute le request pour pouvoir accéder à la structure actuelle de l'utilisateur en cours """
        form_kwargs = super(BaseView, self).get_form_kwargs(**kwargs)
        form_kwargs['request'] = getattr(self, "request", None)
        form_kwargs["mode"] = getattr(self, "mode", None)
        return form_kwargs

    def get_success_url(self):
        if "SaveAndNew" in self.request.POST:
            return reverse_lazy(self.url_ajouter)
        next = self.request.POST.get('next')
        if next:
            return next
        return reverse_lazy(self.url_liste)

    def save_historique(self, instance=None, titre=None, detail=None, form=None):
        # Titre
        if not titre:
            if hasattr(self, "Get_titre_historique"):
                titre = self.Get_titre_historique(instance)
            elif hasattr(self, "titre_historique"):
                titre = getattr(self, "titre_historique")
            else:
                titre = "%s %s" % (self.verbe_action, getattr(self, "objet_singulier", ""))

        # Détail
        if not detail:
            if hasattr(self, "Get_detail_historique"):
                detail = self.Get_detail_historique(instance)
            elif hasattr(self, "detail_historique"):
                detail = getattr(self, "detail_historique", str(instance)).format(instance)
            else:
                details = []
                for nom_champ in form.changed_data:
                    try:
                        label_champ = form.instance._meta.get_field(nom_champ).verbose_name
                        valeur_champ = getattr(form.instance, nom_champ)
                        details.append("%s=%s" % (label_champ, valeur_champ))
                    except:
                        pass
                detail = " ".join(details)

        utilisateur = self.request.user
        objet = instance._meta.verbose_name.capitalize()
        idobjet = instance.pk
        classe = instance._meta.object_name
        famille = getattr(instance, "famille_id", None)
        if classe == "Famille":
            famille = instance.pk
        individu = getattr(instance, "individu_id", None)
        if classe == "Individu":
            individu = instance.pk
        utils_historique.Ajouter(titre=titre, detail=detail, utilisateur=utilisateur, famille=famille, individu=individu, objet=objet, idobjet=idobjet, classe=classe)


class Ajouter(BaseView, CreateView):
    template_name = "core/crud/edit.html"
    texte_confirmation = 'Ajout enregistré'
    verbe_action = "Ajouter"

    def form_valid(self, form):
        # Enregistre l'objet
        self.object = form.save()

        # Affiche un message de réussite
        messages.add_message(self.request, messages.SUCCESS, self.texte_confirmation)

        # Mémorisation dans l'historique
        self.save_historique(instance=self.object, form=form)

        return HttpResponseRedirect(self.get_success_url())

    def Supprimer_defaut_autres_objets(self, form):
        """ Supprime le défaut des autres objects """
        if form.instance.defaut == True:
            self.model.objects.filter(defaut=True).update(defaut=False)


class Modifier(BaseView, UpdateView):
    template_name = "core/crud/edit.html"
    texte_confirmation = "Modification enregistrée"
    verbe_action = "Modifier"

    def form_valid(self, form):
        # Affiche un message de réussite
        messages.add_message(self.request, messages.SUCCESS, self.texte_confirmation)

        # Mémorisation dans l'historique
        if form.changed_data:
            self.save_historique(instance=form.instance, form=form)

        return super(Modifier, self).form_valid(form)

    def Supprimer_defaut_autres_objets(self, form):
        """ Supprime le défaut des autres objects """
        if form.instance.defaut == True:
            self.model.objects.filter(defaut=True).update(defaut=False)



def Formate_liste_objets(objets=[]):
    dict_objets = {}

    # Regroupement par table
    for instance in objets:
        if instance._meta not in dict_objets:
            dict_objets[instance._meta] = 0
        dict_objets[instance._meta] += 1

    # Affichage des objets liés protégés
    liste_resultats = []
    for meta, nbre in dict_objets.items():
        if nbre == 1:
            label = meta.verbose_name
        else:
            label = meta.verbose_name_plural
        liste_resultats.append("%d %s" % (nbre, label))

    texte_resultats = utils_texte.Convert_liste_to_texte_virgules(liste_resultats)
    return texte_resultats


class Supprimer(BaseView, DeleteView):
    template_name = "core/crud/confirm_delete_in_box.html"
    verbe_action = "Supprimer"

    def get_context_data(self, **kwargs):
        context = super(Supprimer, self).get_context_data(**kwargs)
        context['box_introduction'] = None

        # Recherche si des protections existent
        collector = NestedObjects(using='default')
        collector.collect([self.get_object()])
        if collector.protected:
            context['erreurs_protection'] = Formate_liste_objets(objets=collector.protected)

        return context

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        pk = instance.pk

        # Fonction bonus
        if hasattr(self, "Avant_suppression"):
            self.Avant_suppression(objet=instance)

        # Suppression
        try:
            message_erreur = instance.delete()
            if isinstance(message_erreur, str):
                messages.add_message(request, messages.ERROR, message_erreur)
                return HttpResponseRedirect(self.get_success_url(), status=303)

        except ProtectedError as e:
            texte_resultats = Formate_liste_objets(objets=e.protected_objects)
            messages.add_message(request, messages.ERROR, "La suppression est impossible car cet élément est rattaché aux données suivantes : %s." % texte_resultats)
            return HttpResponseRedirect(self.get_success_url(), status=303)

        # Enregistrement dans l'historique
        instance.pk = pk
        self.save_historique(instance)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppression effectuée avec succès')

        return HttpResponseRedirect(self.get_success_url())

    def Attribuer_defaut(self):
        """ Réattribue le défaut à une autre objet """
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(self.model.objects.filter(defaut=True)) == 0:
            objet = self.model.objects.first()
            if objet != None:
                objet.defaut = True
                objet.save()

    def Reordonner(self, champ_ordre="ordre"):
        """ Attribuer un numéro d'ordre à chaque ligne après suppression """
        # On ajuste l'ordre de chaque ligne
        for ordre, objet in enumerate(self.model.objects.all().order_by(champ_ordre), start=1):
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()





class Supprimer_plusieurs(BaseView, CustomView, TemplateView):
    template_name = "core/crud/confirm_delete_in_box.html"
    verbe_action = "Supprimer"

    def get_context_data(self, **kwargs):
        context = super(Supprimer_plusieurs, self).get_context_data(**kwargs)
        context['box_titre'] = "Supprimer %s" % self.objet_pluriel
        context['box_introduction'] = None
        context['selection_multiple'] = True
        context['liste_objets'] = self.get_objets()
        context['model'] = self.model

        # Recherche si des protections existent
        collector = NestedObjects(using='default')
        collector.collect(self.get_objets())
        if collector.protected:
            context['erreurs_protection'] = Formate_liste_objets(objets=collector.protected)

        return context

    def get_objets(self):
        listepk = [int(id) for id in self.kwargs.get("listepk").split(";")]
        liste_objets = self.model.objects.filter(pk__in=listepk)
        return liste_objets

    def post(self, request, **kwargs):
        for objet in self.get_objets():
            pk = objet.pk

            # Suppression de l'objet
            try:
                message_erreur = objet.delete()
                if isinstance(message_erreur, str):
                    messages.add_message(request, messages.ERROR, message_erreur)
                    return HttpResponseRedirect(self.get_success_url(), status=303)
            except ProtectedError as e:
                texte_resultats = Formate_liste_objets(objets=e.protected_objects)
                messages.add_message(request, messages.ERROR, "La suppression de '%s' est impossible car cet élément est rattaché aux données suivantes : %s." % (objet, texte_resultats))
                return HttpResponseRedirect(self.get_success_url(), status=303)

            # Enregistrement dans l'historique
            objet.pk = pk
            self.save_historique(objet)

        # Confirmation de la suppression
        messages.add_message(self.request, messages.SUCCESS, 'Suppressions effectuées avec succès')

        return HttpResponseRedirect(self.get_success_url())



class Dupliquer(CustomView, TemplateView):
    template_name = "core/crud/confirm_dupliquer_in_box.html"

    def get_context_data(self, **kwargs):
        context = super(Dupliquer, self).get_context_data(**kwargs)
        context['box_titre'] = "Dupliquer %s" % self.objet_singulier
        self.object = self.model.objects.get(pk=self.kwargs.get("pk", None))
        context['object'] = self.object
        return context

    def get_success_url(self):
        next = self.request.POST.get('next')
        if next:
            return next
        return reverse_lazy(self.url_liste)

    def post(self, request, **kwargs):
        """ A surcharger """
        # Duplication basique d'objet ci-dessous :
        objet = self.model.objects.get(pk=kwargs.get("pk", None))
        nouvel_objet = objet
        nouvel_objet.pk = None
        nouvel_objet.save()
        return self.Redirection()

    def Redirection(self, url=None):
        messages.add_message(self.request, messages.SUCCESS, "Duplication effectuée avec succès")
        if url:
            messages.add_message(self.request, messages.INFO, "L'objet dupliqué vient d'être ouvert")
        return HttpResponseRedirect(url if url else self.get_success_url())
