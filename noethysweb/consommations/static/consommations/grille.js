
// Fonction 'icontains' qui rend la fonction contains insensible aux accents et aux majuscules (sert à la recherche)
jQuery.expr[':'].icontains = function(a, i, m) {
    var rExps=[
        {re: /[\xC0-\xC6]/g, ch: "A"},
        {re: /[\xE0-\xE6]/g, ch: "a"},
        {re: /[\xC8-\xCB]/g, ch: "E"},
        {re: /[\xE8-\xEB]/g, ch: "e"},
        {re: /[\xCC-\xCF]/g, ch: "I"},
        {re: /[\xEC-\xEF]/g, ch: "i"},
        {re: /[\xD2-\xD6]/g, ch: "O"},
        {re: /[\xF2-\xF6]/g, ch: "o"},
        {re: /[\xD9-\xDC]/g, ch: "U"},
        {re: /[\xF9-\xFC]/g, ch: "u"},
        {re: /[\xC7-\xE7]/g, ch: "c"},
        {re: /[\xD1]/g, ch: "N"},
        {re: /[\xF1]/g, ch: "n"}
    ];

    var element = $(a).text();
    var search = m[3];
    $.each(rExps, function() {
        element = element.replace(this.re, this.ch);
        search = search.replace(this.re, this.ch);
    });

    return element.toUpperCase()
    .indexOf(search.toUpperCase()) >= 0;
};


// Création d'un UUID
function uuid() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}


/*
* jQuery.ajaxQueue - A queue for ajax requests
*
* (c) 2011 Corey Frang
* Dual licensed under the MIT and GPL licenses.
*
* Requires jQuery 1.5+
*/
(function($) {

// jQuery on an empty object, we are going to use this as our Queue
var ajaxQueue = $({});

$.ajaxQueue = function( ajaxOpts ) {
    var jqXHR,
        dfd = $.Deferred(),
        promise = dfd.promise();

    // queue our ajax request
    ajaxQueue.queue( doRequest );

    // add the abort method
    promise.abort = function( statusText ) {

        // proxy abort to the jqXHR if it is active
        if ( jqXHR ) {
            return jqXHR.abort( statusText );
        }

        // if there wasn't already a jqXHR we need to remove from queue
        var queue = ajaxQueue.queue(),
            index = $.inArray( doRequest, queue );

        if ( index > -1 ) {
            queue.splice( index, 1 );
        }

        // and then reject the deferred
        dfd.rejectWith( ajaxOpts.context || ajaxOpts,
            [ promise, statusText, "" ] );

        return promise;
    };

    // run the actual query
    function doRequest( next ) {
        ajaxOpts.data.donnees = JSON.stringify(get_donnees_for_facturation(ajaxOpts.data.keys_cases_touchees));
        jqXHR = $.ajax( ajaxOpts )
            .done( dfd.resolve )
            .fail( dfd.reject )
            .then( next, next );
    }

    return promise;
};

})(jQuery);


// Variables globales
var dict_cases = {};
var dict_cases_memos = {};
var dict_conso = {};
var dict_memos = {};
var pressepapiers_unites = {};
var id_unique_multi = 1;
var dict_places_prises = {};
var dict_places_presents = {};
var dict_places_temp = {};
var cases_touchees = [];
var chrono;
var touche_clavier = null;


class Case_memo {
    constructor(data) {
        this.key = null;
        this.inscription = null;
        this.date = null;
        this.texte = null;
        this.pk = null;
        this.dirty = false;

        if (data) {
            Object.assign(this, data);
        };
    };

    change() {
        // Envoie les données vers le modal
        if (this.texte) {$('#saisie_memo').val(this.texte)} else {$('#saisie_memo').val("")};
        $('#saisie_memo_key').val(this.key);
        $('#modal_saisir_memo').modal('show');
    }

    importe_memo(texte, pk) {
        this.texte = texte;
        if (pk) {this.pk = pk};
        if (texte === null) {texte = ""};
        $("#" + this.key).text(texte);
    };

    set_memo(texte) {
        if (this.texte !== texte) {this.dirty = true};
        this.texte = texte;
        if ((texte === "") && (this.pk !== null)) {
            dict_suppressions.memos.push(this.pk);
            this.pk = null;
        }
        $("#" + this.key).text(texte);
    };
};


class Case_base {
    constructor(data) {
        this.type_case = null;
        this.key_case_parente = null;
        this.key = null;
        this.individu = null;
        this.groupe = null;
        this.famille = null;
        this.date = null;
        this.unite = null;
        this.activite = null;
        this.inscription = null;
        this.evenement = null;
        this.categorie_tarif = null;
        this.consommations = [];

        // Remplit à partir du dict data fourni
        if (data) {Object.assign(this, data)};
    };

    importe_conso(conso) {
        this.consommations.push(new Conso(conso));
        this.maj_affichage();
    }

    check_compatilites_unites() {
        var self = this, resultat = true;
        var unites_incompatibles = dict_unites[self.unite].incompatibilites;
        $.each(dict_cases, function(key, valeurs) {
            if (valeurs.date === self.date && valeurs.inscription === self.inscription) {
                for (var conso of valeurs.consommations) {
                    if (jQuery.inArray(conso.etat, ["reservation", "present", "attente", "demande"]) !== -1 && jQuery.inArray(valeurs.unite, unites_incompatibles) !== -1) {
                        toastr.error("L'unité " + dict_unites[self.unite].nom + " est incompatible avec l'unité " + dict_unites[valeurs.unite].nom);
                        resultat = false;
                        return false;
                    };
                };
                if (resultat === false) {return false};
            };
        });
        return resultat;
    };

    creer_conso(data={}, maj_facturation=true, options=null) {
        // Message si jour complet
        var is_complet = $("#" + this.key).hasClass("complet");

        // Sélection du mode de saisie
        if (mode === "portail") {
            if (activite_validation_type === "MANUELLE") {
                var mode_saisie = "demande";
            } else {
                var mode_saisie = "reservation";
                if (is_complet) {
                    toastr.warning("Attention, il n'y a plus de place sur cette date ! Une place a été réservée sur la liste d'attente.");
                    var mode_saisie = "attente";
                }
            }
        } else {
            var mode_saisie = $("#mode_saisie").val();
            if (is_complet) {
                toastr.warning("Attention, il n'y a plus de place sur cette date !");
            };
        }

        // Tarif spécial
        if ((options == null) && dict_tarifs_speciaux) {
            if (appliquer_tarif_special(this, data, maj_facturation) === true) {return false}
        }

        // Création de la nouvelle conso
        var conso = new Conso({fields:{
            pk: uuid(),
            etat: mode_saisie,
            individu: this.individu,
            groupe : this.groupe,
            inscription: this.inscription,
            date: this.date,
            unite: this.unite,
            activite: this.activite,
            famille: this.famille,
            categorie_tarif: this.categorie_tarif,
            options: options
        }});
        // Assigne des valeurs si un dict data est donné
        if (data) {
            Object.assign(conso, data);
        };

        // Mémorise dans le pressepapiers
        pressepapiers_unites[this.unite] = {heure_debut: conso.heure_debut, heure_fin: conso.heure_fin, quantite: conso.quantite};

        // Si case parente existe, on lui envoie la conso
        if (this.key_case_parente) {
            if (!(conso in dict_cases[this.key_case_parente].consommations)) {
                dict_cases[this.key_case_parente].consommations.push(conso);
            };
        };

        // Enregistre la conso
        this.consommations.push(conso);
        this.maj_affichage();
        maj_remplissage(this.date);

        // Calcul de la facturation
        if (maj_facturation === true) {
            facturer(this);
        };

    };

    // Modifier une conso existante
    modifier_conso(data={}, maj_facturation=false) {
        var conso = this.consommations[0];
        Object.assign(conso, data);
        conso.dirty = true;
        this.consommations[0] = conso;
        this.maj_affichage();
        maj_remplissage(this.date);
        if (conso.facture) {
            // Par sécurité, pour éviter un recalcul d'une prestation facturée
            toastr.warning("La prestation de la consommation " + dict_unites[this.unite].nom + " ne sera pas recalculée car elle a déjà été facturée.");
            maj_facturation = false;
        };
        if (maj_facturation === true) {
            facturer(this);
        }
        return true;
    };

