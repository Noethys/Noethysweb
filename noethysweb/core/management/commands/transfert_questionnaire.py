# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Transfert les réponses d'un questionnaire vers une autre question"

    def add_arguments(self, parser):
        parser.add_argument("idquestion_origine", type=int, help="ID de la question d'origine")
        parser.add_argument("idquestion_destination", type=int, help="ID de la question de destination")

    def handle(self, *args, **kwargs):
        from core.models import QuestionnaireReponse
        reponses_destination = {(reponse.individu_id, reponse.famille_id): reponse for reponse in QuestionnaireReponse.objects.filter(question_id=kwargs["idquestion_destination"])}
        for reponse in QuestionnaireReponse.objects.filter(question_id=kwargs["idquestion_origine"]):
            reponse_destination = reponses_destination.get((reponse.individu_id, reponse.famille_id), None)
            if reponse_destination:
                # Ne fonctionne que pour des questions Case à cocher > Liste déroulante Oui/Non
                reponse_destination.reponse = "Oui" if reponse.reponse == "True" else ""
                reponse_destination.save()
        self.stdout.write(self.style.SUCCESS("Transfert OK"))
