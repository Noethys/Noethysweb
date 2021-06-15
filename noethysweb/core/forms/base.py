# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.models import Structure


class FormulaireBase():
    def __init__(self, *args, **kwargs):
        if not hasattr(self, "request"):
            self.request = kwargs.pop("request", None)
        self.mode = kwargs.pop("mode", None)
        super(FormulaireBase, self).__init__(*args, **kwargs)

        # Définit les caractéristiques du champ de la structure associée
        if self.request and "structure" in self.fields:
            # Affiche uniquement les structures associées à l'utilisateur
            self.fields["structure"].queryset = self.request.user.structures.all().order_by("nom")
            if not self.fields["structure"].required:
                self.fields["structure"].empty_label = "Toutes les structures"

            # self.fields["structure"].empty_label = "Toutes les structures"
            # self.fields["structure"].queryset = Structure.objects.filter(pk=self.request.user.structure_actuelle_id)
            # # Si création, sélectionne la structure actuelle de l'utilisateur en cours
            # if not self.instance.pk:
            #     self.fields["structure"].initial = self.request.user.structure_actuelle_id

        # Envoi du request dans le widget activites pour effectuer un filtre sur les structures accessibles
        if self.request and "activites" in self.fields:
            self.fields["activites"].widget.request = self.request


    def Set_mode_consultation(self):
        # Désactive les champs en mode consultation
        for nom, field in self.fields.items():
            field.disabled = True
            field.help_text = None
