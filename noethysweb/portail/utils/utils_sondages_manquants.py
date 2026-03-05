from core.models import Sondage, SondageRepondant, Rattachement, Inscription


def Get_sondages_manquants(famille=None):
    """
    Retourne la liste des sondages (formulaires) que la famille n'a pas encore complétés.

    La liste peut être retrouvé en trouvant tous les structures de la famille et en choppant tous les sondages de la structure qui ont le bon type de public.

    Retourne une liste de dictionnaires avec les informations sur chaque sondage manquant.
    """
    if not famille:
        return []

    sondages_manquants = []

    # Récupérer toutes les structures auxquelles la famille est rattachée via ses inscriptions
    inscriptions = Inscription.objects.select_related('activite', 'activite__structure').filter(famille=famille)
    structure_ids = inscriptions.values_list('activite__structure', flat=True).distinct()

    # Récupérer tous les sondages actifs pour ces structures
    sondages = Sondage.objects.filter(structure__in=structure_ids, structure__visible=True)

    # Récupérer tous les répondants existants pour cette famille
    repondants_existants = SondageRepondant.objects.filter(famille=famille)

    # Créer un dictionnaire des réponses existantes pour un accès rapide
    # Pour les sondages de type "famille" : {idsondage: True}
    # Pour les sondages de type "individu" : {idsondage: {idindividu: True}}
    dict_reponses_famille = {}
    dict_reponses_individu = {}

    for repondant in repondants_existants:
        if repondant.sondage.public == "famille":
            dict_reponses_famille[repondant.sondage.idsondage] = True
        else:  # type "individu"
            if repondant.sondage.idsondage not in dict_reponses_individu:
                dict_reponses_individu[repondant.sondage.idsondage] = set()
            if repondant.individu_id:
                dict_reponses_individu[repondant.sondage.idsondage].add(repondant.individu_id)

    # Récupérer les rattachements de la famille (individus non décédés)
    rattachements = Rattachement.objects.select_related('individu').filter(
        famille=famille,
        individu__deces=False
    )

    # Pré-chargement des structures par individu pour éviter les requêtes en boucle
    # On crée un dictionnaire : {id_individu: [id_structure1, id_structure2]}
    dict_structures_par_individu = {}
    for inscription in inscriptions:
        ind_id = inscription.individu_id
        struct_id = inscription.activite.structure_id
        if ind_id not in dict_structures_par_individu:
            dict_structures_par_individu[ind_id] = set()
        dict_structures_par_individu[ind_id].add(struct_id)

    # Parcourir tous les sondages
    for sondage in sondages:
        if sondage.public == "famille":
            # (Logique famille inchangée...)
            if sondage.idsondage not in dict_reponses_famille:
                sondages_manquants.append({
                    'sondage': sondage,
                    'titre': sondage.titre,
                    'code': sondage.code,
                    'type': 'famille',
                    'article': None,
                    'individu': None,
                })

        else:  # public == "individu"
            # On ne boucle que sur les individus qui ont une inscription
            # dans la structure du sondage
            for rattachement in rattachements:
                individu = rattachement.individu

                # --- NOUVELLE LOGIQUE DE FILTRAGE ---
                # On vérifie si l'individu est inscrit dans la structure du sondage
                structures_individu = dict_structures_par_individu.get(individu.pk, set())

                if sondage.structure_id not in structures_individu:
                    # L'individu n'est pas concerné par cette structure, on passe au suivant
                    continue

                # Facultatif : On peut garder le filtre par catégorie en plus si besoin
                if sondage.categories_rattachements:
                    categories = [int(cat) for cat in sondage.categories_rattachements]
                    if rattachement.categorie not in categories:
                        continue
                # ------------------------------------

                # Vérifier si cet individu a déjà répondu
                reponses_sondage = dict_reponses_individu.get(sondage.idsondage, set())
                if individu.pk not in reponses_sondage:
                    sondages_manquants.append({
                        'sondage': sondage,
                        'titre': sondage.titre,
                        'code': sondage.code,
                        'type': 'individu',
                        'individu': individu,
                        'article': None,
                    })

    return sondages_manquants


def Get_sondages_manquants_individu(individu=None, famille=None, structure=None):
    """
    Retourne la liste des sondages que l'individu n'a pas encore complétés.

    - Pour les sondages de type "individu" : vérifie la réponse pour cet individu
    - Pour les sondages de type "famille" : vérifie si la famille a répondu

    Retourne une liste de dictionnaires compatibles avec le template existant.
    """

    sondages_manquants = []

    # Tous les sondages actifs de ces structures
    sondages = Sondage.objects.filter(
        structure__in=structure,
        structure__visible=True
    )

    # Réponses existantes
    repondants = SondageRepondant.objects.filter(
        sondage__in=sondages,
        individu=individu.idindividu
    )

    # Réponses famille
    reponses_famille = set(
        r.sondage_id for r in repondants
        if r.sondage.public == "famille"
    )

    # Réponses individu (uniquement pour cet individu)
    reponses_individu = set(
        r.sondage_id for r in repondants
        if r.sondage.public == "individu" and r.individu_id == individu.pk
    )

    # Parcours des sondages
    for sondage in sondages:

        # --- SONDAGE FAMILLE ---
        if sondage.public == "famille":
            if sondage.idsondage not in reponses_famille:
                sondages_manquants.append({
                    'sondage': sondage,
                    'titre': sondage.titre,
                    'code': sondage.code,
                    'type': 'famille',
                    'article': None,
                    'individu': None,
                })

        # --- SONDAGE INDIVIDU ---
        else:
            # Vérifier la catégorie de rattachement si définie
            if sondage.categories_rattachements:
                categories = [int(c) for c in sondage.categories_rattachements]
                if rattachement.categorie not in categories:
                    continue

            # Vérifier si l'individu a répondu
            if sondage.idsondage not in reponses_individu:
                sondages_manquants.append({
                    'sondage': sondage,
                    'titre': sondage.titre,
                    'code': sondage.code,
                    'type': 'individu',
                    'article': None,
                    'individu': individu,
                })

    return sondages_manquants