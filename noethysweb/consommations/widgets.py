# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.db.models import Q
from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe
from core.models import Activite, Groupe, Unite, UniteRemplissage, Evenement, Ecole, Classe, NiveauScolaire, Parametre
from core.utils import utils_dates


class SelectionGroupesWidget(Widget):
    template_name = 'core/widgets/checktree.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            context['selections'] = [int(id) for id in value.split(";")]

        # Récupération des dates
        liste_dates = context.get("dates", [])

        # Branches 1
        liste_activites = Activite.objects.filter(ouverture__date__in=liste_dates, structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom").distinct()
        context['liste_branches1'] = [{"pk": activite.pk, "label": activite.nom} for activite in liste_activites]

        # Branches 2
        context['dict_branches2'] = {}
        for groupe in Groupe.objects.select_related('activite').filter(activite_id__in=liste_activites).order_by("ordre"):
            context['dict_branches2'].setdefault(groupe.activite_id, [])
            context['dict_branches2'][groupe.activite_id].append({"pk": groupe.pk, "label": groupe.nom})

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)



class SelectionUnitesWidget(Widget):
    template_name = 'consommations/widgets/selection_unites.html'
    request = None

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value

        # Récupération de la valeur
        dict_valeurs = {}
        if value:
            for idactivite, liste_valeurs in json.loads(value).items():
                for index, valeur in enumerate(liste_valeurs):
                    categorie, idunite, affichage = valeur.split("_")
                    dict_valeurs["%s_%s_%s" % (idactivite, categorie, idunite)] = {"ordre": index, "affichage": affichage}

        # Récupération des dates
        liste_dates = context.get("dates", [])

        # Importation des activités
        liste_activites = Activite.objects.filter(ouverture__date__in=liste_dates, structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom").distinct()

        # Importation des unités
        dict_unites = {}

        def save_unite(unite=None, categorie=None, affichage=None):
            unite.categorie = categorie
            unite.affichage = affichage
            if unite.categorie == "remplissage":
                unite.ordre = unite.ordre + 100
            dict_unites.setdefault(unite.activite, [])
            dict_valeur = dict_valeurs.get("%s_%s_%s" % (unite.activite_id, unite.categorie, unite.pk))
            if dict_valeur:
                unite.affichage = dict_valeur["affichage"]
                unite.ordre = dict_valeur["ordre"]
            dict_unites[unite.activite].append(unite)

        for unite in Unite.objects.select_related("activite").filter(activite__in=liste_activites).order_by("ordre"):
            save_unite(unite, categorie="consommation", affichage="afficher")

        for unite in UniteRemplissage.objects.select_related("activite").filter(activite__in=liste_activites).order_by("ordre"):
            save_unite(unite, categorie="remplissage", affichage="masquer")

        # Tri par ordre
        for idactivite, liste_valeurs in dict_unites.items():
            dict_unites[idactivite] = sorted(liste_valeurs, key=lambda x: x.ordre)

        context["liste_activites"] = liste_activites
        context["dict_unites"] = dict_unites
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class ColonnesPersoWidget(Widget):
    template_name = 'consommations/widgets/colonnes_perso.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        else:
            context['value'] = "[]"

        # Importation du form de saisie d'une colonne
        from consommations.forms.colonne_personnalisee import Formulaire
        context['form'] = Formulaire()

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class SelectionEvenementsWidget(Widget):
    template_name = 'core/widgets/checktree.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("evenements:", "")
            context['selections'] = [int(id) for id in value.split(";")]

        # Récupération des dates
        liste_dates = context.get("dates", [])

        # Branches 1
        conditions = Q(ouverture__date__in=liste_dates) if liste_dates else Q()
        liste_activites = Activite.objects.filter(conditions, structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom").distinct()

        # Branches 2
        context['dict_branches2'] = {}
        conditions = Q(date__in=liste_dates) if liste_dates else Q()
        if context.get("date_min", None):
            conditions &= Q(date__gte=context["date_min"])
        for evenement in Evenement.objects.select_related('activite', 'groupe').filter(conditions, activite_id__in=liste_activites).order_by("-date", "-heure_debut"):
            context['dict_branches2'].setdefault(evenement.activite_id, [])
            context['dict_branches2'][evenement.activite_id].append({"pk": evenement.pk, "label": "%s : %s (%s)" % (utils_dates.ConvertDateToFR(evenement.date), evenement.nom, evenement.groupe)})

        # Ne conserve que les activités qui possèdent des événements
        context['liste_branches1'] = [{"pk": activite.pk, "label": activite.nom} for activite in liste_activites if activite.pk in context['dict_branches2']]

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)



class SelectionEcolesWidget(Widget):
    template_name = 'core/widgets/checklist.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("ecoles:", "")
            context['selections'] = [int(id) for id in value.split(";")]
            context['coche_tout'] = False

        # Items
        liste_ecoles = Ecole.objects.all().order_by("nom")
        context['items'] = [{"pk": ecole.pk, "label": ecole.nom} for ecole in liste_ecoles]

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)