    detail(action="modifier") {
        // Envoie les infos de la conso vers le modal
        $('#saisie_detail_heure_debut').val(null);
        $('#saisie_detail_heure_fin').val(null);

        if (this.consommations.length > 0) {
            if (this.consommations[0].heure_debut) {$('#saisie_detail_heure_debut').val(this.consommations[0].heure_debut)};
            if (this.consommations[0].heure_fin) {$('#saisie_detail_heure_fin').val(this.consommations[0].heure_fin)};
            if (this.consommations[0].quantite) {$('#saisie_detail_quantite').val(this.consommations[0].quantite)};
            $('#saisie_detail_groupe').val(this.consommations[0].groupe);
            $("input[name='saisie_etat'][value='" + this.consommations[0].etat + "']").prop("checked",true);
        } else {
            // Envoie les infos par défaut si ajout
            if (dict_unites[this.unite].heure_debut) {$('#saisie_detail_heure_debut').val(dict_unites[this.unite].heure_debut)};
            if (dict_unites[this.unite].heure_fin) {$('#saisie_detail_heure_fin').val(dict_unites[this.unite].heure_fin)};
            $('#saisie_detail_quantite').val(1);
            $('#saisie_detail_groupe').val(this.groupe);
            $("input[name='saisie_etat'][value='" + $("#mode_saisie").val() + "']").prop("checked",true);
        };

        $('#saisie_detail_key').val(this.key);
        $('#saisie_detail_action').val(action);
        $('#modal_saisir_detail').modal('show');
    };

    // Calcule le remplissage
    calc_remplissage() {
        // Annule la maj si il y a déjà une conso affichée dans la case
        if (this.consommations.length > 0) {return false};

        var liste_places_initiales = [];
        var liste_places_restantes = [];
        var liste_seuils = [];
        var nbre_places_initiales = null;
        var nbre_places_restantes = null;
        var seuil_alerte = null;

        // Recherche pour chaque unité de remplissage les valeurs
        for (var idunite_remplissage of dict_unites[this.unite].unites_remplissage) {
            for (var idgroupe of [this.groupe, 0]) {
                // Recherche la capacité max sur le groupe
                var key1 = this.date + "_" + idunite_remplissage + "_" + idgroupe;
                if (key1 in dict_capacite) {var capacite_max = dict_capacite[key1]} else {var capacite_max = null};

                if (capacite_max) {
                    // Recherche le nbre de places prises
                    var nbre_places_prises = 0;
                    for (var idunite_conso of dict_unites_remplissage[idunite_remplissage]["unites_conso"]) {
                        var key2 = this.date + "_" + idunite_conso + "_" + idgroupe;
                        if (key2 in dict_places_prises) {
                            nbre_places_prises += dict_places_prises[key2]
                        };
                    };

                    // Calcule le nombre de places disponibles
                    liste_places_initiales.push(capacite_max)
                    liste_places_restantes.push(capacite_max - nbre_places_prises);
                    liste_seuils.push(dict_unites_remplissage[idunite_remplissage]["seuil_alerte"]);
                };
            };
        };

        // Conserve uniquement les valeurs les plus basses
        if (liste_places_initiales.length > 0) {nbre_places_initiales = Math.min.apply(null, liste_places_initiales)};
        if (liste_places_restantes.length > 0) {nbre_places_restantes = Math.min.apply(null, liste_places_restantes)};
        if (liste_seuils.length > 0) {seuil_alerte = Math.min.apply(null, liste_seuils)};

        // Envoie les valeurs à l'affichage de la case
        if (nbre_places_restantes !== null && (!$("#" + this.key).hasClass("fermeture"))) {
            var klass = null;
            if (nbre_places_restantes > seuil_alerte) {klass = "disponible"};
            if ((nbre_places_restantes > 0) && (nbre_places_restantes <= seuil_alerte)) {klass = "dernieresplaces"};
            if (nbre_places_restantes <= 0) {klass = "complet"};

            if (!$("#" + this.key).hasClass(klass)) {
                $("#" + this.key).removeClass("disponible dernieresplaces complet");
                $("#" + this.key).addClass(klass);
            }
        };
    };
};

class Case_standard extends Case_base {
    constructor(data) {
        super(data);
        // Dessine la case
        $("#" + this.key).html("<span class='infos'></span><span class='icones'></span><span class='groupe'></span>");
    };

    has_conso() {
        if (this.consommations.length > 0) {return true} else {return false};
    };

