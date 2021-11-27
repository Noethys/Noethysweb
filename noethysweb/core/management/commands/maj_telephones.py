# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import ContactUrgence, Individu, Medecin


class Command(BaseCommand):
    help = 'MAJ des téléphones'

    def handle(self, *args, **kwargs):
        """ Ajoute un point à la fin des numéros de téléphone """
        nbre_modifications = 0
        for classe in (ContactUrgence, Individu, Medecin):
            for item in classe.objects.all():
                dirty = False
                for champ in ("tel_domicile", "tel_mobile", "tel_travail", "tel_cabinet", "travail_tel"):
                    valeur = getattr(item, champ, None)
                    if valeur:
                        if len(valeur) == 14 and not valeur.endswith("."):
                            setattr(item, champ, valeur + ".")
                            dirty = True
                            nbre_modifications += 1
                if dirty:
                    item.save()
        self.stdout.write("%d modifications effectuees" % nbre_modifications)
        self.stdout.write(self.style.SUCCESS("MAJ OK"))