class SelectionClassesWidget(Widget):
    template_name = 'core/widgets/checktree.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("classes:", "")
            context['selections'] = [int(id) for id in value.split(";")]
            context['coche_tout'] = False

        # Récupération des dates
        liste_dates = context.get("dates", [])
        liste_dates.sort()

        # Branches 2
        context['dict_branches2'] = {}
        conditions = Q()
        if liste_dates:
            conditions &= Q(date_debut__lte=max(liste_dates), date_fin__gte=min(liste_dates))
        for classe in Classe.objects.select_related('ecole').filter(conditions).order_by("date_debut", "nom"):
            context['dict_branches2'].setdefault(classe.ecole_id, [])
            context['dict_branches2'][classe.ecole_id].append({"pk": classe.pk, "label": "%s (%s-%s)" % (classe.nom, classe.date_debut.strftime("%Y"), classe.date_fin.strftime("%y"))})

        # Branches 1
        liste_ecoles = Ecole.objects.filter(pk__in=context['dict_branches2'].keys()).order_by("nom")
        context['liste_branches1'] = [{"pk": ecole.pk, "label": ecole.nom} for ecole in liste_ecoles]

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)


class SelectionNiveauxWidget(Widget):
    template_name = 'core/widgets/checklist.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = self.attrs.get("name", name)

        # Récupère les sélections initiales
        context['selections'] = []
        if value:
            value = value.replace("niveaux:", "")
            context['selections'] = [int(id) for id in value.split(";")]
            context['coche_tout'] = False

        # Items
        liste_niveaux = NiveauScolaire.objects.all().order_by("ordre")
        context['items'] = [{"pk": niveau.pk, "label": niveau.nom} for niveau in liste_niveaux]

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        selections = data.getlist(name, [])
        return ";".join(selections)


class ColonnesEtatNominWidget(Widget):
    template_name = 'consommations/widgets/colonnes_etat_nomin.html'
    request = None

    def get_context(self, name, value, attrs=None):
        from consommations.utils import utils_etat_nomin
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name

        # Conversion des colonnes de l'ancien format
        try:
            colonnes = utils_etat_nomin.Normaliser_colonnes(json.loads(value or "[]"))
        except (ValueError, TypeError, AttributeError):
            colonnes = []
        context['value'] = json.dumps(colonnes)
        utilisateur = self.request.user if self.request else None
        context['catalogue'] = json.dumps(utils_etat_nomin.Get_catalogue(utilisateur))

        # Profils de l'état global (colonne « Heures selon les règles de l'état global »)
        profils = []
        if self.request:
            conditions_profils = Q(categorie="profil_etat_global") & (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
            profils = [{"id": profil.pk, "nom": profil.nom} for profil in Parametre.objects.filter(conditions_profils).order_by("nom")]
        context['profils_etat_global'] = json.dumps(profils)
        context['modeles'] = json.dumps(utils_etat_nomin.Get_modeles())

        # Noms des unités par activité (regroupés par nom, comme pour le filtrage)
        conditions = Q(activite__structure__in=self.request.user.structures.all()) if self.request else Q()
        dict_groupes_activites = {}
        for activite in Activite.objects.filter(Q(structure__in=self.request.user.structures.all()) if self.request else Q()).prefetch_related("groupes_activites"):
            dict_groupes_activites[activite.pk] = [groupe.pk for groupe in activite.groupes_activites.all()]
        dict_unites = {}
        for unite in Unite.objects.filter(conditions).order_by("ordre"):
            item = dict_unites.setdefault(unite.nom.lower().strip(), {"nom": unite.nom.strip(), "activites": [], "groupes_activites": []})
            item["activites"].append(unite.activite_id)
            item["groupes_activites"].extend(dict_groupes_activites.get(unite.activite_id, []))
        context['unites'] = json.dumps(list(dict_unites.values()))
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class EtatsConsoWidget(Widget):
    """ Sélection des états de consommations sous forme de pastilles """
    template_name = 'consommations/widgets/etats_conso.html'
    allow_multiple_selected = True
    # Mêmes couleurs que la grille des consommations (consommations/static/consommations/grille.css)
    couleurs = {"reservation": "#FF9E1E", "present": "#aadd33", "attente": "#abcbff", "absentj": "#e83e8c", "absenti": "#a371ff"}
    aides = {"reservation": "Consommations réservées, pas encore pointées", "present": "Consommations pointées comme présentes",
             "attente": "Consommations sur liste d'attente", "absentj": "Absences justifiées", "absenti": "Absences non justifiées"}

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            value = [value]
        selection = [str(v) for v in (value or [])]
        context = {"name": name, "id": (attrs or {}).get("id", "id_%s" % name),
                   "options": [{"valeur": valeur, "label": label, "couleur": self.couleurs.get(valeur, "#6b7280"), "coche": valeur in selection, "aide": self.aides.get(valeur, "")} for valeur, label in self.choices]}
        return mark_safe(loader.render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        return data.getlist(name) if hasattr(data, "getlist") else data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return False