    // MAJ de l'affichage du contenu de la case
    maj_affichage() {
        $("#" + this.key).removeClass("reservation attente refus present absentj absenti demande");
        $("#" + this.key + " .infos").html("");
        $("#" + this.key + " .groupe").html("");
        $("#" + this.key + " .icones").html("");

        // Si c'est une case event
        if (this.type_case === "event") {
            var label_evenement = "<span style='text-transform : uppercase;font-weight: bold;' title='" + this.evenement.nom.replace(/'/g, '&#39;') + "'>" + this.evenement.nom + "</span>";
            if (this.evenement.description) {
                label_evenement += " <span class='ml-2' title='" + this.evenement.description.replace(/'/g, '&#39;') + "'><i class='fa fa-info-circle'></i> " + this.evenement.description + "</span>";
            }
            $("#" + this.key + " .infos").html(label_evenement);
        };

        // Si la case est sélectionnée
        if (this.has_conso()) {
            var conso = this.consommations[0];

            // Dessine la couleur de fond
            $("#" + this.key).addClass(conso.etat);

            // Dessine les infos
            var infos = "";
            if ((this.type_case === "horaire" || this.type_case === "multi") && (mode !== "portail")) {
                var hdebut, hfin;
                if (conso.heure_debut) {hdebut = conso.heure_debut.substring(0,5).replace(":", "h")} else {hdebut="?"};
                if (conso.heure_fin) {hfin = conso.heure_fin.substring(0,5).replace(":", "h")} else {hfin="?"};
                infos = hdebut + "-" + hfin
                $("#" + this.key + " .infos").html(infos);
            };
            if ((this.type_case === "quantite") && (mode !== "portail")) {
                if (conso.quantite) {infos = conso.quantite} else {infos = 1};
                $("#" + this.key + " .infos").html(infos);
            };

            // Dessine le nom du groupe
            if (Object.keys(dict_groupes).length > 1) {
                $("#" + this.key + " .groupe").html(dict_groupes[conso.groupe].nom);
            };
            if (mode === "portail") {
                var texte = "";
                if (conso.etat === "reservation") {texte= "Réservé"}
                if (conso.etat === "attente") {texte= "Attente"}
                if (conso.etat === "present") {texte= "Présent"}
                if (conso.etat === "refus") {texte= "Refus"}
                if (conso.etat === "demande") {texte= "Demande"}
                if ((conso.etat === "absenti") || (conso.etat === "absentj")) {texte= "Absent"}
                if (dict_unites[this.unite].imposer_saisie_valeur && this.type_case === "horaire") {
                    texte += " (" + conso.heure_debut.substring(0,5).replace(":", "h") + "-" + conso.heure_fin.substring(0,5).replace(":", "h") + ")";
                }
                if (dict_unites[this.unite].imposer_saisie_valeur && this.type_case === "quantite") {
                    texte += " (" + conso.quantite + ")";
                }
                $("#" + this.key + " .groupe").html(texte);
            }

            // Dessine les icones
            var texte_icones = "";
            if (conso.prestation && dict_prestations[conso.prestation] && dict_prestations[conso.prestation].forfait_date_debut) {texte_icones += " <i class='fa fa-tag' style='color: " + dict_prestations[conso.prestation].couleur + ";' title='Forfait crédit'></i>"};
            if ((conso.prestation === null) && (mode !== "portail")) {texte_icones += " <i class='fa fa-exclamation-triangle text-orange' title='Aucune prestation'></i>"};
            if (conso.etat === "present") {texte_icones += " <i class='fa fa-check-circle-o text-green' title='Présent'></i>"};
            if (conso.etat === "absenti") {texte_icones += " <i class='fa fa-times-circle-o text-red' title='Absence injustifiée'></i>"};
            if (conso.etat === "absentj") {texte_icones += " <i class='fa fa-times-circle-o text-green' title='Absence justifiée'></i>"};
            if (conso.forfait === 2) {texte_icones += " <i class='fa fa-lock text-red' title='Cette consommation est non supprimable car elle est associée à un forfait daté'></i>"};
            if (conso.facture) {texte_icones += " <i class='fa fa-file-text-o text-black-50' title='La prestation associée apparaît sur une facture'></i>"};
            $("#" + this.key + " .icones").html(texte_icones);

            // Pour les tests, affiche l'id de la prestation
            // $("#" + this.key + " .groupe").html(conso.prestation);
        };
    };

    // Appliquer un forfait crédit
    appliquer_forfait() {
        $('#modal_forfaits').modal('show');
        $("#id_date_debut").datepicker("setDate", moment(this.date).format("DD/MM/YYYY"));
    };

    // Supprimer une conso
    supprimer(maj_facturation=true) {
        if (this.is_locked()) {return false}
        // Mémorisation de la suppression
        if ((this.consommations.length > 0) && (!(this.consommations[0].pk.toString().includes("-")))) {
            dict_suppressions.consommations.push(this.consommations[0].pk)
        };
        this.consommations = [];
        this.maj_affichage();
        maj_remplissage(this.date);

        // Calcul de la facturation
        if (maj_facturation === true) {
            facturer(this);
        };

        return true;
    };

    copier() {
        // Vérifie la compatiblité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};
        // Si une conso existe dans le pressepapiers, on la reproduit
        if (this.unite in pressepapiers_unites) {
            this.creer_conso(pressepapiers_unites[this.unite]);
            return true;
        };
    }

    // Attribue un état à la conso
    set_etat(etat) {
        if (this.has_conso()) {
            if ((jQuery.inArray(etat, ["present", "absenti", "absentj"]) !== -1) && (jQuery.inArray(this.consommations[0].etat, ["attente", "refus", "demande"]) !== -1)) {
                toastr.error("Vous ne pouvez pas pointer une réservation en attente, en refus ou en demande");
                return false;
            };

            if ((this.consommations[0].facture) && (jQuery.inArray(etat, ["attente", "refus"]) !== -1)) {
                toastr.error("Vous ne pouvez pas sélectionner cet état car la prestation est déjà facturée");
                return false;
            };

            // Vérifie la compatibilité avec les autres unités
            if ((etat === "reservation" || etat === "present" || etat === "demande") && this.check_compatilites_unites() === false) {return false};

            // Modifie l'état de la conso
            this.modifier_conso({etat: etat}, true);
            return true;
        }
    };

    // Attribue un groupe à la conso
    set_groupe(groupe) {
        if (this.has_conso()) {
            this.modifier_conso({groupe: groupe}, true);
            return true;
        };
    };

    // Attribue un groupe à la conso
    set_prestation(idprestation) {
        if (this.has_conso()) {
            this.modifier_conso({prestation: idprestation});
            return true;
        };
    };

    // Attribue un idconso à la conso
    set_idconso(idconso) {
        if (this.has_conso()) {
            this.modifier_conso({pk: idconso});
            return true;
        };
    };

    set_dirty(etat) {
        if (this.has_conso()) {
            this.consommations[0].dirty = etat;
        };
    }

    // Vérifie si la conso est verrouillée
    is_locked() {
        if ((this.consommations.length > 0) && (jQuery.inArray(this.consommations[0].etat, ["present", "absentj", "absenti"]) !== -1)) {
            toastr.error("Vous ne pouvez pas modifier ou supprimer une consommation déjà pointée");
            return true;
        }
        if ((this.consommations.length > 0) && (this.consommations[0].forfait)) {
            toastr.error("Vous ne pouvez pas supprimer cette consommation car elle est associée à un forfait daté");
            return true;
        }
        if (this.consommations[0].facture) {
            toastr.error("Vous ne pouvez pas modifier ou supprimer une consommation dont la prestation associée apparaît sur une facture");
            return true;
        }
        if ((mode === "portail") && (this.consommations.length > 0) && (this.consommations[0].etat === "refus")) {
            toastr.error("Vous ne pouvez pas modifier ou supprimer une consommation refusée");
            return true;
        }
        return false;
    };

};

class Case_unitaire extends Case_standard {
    constructor(data) {
        super(data);
        this.type_case = "unitaire";
    };

    ajouter(data={}, maj_facturation=true) {
        if (this.has_conso()) {return false};

        // Vérifie la compatiblité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};

        // Saisie des heures par défaut
        if (!("heure_debut" in data) && dict_unites[this.unite].heure_debut) {data["heure_debut"] = dict_unites[this.unite].heure_debut};
        if (!("heure_fin" in data) && dict_unites[this.unite].heure_fin) {data["heure_fin"] = dict_unites[this.unite].heure_fin};

        // Mode pointeuse
        if (mode === 'pointeuse') {this.detail("ajouter"); return false};

        // Créer conso
        this.creer_conso(data, maj_facturation);
        return true;
    };

    // Toggle une conso
    toggle() {
        if (this.has_conso()) {
            if (mode === 'pointeuse') {
                this.detail("modifier");
            } else {
                this.supprimer();
            };
        } else {
            this.ajouter();
        };
    };

};

class Case_horaire extends Case_standard {
    constructor(data) {
        super(data);
        this.type_case = "horaire";
    };

    ajouter(data={}, maj_facturation=true) {
        if (this.has_conso()) {return false};

        // Vérifie la compatibilité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};

        // Si saisie en mode portail
        if (((mode === "portail") && (dict_unites[this.unite].imposer_saisie_valeur === false)) || (touche_clavier === 17)) {
            if (!("heure_debut" in data)) {data["heure_debut"] = dict_unites[this.unite].heure_debut};
            if (!("heure_fin" in data)) {data["heure_fin"] = dict_unites[this.unite].heure_fin};
        };

        // Saisie directe si data donnée
        if (Object.keys(data).length > 0) {
            this.creer_conso(data, maj_facturation);
            return true;
        };

        // Mode pointeuse
        if (mode === 'pointeuse') {this.detail("ajouter"); return false};

        // Envoie les heures par défaut de l'unité vers le modal
        if (dict_unites[this.unite].heure_debut) {$('#saisie_heure_debut').val(dict_unites[this.unite].heure_debut)};
        if (dict_unites[this.unite].heure_fin) {$('#saisie_heure_fin').val(dict_unites[this.unite].heure_fin)};

        $('#saisie_heure_key').val(this.key);
        $('#saisie_heure_action').val("ajouter");
        $('#modal_saisir_horaires').modal('show');
    };

    modifier () {
        // Mode pointeuse
        if (mode === 'pointeuse') {this.detail("modifier"); return false};

        // Vérifie si verrouillage
        if (this.is_locked()) {return false};

        // Envoie les heures de la conso vers le modal
        if (this.consommations[0].heure_debut) {$('#saisie_heure_debut').val(this.consommations[0].heure_debut)};
        if (this.consommations[0].heure_fin) {$('#saisie_heure_fin').val(this.consommations[0].heure_fin)};

        $('#saisie_heure_key').val(this.key);
        $('#saisie_heure_action').val("modifier");
        $('#modal_saisir_horaires').modal('show');
    };

    // Toggle une conso
    toggle() {
        if (this.has_conso()) {
            if (((mode === "portail") && (dict_unites[this.unite].imposer_saisie_valeur === false)) || (touche_clavier === 17)) {
                this.supprimer();
            } else {
                this.modifier();
            };
        } else {
            this.ajouter();
        };
    };


};

class Case_quantite extends Case_standard {
    constructor(data) {
        super(data);
        this.type_case = "quantite";
    };

    ajouter(data={}, maj_facturation=true) {
        if (this.has_conso()) {return false};

        // Vérifie la compatiblité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};

        // Saisie des heures par défaut
        if (!("heure_debut" in data) && dict_unites[this.unite].heure_debut) {data["heure_debut"] = dict_unites[this.unite].heure_debut};
        if (!("heure_fin" in data) && dict_unites[this.unite].heure_fin) {data["heure_fin"] = dict_unites[this.unite].heure_fin};

        // Si saisie en mode portail
        if (((mode === "portail") && (dict_unites[this.unite].imposer_saisie_valeur === false)) || (touche_clavier === 17)) {
            if (!("quantite" in data)) {data["quantite"] = 1};
        };

        // Saisie directe si data donnée
        if (Object.keys(data).length > 0) {
            this.creer_conso(data, maj_facturation);
            return true;
        };

        // Mode pointeuse
        if (mode === 'pointeuse') {this.detail("ajouter"); return false};

        $('#saisie_quantite_key').val(this.key);
        $('#saisie_quantite_action').val("ajouter");
        $('#modal_saisir_quantite').modal('show');
    };

    modifier () {
        // Mode pointeuse
        if (mode === 'pointeuse') {this.detail("modifier"); return false};

        // Vérifie si verrouillage
        if (this.is_locked()) {return false};

        // Envoie la quantité de la conso vers le modal
        if (this.consommations[0].quantite) {$('#saisie_quantite').val(this.consommations[0].quantite)};

        $('#saisie_quantite_key').val(this.key);
        $('#saisie_quantite_action').val("modifier");
        $('#modal_saisir_quantite').modal('show');
    };

    // Toggle une conso
    toggle() {
        if (this.has_conso()) {
            if (((mode === "portail") && (dict_unites[this.unite].imposer_saisie_valeur === false)) || (touche_clavier === 17)) {
                this.supprimer();
            } else {
                this.modifier();
            };
        } else {
            this.ajouter();
        };
    };

};


class Case_evenement extends Case_base {
    constructor(data) {
        super(data);
        this.type_case = "evenement";
        var self = this;

        // Dessine la case événement
        var key_evenement = this.date + "_" + this.unite;
        if (key_evenement in dict_evenements) {
            var liste_evenements = dict_evenements[key_evenement];

            // Création des cases html
            var html = "<table class='table table_evenements'><tbody><tr>";
            liste_evenements.forEach(function(evenement) {
                if ((self.groupe === evenement.groupe) && (!(mode === "portail") || ((mode === "portail") && (evenement.visible_portail === true)))) {
                    var classe_event = $("#" + self.key).hasClass("fermeture") ? "fermeture" : "ouvert";
                    var classe_image_event = "";
                    if ((evenement.categorie) && (dict_categories_evenements[evenement.categorie].image)) {
                        classe_image_event = "event-img-" + dict_categories_evenements[evenement.categorie].image;
                    }
                    if (evenement.image) {
                        classe_image_event = "event-img-" + evenement.image.split("/").pop().split(".").shift();
                    }
                    html += "<td class='case " + classe_event + " " + classe_image_event + "' id='event_" + self.key + "_" + evenement.pk + "'";
                    html += "</td>";
                }
            });
            html += "</tr></tbody></table>";
            $("#" + this.key).html(html);

            liste_evenements.forEach(function(evenement) {
                var key_case_event = "event_" + self.key + "_" + evenement.pk;
                data['key'] = key_case_event;
                data['evenement'] = evenement;
                data['key_case_parente'] = self.key;
                var case_event = new Case_event(data);
                dict_cases[key_case_event] = case_event;
            });
        }

    };

};


class Case_event extends Case_standard {
    constructor(data) {
        super(data);
        this.type_case = "event";
        this.key_case_parente = data.key_case_parente;
        this.maj_affichage();
    };

    ajouter() {
        if (this.has_conso()) {return false};
        // Vérifie la compatiblité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};
        // Vérifie s'il faut ouvrir la modal questions
        if (this.ouvrir_modal_questionnaire()) {return false}
        // Créer conso
        this.creer_conso({evenement: this.evenement.pk, heure_debut: this.evenement.heure_debut, heure_fin: this.evenement.heure_fin});
        return true;
    };

    // Toggle une conso
    toggle() {
        if (this.has_conso()) {
            if (mode === 'pointeuse') {
                this.detail("modifier");
            } else {
                if (this.ouvrir_modal_questionnaire()) {return false}
                this.supprimer();
            };
        } else {
            this.ajouter();
        };
    };

    // Vérifie s'il faut ouvrir la modal des questions
    ouvrir_modal_questionnaire() {
        if ((this.evenement.categorie) && (dict_categories_evenements[this.evenement.categorie].questions)) {
            ouvre_modal_questionnaire(this.key);
            return true;
        } else {
            return false;
        }
    }

    // Calcule le remplissage
    calc_remplissage() {
        // Annule la maj si il y a déjà une conso affichée dans la case
        if (this.consommations.length > 0) {return false};

        // Récupération de la capacité max
        var capacite_max = this.evenement.capacite_max;

        // Recherche le nbre de places prises
        var nbre_places_prises = 0;
        var key = this.date + "_" + this.unite + "_" + this.groupe + "_" + this.evenement.pk;
        if (key in dict_places_prises) {
            nbre_places_prises = dict_places_prises[key];
        }

        if (capacite_max) {
            // Calcule le nombre de places disponibles
            var nbre_places_restantes = capacite_max - nbre_places_prises;

            // Recherche le seuil d'alerte
            var liste_seuils = [];
            var seuil_alerte = null;
            for (var idunite_remplissage of dict_unites[this.unite].unites_remplissage) {
                liste_seuils.push(dict_unites_remplissage[idunite_remplissage]["seuil_alerte"]);
            };
            if (liste_seuils.length > 0) {seuil_alerte = Math.min.apply(null, liste_seuils)};

            // MAJ de l'affichage de la couleur de fond
            var klass = null;
            if (nbre_places_restantes > seuil_alerte) {klass = "disponible"};
            if ((nbre_places_restantes > 0) && (nbre_places_restantes <= seuil_alerte)) {klass = "dernieresplaces"};
            if (nbre_places_restantes <= 0) {klass = "complet"};

            if (!$("#" + this.key).hasClass(klass)) {
                $("#" + this.key).removeClass("disponible dernieresplaces complet");
                $("#" + this.key).addClass(klass);
            };
        };
    };

};



class Case_multihoraires extends Case_base {
    constructor(data) {
        super(data);
        this.type_case = "multihoraires";
        this.data_case = data;

        // Dessine la case multihoraires
        var html = "<table class='table table_multihoraires'><tbody><tr>";
        html += "<td class='case multi_ajouter' style='border: 0px;'><a data-key='" + this.key + "' class='bouton_ajouter_multi' title='Ajouter une consommation' href='#'><i class='fa fa-plus-circle'></i></a></td>";
        html += "</tr></tbody></table>";
        $("#" + this.key).html(html);

        // Maj de l'affichage
        this.maj_affichage();
    };

    maj_affichage() {
        var key_case = this.key;
        var data_case = this.data_case;

        // Suppression des cases existantes
        $("#" + this.key + " td[class*='ouvert']").remove();
        for (var key of Object.keys(dict_cases)) {
            if (key.startsWith("multi_" + key_case)) {
                delete dict_cases[key];
            };
        }

        // Tri des conso par heure de début
        function compare(a, b) {
            if (a.heure_debut > b.heure_debut) {return -1};
            return 1;
        };
        this.consommations.sort(compare);

        // Prépare une liste de conso provisoire
        var liste_conso_temp = this.consommations.slice();
        if (liste_conso_temp.length === 0) {
            liste_conso_temp.push(null);
        };

        // Création des cases conso
        liste_conso_temp.forEach(function(conso) {
            // Attribue un key à la case multi
            var key_case_multi = "multi_" + key_case + "_" + id_unique_multi;
            id_unique_multi += 1;

            // Dessine la case
            $("#" + key_case + ' tr').prepend("<td class='case ouvert' id='" + key_case_multi + "'</td>");

            // Création de la case virtuelle
            var data_temp = data_case;
            data_temp['key'] = key_case_multi;
            if (conso) {
                data_temp['consommations'] = [conso];
            } else {
                data_temp['consommations'] = [];
            }
            data_temp['key_case_parente'] = key_case;
            var case_multi = new Case_multi(data_temp);
            dict_cases[key_case_multi] = case_multi;
        });
    };

    ajouter() {
        // Vérifie la compatiblité avec les autres unités
        if (this.check_compatilites_unites() === false) {return false};

        // Envoie les heures par défaut de l'unité vers le modal
        if (dict_unites[this.unite].heure_debut) {$('#saisie_heure_debut').attr({'value':dict_unites[this.unite].heure_debut})};
        if (dict_unites[this.unite].heure_fin) {$('#saisie_heure_fin').attr({'value':dict_unites[this.unite].heure_fin})};

        $('#saisie_heure_key').val(this.key);
        $('#saisie_heure_action').val("ajouter");
        $('#modal_saisir_horaires').modal('show');
    };

    supprimer(conso) {
        this.consommations.splice($.inArray(conso, this.consommations), 1);
        this.maj_affichage();
        maj_remplissage(this.date);
    }
};

class Case_multi extends Case_horaire {
    constructor(data) {
        super(data);
        this.type_case = "multi";
        this.key_case_parente = data.key_case_parente;
        this.maj_affichage();
    };

    // Supprimer une conso
    supprimer() {
        if (this.is_locked()) {return false}
        // Mémorisation de la suppression
        if (!(this.consommations[0].pk.toString().includes("-"))) {
            dict_suppressions.consommations.push(this.consommations[0].pk);
        };
        // Supprime également la conso dans la case parente
        dict_cases[this.key_case_parente].supprimer(this.consommations[0]);
        this.consommations = [];
        this.maj_affichage();
        facturer(dict_cases[this.key_case_parente])
        return true;
    };
};




class Conso {
    constructor(conso) {
        this.pk = null;
        this.activite = null;
        this.inscription = null;
        this.groupe = null;
        this.heure_debut = null;
        this.heure_fin = null;
        this.etat = null;
        this.verrouillage = null;
        this.date_saisie = null;
        this.utilisateur = null;
        this.categorie_tarif = null;
        this.famille = null;
        this.prestation = null;
        this.forfait = null;
        this.facture = null;
        this.quantite = 1;
        this.statut = null;
        this.case = null;
        this.etiquettes = [];
        this.evenement = null;
        this.badgeage_debut = null;
        this.badgeage_fin = null;
        this.options = null;
        this.extra = null;
        this.dirty = false;

        // Importation depuis un array
        if (conso) {
            if ("fields" in conso) {
                Object.assign(this, conso.fields);
                if (conso.fields.pk) {
                    this.pk = conso.fields.pk;
                } else {
                    this.pk = conso.pk;
                }

            } else {
                Object.assign(this, conso);
                this.pk = conso.pk;
            }
        };

        // Importation des données de la prestation associée
        if (this.prestation in dict_prestations) {
            this.facture = dict_prestations[this.prestation].facture
        };

    }
};





$(function () {
    var case_contextmenu = null;

    // Mémorise la touche enfoncée
    $(window).keydown(function(evt) {touche_clavier = evt.which})
    .keyup(function(evt) {touche_clavier = null});

    // Clic sur les cases
    var isMouseDown = false, statut, ancienne_case;
    $(document).on('mousedown', ".table td[class*='ouvert']", function(e) {
        // Si clic gauche de la souris
        if (e.which === 1) {
            isMouseDown = true;
            var case_tableau = dict_cases[$(this).attr('id')];
            statut = case_tableau.has_conso();
            action_sur_clic(case_tableau, statut);
            return false; // prevent text selection
        }
    });
    $(document).on('mouseover', ".table td[class*='ouvert']", function(e) {
        var case_tableau = dict_cases[$(this).attr('id')];
        if (isMouseDown && ancienne_case !== case_tableau) {
            action_sur_clic(case_tableau, statut);
        }
        ancienne_case = case_tableau;
    });
    $(document).mouseup(function () {
        isMouseDown = false;
    });

    function action_sur_clic(case_tableau, statut) {
        if (touche_clavier === 65 && mode !== "portail") {case_tableau.set_etat("reservation")}
        else if (touche_clavier === 80 && mode !== "portail") {case_tableau.set_etat("present")}
        else if (touche_clavier === 74 && mode !== "portail") {case_tableau.set_etat("absentj")}
        else if (touche_clavier === 73 && mode !== "portail") {case_tableau.set_etat("absenti")}
        else if (touche_clavier === 68 && mode !== "portail") {case_tableau.set_etat("demande")}
        else if (touche_clavier === 67) {case_tableau.copier()}
        else if (touche_clavier === 83) {case_tableau.supprimer()}
        else {
            // Toggle sur la case cliquée
            if (case_tableau.has_conso() === statut) {case_tableau.toggle()};

            // Toggle sur case bis sur touche raccourci unité
            if (touche_clavier in dict_touches_raccourcis) {
                var key_case_bis = case_tableau.date + "_" + case_tableau.inscription + "_" + dict_touches_raccourcis[touche_clavier];
                if (key_case_bis in dict_cases && key_case_bis !== case_tableau.key && dict_cases[key_case_bis].has_conso() === statut) {case_supp = dict_cases[key_case_bis].toggle()};
            }
        }
    };

    // Menu contextuel
    $(document).on('contextmenu', ".ouvert", function(e) {
        case_contextmenu = dict_cases[$(this).attr('id')];
        if (!$("#contextMenu").is(':visible') && case_contextmenu.has_conso()) {
            // Rajoute les groupes à la fin du menu
            $("#contextMenu .ctx_groupe").remove();
            liste_groupes.forEach(function(groupe) {
                if (groupe.fields.activite === case_contextmenu.activite) {
                    $("#contextMenu ul").append("<li><a tabindex='-1' href='#' class='dropdown-item ctx_groupe' data-groupe=" + groupe.pk + ">" + groupe.fields.nom + "</a></li>");
                };
            });

            // Met en évidence l'état et le groupe de la conso
            $("#contextMenu a").css('font-weight', 'normal');
            $("#contextMenu a").removeClass("menu-checked");
            $("#contextMenu a[data-etat='" + case_contextmenu.consommations[0].etat + "']").css('font-weight', 'bold').addClass("menu-checked");
            $("#contextMenu a[data-groupe='" + case_contextmenu.consommations[0].groupe + "']").css('font-weight', 'bold').addClass("menu-checked");

            // Affiche le menu
            $("#contextMenu").css({
                display: "block",
                left: e.clientX,
                top: e.clientY
            });
        } else {
            $("#contextMenu").css({display: "none"});
        }
        return false;
    });
    $('html').click(function() {
         $("#contextMenu").hide();
    });
    $(document).on('click', "#contextMenu li a", function(e) {
        var id = $(this).attr('id');
        if (id === "contextmenu_forfait") {case_contextmenu.appliquer_forfait()};
        if (id === "contextmenu_modifier") {case_contextmenu.detail("modifier")};
        if (id === "contextmenu_supprimer") {case_contextmenu.supprimer()};
        if (id === "contextmenu_reservation") {case_contextmenu.set_etat("reservation")};
        if (id === "contextmenu_attente") {case_contextmenu.set_etat("attente")};
        if (id === "contextmenu_refus") {case_contextmenu.set_etat("refus")};
        if (id === "contextmenu_present") {case_contextmenu.set_etat("present")};
        if (id === "contextmenu_absentj") {case_contextmenu.set_etat("absentj")};
        if (id === "contextmenu_absenti") {case_contextmenu.set_etat("absenti")};
        if (id === "contextmenu_demande") {case_contextmenu.set_etat("demande")};
        if ($(this).hasClass("ctx_groupe")) {case_contextmenu.set_groupe(this.dataset.groupe)};
        $("#contextMenu").hide();
        return false;
    });

    // Clic sur les cases mémo
    $(".table td[class*='memo']").click(function (e) {
        var case_memo = dict_cases_memos[$(this).attr('id')];
        case_memo.change();
        return false; // prevent text selection
    });

    // Clic sur le bouton Ajouter un multi
    $(".bouton_ajouter_multi").click(function(e){
        e.preventDefault();
        var case_multihoraires = dict_cases[this.dataset.key];
        case_multihoraires.ajouter();
        return false;
    });

    // Barre de recherche
    $('#rechercher').on('input',function(e){
        $(".table-grille tr[class*='masquer']").removeClass("masquer");
        $(".table-grille tbody th:not(:icontains('" + $(this).val() + "')):not('.date_regroupement')").closest("tr").addClass("masquer");
    });

    // Recherche avec l'alphabet
    $(".bouton_alphabet").click(function(e){
        var scrolled = false;
        $(".table-grille tbody th").each(function() {
            if ($(this)[0].innerText.substring(0,1) === e.target.innerText) {
                if (scrolled === false) {
                    var $container = $("#table_grille");
                    var $scrollTo = $(this);
                    $container.scrollTop($scrollTo.offset().top - $container.offset().top + $container.scrollTop() - $scrollTo[0].offsetHeight);
                    scrolled = true;
                }
                $(this).fadeTo(100, 0.3, function() { $(this).fadeTo(500, 1.0); });
            }
        });
    });


});


// Calcul des places prises
function maj_remplissage(date) {
    dict_places_prises = {};
    dict_places_presents = {};
    // Recherche des places prises affichées
    $.each(dict_cases, function (key, case_tableau) {
        if (!(case_tableau.type_case === "evenement") && !(case_tableau.type_case === "multi")) {
            for (var conso of case_tableau.consommations) {
                // Mémorise les places pour chaque conso
                if (conso.etat === "reservation" || conso.etat === "present") {
                    for (var idgroupe of [conso.groupe, 0]) {
                        var key = conso.date + "_" + conso.unite + "_" + idgroupe;
                        if (!(key in dict_places_prises)) {dict_places_prises[key] = 0};
                        if (conso.quantite) {var quantite = conso.quantite} else {quantite = 1};
                        dict_places_prises[key] += quantite;

                        // Mémorise uniquement les présents pour les totaux
                        if (conso.etat === "present") {
                            if (!(key in dict_places_presents)) {dict_places_presents[key] = 0};
                            dict_places_presents[key] += quantite;
                        }

                        // Mémorise également les événements
                        if (conso.evenement) {
                            key += "_" + conso.evenement;
                            if (!(key in dict_places_prises)) {dict_places_prises[key] = 0};
                            dict_places_prises[key] += 1;
                            // Mémorise uniquement les présents pour les totaux
                            if (conso.etat === "present") {
                                if (!(key in dict_places_presents)) {dict_places_presents[key] = 0};
                                dict_places_presents[key] += 1;
                            }
                        };
                    };
                };
            };
        };
    });

    // Ajout des places des individus non affichés
    Object.assign(dict_places_prises, dict_places);

    dict_places_temp = dict_places_prises;
    if ($("#id_afficher_presents_totaux").val() === "oui") {
        dict_places_temp = dict_places_presents;
    }

    // Maj de la box totaux
    $("#table_totaux td[id^='total_']").each(function() {
        var key = periode_json.selections.jour + "_" + this.id.slice(6);
        if (key in dict_places_temp) {
            $(this).html(dict_places_temp[key]);
        } else {
            $(this).html(0);
        };
    });

    $("#table_totaux td[id^='total_remplissage_']").each(function() {
        idunite_remplissage = $(this).data("idunite");
        idgroupe = $(this).data("idgroupe");
        var nbre_places_prises = 0;
        if (idunite_remplissage in dict_unites_remplissage) {
            for (var idunite_conso of dict_unites_remplissage[idunite_remplissage]["unites_conso"]) {
                var key = periode_json.selections.jour + "_" + idunite_conso + "_" + idgroupe;
                if (key in dict_places_temp) {
                    nbre_places_prises += dict_places_temp[key]
                };
            };
        };
        $(this).html(nbre_places_prises);
    });

    // MAJ du remplissage des cases
    $.each(dict_cases, function (key, case_tableau) {
        if ((date === undefined) || (case_tableau.date === date)) {
            case_tableau.calc_remplissage();
        };
    });

};


// Actions au chargement de la page
$(document).ready(function() {

    // Importe les conso en mémoire
    $.each(dict_conso, function (key, liste_conso) {
        if (key in dict_cases) {
            liste_conso.forEach(function(conso) {
                dict_cases[key].importe_conso(conso);
            });
        };
    });

    // Importe les conso existantes
    for (var conso of liste_conso_existantes) {
        var key = conso.fields.date + "_" + conso.fields.inscription + "_" + conso.fields.unite;
        if (conso.fields.evenement !== null) {key = "event_" + key + "_" + conso.fields.evenement};
        if ((key in dict_cases) && !(key in dict_conso)) {
            dict_cases[key].importe_conso(conso);
        };
    };

    // Importe les mémos en mémoire
    $.each(dict_memos, function (key, valeurs) {
        if (key in dict_cases_memos) {
            dict_cases_memos[key].importe_memo(valeurs.texte, valeurs.pk);
        };
    });

    // Importe les mémos journaliers
    for (var memo of liste_memos_existants) {
        var key = memo.fields.date + "_" + memo.fields.inscription;
        if ((key in dict_cases_memos) && !(key in dict_memos)) {
            dict_cases_memos[key].importe_memo(memo.fields.texte, memo.pk);
        };
    };

    // MAJ du remplissage
    maj_remplissage();

    // MAJ du box facturation
    maj_box_facturation();

    // Affiche la table
    $(".table").removeClass("masquer");
    $("#in_progress").addClass("masquer");
    $("#in_progress").removeClass("overlay");

    $('[name=bouton_outils]').on('click', function(event) {
        $('#modal_outils').modal('show');
    });

    $('[name=bouton_parametres]').on('click', function(event) {
        $('#modal_parametres').modal('show');
    });

    $('[name=bouton_totaux]').on('click', function(event) {
        $('#modal_totaux').modal('show');
    });

    $('[name=bouton_suggestions]').on('click', function(event) {
        $('#modal_suggestions').modal('show');
    });

    $('.suggestion').on('click', function(event) {
        $('#rechercher').val($(this).data("suggestion")).trigger("input");
        $('#modal_suggestions').modal('hide');
    });

    $('[name=bouton_enregistrer]').on('click', function(event) {
        if (afficher_facturation === false) {
            // Si mode portail, on génére la facturation avant le submit
            var box = bootbox.dialog({
                message: "<p class='text-center mb-0'><i class='fa fa-spin fa-cog'></i> Veuillez patienter...</p>",
                closeButton: false
            });
            tout_recalculer();
        } else {
            $('#form-maj').submit();
        }
    });

    $('[name=bouton_annuler]').on('click', function(event) {
        if (mode === "pointeuse") {
            window.location.href = url_annuler;
            return
        };
        var box = bootbox.dialog({
            title: "Fermer le planning",
            message: "Souhaitez-vous vraiment fermer le planning ? <br>Les éventuelles modifications effectuées seront perdues...",
            buttons: {
                ok: {
                    label: "<i class='fa fa-check'></i> Oui, je veux fermer",
                    className: 'btn-primary',
                    callback: function(){
                        window.location.href = url_annuler;
                    }
                },
                cancel: {
                    label: "<i class='fa fa-ban'></i> Non, je veux rester",
                    className: 'btn-danger',
                }
            }
        });
    });

    // Envoi des paramètres au format json vers le form de maj
    $("#form-maj").on('submit', function(event) {

        if ((mode === "portail") && (!(valider_limitations_evenements()))) {
            event.preventDefault();
            bootbox.hideAll();
            return false;
        }

        if (((mode !== "portail") || (afficher_facturation === true)) && (mode !== "pointeuse")) {

            // Vérifie qu'il n'y a pas un calcul de facturation en cours
            if (!($("#loader_facturation").hasClass("masquer"))) {
                event.preventDefault();
                toastr.error("Vous devez attendre la fin du calcul de la facturation avant de pouvoir quitter");
                return false;
            };

            // Affiche un loader durant le submit
            var box = bootbox.dialog({
                message: "<p class='text-center mb-0'><i class='fa fa-spin fa-cog margin-r-5'></i> Veuillez patienter...</p>",
                closeButton: false
            });

        };

        // Validation du formulaire
        return validation_form(event);
    });

});

function valider_limitations_evenements() {
    var resultat = true;
    $.each(dict_categories_evenements, function (idcategorie, dict_categorie) {
        if (dict_categorie.limitations) {
            var type_limitation = dict_categorie.limitations.indexOf("SEMAINE") >= 0 ? "SEMAINE": "JOUR";
            var nbre_evt_max = parseInt(dict_categorie.limitations.charAt(0));
            var dict_evt_semaines = {};
            var dict_evt_jours = {};
            $.each(dict_cases, function (key, case_tableau) {
                if ((case_tableau.type_case === "event") && (case_tableau.evenement) && (case_tableau.evenement.categorie === parseInt(idcategorie))) {
                    for (var conso of case_tableau.consommations) {
                        var date_moment = moment(conso.date);
                        var key_date = date_moment.year().toString() + date_moment.week().toString()
                        if (!(key_date in dict_evt_semaines)) {dict_evt_semaines[key_date] = 0;}
                        if (!(key_date in dict_evt_jours)) {dict_evt_jours[key_date] = 0;}
                        dict_evt_semaines[key_date] += 1;
                        dict_evt_jours[key_date] += 1;
                        if ((type_limitation === "SEMAINE") && (dict_evt_semaines[key_date] > nbre_evt_max)) {
                            toastr.error("Vous ne pouvez pas réserver plus de " + nbre_evt_max + " événement" + (nbre_evt_max > 1 ? "s" : "") + " de type '" + dict_categorie.nom + "' par semaine");
                            resultat = false;
                            return false;
                        }
                        if ((type_limitation === "JOUR") && (dict_evt_jours[key_date] > nbre_evt_max)) {
                            toastr.error("Vous ne pouvez pas réserver plus de " + nbre_evt_max + " événement" + (nbre_evt_max > 1 ? "s" : "") + " de type '" + dict_categorie.nom + "' par jour");
                            resultat = false;
                            return false;
                        }
                    }
                }
            })
        }
    })
    return resultat;
}

function Get_activite() {
    // return selection_activite;
    return $('#selection_activite').val();
};


function validation_form(event) {

    // Mémorise les conso
    $.each(dict_cases, function (key, case_tableau) {
        if (!(case_tableau.type_case === "evenement") && !(case_tableau.type_case === "multi")) {
            dict_conso[key] = case_tableau.consommations;
        }
        ;
    });

    // Mémorise les mémos
    $.each(dict_cases_memos, function (key, case_memo) {
        dict_memos[key] = {
            "pk": case_memo.pk, "texte": case_memo.texte, "inscription": case_memo.inscription,
            "date": case_memo.date, "dirty": case_memo.dirty
        };
    });

    // Validation des données
    if (Get_periode() === false) {
        event.preventDefault();
        return false;
    };

    // Envoi des données à django
    var donnees = JSON.stringify({
        "individus": Get_individus(),
        "periode": Get_periode(),
        "activite": Get_activite(),
        "ancienne_activite": selection_activite,
        "groupes": Get_groupes(),
        "classes": Get_classes(),
        "mode_parametres": Get_mode_parametres(),
        "consommations": dict_conso,
        "memos": dict_memos,
        "options": Get_options(),
        "suppressions": dict_suppressions,
        "prestations": dict_prestations,
    });
    $('#donnees').val(donnees);
    return true;
};


function afficher_loader_facturation(etat) {
    if (etat) {
        $("#loader_facturation").removeClass("masquer");
        $("#loader_facturation").addClass("overlay");
    } else {
        $("#loader_facturation").removeClass("overlay");
        $("#loader_facturation").addClass("masquer");
    }
};

function search_unites_liees(case_tableau) {
    $.each(dict_cases, function (key, valeurs) {
        if (valeurs.date === case_tableau.date && valeurs.inscription === case_tableau.inscription) {
            for (var conso of valeurs.consommations) {
                dependances_unite = dict_unites[conso.unite].dependances;
                if (dependances_unite.length > 0) {
                    // Recherche les états des unités dépendantes
                    var conso_trouvees = [];
                    for (var idunite_dependance of dependances_unite) {
                        let key_unite_dependance = conso.date + "_" + conso.inscription + "_" + idunite_dependance;
                        if (key_unite_dependance in dict_cases) {
                            var case_dependance = dict_cases[key_unite_dependance]
                            for (var conso_unite_dependance of case_dependance.consommations) {
                                dict_cases[key].modifier_conso({etat: conso_unite_dependance.etat}, false);
                                conso_trouvees.push(conso_unite_dependance);
                            }
                        }
                    }
                    // Si aucune conso dépendante, on supprime la conso
                    if (conso_trouvees.length === 0) {
                        dict_cases[key].supprimer();
                    }
                }
            }
        }
    })
}

function facturer(case_tableau) {
    // Si mode portail, on évite le calcul de la facturation
    if (mode === "portail") {
        search_unites_liees(case_tableau);
        if (afficher_facturation === false) {
            return false;
        }
    }
    // Si mode pointeuse, on affiche un loader
    if (mode === "pointeuse") {
        box = bootbox.dialog({
            message: "<p class='text-center mb-0'><i class='fa fa-spin fa-cog margin-r-5'></i> Veuillez patienter...</p>",
            closeButton: false, animate: false, centerVertical: true, size: "small",
        });
    }

    afficher_loader_facturation(true);
    cases_touchees.push(case_tableau.key);
    clearTimeout(chrono);
    chrono = setTimeout(function () {
        ajax_facturer(cases_touchees);
        cases_touchees = [];
    }, 1000);
};


function get_donnees_for_facturation(keys_cases_touchees) {
    // Mémorise toutes les conso
    var dict_conso_facturation = {};
    $.each(dict_cases, function (key, case_tableau) {
        if (!(case_tableau.type_case === "evenement") && !(case_tableau.type_case === "multihoraires") && case_tableau.consommations.length > 0) {
            var key = case_tableau.date + "_" + case_tableau.inscription;
            if (!(key in dict_conso_facturation)) {
                dict_conso_facturation[key] = []
            };
            for (var conso of case_tableau.consommations) {
                conso["key_case"] = case_tableau.key;
                if (conso.evenement) {
                    conso["nom_evenement"] = dict_cases[case_tableau.key].evenement.nom;
                    conso["description_evenement"] = dict_cases[case_tableau.key].evenement.description;
                }
                dict_conso_facturation[key].push(conso);
            };
        };
    });
    var dict_cases_touchees_temp = {};
    var liste_keys_pour_prestations = [];
    for (var key of keys_cases_touchees) {
        dict_cases_touchees_temp[key] = dict_cases[key];
        liste_keys_pour_prestations.push(dict_cases[key].date + "_" + dict_cases[key].famille + "_" + dict_cases[key].individu+ "_" + dict_cases[key].activite);
    };
    var dict_prestations_temp = {};
    var aides_temp = [];
    $.each(dict_prestations, function (idprestation, dict_prestation) {
        // Mémorisation des prestations de la ligne uniquement
        var key = dict_prestation.date + "_" + dict_prestation.famille + "_" + dict_prestation.individu + "_" + dict_prestation.activite;
        if (liste_keys_pour_prestations.includes(key) || dict_prestation.forfait_date_debut) {
            dict_prestations_temp[idprestation] = dict_prestation;
        }
        // Mémorisation de toutes les aides
        for (var dict_aide of dict_prestation.aides) {
            aides_temp.push({"idprestation": parseInt(idprestation), "famille": dict_prestation["famille"], "individu": dict_prestation["individu"],
                            "date": dict_prestation["date"], "montant": dict_aide["montant"], "aide": dict_aide["aide"]});
        };
    });
    return {
        consommations: dict_conso_facturation,
        prestations: dict_prestations_temp,
        dict_aides: aides_temp,
        cases_touchees: dict_cases_touchees_temp,
        liste_vacances: liste_vacances,
        dict_suppressions: dict_suppressions,
        mode: mode,
        // dict_conso: dict_conso,
    };
};

// Facturation
function ajax_facturer(cases_touchees_temp) {
    // Appel ajax
    $.ajaxQueue({
        type: "POST",
        url: url_facturer,
        data: {
            keys_cases_touchees : cases_touchees_temp,
            csrfmiddlewaretoken: csrf_token
            },
        datatype: "json",
        success: function(data){
            // Envoie les nouvelles prestations au dict_prestations
            $.each(data.nouvelles_prestations, function (idprestation, dict_prestation) {
                dict_prestations[idprestation] = dict_prestation;
            });

            for (var idprestation of data.anciennes_prestations) {
                if (!(idprestation.toString().includes("-"))) {
                    dict_suppressions.prestations.push(parseInt(idprestation));
                }
                delete dict_prestations[idprestation];
            }

            // Met à jour les conso
            $.each(data.modifications_idprestation, function (key, idprestation) {
                dict_cases[key].set_prestation(idprestation);
            });

            if (data.modifications_idconso) {
                $.each(data.modifications_idconso, function (ancien_idconso, nouvel_idconso) {
                    $.each(dict_cases, function(key_case, valeurs) {
                        for (var conso of valeurs.consommations) {
                            if (conso.pk === ancien_idconso) {
                                dict_cases[key_case].set_idconso(nouvel_idconso);
                            };
                        };
                    });
                });
            };

            // Messages
            if (data.messages) {
                for (var message of data.messages) {
                    if (message[0] === "info") {toastr.info(message[1])}
                    if (message[0] === "erreur") {toastr.error(message[1])}
                }
            }

            // Si mode pointeuse, on désactive le dirty de toutes les consommations
            if (mode === 'pointeuse') {
                $.each(dict_cases, function (key, case_tableau) {
                    try {dict_cases[key].set_dirty(false)} catch {};
                })
                dict_suppressions = {"consommations": [], "prestations": [], "memos": []};
            }

            // MAJ du box facturation
            maj_box_facturation();

            if (data.tout_recalculer) {
                tout_recalculer();
                maj_box_forfaits();
            }

            // Masque loader du box facturation
            afficher_loader_facturation(false);

            if (mode === "pointeuse") {
                box.modal("hide");
            };

            // Si mode portail, on déclenche le submit
            if ((mode === "portail") && (afficher_facturation === false))  {
                $('#form-maj').submit();
            };

        },
        error: function(data) {
            console.log("Erreur de facturation !");
            if (mode === "portail" || mode === "pointeuse") {
                box.modal("hide");
            };
        }
    });
};

function maj_box_facturation() {
    // Préparation des données
    var dict_prestations_temp = {};
    $.each(dict_prestations, function (idprestation, prestation) {
        if (prestation.activite === selection_activite) {
            var key = prestation.individu + "_" + prestation.famille;
            if (!(key in dict_prestations_temp)) {dict_prestations_temp[key] = {}};
            if (!(prestation.date in dict_prestations_temp[key])) {dict_prestations_temp[key][prestation.date] = []};
            dict_prestations_temp[key][prestation.date].push(idprestation);
        };
    });

    var afficher_quantites = dict_options.afficher_quantites;

    // Dessine la table facturation
    var total_individus = {'montant': 0, 'quantite': 0};
    for (var key_individu of liste_key_individus) {
        var total_individu = {'montant': 0, 'quantite': 0};
        var html = "";
        var key = key_individu[0] + '_' + key_individu[1]
        if (key in dict_prestations_temp) {
            var dict_dates = dict_prestations_temp[key];
            for (var date of Object.keys(dict_dates).sort()) {
                // Vérifie que la date est comprise dans la période affichée
                var valide = false;
                for (var periode of periode_json.periodes) {
                    var date_min = periode.split(";")[0];
                    var date_max = periode.split(";")[1];
                    if ((date >= date_min) && (date <= date_max)) {valide = true};
                }
                // Affiche la date et la prestation
                if (valide === true) {
                    var datefr = new Date(date);
                    datefr = datefr.toLocaleDateString('fr-FR', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    });
                    if ((mode == "individu") || (mode == "portail")) {
                        html += "<tr><td class='date_prestation'>" + datefr + "</td><td class='montant_prestation'></td></tr>";
                    };
                    for (var idprestation of dict_dates[date].sort()) {
                        var dict_prestation = dict_prestations[idprestation];
                        var label = dict_prestation.label;
                        if (dict_prestation.aides.length > 0) {label += " <span class='exposant'>(Aide)</span>"};
                        html += "<tr class='ligne_prestation'><td class='label_prestation'>" + label + "</td><td class='montant_prestation'>" + dict_prestation.montant.toFixed(2) + " €";
                        if (afficher_quantites) {html += " (" + dict_prestation.quantite + ")"}
                        html += "</td></tr>";
                        total_individu['montant'] += dict_prestation.montant;
                        total_individu['quantite'] += dict_prestation.quantite;
                    };
                };
            };
        };
        $('#detail_facturation_individu_' + key_individu[0] + '_' + key_individu[1]).html(html);
        var texte = total_individu['montant'].toFixed(2) + " €";
        if (afficher_quantites) {texte += " (" + total_individu['quantite'] + ")"}
        $('#total_facturation_individu_' + key_individu[0] + '_' + key_individu[1]).html(texte);
        total_individus['montant'] += total_individu['montant'];
        total_individus['quantite'] += total_individu['quantite'];
    };
    var texte = total_individus['montant'].toFixed(2) + " €";
    if (afficher_quantites) {texte += " (" + total_individus['quantite'] + ")"}
    $('#total_facturation_individus').html(texte);
};

function tout_recalculer() {
    afficher_loader_facturation(true);
    var liste_temp = [];
    $.each(dict_cases, function (key, case_tableau) {
        var key_temp = case_tableau.date + "_" + case_tableau.inscription;
        if (!(liste_temp.includes(key_temp))) {
            cases_touchees.push(key);
            liste_temp.push(key_temp);
        };
    });
    ajax_facturer(cases_touchees);
};

// Impression du PDF des réservations
function impression_pdf(email=false) {
    var liste_conso_impression = [];
    var dict_prestations_impression = {}
    $("td[class*='ouvert']").each(function() {
        var case_tableau = dict_cases[$(this).attr('id')];
        for (var conso of case_tableau.consommations) {
            liste_conso_impression.push(conso);
            if (conso.prestation in dict_prestations) {
                dict_prestations_impression[conso.prestation] = dict_prestations[conso.prestation]
            };
        };
    });
    $.ajax({
        type: "POST",
        url: url_impression_pdf,
        data: {
            consommations: JSON.stringify(liste_conso_impression),
            prestations: JSON.stringify(dict_prestations_impression),
            idfamille: idfamille,
            csrfmiddlewaretoken: csrf_token,
        },
        datatype: "json",
        success: function(data){
            if (email) {
                envoyer_email(data);
            } else {
                charge_pdf(data);
            }
        },
        error: function(data) {
            toastr.error(data.responseJSON.erreur);
        }
    })
};


function appliquer_tarif_special(case_tableau, data, maj_facturation) {
    var liste_choix_tarifs = [];
    $.each(dict_tarifs_speciaux, function (idtarif, dict_tarif) {
        if ((dict_tarif.unites.indexOf(case_tableau.unite) !== -1) && (dict_tarif.categories_tarifs.indexOf(case_tableau.categorie_tarif) !== -1)) {
            for (var ligne of dict_tarif.lignes) {
                liste_choix_tarifs.push({
                    "text": ligne.montant.toFixed(2) + (ligne.label ? " € : " + ligne.label: ""),
                    "value": "choix_tarif=" + ligne.idligne
                })
            }
        }
    })
    if (liste_choix_tarifs.length) {
        var dlg = bootbox.prompt({
            title: "Montant au choix",
            message: "<b>Quel montant souhaitez-vous appliquer ?<br><br>",
            inputType: "radio",
            locale: "custom",
            inputOptions: liste_choix_tarifs,
            buttons: {
                cancel: {
                    label: "<i class='fa fa-times'></i> Annuler",
                    className: "btn-danger"
                },
                confirm: {
                    label: "<i class='fa fa-check'></i> Valider"
                }
            },
            callback: function (choix_tarif) {
                if (choix_tarif) {
                    case_tableau.creer_conso(data, maj_facturation, choix_tarif)
                }
            }
        })
        return true
    }
    return false
}
