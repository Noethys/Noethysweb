# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy
from django.urls import reverse_lazy
from django.utils.translation import gettext as _


def GetMenuPrincipal(parametres_portail=None, user=None):

    menu = Menu(titre=_("Menu principal"), user=user)
    menu.Add(code="portail_accueil", titre=_("Accueil"), icone="home", toujours_afficher=True)
    menu.Add(code="portail_renseignements", titre=_("Renseignements"), icone="folder-open-o", toujours_afficher=parametres_portail.get("renseignements_afficher_page", False))
    menu.Add(code="portail_cotisations", titre=_("Adhésions"), icone="folder-o", toujours_afficher=parametres_portail.get("cotisations_afficher_page", False))
    menu.Add(code="portail_activites", titre=_("Activités"), icone="star-o", toujours_afficher=parametres_portail.get("activites_afficher_page", False))
    menu.Add(code="portail_reservations", titre=_("Réservations"), icone="calendar", toujours_afficher=parametres_portail.get("reservations_afficher_page", False))
    menu.Add(code="portail_documents", titre=_("Documents"), icone="file-text-o", toujours_afficher=parametres_portail.get("documents_afficher_page", False))
    menu.Add(code="portail_facturation", titre=_("Facturation"), icone="euro", toujours_afficher=parametres_portail.get("facturation_afficher_page", False))
    menu.Add(code="portail_reglements", titre=_("Règlements"), icone="money", toujours_afficher=parametres_portail.get("reglements_afficher_page", False))
    menu.Add(code="portail_contact", titre=_("Contact"), icone="comments", toujours_afficher=parametres_portail.get("contact_afficher_page", False))
    menu.Add(code="portail_mentions", titre=_("Mentions légales"), icone="info-circle", toujours_afficher=parametres_portail.get("mentions_afficher_page", False))

    return menu




class Menu():
    def __init__(self, parent=None, code="", titre="", icone=None, url=None, user=None, toujours_afficher=False, compatible_demo=True, args=None):
        self.parent = parent
        self.code = code
        self.titre = titre
        self.icone = icone
        self.url = url
        self.args = args
        self.children = []
        self.user = user
        self.toujours_afficher = toujours_afficher
        self.compatible_demo = compatible_demo

    def __repr__(self):
        return "<Menu '%s'>" % self.titre

    def GetParent(self):
        return self.parent

    def Add(self, code="", titre="", icone="", url=None, toujours_afficher=False, compatible_demo=True, args=None):
        menu = Menu(self, code=code, titre=titre, icone=icone, url=url, args=args, user=self.user,
                    compatible_demo=compatible_demo, toujours_afficher=toujours_afficher)

        # Determine if the menu should be added
        if toujours_afficher or (code and self.user and self.user.has_perm(f"core.{code}")):
            self.children.append(menu)
        else:
            # If the parent is not set to always display, log and skip adding
            if self.parent and not self.parent.toujours_afficher:
                print(f"Skipping menu {code}: parent 'toujours_afficher'={self.parent.toujours_afficher}")
            return None

        return menu

    def GetUrl(self):
        if self.args:
            return reverse_lazy(self.code, args=self.args)
        return reverse_lazy(self.code)

    def GetChildren(self):
        return self.children

    def GetChildrenParts(self):
        """ Divise la liste des items en 2 colonnes """
        liste = copy.copy(self.GetChildren())
        nbre_parts = 2
        for i in range(0, nbre_parts):
            yield liste[i::nbre_parts]
        return liste

    def GetBrothers(self):
        brothers = copy.copy(self.parent.children)
        brothers.remove(self)
        return brothers

    def HasChildren(self):
        return len(self.children) > 0

    def Find(self, code=""):
        def boucle(children):
            for child in children:
                if child.code == code:
                    return child
                resultat = boucle(child.GetChildren())
                if resultat != None :
                    return resultat
        return boucle(self.GetChildren())

    def GetBreadcrumb(self):
        breadcrumb = [self,]

        def boucle(menu):
            parent = menu.GetParent()
            breadcrumb.append(parent)
            if parent.GetParent() != None:
                boucle(menu=parent)

        boucle(menu=self)
        breadcrumb.reverse()

        return breadcrumb[1:]
