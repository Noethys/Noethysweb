
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
var dict_valeurs = {};
var touche_clavier = null;
var pressepapiers = {};
var dirty = false;
var mode_impression_pdf_email = null;


class Case_base {
    constructor(data) {
        this.categorie = null;
        this.key = null;
        this.date = null;
        this.colonne = null;
        this.valeur = null;
        this.texte = null;
        this.suggestion = null;
        if (data) {Object.assign(this, data)};
    };

    importe_data(data, actualiser_totaux=true) {
        Object.assign(this, data);
        this.maj_affichage();
        if (actualiser_totaux) {
            calculer_totaux();
            pressepapiers[this.colonne] = {valeur: this.valeur, texte: this.texte};
            dirty = true;
        }
    }

    copier() {
        // Si une valeur ou texte existe dans le pressepapiers, on la reproduit
        if (this.colonne in pressepapiers) {
            this.importe_data({valeur: pressepapiers[this.colonne].valeur, texte: pressepapiers[this.colonne].texte});
            return true;
        };
    }

}


class Case_numerique_conso extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = false;
        // Dessine la case
        $("#" + this.key).html("<span class='valeur numerique'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .valeur").html(this.valeur);
    };
}


class Case_numerique_suggestion extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = true;
        // Dessine la case
        $("#" + this.key).html("<span class='valeur numerique'></span><span class='suggestion' title='Valeur suggérée'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .valeur").html(this.valeur);
        $("#" + this.key + " .suggestion").html(this.suggestion);
    };

    modifier() {
        $('#saisie_quantite').val(this.valeur);
        $('#saisie_quantite_suggestion').html(this.suggestion);
        $('#saisie_quantite_key').val(this.key);
        $('#modal_saisir_quantite').modal('show');
    };
}

class Case_numerique_libre extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = true;
        // Dessine la case
        $("#" + this.key).html("<span class='valeur numerique'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .valeur").html(this.valeur);
    };

    modifier() {
        $('#saisie_quantite').val(this.valeur);
        $('#saisie_quantite_suggestion').html("");
        $('#saisie_quantite_key').val(this.key);
        $('#modal_saisir_quantite').modal('show');
    };
}


class Case_numerique_total extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = false;
        // Dessine la case
        $("#" + this.key).html("<span class='valeur numerique'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .valeur").html(this.valeur);
    };
}


class Case_texte_libre extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = true;
        // Dessine la case
        $("#" + this.key).html("<span class='texte'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .texte").html(this.texte);
    };

    modifier() {
        $('#saisie_texte').val(this.texte);
        $('#saisie_texte_key').val(this.key);
        $('#modal_saisir_texte').modal('show');
    };
}


class Case_texte_infos extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = false;
        // Dessine la case
        $("#" + this.key).html("<span class='texte'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .texte").html(this.texte);
    };
}


class Case_total extends Case_base {
    constructor(data) {
        super(data);
        this.modification_autorisee = false;
        // Dessine la case
        $("#" + this.key).html("<span class='valeur'></span>");
    };

    maj_affichage() {
        $("#" + this.key + " .valeur").html(this.valeur);
    };
}


$(function () {
    // Mémorise la touche enfoncée
    $(window).keydown(function (evt) {
        touche_clavier = evt.which
    })
        .keyup(function (evt) {
            touche_clavier = null
        });

    // Clic sur les cases
    var isMouseDown = false, ancienne_case;
    $(document).on('mousedown', ".table td", function (e) {
        // Si clic gauche de la souris
        if (e.which === 1) {
            isMouseDown = true;
            var case_tableau = dict_cases[$(this).attr('id')];
            action_sur_clic(case_tableau);
            return false;
        }
    });
    $(document).on('mouseover', ".table td", function (e) {
        var case_tableau = dict_cases[$(this).attr('id')];
        if (isMouseDown && ancienne_case !== case_tableau) {
            action_sur_clic(case_tableau);
        }
        ancienne_case = case_tableau;
    });
    $(document).mouseup(function () {
        isMouseDown = false;
    });

    function action_sur_clic(case_tableau) {
        if (case_tableau.modification_autorisee) {
            if (touche_clavier === 67) {
                case_tableau.copier()
            } else {
                case_tableau.modifier();
            }
        }
    };
})


