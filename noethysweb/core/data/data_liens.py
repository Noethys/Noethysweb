# -*- coding: utf-8 -*-


#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

DICT_TYPES_LIENS = {
    1: {"M": "père", "F": "mère", "public": "A", "lien": 2, "type": "parent", "texte": {"M": "est son père", "F": "est sa mère"}},
    2: {"M": "fils", "F": "fille", "public": "E", "lien": 1, "type": "enfant", "texte": {"M": "est son fils", "F": "est sa fille"}},
    
    3: {"M": "frère", "F": "soeur", "public": "AE", "lien": 3, "type": None, "texte": {"M": "est son frère", "F": "est sa soeur"}},
    
    4: {"M": "grand-père", "F": "grand-mère", "public": "A", "lien": 5, "type": None, "texte": {"M": "est son grand-père", "F": "est sa grand-mère"}},
    5: {"M": "petit-fils", "F": "petite-fille", "public": "E", "lien": 4, "type": None, "texte": {"M": "est son petit-fils", "F": "est sa petite-fille"}},
    
    6: {"M": "oncle", "F": "tante", "public": "A", "lien": 7, "type": None, "texte": {"M": "est son oncle", "F": "est sa tante"}},
    7: {"M": "neveu", "F": "nièce", "public": "E", "lien": 6, "type": None, "texte": {"M": "est son neveu", "F": "est sa nièce"}},
    
##    8: {"M": "parrain", "F": "marraine", "public": "AE", "lien": 9 },
##    9: {"M": "filleul", "F": "filleule", "public": "AE", "lien": 8 },
    
    10: {"M": "mari", "F": "femme", "public": "A", "lien": 10, "type": "couple", "texte": {"M": "est son mari", "F": "est sa femme"}},
    
    11: {"M": "concubin", "F": "concubine", "public": "A", "lien": 11, "type": "couple", "texte": {"M": "est son concubin", "F": "est sa concubine"}},
    
    12: {"M": "veuf", "F": "veuve", "public": "A", "lien": 12, "type": "couple", "texte": {"M": "est son veuf", "F": "est sa veuve"}},

    13: {"M": "beau-père", "F": "belle-mère", "public": "A", "lien": 14, "type": None, "texte": {"M": "est son beau-père", "F": "est sa belle-mère"}},
    14: {"M": "beau-fils", "F": "belle-fille", "public": "E", "lien": 13, "type": None, "texte": {"M": "est son beau-fils", "F": "est sa belle-fille"}},    
    
    15: {"M": "pacsé", "F": "pacsée", "public": "A", "lien": 15, "type": "couple", "texte": {"M": "est son pacsé", "F": "est sa pacsée"}},
    
    16: {"M": "ex-mari", "F": "ex-femme", "public": "A", "lien": 16, "type": "ex-couple", "texte": {"M": "est son ex-mari", "F": "est son ex-femme"}},
    
    17: {"M": "ex-concubin", "F": "ex-concubine", "public": "A", "lien": 17, "type": "ex-couple", "texte": {"M": "est son ex-concubin", "F": "est son ex-concubine"}},
    
    18: {"M": "tuteur", "F": "tutrice", "public": "A", "lien": 19, "type": None, "texte": {"M": "est son tuteur", "F": "est sa tutrice"}},
    19: {"M": "sous sa tutelle", "F": "sous sa tutelle", "public": "E", "lien": 18, "type": None, "texte": {"M": "est sous sa tutelle", "F": "est sous sa tutelle"}},

    20: {"M": "assistant maternel", "F": "assistante maternelle", "public": "A", "lien": 21, "type": None, "texte": {"M": "est son assistant maternel", "F": "est son assistante maternelle"}},
    21: {"M": "sous sa garde", "F": "sous sa garde", "public": "E", "lien": 20, "type": None, "texte": {"M": "est sous sa garde", "F": "est sous sa garde"}},

    22: {"M": "ami", "F": "amie", "public": "AE", "lien": 22, "type": None, "texte": {"M": "est son ami", "F": "est son amie"}},

    23: {"M": "voisin", "F": "voisine", "public": "AE", "lien": 23, "type": None, "texte": {"M": "est son voisin", "F": "est sa voisine"}},

    24: {"M": u"assistant familial", "F": u"assistante familiale", "public": "A", "lien": 25, "type": None, "texte": {"M": u"est son assistant familial", "F": u"est son assistante familiale"}},
    25: {"M": u"sous sa garde", "F": u"sous sa garde", "public": "E", "lien": 24, "type": None, "texte": {"M": u"est sous sa garde", "F": u"est sous sa garde"}},

}

