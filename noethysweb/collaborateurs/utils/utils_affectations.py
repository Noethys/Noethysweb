# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import AffectationCollaborateur


class Arbre():
    """ Arborescence des affectations chargée en une seule requête """
    def __init__(self, actives_seulement=False):
        conditions = {"actif": True} if actives_seulement else {}
        self.affectations = {affectation.pk: affectation for affectation in AffectationCollaborateur.objects.select_related("activite", "groupe").filter(**conditions).order_by("ordre", "nom")}
        self.enfants = {}
        for affectation in self.affectations.values():
            parent = affectation.parent_id if affectation.parent_id in self.affectations else None
            self.enfants.setdefault(parent, []).append(affectation)

    def Parcourir(self, parent=None, niveau=0):
        """ Renvoie la liste des affectations dans l'ordre d'affichage (parcours en profondeur) avec leur niveau """
        for affectation in self.enfants.get(parent, []):
            yield affectation, niveau
            yield from self.Parcourir(parent=affectation.pk, niveau=niveau + 1)

    def Get_chemin(self, idaffectation=None, separateur=" › ", abrege=False):
        noms = []
        affectation = self.affectations.get(idaffectation)
        while affectation:
            noms.insert(0, (affectation.abrege or affectation.nom) if abrege else affectation.nom)
            affectation = self.affectations.get(affectation.parent_id)
        return separateur.join(noms)

    def Get_descendants(self, idaffectation=None):
        resultats = []
        for enfant in self.enfants.get(idaffectation, []):
            resultats.append(enfant.pk)
            resultats.extend(self.Get_descendants(enfant.pk))
        return resultats

    def Get_choix(self, exclure=[]):
        """ Choix pour un champ de formulaire, indentés selon le niveau """
        return [(affectation.pk, "%s%s" % (" " * niveau, affectation.nom)) for affectation, niveau in self.Parcourir() if affectation.pk not in exclure]

    def Get_liste_dict(self, nbre_evenements={}):
        return [{
            "id": affectation.pk, "nom": affectation.nom, "abrege": affectation.abrege or "", "parent": affectation.parent_id,
            "ordre": affectation.ordre, "couleur": affectation.couleur or "", "actif": affectation.actif, "niveau": niveau,
            "chemin": self.Get_chemin(affectation.pk), "nbre_evenements": nbre_evenements.get(affectation.pk, 0),
            "lien": self.Get_texte_lien(affectation), "seuil": self.Get_seuil_encadrement(affectation.pk),
        } for affectation, niveau in self.Parcourir()]

    def Get_texte_lien(self, affectation=None):
        """ Texte du lien avec les consommations : activité › groupe """
        if not affectation.activite_id:
            return ""
        return affectation.activite.nom + (" › " + affectation.groupe.nom if affectation.groupe_id else "")

    def Get_seuil_encadrement(self, idaffectation=None):
        """ Taux d'encadrement maximal de l'affectation ou, à défaut, de son ancêtre le plus proche """
        affectation = self.affectations.get(idaffectation)
        while affectation:
            if affectation.seuil_encadrement:
                return affectation.seuil_encadrement
            affectation = self.affectations.get(affectation.parent_id)
        return None

    def Get_sources_remplissage(self, idaffectation=None):
        """ Affectations liées à une activité dont les consommations sont affichées pour une affectation :
            elle-même si elle est liée, sinon ses descendants liés les plus proches """
        affectation = self.affectations.get(idaffectation)
        if not affectation:
            return []
        if affectation.activite_id:
            return [affectation]
        sources = []
        for enfant in self.enfants.get(idaffectation, []):
            sources.extend(self.Get_sources_remplissage(enfant.pk))
        return sources