// Actions au chargement de la page
$(document).ready(function() {

    // Importe les valeurs dans les cases
    $.each(dict_valeurs, function (key, valeur) {
        if (key in dict_cases) {
            dict_cases[key].importe_data(valeur, actualiser_totaux=false);
        };
    });
    calculer_totaux();

    // Envoi des paramètres au format json vers le form de maj
    $("#form-maj").on('submit', function(event) {
        $('#donnees').val(JSON.stringify(get_donnees()));
        return true;
    });

    $("#bouton_appliquer_suggestions").on('click', function(e) {
        $.each(dict_cases, function (key, case_tableau) {
            if (case_tableau.categorie === "numerique_suggestion") {
                case_tableau.importe_data({valeur: case_tableau.suggestion}, actualiser_totaux=false)
            }
        });
        calculer_totaux();
    })

});


function verification_dirty(url) {
    if (dirty) {
        var box = bootbox.dialog({
            title: "Modifications",
            message: "Attention, les modifications enregistrées seront perdues. Souhaitez-vous enregistrer maintenant ?",
            buttons: {
                ok: {
                    label: "<i class='fa fa-check'></i> Oui",
                    className: 'btn-primary',
                    callback: function () {
                        $('#form-maj').submit();
                    }
                },
                cancel: {
                    label: "<i class='fa fa-ban'></i> Non",
                    className: 'btn-danger',
                    callback: function () {
                        window.location.href = url;
                    }
                }
            }
        });
    } else {
        window.location.href = url;
    }
}


function get_donnees() {
    var dict_donnees = {};
    $.each(dict_cases, function (key, case_tableau) {
        dict_donnees[key] = {
            categorie: case_tableau.categorie,
            date: case_tableau.date,
            colonne: case_tableau.colonne,
            valeur: case_tableau.valeur,
            texte: case_tableau.texte
        };
    });
    return dict_donnees
}


function calculer_totaux() {
    var dict_totaux = {};
    $.each(dict_cases, function (key, case_tableau) {
        // Colonnes de type total
        if (case_tableau.categorie === "numerique_total") {
            var total = 0;
            for (var idcolonneassociee of dict_colonnes_total[case_tableau.colonne]) {
                key_colonne_associee = case_tableau.date + "_" + idcolonneassociee
                total += dict_cases[key_colonne_associee].valeur
            }
            case_tableau.importe_data({valeur: total}, actualiser_totaux=false);
        }
        // Lignes de type total
        if (case_tableau.categorie.indexOf("numerique") !== -1) {
            if (!(case_tableau.colonne in dict_totaux)) {
                dict_totaux[case_tableau.colonne] = 0;
            }
            dict_totaux[case_tableau.colonne] += case_tableau.valeur;
        }
    })
    $.each(dict_totaux, function (idcolonne, total) {
        dict_cases["total_" + idcolonne].importe_data({valeur: total}, actualiser_totaux=false);
    })
}

// Impression du PDF
function impression_pdf(email=false) {
    mode_impression_pdf_email = email;
    $("#modal_options_impression").modal("show");
};

function run_impression_pdf() {
    $.ajax({
        type: "POST",
        url: url_impression_pdf,
        data: {
            donnees: JSON.stringify(get_donnees()),
            options_impression: JSON.stringify($("#form_commandes_options_impression").serializeObject()),
            idcommande: idcommande,
            email: mode_impression_pdf_email,
            csrfmiddlewaretoken: csrf_token,
        },
        datatype: "json",
        success: function(data){
            if (mode_impression_pdf_email) {
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
